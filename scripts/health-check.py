#!/usr/bin/env python3
"""VF Health Check - verifies key services are running."""
import subprocess, sys

checks = [
    ('PostgreSQL', 'pg_isready'),
    ('Redis', 'redis-cli ping'),
    ('Celery', 'ps aux | grep celery | grep -v grep'),
]

all_ok = True
for name, cmd in checks:
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, timeout=10)
        ok = result.returncode == 0
        if not ok:
            all_ok = False
        print(f'  {name}: {"OK" if ok else "FAIL"}')
    except Exception as e:
        all_ok = False
        print(f'  {name}: ERROR ({e})')

# Check swap
with open('/proc/meminfo') as f:
    for line in f:
        if line.startswith('SwapTotal'):
            swap = line.split()[1]
            if int(swap) == 0:
                print('  Swap: WARNING - 0 bytes')
            else:
                print(f'  Swap: {int(swap)//1024}MB OK')

# Check disk
result = subprocess.run('df / | tail -1', shell=True, capture_output=True, text=True)
parts = result.stdout.split()
if len(parts) >= 5:
    pct = parts[4].rstrip('%')
    if pct and int(pct) > 90:
        all_ok = False
        print(f'  Disk: WARNING - {pct}% used')
    else:
        print(f'  Disk: {pct}% used OK')

sys.exit(0 if all_ok else 1)
