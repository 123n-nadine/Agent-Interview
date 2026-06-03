import ollama
import json
import re
import os
import logging

logger = logging.getLogger("ai_service")

OLLAMA_MODEL_FAST = os.getenv("OLLAMA_MODEL_FAST", "qwen2.5:1.5b")
OLLAMA_MODEL_EVAL = os.getenv("OLLAMA_MODEL_EVAL", "qwen2.5:1.5b")


def clean_json_response(response_text: str) -> dict:
    """Robustly extract JSON from a model response using multiple strategies."""
    if not response_text:
        return {}

    # Strategy 1: Direct parse
    try:
        return json.loads(response_text)
    except Exception:
        pass

    # Strategy 2: Extract from markdown code block ```json ... ```
    try:
        match = re.search(r'```(?:json)?\s*([\s\S]*?)\s*```', response_text)
        if match:
            return json.loads(match.group(1))
    except Exception:
        pass

    # Strategy 3: Find first complete {...} block
    try:
        match = re.search(r'\{[\s\S]*\}', response_text)
        if match:
            return json.loads(match.group(0))
    except Exception:
        pass

    logger.warning("Could not parse JSON from model response (first 200 chars): %s",
                   response_text[:200].encode('ascii', errors='replace').decode('ascii'))
    return {}


# ─────────────────────────────────────────
# Question Streaming (for non-MCQ questions)
# ─────────────────────────────────────────
def stream_generate_question(
    job_title: str, skills: list, previous_questions: list,
    q_type: str = "technical", difficulty: str = "medium"
):
    type_instructions = {
        "short_qa":  "Generate a short question requiring a concise explanation.",
        "technical": "Generate a deep conceptual technical question.",
        "scenario":  "Generate a realistic scenario-based question for a real-world situation. "
                     "Start with 'You are a...' to set the scene.",
        "coding":    "Generate a coding/algorithm problem. Keep it brief but challenging.",
        "reasoning": "Generate a logical reasoning or architecture design question.",
    }
    instruction = type_instructions.get(q_type, type_instructions["technical"])

    prompt = f"""You are an expert technical interviewer for a {job_title} role.
Required skills: {', '.join(skills)}.
Previously asked (DO NOT repeat): {', '.join(previous_questions[:3]) if previous_questions else 'None'}.

Task: {instruction}
Difficulty: {difficulty.upper()}

Respond ONLY with the raw question text. No quotes, no markdown, no filler."""

    try:
        stream = ollama.chat(
            model=OLLAMA_MODEL_FAST,
            messages=[
                {'role': 'system', 'content': 'Output only the raw question text. No preamble.'},
                {'role': 'user',   'content': prompt}
            ],
            stream=True
        )
        for chunk in stream:
            yield chunk['message']['content']
    except Exception as e:
        logger.error("Ollama stream_generate_question failed: %s", str(e))
        skill = skills[0] if skills else 'software development'
        yield f"Describe your hands-on experience with {skill} and a challenge you overcame."


# ─────────────────────────────────────────
# MCQ Generation
# ─────────────────────────────────────────
def generate_mcq_question(
    job_title: str, skills: list, previous_questions: list, difficulty: str = "easy"
) -> dict:
    prev = ', '.join(previous_questions[:3]) if previous_questions else 'None'
    prompt = f"""You are a {job_title} technical interviewer.
Skills required: {', '.join(skills)}.
Previously asked (DO NOT repeat these concepts): {prev}.

Generate ONE unique Multiple Choice Question testing foundational knowledge.
Difficulty: {difficulty.upper()}

Return a JSON object with these fields:
- question: the question text
- options: an array of exactly 4 strings, each starting with A), B), C), or D)
- correct_answer: one of the option strings (the correct one)

JSON format:
{{"question":"Your question text","options":["A) Option one","B) Option two","C) Option three","D) Option four"],"correct_answer":"A) Option one"}}"""

    try:
        response = ollama.chat(
            model=OLLAMA_MODEL_FAST,
            format='json',
            messages=[
                {'role': 'system', 'content': 'You are a JSON-only API. Return only valid JSON.'},
                {'role': 'user',   'content': prompt}
            ]
        )
        result = clean_json_response(response['message']['content'])
        if result and "question" in result and "options" in result and "correct_answer" in result:
            # Validate options list has exactly 4 items
            if isinstance(result["options"], list) and len(result["options"]) == 4:
                return result
        raise ValueError("Invalid MCQ response structure")
    except Exception as e:
        logger.error("MCQ generation failed: %s", str(e))
        skill = skills[0] if skills else "Software Engineering"
        return {
            "question": f"Which of the following is a best practice in {skill}?",
            "options": [
                "A) Writing clean, documented, and modular code",
                "B) Hardcoding credentials directly in source code",
                "C) Avoiding version control systems entirely",
                "D) Skipping tests and deploying directly to production"
            ],
            "correct_answer": "A) Writing clean, documented, and modular code"
        }


