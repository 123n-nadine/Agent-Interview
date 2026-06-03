import requests
import time
import json

BASE_URL = "http://127.0.0.1:8000/api/v1"

def print_section(title, data):
    print(f"\n{'='*50}\n{title}\n{'='*50}")
    print(json.dumps(data, indent=2))

try:
    # 1. Start Interview
    print("1. Starting interview...")
    start_payload = {
        "job_id": 1, 
        "candidate_name": "Test User",
        "candidate_email": "test@example.com"
    }
    r = requests.post(f"{BASE_URL}/interviews/start", json=start_payload)
    interview = r.json()
    print_section("Started Interview", interview)
    interview_id = interview["id"]

    # 2. Get Question
    print("\n2. Generating first question (Ollama)...")
    t0 = time.time()
    r = requests.get(f"{BASE_URL}/interviews/{interview_id}/question")
    question = r.json()
    print_section(f"Question Generated (Took {time.time()-t0:.2f}s)", question)
    question_id = question["id"]

    # 3. Submit Answer
    print("\n3. Evaluating answer (Ollama)...")
    answer_payload = {
        "question_id": question_id,
        "answer": "I have extensive experience with Node.js and React. I use Express for my backends and Redux for state management.",
        "time_taken_seconds": 45
    }
    t0 = time.time()
    r = requests.post(f"{BASE_URL}/interviews/{interview_id}/answer", json=answer_payload)
    evaluation = r.json()
    print_section(f"Answer Evaluated (Took {time.time()-t0:.2f}s)", evaluation)

    # 4. Get Report
    print("\n4. Generating Final Report (Ollama)...")
    t0 = time.time()
    r = requests.get(f"{BASE_URL}/interviews/{interview_id}/report")
    report = r.json()
    print_section(f"Final Report Generated (Took {time.time()-t0:.2f}s)", report)

except Exception as e:
    print(f"Test failed: {e}")
