import requests, json, time, ollama

BASE = 'http://127.0.0.1:8000/api/v1'

def p(title, data):
    print(f'\n=== {title} ===')
    print(json.dumps(data, indent=2))

def get_answer(q_text, q_type, options=None):
    if q_type == "mcq":
        # Guess correct option using Ollama
        prompt = f"Question: {q_text}\nOptions: {options}\nWhich option is correct? Respond with ONLY the exact option text from the list (e.g. 'A) Python')."
        resp = ollama.chat(model="qwen2.5:1.5b", messages=[{"role": "user", "content": prompt}])
        ans = resp["message"]["content"].strip()
        print(f"   [AI MCQ Guess] -> '{ans}'")
        return ans
    else:
        # Generate good answer using Ollama
        prompt = f"Question: {q_text}\nProvide a clear, detailed, and technically accurate answer to this question for a developer interview. Keep it under 3 sentences."
        resp = ollama.chat(model="qwen2.5:1.5b", messages=[{"role": "user", "content": prompt}])
        ans = resp["message"]["content"].strip()
        print(f"   [AI Answer Gen] -> '{ans[:100]}...'")
        return ans

# Start fresh interview
r = requests.post(f'{BASE}/interviews/start', json={'job_id':1,'candidate_name':'BonusTest','candidate_email':'bonus@test.com'})
iid = r.json()['id']
print(f'Interview ID: {iid}')

# Submit 6 answers - confirm each is stored
for i in range(6):
    r = requests.get(f'{BASE}/interviews/{iid}/question')
    q = r.json()
    print(f'\nQ{i+1} shell ID={q["id"]} content="{q["content"][:50] or "(empty - will stream)"}"')

    # Trigger generation for streaming questions so the AI knows what the question is
    if q["question_type"] != "mcq" and not q.get("content"):
        stream_r = requests.get(f'{BASE}/interviews/{iid}/question/{q["id"]}/stream')
        # consume the stream
        _ = stream_r.text
        # Fetch the updated question to show its content
        r = requests.get(f'{BASE}/interviews/{iid}/question')
        q = r.json()
        print(f'   [Streamed] -> {q["content"][:60]}...')

    ans_text = get_answer(q["content"], q["question_type"], q.get("options"))

    r = requests.post(f'{BASE}/interviews/{iid}/answer', json={
        'question_id': q['id'],
        'answer': ans_text,
        'time_taken_seconds': 25 + i
    })
    resp = r.json()
    print(f'  -> stored: status={resp["status"]} | is_complete={resp["is_complete"]}')

# Generate report - ONLY after 6 stored answers
print('\n>>> Generating Final Batch Report...')
t0 = time.time()
r = requests.get(f'{BASE}/interviews/{iid}/report')
elapsed = round(time.time() - t0, 2)
report = r.json()
p(f'FINAL REPORT ({elapsed}s | answers_evaluated={report.get("answers_evaluated")})', report)

final_score = report.get('final_score', 0)
print(f"Final Score: {final_score}")
assert final_score > 40, f"Score should be decent for good answers, got {final_score}"
assert len(report.get("question_evaluations", [])) == 6, "Should evaluate all 6 questions"
print('\n[PASS] Full flow completed successfully with valid answers.')
