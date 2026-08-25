
with open('/root/video_factory/app/services/trend_raw.py', 'r', encoding='utf-8') as f:
    raw_lines = f.readlines()
print('=== trend_raw.py (first 40 lines) ===')
for l in raw_lines[:40]:
    print(l.rstrip())

with open('/root/video_factory/app/services/trend_refine.py', 'r', encoding='utf-8') as f:
    ref_lines = f.readlines()
print('\n=== trend_refine.py (first 40 lines) ===')
for l in ref_lines[:40]:
    print(l.rstrip())
