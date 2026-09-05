"""
B8 Video Render - Celery Task Wrapper
Stage: B8 (Video Rendering via Remotion)
Input: All assets (images, audio, subtitles) from B4-B7
Output: Final video file (.mp4) in workspace
Timeout: 120 minutes (rendering is CPU-intensive)
Retries: 2 (limited due to long execution time)
"""

from app.celery_app import celery_app
import subprocess
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

@celery_app.task(
    bind=True,
    name='vf.b8.video_render',
    max_retries=2,  # Only 2 retries due to long execution
    default_retry_delay=900,  # 15 min base
    autoretry_for=(subprocess.CalledProcessError, subprocess.TimeoutExpired),
    retry_backoff=True,
    retry_backoff_max=3600,
    retry_jitter=True,
    time_limit=7200,  # 120 min hard limit
    soft_time_limit=6900,  # 115 min soft limit
)
def run_b8_video_render(self, episode_id: str):
    """
    Execute B8 video rendering for an episode.

    Args:
        episode_id: Episode identifier (e.g., "EN_EP0251")

    Returns:
        dict: {
            "status": "success",
            "episode_id": str,
            "video_path": str,
            "video_size_mb": float,
            "execution_time": float
        }

    Raises:
        Retry on failure, up to max_retries
    """
    import time
    start_time = time.time()

    logger.info(f"[B8] Starting video render for {episode_id} (attempt {self.request.retries + 1})")

    try:
        # Execute B8 video renderer
        result = subprocess.run(
            ["python3", "/root/video_factory/app/services/video_renderer_b8.py", episode_id],
            check=True,
            capture_output=True,
            text=True,
            timeout=6900,
            cwd="/root/video_factory"
        )

        execution_time = time.time() - start_time

        # Verify video output exists
        workspace = Path(f"/root/video_factory/workspace/{episode_id}")
        video_files = list(workspace.glob("*.mp4"))

        if not video_files:
            raise FileNotFoundError(f"B8 no video file generated in {workspace}")

        # Get the most recent video file
        video_path = max(video_files, key=lambda p: p.stat().st_mtime)
        video_size_mb = video_path.stat().st_size / (1024 * 1024)

        logger.info(f"[B8] Success for {episode_id} in {execution_time:.2f}s ({video_size_mb:.2f} MB)")

        return {
            "status": "success",
            "episode_id": episode_id,
            "video_path": str(video_path),
            "video_size_mb": round(video_size_mb, 2),
            "execution_time": execution_time,
            "stdout": result.stdout[-500:] if result.stdout else "",
        }

    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as exc:
        execution_time = time.time() - start_time
        logger.error(f"[B8] Failed for {episode_id} after {execution_time:.2f}s: {exc}")

        # Longer countdown for render retries
        countdown = min(900 * (2 ** self.request.retries), 3600)
        raise self.retry(exc=exc, countdown=countdown)

    except Exception as exc:
        logger.critical(f"[B8] Unexpected error for {episode_id}: {exc}", exc_info=True)
        raise
