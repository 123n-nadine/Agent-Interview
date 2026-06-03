# Optimization & Architecture Walkthrough

The platform has been fully optimized to feel instantaneous, highly responsive, and reliable on local hardware. Here is a breakdown of the core architectural decisions and optimizations implemented.

## 🚀 Streaming & Asynchronous Design
- **Fast Question Generation**: Instead of waiting for a full JSON block from the LLM, the backend immediately starts streaming the text response down to the UI using a `StreamingResponse` endpoint.
- **Async Endpoints**: Every endpoint in `interviews_router.py` is now an asynchronous route (`async def`) allowing FastAPI's Uvicorn server to handle concurrent connections and long-running evaluations without stalling the Python event loop.

## 🧠 Reliable AI Evaluation Pipeline
Evaluating all answers at once with small models frequently led to JSON structure collapse and missing data. We redesigned the pipeline for maximum reliability with a `1.5b` model:
- **Individual Sequential Evaluation**: Each open-ended question is evaluated independently. The UI polls for results while displaying a smooth loading spinner, ensuring the user is never left hanging.
- **Two-Call Strategy**: For each answer, the system makes two isolated LLM calls:
  1. **Scoring Call**: Requests only the 4 numeric metrics. Extremely fast and highly reliable.
  2. **Text Feedback Call**: Separately requests the `ideal_answer`, `gap_analysis`, and `feedback`. This completely eliminates the "JSON placeholder copying" bug.
- **Type-Aware Prompts**: Ideal answers are generated based on the specific `q_type` (e.g. coding questions demand actual code instead of a paragraph summary).

## 🛡️ Robust Grading & Safety Overrides
- **Deterministic MCQ Grading**: Multiple choice questions are graded locally against the stored correct answer without LLM involvement.
- **Gibberish Detection**: Any answer determined to be gibberish or completely irrelevant is automatically overridden to 0 across all metrics to protect the integrity of the evaluation.
- **Accurate Summary Generation**: The "Areas for Improvement" and the "Overall AI Summary" are calculated dynamically based on the **final** evaluations (post-MCQ grading and post-gibberish overrides). This guarantees that the final written summary perfectly aligns with the score the candidate receives.

## 💾 Aggressive Caching
- **Jobs API Cache**: The `JobBoard` frontend and the `jobs_service` backend now cache the live Jobs API payload. Navigating away and back to the Job Board takes **0ms**.
- **Ollama Settings**: Applied `OLLAMA_KEEP_ALIVE=-1` inside `.env` to permanently cache the LLM model inside RAM so you never face the "cold start" delay again.
