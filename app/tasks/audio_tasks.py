"""
B6 Audio Generation - Celery Task Wrapper
Stage: B6 (TTS + Background Music)
Input: script.json from B5
Output: audio files (speech + music) in workspace
Timeout: 90 minutes (TTS can be slow)
Retries: 3 with exponential backoff
"""

from app.celery_app import celery_app
import subprocess
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

@celery_app.task(
    bind=True,
    name='vf.b6.audio_generation',
    max_retries=3,
    default_retry_delay=600,  # 10 min base (TTS can have rate limits)
    autoretry_for=(subprocess.CalledProcessError, subprocess.TimeoutExpired),
    retry_backoff=True,
    retry_backoff_max=3600,  # Max 60 min between retries
    retry_jitter=True,
    time_limit=5400,  # 90 min hard limit
    soft_time_limit=5100,  # 85 min soft limit
)
def run_b6_audio_generation(self, episode_id: str):
    """
    Execute B6 audio generation for an episode.

    Args:
        episode_id: Episode identifier (e.g., "EN_EP0251")

    Returns:
        dict: {
            "status": "success",
            "episode_id": str,
            "audio_files": list,
            "execution_time": float
        }

    Raises:
        Retry on failure, up to max_retries
    """
    import time
    start_time = time.time()

    logger.info(f"[B6] Starting audio generation for {episode_id} (attempt {self.request.retries + 1})")

    try:
        # Execute B6 audio generation
        result = subprocess.run(
            ["python3", "/root/video_factory/app/services/audio_generator_b6.py", episode_id],
            check=True,
            capture_output=True,
            text=True,
            timeout=5100,
            cwd="/root/video_factory"
        )

        execution_time = time.time() - start_time

        # Verify audio outputs exist
        workspace = Path(f"/root/video_factory/workspace/{episode_id}")
        audio_dir = workspace / "audio"

        if not audio_dir.exists():
            raise FileNotFoundError(f"B6 audio directory not found: {audio_dir}")

        # List generated audio files
        audio_files = [str(f.relative_to(workspace)) for f in audio_dir.glob("*.wav")]

        if not audio_files:
            raise FileNotFoundError(f"B6 no audio files generated in {audio_dir}")

        logger.info(f"[B6] Success for {episode_id} in {execution_time:.2f}s ({len(audio_files)} files)")

        return {
            "status": "success",
            "episode_id": episode_id,
            "audio_files": audio_files,
            "audio_count": len(audio_files),
            "execution_time": execution_time,
            "stdout": result.stdout[-500:] if result.stdout else "",
        }

    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as exc:
        execution_time = time.time() - start_time
        logger.error(f"[B6] Failed for {episode_id} after {execution_time:.2f}s: {exc}")

        countdown = min(600 * (2 ** self.request.retries), 3600)
        raise self.retry(exc=exc, countdown=countdown)

    except Exception as exc:
        logger.critical(f"[B6] Unexpected error for {episode_id}: {exc}", exc_info=True)
        raise
