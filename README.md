# AI-Powered Hiring Platform

A graduation-project-quality, scalable, and modular AI-powered hiring platform built with FastAPI and React.

This platform dynamically fetches jobs from a live API, generates smart technical interviews using local AI models, evaluates candidate answers with deep per-question analytics, and features a robust anti-cheat tracking system.

## Key Features

- **Dynamic AI Interviews**: 6 questions per interview — 2 MCQs + 4 open-ended (short answer, technical, scenario, coding) — generated on the fly based on specific job requirements and seniority level.
- **Real-Time Streaming**: Open-ended questions are streamed character-by-character to the UI using Server-Sent Events for a fast, engaging experience.
- **MCQ Auto-Grading**: Multiple choice questions are graded deterministically (no AI needed) using the stored correct answer.
- **Individual AI Evaluation**: Each open-ended answer is evaluated independently by the AI model for maximum reliability using a two-call strategy (one for scores, one for text feedback) to avoid JSON placeholder hallucinations.
- **Type-Aware Ideal Answers**: The AI generates ideal answers tailored to the question type (e.g., providing actual working code for coding questions, or 4-6 sentence deep-dives for scenario questions).
- **Weighted Scoring**: Final score = Correctness (45%) + Tech Depth (30%) + Reasoning (15%) + Clarity (10%).
- **Gibberish Detection**: Automatically detects and penalizes random/gibberish answers with a score of 0, protecting the integrity of the evaluation.
- **Accurate Reporting**: Areas for Improvement and Overall Summary are derived *after* all safety overrides, MCQ grading, and gibberish penalties are applied, ensuring the summary perfectly matches the candidate's final score.
- **Anti-Cheat System**: Tracks tab-switching, copy/pasting, and suspiciously fast answers to generate a `suspicion_score`.
- **Candidate Dashboard**: Full question-by-question breakdown with metric bars, ideal answers, gap analysis, and AI feedback.
- **HR Dashboard**: Overview of all AI-conducted interviews with hiring decisions.

## Tech Stack

- **Frontend**: React + Vite + Vanilla CSS Modules, React Router, Axios, Monaco Editor
- **Backend**: FastAPI (Async), SQLAlchemy ORM, SQLite, Python-dotenv
- **AI System**: Ollama (`qwen2.5:1.5b`) for question generation and evaluation

## Quick Start

See [`RUN_NOTES.md`](RUN_NOTES.md) for step-by-step startup instructions.
See [`INSTALLATION.md`](INSTALLATION.md) for first-time setup.
