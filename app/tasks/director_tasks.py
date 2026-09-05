"""
B3 Director Plan - Celery Task Wrapper
Stage: B3 (Director/DP Planning)
Input: story.json from B2
Output: director_plan.json + dp_plan.json
Timeout: 45 minutes
Retries: 3 with exponential backoff
"""

from app.celery_app import celery_app
import subprocess
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

@celery_app.task(
    bind=True,
    name='vf.b3.director_plan',
    max_retries=3,
    default_retry_delay=300,
    autoretry_for=(subprocess.CalledProcessError, subprocess.TimeoutExpired),
    retry_backoff=True,
    retry_backoff_max=1800,
    retry_jitter=True,
    time_limit=2700,  # 45 min hard limit
    soft_time_limit=2550,  # 42.5 min soft limit
)
def run_b3_director_plan(self, episode_id: str):
    """
    Execute B3 director/DP planning for an episode.

    Args:
        episode_id: Episode identifier (e.g., "EN_EP0251")

    Returns:
        dict: {
            "status": "success",
            "episode_id": str,
            "director_plan_path": str,
            "dp_plan_path": str,
            "execution_time": float
        }

    Raises:
        Retry on failure, up to max_retries
    """
    import time
    start_time = time.time()

    logger.info(f"[B3] Starting director plan for {episode_id} (attempt {self.request.retries + 1})")

    try:
        # Execute B3 director/DP planner
        result = subprocess.run(
            ["python3", "/root/video_factory/app/services/director_planner_b3.py", episode_id],
            check=True,
            capture_output=True,
            text=True,
            timeout=2550,
            cwd="/root/video_factory"
        )

        execution_time = time.time() - start_time

        # Verify outputs exist
        workspace = Path(f"/root/video_factory/workspace/{episode_id}")
        director_plan = workspace / "director_plan.json"
        dp_plan = workspace / "dp_plan.json"

        if not director_plan.exists():
            raise FileNotFoundError(f"B3 director_plan not found: {director_plan}")
        if not dp_plan.exists():
            raise FileNotFoundError(f"B3 dp_plan not found: {dp_plan}")

        logger.info(f"[B3] Success for {episode_id} in {execution_time:.2f}s")

        return {
            "status": "success",
            "episode_id": episode_id,
            "director_plan_path": str(director_plan),
            "dp_plan_path": str(dp_plan),
            "execution_time": execution_time,
            "stdout": result.stdout[-500:] if result.stdout else "",
        }

    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as exc:
        execution_time = time.time() - start_time
        logger.error(f"[B3] Failed for {episode_id} after {execution_time:.2f}s: {exc}")

        countdown = min(300 * (2 ** self.request.retries), 1800)
        raise self.retry(exc=exc, countdown=countdown)

    except Exception as exc:
        logger.critical(f"[B3] Unexpected error for {episode_id}: {exc}", exc_info=True)
        raise
