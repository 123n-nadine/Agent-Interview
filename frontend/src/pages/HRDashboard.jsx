import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import api from '../services/api';
import styles from './HRDashboard.module.css';

export default function HRDashboard() {
  const [interviews, setInterviews] = useState([]);
  const navigate = useNavigate();

  // In a real app we would have a dedicated endpoint for listing interviews.
  // For this prototype we can just mock the UI or add a quick endpoint if needed.
  // Since I am sticking strictly to the API written, I will render an empty state or 
  // instructions on how HR would view the individual candidate links.

  return (
    <div className={styles.container}>
      <header className={styles.header}>
        <h1>HR Analytics Dashboard</h1>
        <p>Overview of all AI-conducted interviews.</p>
      </header>

      <div className={`glass-panel ${styles.tableContainer} animate-fade-in`}>
        <table>
          <thead>
            <tr>
              <th>Candidate</th>
              <th>Score</th>
              <th>AI Probability</th>
              <th>Suspicion Score</th>
              <th>Decision</th>
              <th>Action</th>
            </tr>
          </thead>
          <tbody>
            {/* Placeholders representing data that would be fetched */}
            <tr>
              <td colSpan="6" style={{textAlign: "center", padding: "2rem", color: "var(--text-secondary)"}}>
                End of the prototype. To view candidates, use the Candidate Dashboard links provided at the end of each session.
              </td>
            </tr>
          </tbody>
        </table>
      </div>
    </div>
  );
}
