"""
B7 Subtitle Generation - Celery Task Wrapper
Stage: B7 (Subtitle/Caption Generation)
Input: audio files from B6 + timing data
Output: subtitle files (.srt, .vtt) in workspace
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
    name='vf.b7.subtitle_generation',
    max_retries=3,
    default_retry_delay=300,
    autoretry_for=(subprocess.CalledProcessError, subprocess.TimeoutExpired),
    retry_backoff=True,
    retry_backoff_max=1800,
    retry_jitter=True,
    time_limit=1800,  # 30 min hard limit
    soft_time_limit=1650,  # 27.5 min soft limit
)
def run_b7_subtitle_generation(self, episode_id: str):
    """
    Execute B7 subtitle generation for an episode.

    Args:
        episode_id: Episode identifier (e.g., "EN_EP0251")

    Returns:
        dict: {
            "status": "success",
            "episode_id": str,
            "subtitle_files": list,
            "execution_time": float
        }

    Raises:
        Retry on failure, up to max_retries
    """
    import time
    start_time = time.time()

    logger.info(f"[B7] Starting subtitle generation for {episode_id} (attempt {self.request.retries + 1})")

    try:
        # Execute B7 subtitle generator
        result = subprocess.run(
            ["python3", "/root/video_factory/app/services/subtitle_generator_b7.py", episode_id],
            check=True,
            capture_output=True,
            text=True,
            timeout=1650,
            cwd="/root/video_factory"
        )

        execution_time = time.time() - start_time

        # Verify subtitle outputs exist
        workspace = Path(f"/root/video_factory/workspace/{episode_id}")
        subtitle_files = list(workspace.glob("*.srt")) + list(workspace.glob("*.vtt"))

        if not subtitle_files:
            raise FileNotFoundError(f"B7 no subtitle files generated in {workspace}")

        logger.info(f"[B7] Success for {episode_id} in {execution_time:.2f}s ({len(subtitle_files)} files)")

        return {
            "status": "success",
            "episode_id": episode_id,
            "subtitle_files": [str(f.relative_to(workspace)) for f in subtitle_files],
            "subtitle_count": len(subtitle_files),
            "execution_time": execution_time,
            "stdout": result.stdout[-500:] if result.stdout else "",
        }

    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as exc:
        execution_time = time.time() - start_time
        logger.error(f"[B7] Failed for {episode_id} after {execution_time:.2f}s: {exc}")

        countdown = min(300 * (2 ** self.request.retries), 1800)
        raise self.retry(exc=exc, countdown=countdown)

    except Exception as exc:
        logger.critical(f"[B7] Unexpected error for {episode_id}: {exc}", exc_info=True)
        raise
