# app/celery_app.py
# VF Celery application — broker = RabbitMQ (NOT Redis broker)
# Redis chỉ dùng cho app state (rate-limit, episode lock, cache)
import os
from celery import Celery
from app.celery_config import CELERY_CONFIG

# Broker: RabbitMQ amqp vhost video_factory
# Result backend: Redis db=1 (app-state only, NOT broker)
BROKER_URL = os.environ.get(
    "CELERY_BROKER_URL",
    os.environ.get("RABBITMQ_URL", "amqp://vf_user:password@127.0.0.1:5672/video_factory")
)
RESULT_BACKEND = os.environ.get("REDIS_URL", "redis://127.0.0.1:6379/1")

celery_app = Celery(
    "vf",
    broker=BROKER_URL,
    backend=RESULT_BACKEND,
    include=["app.tasks"],
)

# Apply config from celery_config.py
celery_app.conf.update(
    task_acks_late=CELERY_CONFIG["task_acks_late"],
    task_reject_on_worker_lost=CELERY_CONFIG["task_reject_on_worker_lost"],
    task_max_retries=CELERY_CONFIG["task_max_retries"],
    worker_max_memory_per_child=CELERY_CONFIG["worker_max_memory_per_child"],
    worker_max_tasks_per_child=CELERY_CONFIG["worker_max_tasks_per_child"],
    # Serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    timezone="Asia/Ho_Chi_Minh",
    enable_utc=True,
    # Queue routing
    task_routes={
        "app.tasks.video.*": {"queue": "video_heavy"},
        "app.tasks.render.*": {"queue": "video_heavy"},
    },
    # Dead letter queue
    task_queues_kwargs={
        "default": {"x-dead-letter-exchange": "vf.dlq"},
        "video_heavy": {"x-dead-letter-exchange": "vf.dlq"},
    },
)

if __name__ == "__main__":
    celery_app.start()
