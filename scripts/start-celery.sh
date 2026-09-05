#!/bin/bash
# VF Celery Workers — start default + video_heavy queues
# Created by Notion AI audit 15/08/2026
set -euo pipefail
cd /root/video_factory
source venv/bin/activate
set -a
source .env 2>/dev/null || true
set +a

# Stop existing workers if any
pkill -f 'celery.*app.celery_app' 2>/dev/null || true
sleep 1

# Start default queue (c=2, 900MB max per child)
celery -A app.celery_app worker -Q default -c 2 \
  --detach --logfile=/tmp/vf/celery-default.log

# Start video_heavy queue (c=1, for FFmpeg/Wan render)
celery -A app.celery_app worker -Q video_heavy -c 1 \
  --detach --logfile=/tmp/vf/celery-heavy.log

sleep 2
pgrep -a celery | head -10
echo "Celery workers started."
