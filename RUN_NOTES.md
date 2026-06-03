# How to Run the AI Interview Platform

Whenever you want to start the project from scratch, open **two separate terminal windows** and follow these steps.

---

## Step 1 — Start the Backend (API & AI Service)

Open your **first terminal** and run:

```powershell
cd "C:\Users\nadie\Desktop\Agent Interview\backend"
.\venv\Scripts\activate
python -X utf8 -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

> **Important:** The `-X utf8` flag is required on Windows to prevent encoding crashes when AI-generated text contains special characters.
>
> The backend API will be running at: **http://127.0.0.1:8000/docs**

---

## Step 2 — Start the Frontend (User Interface)

Open a **second terminal** and run:

```powershell
cd "C:\Users\nadie\Desktop\Agent Interview\frontend"
npm run dev
```

> The website will be running at: **http://localhost:5173**

---

## Step 3 — Make Sure Ollama AI is Running

If you restarted your computer, make sure Ollama is running in the background. Open any terminal and run:

```powershell
ollama run qwen2.5:1.5b
```

*(After the model loads, you can close or minimize that terminal — Ollama stays running in the system tray.)*

---

## Quick Troubleshooting

| Problem | Solution |
|---|---|
| `ModuleNotFoundError` | Forgot to activate venv — run `.\venv\Scripts\activate` first |
| Port 8000 / 5173 in use | Old terminal still running — close it or press `CTRL+C` |
| "Generating AI Analytics..." stuck | Backend is processing — wait up to 90 seconds; the page retries automatically |
| Backend crashes with `UnicodeEncodeError` | Make sure you used `python -X utf8` when starting uvicorn |
| Report shows 0 score / Reject for good answers | Restart Ollama: `ollama run qwen2.5:1.5b` |
| Frontend not updating | Hard refresh the browser: `CTRL + SHIFT + R` |