# ─────────────────────────────────────────
# Single Answer Evaluation (core fix)
# ─────────────────────────────────────────
def evaluate_single_answer(job_title: str, question: str, answer: str, q_type: str = "technical") -> dict | None:
    """
    Evaluate ONE Q&A pair. Returns a dict with metrics + feedback,
    or None if the model completely fails (caller handles fallback).
    Evaluating one question at a time is far more reliable than batching
    with a small 1.5b model.
    """
    # Truncate to avoid overwhelming the small model
    q_short = question[:500]
    a_short = answer[:500] if answer else "(no answer provided)"

    # ── Call 1: Get numeric scores (fast, simple, very reliable) ──────────
    score_prompt = f"""You are a technical interviewer for a {job_title} role.

Question asked: {q_short}
Candidate's answer: {a_short}

Score the candidate's answer on each dimension from 0 to 100.
If the answer is gibberish, irrelevant, or blank, score all metrics 0.
If the answer is short but correct, still give high scores.

Return ONLY a JSON object with four integer fields:
{{"correctness": 80, "reasoning": 70, "clarity": 85, "technical_depth": 75}}"""

    def clamp(val):
        try:
            return max(0, min(100, int(val)))
        except Exception:
            return 0

    # ── Call 1: Numeric scores only (tiny JSON = fast and reliable) ───────
    try:
        resp1 = ollama.chat(
            model=OLLAMA_MODEL_EVAL,
            format='json',
            messages=[
                {'role': 'system', 'content': 'You are a JSON-only API. Return only valid JSON.'},
                {'role': 'user',   'content': score_prompt}
            ]
        )
        scores = clean_json_response(resp1['message']['content'])
        if not scores or 'correctness' not in scores:
            raise ValueError("Missing correctness field")
    except Exception as e:
        logger.error("Score evaluation failed for Q: %s", str(e))
        return None  # Cannot score = signal failure to caller

    correctness     = clamp(scores.get("correctness", 0))
    reasoning       = clamp(scores.get("reasoning", 0))
    clarity         = clamp(scores.get("clarity", 0))
    technical_depth = clamp(scores.get("technical_depth", 0))

    # ── Call 2: Text feedback only (separate call = no placeholder bug) ───
    # Instruction varies by question type so coding Qs get real code, not summaries
    if q_type == "coding":
        ideal_instruction = (
            "Write a complete, working code implementation for this problem. "
            "Include: the function signature, the full implementation logic, "
            "and a 1-2 sentence explanation of the approach. "
            "Use real code, not pseudocode or placeholders like '// Your code here'."
        )
    elif q_type == "scenario":
        ideal_instruction = (
            "Write a thorough scenario response (4-6 sentences) covering: "
            "the approach you would take, the technical decisions involved, "
            "potential trade-offs, and how you would validate the result."
        )
    elif q_type == "technical":
        ideal_instruction = (
            "Write a complete technical answer (4-6 sentences) covering: "
            "the core concept, how it works, why it matters, "
            "and at least one practical example or use case."
        )
    else:  # short_qa or anything else
        ideal_instruction = (
            "Write a comprehensive answer (3-5 sentences) covering "
            "all the important technical concepts and best practices relevant to this question."
        )

    text_prompt = f"""You are a {job_title} technical interviewer giving feedback.

Question: {q_short}
Candidate's Answer: {a_short}

Provide three things:
1. ideal_answer: {ideal_instruction}
2. gap_analysis: Explain specifically what the candidate's answer was missing or got wrong. Be concrete.
3. feedback: Give one specific, constructive sentence of feedback for the candidate.

Return ONLY a JSON object:
{{"ideal_answer": "Full answer text here", "gap_analysis": "Specific gaps here", "feedback": "One sentence here"}}"""

    ideal_answer = ""
    gap_analysis = ""
    feedback_text = ""
    try:
        resp2 = ollama.chat(
            model=OLLAMA_MODEL_EVAL,
            format='json',
            messages=[
                {'role': 'system', 'content': 'You are a JSON-only API. Return only valid JSON.'},
                {'role': 'user',   'content': text_prompt}
            ]
        )
        text_result = clean_json_response(resp2['message']['content'])
        # Only accept if the values are real text (not "..." or empty)
        raw_ideal = str(text_result.get("ideal_answer", "")).strip()
        raw_gap   = str(text_result.get("gap_analysis", "")).strip()
        raw_feed  = str(text_result.get("feedback", "")).strip()

        ideal_answer  = raw_ideal  if len(raw_ideal) > 5  else ""
        gap_analysis  = raw_gap    if len(raw_gap) > 5    else ""
        feedback_text = raw_feed   if len(raw_feed) > 5   else ""
    except Exception as e:
        logger.warning("Text feedback call failed (scores still valid): %s", str(e))

    return {
        "correctness":     correctness,
        "reasoning":       reasoning,
        "clarity":         clarity,
        "technical_depth": technical_depth,
        "ideal_answer":    ideal_answer,
        "gap_analysis":    gap_analysis,
        "feedback":        feedback_text,
    }


