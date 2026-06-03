# Installation Guide

## 1. Prerequisites
- Python 3.10+
- Node.js 18+
- PostgreSQL
- Ollama

## 2. Setting up the Local AI (Ollama)
1. Install [Ollama](https://ollama.com/).
2. Start the Ollama server and pull the `qwen2.5:3b` model:
   ```bash
   ollama run qwen2.5:3b
   ```

## 3. Database Setup
Ensure PostgreSQL is running on your machine.
Create a database (default: `interview_db`).
```sql
CREATE DATABASE interview_db;
```

## 4. Backend Setup
Navigate to the `backend` directory.

1. Create a virtual environment:
   ```bash
   python -m venv venv
   # Windows
   .\venv\Scripts\activate
   # Linux/Mac
   source venv/bin/activate
   ```

2. Install dependencies:
   ```bash
   pip install fastapi uvicorn requests sqlalchemy psycopg2-binary python-dotenv ollama openai sentence-transformers faiss-cpu
   ```

3. Setup environment variables:
   Copy `.env.example` to `.env` and configure your database URI.
   ```bash
   cp .env.example .env
   ```

4. Run the Backend:
   ```bash
   uvicorn main:app --reload
   ```
   The backend will run at `http://localhost:8000`.

## 5. Frontend Setup
Navigate to the `frontend` directory.

1. Install dependencies:
   ```bash
   npm install axios react-router-dom react-hot-toast @monaco-editor/react
   ```

2. Run the Frontend:
   ```bash
   npm run dev
   ```
   The frontend will run at `http://localhost:5173`.
