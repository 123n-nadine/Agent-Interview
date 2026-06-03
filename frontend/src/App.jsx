import React from 'react';
import { BrowserRouter, Routes, Route } from 'react-router-dom';
import { Toaster } from 'react-hot-toast';
import JobBoard from './pages/JobBoard';
import InterviewSession from './pages/InterviewSession';
import CandidateDashboard from './pages/CandidateDashboard';
import HRDashboard from './pages/HRDashboard';
import './index.css';

function App() {
  return (
    <BrowserRouter>
      <Toaster position="top-right" toastOptions={{
        style: {
          background: '#1e293b',
          color: '#f8fafc',
          border: '1px solid rgba(255, 255, 255, 0.1)',
        }
      }} />
      <Routes>
        <Route path="/" element={<JobBoard />} />
        <Route path="/interview/:jobId" element={<InterviewSession />} />
        <Route path="/candidate/:interviewId" element={<CandidateDashboard />} />
        <Route path="/hr/dashboard" element={<HRDashboard />} />
      </Routes>
    </BrowserRouter>
  );
}

export default App;
