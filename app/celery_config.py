CELERY_CONFIG = {
    "task_acks_late": True,
    "task_reject_on_worker_lost": True,
    "task_max_retries": 3,
    "worker_max_memory_per_child": 900000,   # T5: 450000 -> 900000 (KB ~ 900MB)
    "worker_concurrency": 2,                  # default giu c=2 (4 vCPU, FFmpeg CPU-bound)
    "worker_max_tasks_per_child": 10,
}
