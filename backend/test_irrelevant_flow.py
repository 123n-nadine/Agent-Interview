"""
test_irrelevant_flow.py
Verifies that gibberish/random answers → score < 40 and hiring_decision = "Reject"
"""
import requests, json, time

BASE = 'http://127.0.0.1:8000/api/v1'

def p(title, data):
    print(f'\n{"="*60}\n{title}\n{"="*60}')
    print(json.dumps(data, indent=2))

# Start fresh interview
r = requests.post(f'{BASE}/interviews/start', json={
    'job_id': 1,
    'candidate_name': 'GibberishTest',
    'candidate_email': 'gibberish@test.com'
})
r.raise_for_status()
iid = r.json()['id']
print(f'\n[INFO] Started interview ID={iid}')

# Submit 6 deliberately terrible/gibberish answers
answers = [
    'A',          # MCQ: might be correct or wrong
    'B',          # MCQ: random choice
    'dwdw',       # Gibberish #1
    'ksw',        # Gibberish #2
    'asdf',       # Gibberish #3
    'ef',         # Gibberish #4
]

for i, ans_text in enumerate(answers):
    r = requests.get(f'{BASE}/interviews/{iid}/question')
    r.raise_for_status()
    q = r.json()
    q_type = q.get('question_type', 'unknown')
    q_preview = q.get('content', '')[:60] or '(empty - will stream)'
    print(f'\nQ{i+1} [{q_type}] id={q["id"]} | "{q_preview}"')
    if q.get('options'):
        print(f'   Options: {q["options"]}')

    r = requests.post(f'{BASE}/interviews/{iid}/answer', json={
        'question_id': q['id'],
        'answer': ans_text,
        'time_taken_seconds': 5
    })
    r.raise_for_status()
    resp = r.json()
    print(f'   -> stored: is_complete={resp["is_complete"]}')

# Generate report
print('\n\n>>> Generating Final Batch Report (gibberish test)...')
t0 = time.time()
r = requests.get(f'{BASE}/interviews/{iid}/report')
elapsed = round(time.time() - t0, 2)
report = r.json()
p(f'FINAL REPORT ({elapsed}s)', report)

# Assertions
final_score = report.get('final_score', 999)
decision = report.get('hiring_decision', '')
evals = report.get('question_evaluations', [])

print(f'\n{"="*60}')
print('VALIDATION RESULTS:')
print(f'{"="*60}')
print(f'  final_score    = {final_score}')
print(f'  hiring_decision = "{decision}"')
print(f'  questions_in_report = {len(evals)}')

assert final_score < 40, f"FAIL: Score should be < 40 for gibberish answers, got {final_score}"
assert decision == "Reject", f"FAIL: Decision should be 'Reject', got '{decision}'"
assert len(evals) > 0, "FAIL: Question evaluations should not be empty"

print('\n[PASS] ALL ASSERTIONS PASSED: Gibberish answers correctly trigger rejection and low score!')
