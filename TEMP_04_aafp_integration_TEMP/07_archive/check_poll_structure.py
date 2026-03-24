import json

JSON_PATH = r'C:\Users\mpsch\Desktop\claude_knowledge\board_prep\aafp_integration\02_working\session_hy_inserts_v2_adjusted.json'

with open(JSON_PATH, encoding='utf-8') as f:
    data = json.load(f)

# Find a session with poll questions
for snum, sess in data.items():
    polls = sess.get('poll_questions', [])
    if polls:
        print(f'=== Session {snum} - {len(polls)} poll questions ===')
        for i, pq in enumerate(polls[:3], 1):
            print(f'\nQ{i} keys: {list(pq.keys())}')
            for k, v in pq.items():
                print(f'  {k}: {repr(str(v))[:120]}')
        break

# Also check ITE question structure
print('\n\n=== ITE Question structure ===')
for snum, sess in data.items():
    qs = sess.get('top_questions', [])
    if qs:
        print(f'Session {snum}, Q1 keys: {list(qs[0].keys())}')
        for k, v in qs[0].items():
            print(f'  {k}: {repr(str(v))[:120]}')
        break

# Count sessions with polls
print(f'\n\nSessions with poll_questions: {sum(1 for s in data.values() if s.get("poll_questions"))}')
print(f'Total sessions: {len(data)}')
