
import os, glob

matches = []
for root, dirs, files in os.walk('/root/video_factory/app'):
    for f in files:
        if f.endswith('.py'):
            p = os.path.join(root, f)
            try:
                with open(p, 'r', encoding='utf-8', errors='ignore') as fp:
                    for idx, line in enumerate(fp):
                        if any(term in line.lower() for term in ['hhtech', 'sol', 'gpt-5', 'llm_client', 'reasoning', 'chat/completions']):
                            matches.append(f"{p}:{idx+1} {line.strip()[:120]}")
            except Exception:
                pass

print('Found matches:')
for m in matches[:30]:
    print(m)
