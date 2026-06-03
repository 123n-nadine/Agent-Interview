from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session
from ..database import get_db
from ..models import InterviewSession, Question, Answer, CheatLog, Job
from ..schemas import InterviewStart, InterviewResponse, QuestionResponse, AnswerSubmit, AnswerResponse, CheatEvent
from ..services import ai_service
import asyncio
import logging
import re as _re

logger = logging.getLogger("interviews")

router = APIRouter()

# ─────────────────────────────────────────
# Gibberish Detection
# ─────────────────────────────────────────
_GIBBERISH_SEQUENCES = {
    "asdf", "qwer", "zxcv", "dwdw", "ksw", "kkw", "dsd", "dsfdfdf",
    "ef", "lol", "idk", "xyz", "abc", "kkk", "kk", "jjj", "jj",
    "aaa", "bbb", "ccc", "fff", "ggg", "hhh", "mmm", "nnn",
    "ppp", "rrr", "sss", "ttt", "uuu", "vvv", "www", "zzz",
    "test", "na", "n/a", "idk", "none", "nope", "ok", "okay",
}
_MIN_REAL_WORDS = 3


def _is_gibberish(answer: str) -> bool:
    """Detect nonsense / random / near-empty answers."""
    stripped = answer.strip()
    if not stripped:
        return True
    words = stripped.split()
    # If very short AND matches a known nonsense pattern
    if len(words) < _MIN_REAL_WORDS and len(stripped) < 20:
        if stripped.lower() in _GIBBERISH_SEQUENCES:
            return True
        # Single short all-alpha word with repetitive characters (e.g. "kkkkk")
        if _re.match(r'^([a-z])\1{2,}$', stripped.lower()):
            return True
        # Pure repeating pairs like "kk", "jj", "aa"
        if _re.match(r'^[a-z]{1,2}$', stripped.lower()):
            return True
    # All commas / special characters (e.g. ",,,,,")
    if _re.match(r'^[^a-zA-Z0-9]+$', stripped):
        return True
    return False


def _weighted_score(metrics: dict) -> float:
    """Weighted score: Correctness=45%, TechDepth=30%, Reasoning=15%, Clarity=10%."""
    return (
        metrics.get("correctness", 0) * 0.45 +
        metrics.get("technical_depth", 0) * 0.30 +
        metrics.get("reasoning", 0) * 0.15 +
        metrics.get("clarity", 0) * 0.10
    )


# ─────────────────────────────────────────
# 1. Start Interview
# ─────────────────────────────────────────
@router.post("/start", response_model=InterviewResponse)
async def start_interview(payload: InterviewStart, db: Session = Depends(get_db)):
    job = db.query(Job).filter(Job.id == payload.job_id).first()
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")

    interview = InterviewSession(
        job_id=job.id,
        candidate_name=payload.candidate_name,
        candidate_email=payload.candidate_email
    )
    db.add(interview)
    db.commit()
    db.refresh(interview)
    logger.info("[START] Interview #%d started for '%s' by '%s'",
                interview.id, job.title, payload.candidate_name)
    return interview


