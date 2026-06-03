import React, { useState, useEffect, useRef } from 'react';
import { useParams, useNavigate } from 'react-router-dom';
import api from '../services/api';
import Editor from '@monaco-editor/react';
import toast from 'react-hot-toast';
import styles from './InterviewSession.module.css';

export default function InterviewSession() {
  const { jobId } = useParams(); // actually interviewId, but we matched the route var
  const navigate = useNavigate();
  const [question, setQuestion] = useState(null);
  const [questionContent, setQuestionContent] = useState('');
  const [answer, setAnswer] = useState('');
  const [loading, setLoading] = useState(true);
  const [submitting, setSubmitting] = useState(false);
  const startTime = useRef(Date.now());
  const [secondsElapsed, setSecondsElapsed] = useState(0);

  // Anti-cheat tracking
  useEffect(() => {
    const handleVisibilityChange = () => {
      if (document.hidden) {
        toast.error('Warning: Tab switching detected!');
        api.post(`/interviews/${jobId}/track`, {
          event_type: 'tab_switch',
          details: 'User switched away from the interview tab.'
        });
      }
    };

    const handleCopyPaste = (e) => {
      toast.error('Warning: Copy/Paste is tracked!');
      api.post(`/interviews/${jobId}/track`, {
        event_type: 'copy_paste',
        details: `Clipboard event: ${e.type}`
      });
    };

    document.addEventListener('visibilitychange', handleVisibilityChange);
    window.addEventListener('copy', handleCopyPaste);
    window.addEventListener('paste', handleCopyPaste);

    return () => {
      document.removeEventListener('visibilitychange', handleVisibilityChange);
      window.removeEventListener('copy', handleCopyPaste);
      window.removeEventListener('paste', handleCopyPaste);
    };
  }, [jobId]);

  // Timer
  useEffect(() => {
    const interval = setInterval(() => {
      setSecondsElapsed(Math.floor((Date.now() - startTime.current) / 1000));
    }, 1000);
    return () => clearInterval(interval);
  }, []);

  const streamQuestionText = async (qId) => {
    try {
      // Direct fetch to stream
      const response = await fetch(`http://127.0.0.1:8000/api/v1/interviews/${jobId}/question/${qId}/stream`);
      const reader = response.body.getReader();
      const decoder = new TextDecoder("utf-8");
      
      setQuestionContent('');
      let done = false;
      
      while (!done) {
        const { value, done: readerDone } = await reader.read();
        done = readerDone;
        if (value) {
          const chunk = decoder.decode(value, { stream: true });
          setQuestionContent(prev => prev + chunk);
        }
      }
    } catch (err) {
      console.error("Stream failed", err);
      setQuestionContent("Failed to load question stream. Please refresh.");
    }
  };

  const fetchNextQuestion = async () => {
    try {
      setLoading(true);
      const res = await api.get(`/interviews/${jobId}/question`);
      setQuestion(res.data);
      setAnswer('');
      startTime.current = Date.now();
      setSecondsElapsed(0);
      setLoading(false);
      
      if (!res.data.content) {
        // Stream the content if it's new
        streamQuestionText(res.data.id);
      } else {
        setQuestionContent(res.data.content);
      }
    } catch (error) {
      toast.error('Failed to get question');
      setLoading(false);
    }
  };

  useEffect(() => {
    fetchNextQuestion();
  }, [jobId]);

  const handleSubmit = async () => {
    if (!answer.trim()) return toast.error('Answer cannot be empty');
    
    try {
      setSubmitting(true);
      const timeTaken = Math.floor((Date.now() - startTime.current) / 1000);
      const res = await api.post(`/interviews/${jobId}/answer`, {
        question_id: question.id,
        answer: answer,
        time_taken_seconds: timeTaken
      });

      if (res.data.is_complete) {
        toast.success('Interview Completed! Generating Final Report...');
        navigate(`/candidate/${jobId}`);
      } else {
        // toast.success('Answer submitted! Loading next question...');
        fetchNextQuestion();
      }
    } catch (error) {
      toast.error('Submission failed');
    } finally {
      setSubmitting(false);
    }
  };

  if (loading && !question) {
    return (
      <div className={styles.container}>
        <div className={styles.content}>
           <div className={`glass-panel ${styles.questionCard}`} style={{opacity: 0.5}}>
             <h3 className="animate-pulse">Preparing next question...</h3>
           </div>
        </div>
      </div>
    );
  }

  if (!question) return <div className={styles.container}><h3>No question found.</h3></div>;

  const isCode = question.question_type === 'coding';
  const isMcq = question.question_type === 'mcq' && question.options && question.options.length > 0;

  const formatTime = (sec) => {
    const m = Math.floor(sec / 60).toString().padStart(2, '0');
    const s = (sec % 60).toString().padStart(2, '0');
    return `${m}:${s}`;
  };

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <div className={styles.warning}>
          <span className="material-icons"></span> Proctoring Active
        </div>
        <div className={styles.timer}>{formatTime(secondsElapsed)}</div>
      </header>

      <div className={styles.content}>
        <div className={`glass-panel ${styles.questionCard} animate-fade-in`}>
          <span className={styles.badge}>{question.question_type}</span>
          <p className={styles.questionText}>
            {questionContent || <span className="animate-pulse">Thinking...</span>}
          </p>
        </div>

        <div className={`${styles.answerArea} animate-fade-in`} style={{ animationDelay: '0.2s' }}>
          {isMcq ? (
            <div className={styles.mcqContainer}>
              <p className={styles.mcqInstruction}>Select the correct answer:</p>
              {question.options.map((opt, idx) => (
                <button
                  key={idx}
                  id={`mcq-option-${idx}`}
                  className={`${styles.mcqOption} ${answer === opt ? styles.mcqOptionSelected : ''}`}
                  onClick={() => setAnswer(opt)}
                  disabled={submitting}
                >
                  {opt}
                </button>
              ))}
            </div>
          ) : isCode ? (
            <div className={styles.editorContainer}>
              <Editor
                height="100%"
                defaultLanguage="javascript"
                theme="vs-dark"
                value={answer}
                onChange={(val) => setAnswer(val || '')}
                options={{ minimap: { enabled: false }, fontSize: 16 }}
              />
            </div>
          ) : (
            <textarea 
              className={styles.textArea} 
              placeholder="Type your answer here..."
              value={answer}
              onChange={(e) => setAnswer(e.target.value)}
            />
          )}
          <button 
            className={styles.submitBtn} 
            onClick={handleSubmit} 
            disabled={submitting || (isMcq && !answer)}
          >
            {submitting ? 'Submitting...' : isMcq && !answer ? 'Select an Option First' : 'Submit Answer'}
          </button>
        </div>
      </div>
    </div>
  );
}