# ─────────────────────────────────────────
# Batch Report (evaluates each Q individually)
# ─────────────────────────────────────────
def batch_evaluate_and_report(job_title: str, skills: list, q_a_pairs: list) -> dict:
    """
    Evaluate each non-MCQ answer individually for maximum reliability.
    A 1.5b model handles one question at a time far better than a batch of 4+.
    """
    if not q_a_pairs:
        logger.info("No Q&A pairs to evaluate.")
        return {
            "skill_gaps": {"missing_skills": list(skills), "weak_areas": [], "recommended_topics": []},
            "question_evaluations": [],
            "feedback": "No answers were submitted by the candidate."
        }

    logger.info("Starting individual evaluation of %d answers...", len(q_a_pairs))

    question_evaluations = []
    for i, qa in enumerate(q_a_pairs):
        logger.info("Evaluating answer %d/%d...", i + 1, len(q_a_pairs))
        eval_result = evaluate_single_answer(
            job_title, qa['q'], qa['a'], qa.get('q_type', 'technical')
        )

        if eval_result is None:
            # Evaluation failed for this question — mark it clearly but don't score 0
            question_evaluations.append({
                "question":    qa['q'],
                "user_answer": qa['a'],
                "ideal_answer": "",
                "gap_analysis": "Automated evaluation could not be completed for this answer. Manual review recommended.",
                "metrics": None,  # None = evaluation failed, not zero score
                "feedback": "Evaluation failed for this question. Manual review required."
            })
        else:
            question_evaluations.append({
                "question":    qa['q'],
                "user_answer": qa['a'],
                "ideal_answer": eval_result["ideal_answer"],
                "gap_analysis": eval_result["gap_analysis"],
                "metrics": {
                    "correctness":     eval_result["correctness"],
                    "reasoning":       eval_result["reasoning"],
                    "clarity":         eval_result["clarity"],
                    "technical_depth": eval_result["technical_depth"],
                },
                "feedback": eval_result["feedback"]
            })

    # Derive skill gaps and feedback from results — no extra LLM call needed
    skill_gaps      = _derive_skill_gaps(skills, question_evaluations)
    overall_feedback = _derive_overall_feedback(question_evaluations)

    return {
        "skill_gaps":           skill_gaps,
        "question_evaluations": question_evaluations,
        "feedback":             overall_feedback
    }


def _derive_skill_gaps(skills: list, evaluations: list) -> dict:
    """Derive skill gaps from ai_service internal evaluations (used inside batch_evaluate_and_report)."""
    weak_areas = []
    for e in evaluations:
        m = e.get("metrics")
        if m and isinstance(m, dict) and m.get("correctness", 100) < 55:
            preview = e.get("question", "")[:80]
            if preview and preview not in weak_areas:
                weak_areas.append(preview)

    has_gaps = len(weak_areas) > 0
    return {
        "missing_skills":      [],
        "weak_areas":          weak_areas[:3],
        "recommended_topics":  list(skills[:3]) if has_gaps else []
    }


