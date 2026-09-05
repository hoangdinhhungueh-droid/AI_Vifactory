"""
B2 Story Generation - Celery Task Wrapper
Stage: B2 (Story Engine)
Input: Episode ID from Notion
Output: story.json in episode workspace
Timeout: 30 minutes
Retries: 3 with exponential backoff
"""

from app.celery_app import celery_app
import subprocess
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

@celery_app.task(
    bind=True,
    name='vf.b2.story_generation',
    max_retries=3,
    default_retry_delay=300,  # 5 minutes base
    autoretry_for=(subprocess.CalledProcessError, subprocess.TimeoutExpired),
    retry_backoff=True,
    retry_backoff_max=1800,  # Max 30 min between retries
    retry_jitter=True,
    time_limit=1800,  # 30 min hard limit
    soft_time_limit=1650,  # 27.5 min soft limit
)
def run_b2_story_generation(self, episode_id: str):
    """
    Execute B2 story generation for an episode.

    Args:
        episode_id: Episode identifier (e.g., "EN_EP0251")

    Returns:
        dict: {
            "status": "success",
            "episode_id": str,
            "output_path": str,
            "execution_time": float
        }

    Raises:
        Retry on failure, up to max_retries
    """
    import time
    start_time = time.time()

    logger.info(f"[B2] Starting story generation for {episode_id} (attempt {self.request.retries + 1})")

    try:
        # Execute B2 story engine
        result = subprocess.run(
            ["python3", "/root/video_factory/app/services/story_engine_b2.py", episode_id],
            check=True,
            capture_output=True,
            text=True,
            timeout=1650,  # Match soft_time_limit
            cwd="/root/video_factory"
        )

        execution_time = time.time() - start_time

        # Verify output exists
        output_path = f"/root/video_factory/workspace/{episode_id}/story.json"
        if not Path(output_path).exists():
            raise FileNotFoundError(f"B2 output not found: {output_path}")

        logger.info(f"[B2] Success for {episode_id} in {execution_time:.2f}s")

        return {
            "status": "success",
            "episode_id": episode_id,
            "output_path": output_path,
            "execution_time": execution_time,
            "stdout": result.stdout[-500:] if result.stdout else "",  # Last 500 chars
        }

    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as exc:
        execution_time = time.time() - start_time
        logger.error(f"[B2] Failed for {episode_id} after {execution_time:.2f}s: {exc}")

        # Calculate exponential backoff countdown
        countdown = min(300 * (2 ** self.request.retries), 1800)

        # Retry with exponential backoff
        raise self.retry(exc=exc, countdown=countdown)

    except Exception as exc:
        # Unexpected errors - log and fail without retry
        logger.critical(f"[B2] Unexpected error for {episode_id}: {exc}", exc_info=True)
        raise
