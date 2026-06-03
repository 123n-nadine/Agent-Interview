from sqlalchemy import Column, Integer, String, Float, ForeignKey, DateTime, JSON, Boolean, Text
from sqlalchemy.orm import relationship
from .database import Base
from datetime import datetime

class Job(Base):
    __tablename__ = "jobs"
    id = Column(Integer, primary_key=True, index=True)
    revup_id = Column(Integer, unique=True, index=True)
    title = Column(String, index=True)
    description = Column(Text)
    skills = Column(JSON)  # List of skill names
    seniority = Column(String, nullable=True)
    
    interviews = relationship("InterviewSession", back_populates="job")

class InterviewSession(Base):
    __tablename__ = "interview_sessions"
    id = Column(Integer, primary_key=True, index=True)
    job_id = Column(Integer, ForeignKey("jobs.id"))
    candidate_name = Column(String)
    candidate_email = Column(String)
    status = Column(String, default="in_progress") # in_progress, completed
    final_score = Column(Float, nullable=True)
    hiring_decision = Column(String, nullable=True)
    ai_probability_avg = Column(Float, nullable=True)
    suspicion_score = Column(Float, default=0.0)
    skill_gaps = Column(JSON, nullable=True)
    question_evaluations = Column(JSON, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    job = relationship("Job", back_populates="interviews")
    questions = relationship("Question", back_populates="interview")
    cheat_logs = relationship("CheatLog", back_populates="interview")

class Question(Base):
    __tablename__ = "questions"
    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(Integer, ForeignKey("interview_sessions.id"))
    question_type = Column(String) # technical, behavioral, code_analysis
    content = Column(Text)
    options = Column(JSON, nullable=True) # Options for MCQ questions
    correct_answer = Column(String, nullable=True) # Correct answer for MCQ questions
    difficulty = Column(String)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    interview = relationship("InterviewSession", back_populates="questions")
    answer = relationship("Answer", back_populates="question", uselist=False)

class Answer(Base):
    __tablename__ = "answers"
    id = Column(Integer, primary_key=True, index=True)
    question_id = Column(Integer, ForeignKey("questions.id"), unique=True)
    content = Column(Text)
    time_taken_seconds = Column(Integer)
    score = Column(Float, nullable=True)
    feedback = Column(Text, nullable=True)
    ai_probability = Column(Float, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    
    question = relationship("Question", back_populates="answer")

class CheatLog(Base):
    __tablename__ = "cheat_logs"
    id = Column(Integer, primary_key=True, index=True)
    interview_id = Column(Integer, ForeignKey("interview_sessions.id"))
    event_type = Column(String) # tab_switch, copy_paste, inactive
    details = Column(String)
    timestamp = Column(DateTime, default=datetime.utcnow)
    
    interview = relationship("InterviewSession", back_populates="cheat_logs")