# ─────────────────────────────────────────
# 2. Get Next Question
# ─────────────────────────────────────────
@router.get("/{interview_id}/question", response_model=QuestionResponse)
async def get_next_question(interview_id: int, db: Session = Depends(get_db)):
    interview = db.query(InterviewSession).filter(InterviewSession.id == interview_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    # Return existing unanswered question first
    unanswered = db.query(Question).filter(
        Question.interview_id == interview_id,
        ~Question.answer.has()
    ).first()
    if unanswered:
        return unanswered

    count = db.query(Question).filter(Question.interview_id == interview_id).count()
    if count >= 6:
        raise HTTPException(status_code=400, detail="Interview already has 6 questions")

    types = ["mcq", "mcq", "short_qa", "technical", "scenario", "coding"]
    diffs = ["easy",  "medium", "medium",   "medium",    "hard",     "hard"]

    q_type = types[count]
    diff   = diffs[count]

    new_q = Question(
        interview_id=interview_id,
        question_type=q_type,
        content="",
        difficulty=diff
    )

    if q_type == "mcq":
        previous_qs = [q.content for q in interview.questions if q.content]
        logger.info("[MCQ] Generating MCQ #%d for interview #%d...", count + 1, interview_id)
        mcq_data = await asyncio.to_thread(
            ai_service.generate_mcq_question,
            interview.job.title, interview.job.skills, previous_qs, diff
        )
        new_q.content        = mcq_data.get("question", "")
        new_q.options        = mcq_data.get("options", [])
        new_q.correct_answer = mcq_data.get("correct_answer", "")
        logger.info("[MCQ] Generated: '%s...' | correct=%s",
                    new_q.content[:60], new_q.correct_answer)

    db.add(new_q)
    db.commit()
    db.refresh(new_q)
    logger.info("[QUESTION] Created Q#%d (%s, %s) for interview #%d",
                new_q.id, q_type, diff, interview_id)
    return new_q


# ─────────────────────────────────────────
# 3. Stream Question Content via LLM
# ─────────────────────────────────────────
@router.get("/{interview_id}/question/{question_id}/stream")
async def stream_question(interview_id: int, question_id: int, db: Session = Depends(get_db)):
    interview = db.query(InterviewSession).filter(InterviewSession.id == interview_id).first()
    question  = db.query(Question).filter(Question.id == question_id).first()
    if not interview or not question:
        raise HTTPException(status_code=404, detail="Not found")

    previous_qs = [q.content for q in interview.questions if q.content and q.id != question_id]

    async def generator():
        full_content = ""
        for chunk in ai_service.stream_generate_question(
            interview.job.title, interview.job.skills,
            previous_qs, question.question_type, question.difficulty
        ):
            full_content += chunk
            yield chunk
            await asyncio.sleep(0)
        question.content = full_content.strip()
        db.commit()
        logger.info("[STREAM] Q#%d content stored (%d chars)", question_id, len(question.content))

    return StreamingResponse(generator(), media_type="text/plain")


# ─────────────────────────────────────────
# 4. Submit Answer
# ─────────────────────────────────────────
@router.post("/{interview_id}/answer", response_model=AnswerResponse)
async def submit_answer(interview_id: int, payload: AnswerSubmit, db: Session = Depends(get_db)):
    question = db.query(Question).filter(
        Question.id == payload.question_id,
        Question.interview_id == interview_id
    ).first()
    if not question:
        raise HTTPException(status_code=404, detail="Question not found")
    if db.query(Answer).filter(Answer.question_id == question.id).first():
        raise HTTPException(status_code=400, detail="Answer already submitted for this question")
    if not payload.answer or not payload.answer.strip():
        raise HTTPException(status_code=422, detail="Answer cannot be empty")

    answer = Answer(
        question_id=question.id,
        content=payload.answer,
        time_taken_seconds=payload.time_taken_seconds,
        score=0,
        feedback="",
        ai_probability=0.0
    )
    db.add(answer)
    db.commit()

    answered_count = db.query(Answer).join(Question).filter(
        Question.interview_id == interview_id
    ).count()
    is_complete = answered_count >= 6

    if is_complete:
        interview = db.query(InterviewSession).filter(InterviewSession.id == interview_id).first()
        interview.status = "completed"
        db.commit()
        logger.info("[COMPLETE] Interview #%d marked complete after %d answers.", interview_id, answered_count)

    logger.info("[ANSWER] Q#%d in interview #%d | time=%ds",
                question.id, interview_id, payload.time_taken_seconds)
    return {
        "status": "recorded",
        "evaluation": {
            "score": 0,
            "feedback": "Answer stored. Evaluation runs at end of interview.",
            "ai_probability": 0.0
        },
        "is_complete": is_complete
    }


# ─────────────────────────────────────────
# 5. Anti-Cheat Tracking
# ─────────────────────────────────────────
@router.post("/{interview_id}/track")
async def track_event(interview_id: int, payload: CheatEvent, db: Session = Depends(get_db)):
    interview = db.query(InterviewSession).filter(InterviewSession.id == interview_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    log = CheatLog(interview_id=interview_id, event_type=payload.event_type, details=payload.details)
    db.add(log)

    weight = 5 if payload.event_type == "tab_switch" else 10 if payload.event_type == "copy_paste" else 2
    interview.suspicion_score += weight
    db.commit()
    logger.info("[CHEAT] Event '%s' logged for interview #%d. Suspicion=%d",
                payload.event_type, interview_id, interview.suspicion_score)
    return {"status": "logged"}


# ─────────────────────────────────────────
# 6. Generate Final Report
# ─────────────────────────────────────────
@router.get("/{interview_id}/report")
async def get_report(interview_id: int, db: Session = Depends(get_db)):
    interview = db.query(InterviewSession).filter(InterviewSession.id == interview_id).first()
    if not interview:
        raise HTTPException(status_code=404, detail="Interview not found")

    all_questions = sorted(interview.questions, key=lambda q: q.id)
    answered_count = sum(
        1 for q in all_questions if q.answer and q.answer.content and q.answer.content.strip()
    )
    logger.info("[REPORT] Interview #%d: %d answered questions found.", interview_id, answered_count)

    # Return empty report if nothing submitted yet
    if answered_count == 0 and not interview.hiring_decision:
        return {
            "interview_id": interview.id,
            "candidate_name": interview.candidate_name,
            "final_score": 0.0,
            "hiring_decision": "Reject",
            "ai_probability_avg": 0.0,
            "suspicion_score": interview.suspicion_score,
            "skill_gaps": {"missing_skills": [], "weak_areas": [], "recommended_topics": []},
            "question_evaluations": [],
            "feedback": "No answers were submitted.",
            "answers_evaluated": 0
        }

    # Only run evaluation once
    if not interview.hiring_decision:
        logger.info("[REPORT] Running evaluation for interview #%d...", interview_id)

        # ── Step 1: Deterministic MCQ grading ──────────────────────────────
        mcq_grades = {}
        for q in all_questions:
            if q.question_type == "mcq":
                user_ans = (q.answer.content.strip() if q.answer and q.answer.content else "").lower()
                correct  = (q.correct_answer or "").strip().lower()
                is_correct = False
                if user_ans and correct:
                    if user_ans == correct:
                        is_correct = True
                    elif correct.startswith(user_ans):
                        is_correct = True
                    elif len(correct) > 0 and len(user_ans) > 0 and correct[0] == user_ans[0]:
                        is_correct = True
                mcq_grades[q.id] = {"is_correct": is_correct}
                logger.info("[MCQ] Q#%d: user='%s' | correct='%s' | ok=%s",
                            q.id, user_ans, correct, is_correct)

        # ── Step 2: Collect non-MCQ Q&A for AI evaluation ──────────────────
        qa_pairs_for_ai = []
        for q in all_questions:
            if q.question_type != "mcq":
                ans_text = q.answer.content.strip() if q.answer and q.answer.content else ""
                qa_pairs_for_ai.append({
                    "q": q.content or "(question text unavailable)",
                    "a": ans_text,
                    "q_id": q.id,
                    "q_type": q.question_type
                })

        # ── Step 3: AI Evaluation (each answer individually, in a thread) ──
        ai_evals_by_qid = {}
        if qa_pairs_for_ai:
            # Pass q_type so evaluate_single_answer can tailor the ideal-answer prompt
            ai_payload = [{"q": x["q"], "a": x["a"], "q_type": x["q_type"]} for x in qa_pairs_for_ai]
            report_data = await asyncio.to_thread(
                ai_service.batch_evaluate_and_report,
                interview.job.title,
                interview.job.skills,
                ai_payload
            )
            ai_question_evals = report_data.get("question_evaluations", [])
            for i, item in enumerate(qa_pairs_for_ai):
                if i < len(ai_question_evals):
                    ai_evals_by_qid[item["q_id"]] = ai_question_evals[i]
        else:
            report_data = {"skill_gaps": {}, "feedback": "MCQ-only session."}

        # ── Step 4: Build per-question result for all 6 questions ──────────
        final_question_evaluations = []
        question_weighted_scores   = []
        gibberish_count            = 0
        ai_eval_failed_count       = 0

        for q in all_questions:
            user_ans = q.answer.content.strip() if q.answer and q.answer.content else ""
            q_text   = q.content or "(question text unavailable)"

            if q.question_type == "mcq":
                is_correct    = mcq_grades.get(q.id, {}).get("is_correct", False)
                correct_label = q.correct_answer or "N/A"
                score_val = 100 if is_correct else 0
                metrics  = {
                    "correctness":     score_val,
                    "reasoning":       score_val,
                    "clarity":         100 if user_ans else 0,
                    "technical_depth": score_val
                }
                gap      = "Correct answer selected." if is_correct else f"Incorrect. Correct answer: {correct_label}"
                feedback = "Correct MCQ answer!" if is_correct else f"Incorrect. The correct answer was: {correct_label}"
                ideal    = correct_label
                w_score  = _weighted_score(metrics)

            else:
                ai_eval = ai_evals_by_qid.get(q.id)

                # Ensure ai_eval is a proper dict
                if not isinstance(ai_eval, dict):
                    ai_eval = None

                is_gibberish = _is_gibberish(user_ans) if user_ans else True

                if not user_ans:
                    metrics  = {"correctness": 0, "reasoning": 0, "clarity": 0, "technical_depth": 0}
                    gap      = "No answer was submitted for this question."
                    feedback = "No answer submitted."
                    ideal    = ai_eval.get("ideal_answer", "") if ai_eval else ""
                    w_score  = 0.0

                elif is_gibberish:
                    gibberish_count += 1
                    logger.warning("[GIBBERISH] Q#%d: answer appears to be gibberish.", q.id)
                    metrics  = {"correctness": 0, "reasoning": 0, "clarity": 0, "technical_depth": 0}
                    gap      = "Answer was irrelevant, random, or gibberish."
                    feedback = "Answer detected as irrelevant or gibberish. Score set to 0."
                    ideal    = ai_eval.get("ideal_answer", "") if ai_eval else ""
                    w_score  = 0.0

                else:
                    # Check if AI metrics are available
                    ai_metrics = ai_eval.get("metrics") if ai_eval else None

                    if ai_eval and isinstance(ai_metrics, dict):
                        # Successful AI evaluation
                        metrics = {
                            "correctness":     ai_metrics.get("correctness", 0),
                            "reasoning":       ai_metrics.get("reasoning", 0),
                            "clarity":         ai_metrics.get("clarity", 0),
                            "technical_depth": ai_metrics.get("technical_depth", 0),
                        }
                        gap      = ai_eval.get("gap_analysis", "")
                        feedback = ai_eval.get("feedback", "")
                        ideal    = ai_eval.get("ideal_answer", "")
                        w_score  = _weighted_score(metrics)
                    else:
                        # AI evaluation failed for this question
                        # Use neutral score (50) so we don't unfairly penalize the candidate
                        ai_eval_failed_count += 1
                        logger.warning("[EVAL_FAIL] Q#%d: AI evaluation failed; using neutral score.", q.id)
                        metrics  = {"correctness": 50, "reasoning": 50, "clarity": 50, "technical_depth": 50}
                        gap      = "Automated evaluation could not be completed. Manual review recommended."
                        feedback = "Evaluation failed for this question. Manual review required."
                        ideal    = ""
                        w_score  = _weighted_score(metrics)

            question_weighted_scores.append(w_score)
            final_question_evaluations.append({
                "question":      q_text,
                "question_type": q.question_type,
                "user_answer":   user_ans or "(no answer submitted)",
                "ideal_answer":  ideal,
                "gap_analysis":  gap,
                "metrics":       metrics,
                "feedback":      feedback,
            })

        # ── Step 5: Compute final score ─────────────────────────────────────
        raw_final_score = (
            sum(question_weighted_scores) / len(question_weighted_scores)
            if question_weighted_scores else 0.0
        )

        # Collect only REAL correctness values (exclude neutral fallbacks)
        real_correctness_vals = []
        for q, ev in zip(all_questions, final_question_evaluations):
            m = ev["metrics"]
            # Only count scores that were genuinely evaluated (not neutral fallback 50s)
            if q.question_type == "mcq" or (not _is_gibberish(q.answer.content.strip() if q.answer and q.answer.content else "")
                                            and ai_evals_by_qid.get(q.id) and isinstance(ai_evals_by_qid[q.id].get("metrics"), dict)):
                real_correctness_vals.append(m.get("correctness", 0))

        avg_correctness = (
            sum(real_correctness_vals) / len(real_correctness_vals)
            if real_correctness_vals else 50.0  # Default neutral when no real evals
        )

        # ── Step 6: Safety rules ────────────────────────────────────────────
        if gibberish_count >= 2:
            final_score      = min(round(raw_final_score, 1), 39.9)
            hiring_decision  = "Reject"
            logger.warning("[SAFETY] Interview #%d: %d gibberish answers. Capped at %.1f. Decision: Reject.",
                           interview_id, gibberish_count, final_score)
        elif len(real_correctness_vals) > 0 and avg_correctness < 40:
            # Only apply this rule when we have ACTUAL evaluated scores (not fallbacks)
            final_score     = min(round(raw_final_score, 1), 49.9)
            hiring_decision = "Reject"
            logger.warning("[SAFETY] Interview #%d: avg correctness=%.1f%% < 40%%. Decision: Reject.",
                           interview_id, avg_correctness)
        else:
            final_score = round(raw_final_score, 1)
            if final_score >= 75:
                hiring_decision = "Hire"
            elif final_score >= 60:
                hiring_decision = "Review Required"
            else:
                hiring_decision = "Reject"

        logger.info("[REPORT] Interview #%d: raw=%.1f | final=%s | decision=%s | gibberish=%d | eval_failed=%d",
                    interview_id, raw_final_score, final_score, hiring_decision, gibberish_count, ai_eval_failed_count)

        # ── Persist ─────────────────────────────────────────────────────────
        # Derive skill_gaps and feedback from the FINAL evaluations (post MCQ + gibberish overrides)
        # so Areas for Improvement and Overall Summary always match the actual displayed scores.
        final_skill_gaps, feedback = ai_service.derive_final_report_summary(
            final_score, final_question_evaluations, interview.job.skills
        )

        interview.final_score           = final_score
        interview.ai_probability_avg    = 0.0
        interview.hiring_decision       = hiring_decision
        interview.skill_gaps            = final_skill_gaps
        interview.question_evaluations  = final_question_evaluations
        db.commit()
        db.refresh(interview)

    else:
        feedback = "Report already generated."
        logger.info("[REPORT] Interview #%d: returning cached report.", interview_id)

    return {
        "interview_id":         interview.id,
        "candidate_name":       interview.candidate_name,
        "final_score":          interview.final_score,
        "hiring_decision":      interview.hiring_decision,
        "ai_probability_avg":   interview.ai_probability_avg,
        "suspicion_score":      interview.suspicion_score,
        "skill_gaps":           interview.skill_gaps or {"missing_skills": [], "weak_areas": [], "recommended_topics": []},
        "question_evaluations": interview.question_evaluations or [],
        "feedback":             feedback,
        "answers_evaluated":    answered_count,
    }