def _derive_overall_feedback(evaluations: list) -> str:
    """Internal feedback from ai_service evaluations (used inside batch_evaluate_and_report)."""
    scored = [e for e in evaluations if e.get("metrics") and isinstance(e["metrics"], dict)]
    if not scored:
        return "Automated evaluation could not be completed. Manual review is recommended."

    avg = sum(e["metrics"].get("correctness", 0) for e in scored) / len(scored)

    if avg >= 75:
        return ("Strong candidate demonstrating solid technical knowledge across most areas. "
                "Recommended for the next stage of the hiring process.")
    elif avg >= 55:
        return ("Candidate shows foundational knowledge with some gaps. "
                "Further technical review is recommended before making a hiring decision.")
    elif avg >= 35:
        return ("Candidate demonstrated limited technical proficiency. "
                "Significant knowledge gaps were identified in core areas.")
    else:
        return ("Candidate did not demonstrate sufficient technical knowledge for this role. "
                "The answers lacked depth and accuracy across most evaluated areas.")


# ─────────────────────────────────────────
# Final Report Summary (called by router)
# ─────────────────────────────────────────
def derive_final_report_summary(final_score: float, final_evaluations: list, skills: list) -> tuple:
    """
    Derive ACCURATE skill_gaps and overall feedback from the router's FINAL
    per-question evaluations — AFTER MCQ grading, gibberish detection, and all
    safety overrides have been applied.  Call this instead of using the pre-computed
    values from batch_evaluate_and_report, which run before those overrides.

    Returns: (skill_gaps: dict, feedback: str)
    """
    weak_areas = []
    blank_or_zero_count = 0

    for ev in final_evaluations:
        metrics = ev.get("metrics")
        if not isinstance(metrics, dict):
            continue

        correctness  = metrics.get("correctness", 0)
        user_answer  = ev.get("user_answer", "")
        gap          = ev.get("gap_analysis", "")
        q_type       = ev.get("question_type", "")
        q_text       = ev.get("question", "")

        # Track blank / zero-score answers
        is_blank     = user_answer in ["", "(no answer submitted)"]
        is_gibberish = "gibberish" in gap.lower() or "irrelevant" in gap.lower()
        if is_blank or (correctness == 0 and is_gibberish):
            blank_or_zero_count += 1

        # Build a short, readable topic label for this weak area
        if correctness < 60:
            type_prefix = {
                "mcq":       "MCQ",
                "coding":    "Coding",
                "scenario":  "Scenario",
                "technical": "Technical",
                "short_qa":  "Short Answer",
            }.get(q_type, "Question")
            label = f"{type_prefix}: {q_text[:65].rstrip()}"
            if label not in weak_areas:
                weak_areas.append(label)

    recommended_topics = list(skills[:3]) if weak_areas else []

    skill_gaps = {
        "missing_skills":     [],
        "weak_areas":         weak_areas[:3],
        "recommended_topics": recommended_topics,
    }

    # ── Overall feedback: score-based and honest about blanks ─────────────
    score = round(final_score)

    if blank_or_zero_count >= 3:
        feedback = (
            f"Candidate left {blank_or_zero_count} question(s) unanswered or submitted "
            f"irrelevant responses, resulting in a score of {score}/100. "
            f"Completing all questions is essential for a fair technical assessment."
        )
    elif score >= 80:
        feedback = (
            f"Excellent performance with a score of {score}/100. "
            f"The candidate demonstrated strong, accurate technical knowledge across all "
            f"areas and is highly recommended for the next stage."
        )
    elif score >= 70:
        feedback = (
            f"Strong candidate with a score of {score}/100, showing solid technical "
            f"proficiency across most areas. Minor gaps identified; recommended for "
            f"further review."
        )
    elif score >= 55:
        feedback = (
            f"Candidate scored {score}/100, demonstrating foundational technical knowledge "
            f"with some notable gaps. A technical follow-up interview is recommended "
            f"before making a hiring decision."
        )
    elif score >= 40:
        feedback = (
            f"Candidate scored {score}/100, reflecting limited technical proficiency. "
            f"Significant knowledge gaps were identified in core areas. "
            f"Additional preparation is needed before re-applying."
        )
    else:
        feedback = (
            f"Candidate scored {score}/100. Most answers were incomplete, "
            f"incorrect, or missing entirely. The candidate did not demonstrate "
            f"sufficient technical knowledge for this role at this time."
        )

    return skill_gaps, feedback

