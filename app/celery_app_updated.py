"""
VF Pipeline - Celery Application Configuration (Pattern 2)
Updated: 2026-09-02
Changes from original:
- Broker: RabbitMQ → Redis (redis://localhost:6379/0)
- Backend: Redis for result storage
- Added: Task tracking, time limits, error handling config
"""

from celery import Celery
from celery.signals import task_failure, task_success, task_retry
import logging

logger = logging.getLogger(__name__)

# Initialize Celery app
celery_app = Celery(
    'vf_pipeline',
    broker='redis://localhost:6379/0',
    backend='redis://localhost:6379/0',
    include=[
        'app.tasks.story_tasks',
        'app.tasks.director_tasks',
        'app.tasks.prompt_tasks',
        'app.tasks.audio_tasks',
        'app.tasks.subtitle_tasks',
        'app.tasks.render_tasks',
        'app.tasks.quality_tasks',
    ]
)

# Celery configuration
celery_app.conf.update(
    # Serialization
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',

    # Timezone
    timezone='UTC',
    enable_utc=True,

    # Task tracking
    task_track_started=True,
    task_send_sent_event=True,

    # Time limits (global defaults)
    task_time_limit=3600,        # 1 hour hard limit
    task_soft_time_limit=3300,   # 55 min soft limit

    # Result backend settings
    result_expires=86400,         # Results expire after 24 hours
    result_extended=True,         # Store more metadata

    # Retry settings
    task_acks_late=True,          # Acknowledge after task completes
    task_reject_on_worker_lost=True,

    # Worker settings
    worker_prefetch_multiplier=1, # Process one task at a time per worker
    worker_max_tasks_per_child=100, # Restart worker after 100 tasks

    # Logging
    worker_log_format='[%(asctime)s: %(levelname)s/%(processName)s] %(message)s',
    worker_task_log_format='[%(asctime)s: %(levelname)s/%(processName)s][%(task_name)s(%(task_id)s)] %(message)s',
)

# Task routing (can add specific queues later)
celery_app.conf.task_routes = {
    'app.tasks.story_tasks.*': {'queue': 'story'},
    'app.tasks.director_tasks.*': {'queue': 'director'},
    'app.tasks.prompt_tasks.*': {'queue': 'prompt'},
    'app.tasks.audio_tasks.*': {'queue': 'audio'},
    'app.tasks.subtitle_tasks.*': {'queue': 'subtitle'},
    'app.tasks.render_tasks.*': {'queue': 'render'},
    'app.tasks.quality_tasks.*': {'queue': 'quality'},
}

# Signal handlers for logging
@task_failure.connect
def task_failure_handler(sender=None, task_id=None, exception=None, args=None, kwargs=None, traceback=None, einfo=None, **kw):
    logger.error(f"Task {sender.name}[{task_id}] failed: {exception}")

@task_success.connect
def task_success_handler(sender=None, result=None, **kwargs):
    logger.info(f"Task {sender.name} completed successfully")

@task_retry.connect
def task_retry_handler(sender=None, task_id=None, reason=None, einfo=None, **kwargs):
    logger.warning(f"Task {sender.name}[{task_id}] retrying: {reason}")
