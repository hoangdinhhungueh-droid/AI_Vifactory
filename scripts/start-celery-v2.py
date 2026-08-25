#!/usr/bin/env python3
"""VF Celery Starter v2 — loads env from secrets and starts celery workers
Run: /root/video_factory/venv/bin/python /root/video_factory/scripts/start-celery-v2.py
"""
import os
import sys
import subprocess
import time

sys.path.insert(0, '/root/video_factory')

# Load environment from secrets directory
from dotenv import load_dotenv
env_file = os.path.join('/root', 'secrets', os.extsep + 'env')
load_dotenv(env_file)

os.chdir('/root/video_factory')
venv_celery = '/root/video_factory/venv/bin/celery'

# Stop existing workers
subprocess.run(['pkill', '-f', 'celery.*app.celery_app'], capture_output=True)
time.sleep(1)

# Start default queue (c=2)
subprocess.run([
    venv_celery, '-A', 'app.celery_app', 'worker', '-Q', 'default', '-c', '2',
    '--detach', '--logfile=/tmp/vf/celery-default.log'
])

# Start video_heavy queue (c=1)
subprocess.run([
    venv_celery, '-A', 'app.celery_app', 'worker', '-Q', 'video_heavy', '-c', '1',
    '--detach', '--logfile=/tmp/vf/celery-heavy.log'
])

time.sleep(2)

# Check
result = subprocess.run(['pgrep', '-a', 'celery'], capture_output=True, text=True)
print(result.stdout[:500] if result.stdout else "No celery processes found")
print("Celery workers started.")
