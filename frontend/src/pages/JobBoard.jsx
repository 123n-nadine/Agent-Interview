import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import styles from './JobBoard.module.css';
import toast from 'react-hot-toast';

export default function JobBoard() {
  const [jobs, setJobs] = useState([]);
  const [loading, setLoading] = useState(true);
  const navigate = useNavigate();

  useEffect(() => {
    fetchJobs();
  }, []);

  const fetchJobs = async () => {
    try {
      const cached = sessionStorage.getItem('jobsCache');
      if (cached) {
        setJobs(JSON.parse(cached));
        setLoading(false);
      }
      
      const response = await api.get('/jobs');
      setJobs(response.data);
      sessionStorage.setItem('jobsCache', JSON.stringify(response.data));
    } catch (error) {
      toast.error('Failed to load jobs. Is backend running?');
      console.error(error);
    } finally {
      setLoading(false);
    }
  };

  const handleStartInterview = async (jobId) => {
    try {
      const candidateName = prompt("Enter your name:");
      const candidateEmail = prompt("Enter your email:");
      if (!candidateName || !candidateEmail) return;

      const response = await api.post('/interviews/start', {
        job_id: jobId,
        candidate_name: candidateName,
        candidate_email: candidateEmail
      });
      navigate(`/interview/${response.data.id}`);
    } catch (error) {
      toast.error('Failed to start interview');
    }
  };

  if (loading) {
    return (
      <div className={styles.loader}>
        <div className={styles.spinner}></div>
        <h2>Loading Live Jobs...</h2>
      </div>
    );
  }

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1 className="animate-fade-in">Join the Future.</h1>
        <p className="animate-fade-in" style={{ animationDelay: '0.1s' }}>
          Discover your next role and take our AI-powered technical interview.
        </p>
      </header>

      <div className={styles.grid}>
        {jobs.map((job, index) => (
          <div 
            key={job.id} 
            className={`glass-panel ${styles.card} animate-fade-in`}
            style={{ animationDelay: `${0.1 * index}s` }}
          >
            <h2 className={styles.cardTitle}>{job.title}</h2>
            <div className={styles.company}>RevUp Partner</div>
            <p className={styles.description}>
              {job.description.substring(0, 150)}...
            </p>
            <div className={styles.skills}>
              {job.skills.slice(0, 4).map(skill => (
                <span key={skill} className={styles.skill}>{skill}</span>
              ))}
              {job.skills.length > 4 && <span className={styles.skill}>+{job.skills.length - 4}</span>}
            </div>
            <button 
              className={styles.applyButton}
              onClick={() => handleStartInterview(job.id)}
            >
              Start AI Interview
            </button>
          </div>
        ))}
      </div>
    </div>
  );
}
