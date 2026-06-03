from pydantic import BaseModel
from typing import List, Optional, Any
from datetime import datetime

# Job Schemas
class JobBase(BaseModel):
    title: str
    description: str
    skills: List[str]
    seniority: Optional[str] = None

class JobCreate(JobBase):
    revup_id: int

class JobResponse(JobBase):
    id: int
    revup_id: int
    class Config:
        from_attributes = True

# Interview Schemas
class InterviewStart(BaseModel):
    job_id: int
    candidate_name: str
    candidate_email: str

class InterviewResponse(BaseModel):
    id: int
    job_id: int
    status: str
    candidate_name: str
    class Config:
        from_attributes = True

# Question & Answer Schemas
class QuestionResponse(BaseModel):
    id: int
    question_type: str
    content: str
    options: Optional[List[str]] = None
    difficulty: str
    class Config:
        from_attributes = True

class AnswerSubmit(BaseModel):
    question_id: int
    answer: str
    time_taken_seconds: int

class AnswerEvaluation(BaseModel):
    score: float
    feedback: str
    ai_probability: float

class AnswerResponse(BaseModel):
    status: str
    evaluation: AnswerEvaluation
    is_complete: bool

# Cheat Log Schema
class CheatEvent(BaseModel):
    event_type: str
    details: str

# Final Report Schema
class SkillGaps(BaseModel):
    missing_skills: List[str]
    weak_areas: List[str]
    recommended_topics: List[str]

class QuestionMetrics(BaseModel):
    correctness: float
    reasoning: float
    clarity: float
    technical_depth: float

class QuestionEvaluation(BaseModel):
    question: str
    user_answer: str
    ideal_answer: str
    gap_analysis: str
    metrics: QuestionMetrics
    feedback: str

class FinalReport(BaseModel):
    interview_id: int
    candidate_name: str
    final_score: float
    hiring_decision: str
    ai_probability_avg: float
    suspicion_score: float
    skill_gaps: SkillGaps
    question_evaluations: List[QuestionEvaluation] = []
    feedback: str
