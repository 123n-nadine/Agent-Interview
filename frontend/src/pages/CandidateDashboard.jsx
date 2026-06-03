import React, { useEffect, useState, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../services/api';
import styles from './CandidateDashboard.module.css';

const MAX_RETRIES = 20;       // 20 × 4 s = up to 80 s waiting
const RETRY_DELAY_MS = 4000;

export default function CandidateDashboard() {
  const { interviewId } = useParams();
  const navigate = useNavigate();
  const [report, setReport]       = useState(null);
  const [fetchError, setFetchError] = useState(false);
  const [attempt, setAttempt]     = useState(0);
  const retryRef = useRef(null);

  useEffect(() => {
    let retryCount = 0;

    const fetchReport = async () => {
      try {
        const res = await api.get(`/interviews/${interviewId}/report`);
        setReport(res.data);
      } catch (err) {
        retryCount++;
        setAttempt(retryCount);
        console.error(`Report fetch attempt ${retryCount} failed:`, err);
        if (retryCount < MAX_RETRIES) {
          retryRef.current = setTimeout(fetchReport, RETRY_DELAY_MS);
        } else {
          setFetchError(true);
        }
      }
    };

    fetchReport();
    return () => { if (retryRef.current) clearTimeout(retryRef.current); };
  }, [interviewId]);

  // ── Loading state ──────────────────────────────────────────────
  if (!report && !fetchError) {
    return (
      <div className={styles.loadingContainer}>
        <div className={styles.loadingSpinner} />
        <h2 className={styles.loadingTitle}>Generating AI Analytics...</h2>
        <p className={styles.loadingSubtitle}>
          Our AI is carefully evaluating your responses.
          {attempt > 0 && ` (attempt ${attempt + 1})`}
        </p>
        <p className={styles.loadingHint}>
          This usually takes 30–90 seconds depending on answer complexity.
        </p>
      </div>
    );
  }

  // ── Error state ────────────────────────────────────────────────
  if (fetchError) {
    return (
      <div className={styles.loadingContainer}>
        <div className={styles.errorIcon}>!</div>
        <h2 className={styles.loadingTitle}>Could Not Load Report</h2>
        <p className={styles.loadingSubtitle}>
          The backend took too long to respond. This usually means Ollama is busy.
        </p>
        <button className={styles.retryBtn} onClick={() => window.location.reload()}>
          Try Again
        </button>
      </div>
    );
  }

  // ── Helpers ────────────────────────────────────────────────────
  const decisionColor = (d) =>
    d === 'Hire' ? 'var(--success)' : d === 'Review Required' ? 'var(--accent-primary)' : 'var(--danger)';

  const scoreGradient = (score) => {
    if (score >= 75) return 'linear-gradient(135deg, #00c896, #00a878)';
    if (score >= 60) return 'linear-gradient(135deg, #6c63ff, #4a43d6)';
    return 'linear-gradient(135deg, #ff6b6b, #d63031)';
  };

  const metricColor = (val) => {
    if (val >= 70) return '#00c896';
    if (val >= 45) return '#f9ca24';
    return '#ff6b6b';
  };

  const qTypeBadgeStyle = (type) => {
    const map = {
      mcq:       { background: 'rgba(108, 99, 255, 0.25)', color: '#a29bfe' },
      short_qa:  { background: 'rgba(0, 200, 150, 0.20)', color: '#00cec9' },
      technical: { background: 'rgba(253, 203, 110, 0.20)', color: '#fdcb6e' },
      scenario:  { background: 'rgba(255, 107, 107, 0.20)', color: '#ff7675' },
      coding:    { background: 'rgba(0, 184, 255, 0.20)', color: '#74b9ff' },
    };
    return map[type] || { background: 'rgba(255,255,255,0.1)', color: '#dfe6e9' };
  };

  const typeLabel = (type) => {
    const labels = {
      mcq: 'MCQ', short_qa: 'Short Answer', technical: 'Technical',
      scenario: 'Scenario', coding: 'Coding',
    };
    return labels[type] || type;
  };

  const evals = report.question_evaluations || [];

  return (
    <div className={styles.container}>

      {/* ── Header ── */}
      <header className={styles.header}>
        <h1>Interview Results</h1>
        <p className={styles.candidateName}>{report.candidate_name}</p>
      </header>

      {/* ── Score Card ── */}
      <div className={`glass-panel ${styles.scoreCard} animate-fade-in`}>
        <div
          className={styles.scoreCircle}
          style={{ background: scoreGradient(report.final_score) }}
        >
          <span className={styles.scoreNumber}>{Math.round(report.final_score)}</span>
          <span className={styles.scoreLabel}>/ 100</span>
        </div>
        <div className={styles.scoreDetails}>
          <h2>Overall AI Evaluation Score</h2>
          <p className={styles.decisionBadge} style={{ color: decisionColor(report.hiring_decision) }}>
            Decision: <strong>{report.hiring_decision}</strong>
          </p>
          <p className={styles.weightNote}>
            Score Weights: Correctness 45% · Tech Depth 30% · Reasoning 15% · Clarity 10%
          </p>
          <p className={styles.metaNote}>
            Answers evaluated: {report.answers_evaluated} · Suspicion score: {report.suspicion_score}
          </p>
        </div>
      </div>

      {/* ── Skill Gaps Grid ── */}
      <div className={styles.grid}>
        <div className={`glass-panel ${styles.panel} animate-fade-in`} style={{ animationDelay: '0.1s' }}>
          <h3>Areas for Improvement</h3>
          {report.skill_gaps?.weak_areas?.length > 0 ? (
            <ul className={styles.list}>
              {report.skill_gaps.weak_areas.map((w, i) => <li key={i}>{w}</li>)}
            </ul>
          ) : (
            <p className={styles.emptyNote}>No specific weak areas identified.</p>
          )}
        </div>
        <div className={`glass-panel ${styles.panel} animate-fade-in`} style={{ animationDelay: '0.2s' }}>
          <h3>Recommended Topics</h3>
          {report.skill_gaps?.recommended_topics?.length > 0 ? (
            <ul className={styles.list}>
              {report.skill_gaps.recommended_topics.map((t, i) => <li key={i}>{t}</li>)}
            </ul>
          ) : (
            <p className={styles.emptyNote}>No additional topics recommended.</p>
          )}
        </div>
      </div>

      {/* ── Overall Feedback ── */}
      <div className={`glass-panel ${styles.feedback} animate-fade-in`} style={{ animationDelay: '0.3s' }}>
        <h3>Overall AI Summary</h3>
        <p>{report.feedback || 'Evaluation complete.'}</p>
      </div>

      {/* ── Question Evaluations ── */}
      {evals.length > 0 && (
        <div className={styles.evalContainer}>
          <h2 className="animate-fade-in">Detailed Question Breakdown</h2>
          {evals.map((ev, idx) => (
            <div
              key={idx}
              className={`glass-panel ${styles.evalCard} animate-fade-in`}
              style={{ animationDelay: `${0.08 * idx}s` }}
            >
              {/* Card header */}
              <div className={styles.qHeader}>
                <span className={styles.qNum}>Question {idx + 1}</span>
                {ev.question_type && (
                  <span className={styles.qTypeBadge} style={qTypeBadgeStyle(ev.question_type)}>
                    {typeLabel(ev.question_type)}
                  </span>
                )}
              </div>

              {/* Question text */}
              <p className={styles.qText}>{ev.question}</p>

              {/* Your answer / ideal answer */}
              <div className={styles.qaGrid}>
                <div className={styles.answerBox}>
                  <h4>Your Answer</h4>
                  <p>{ev.user_answer}</p>
                </div>
                <div className={styles.answerBox}>
                  <h4>Ideal Answer</h4>
                  <p>{ev.ideal_answer || '—'}</p>
                </div>
              </div>

              {/* Gap analysis */}
              {ev.gap_analysis && (
                <div className={styles.gapBox}>
                  <h4>Gap Analysis</h4>
                  <p>{ev.gap_analysis}</p>
                </div>
              )}

              {/* Metrics bars */}
              <div className={styles.metricsGrid}>
                {[
                  { label: 'Correctness',  key: 'correctness' },
                  { label: 'Tech Depth',   key: 'technical_depth' },
                  { label: 'Reasoning',    key: 'reasoning' },
                  { label: 'Clarity',      key: 'clarity' },
                ].map(({ label, key }) => {
                  const val = ev.metrics?.[key] ?? 0;
                  return (
                    <div key={key} className={styles.metric}>
                      <div className={styles.metricHeader}>
                        <span>{label}</span>
                        <span style={{ color: metricColor(val) }}>{val}%</span>
                      </div>
                      <div className={styles.bar}>
                        <div
                          className={styles.fill}
                          style={{ width: `${val}%`, background: metricColor(val) }}
                        />
                      </div>
                    </div>
                  );
                })}
              </div>

              {/* Feedback */}
              {ev.feedback && (
                <div className={styles.feedbackBox}>
                  <h4>AI Feedback</h4>
                  <p>{ev.feedback}</p>
                </div>
              )}
            </div>
          ))}
        </div>
      )}

      {/* ── Back button ── */}
      <div style={{ textAlign: 'center', marginTop: '3rem', paddingBottom: '3rem' }}>
        <button className={styles.backBtn} onClick={() => navigate('/')}>
          Back to Job Board
        </button>
      </div>
    </div>
  );
}
