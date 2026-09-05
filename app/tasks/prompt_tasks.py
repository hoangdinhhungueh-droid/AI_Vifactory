"""
B3.5 Prompt Forge - Celery Task Wrapper
Stage: B3.5 (Prompt Forge - Image Generation Prompts)
Input: director_plan.json + dp_plan.json from B3
Output: prompts_forge.json
Timeout: 60 minutes (LLM-heavy)
Retries: 3 with exponential backoff
"""

from app.celery_app import celery_app
import subprocess
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

@celery_app.task(
    bind=True,
    name='vf.b3_5.prompt_forge',
    max_retries=3,
    default_retry_delay=300,
    autoretry_for=(subprocess.CalledProcessError, subprocess.TimeoutExpired),
    retry_backoff=True,
    retry_backoff_max=1800,
    retry_jitter=True,
    time_limit=3600,  # 60 min hard limit
    soft_time_limit=3450,  # 57.5 min soft limit
)
def run_b3_5_prompt_forge(self, episode_id: str):
    """
    Execute B3.5 prompt forge for an episode.

    Args:
        episode_id: Episode identifier (e.g., "EN_EP0251")

    Returns:
        dict: {
            "status": "success",
            "episode_id": str,
            "output_path": str,
            "prompt_count": int,
            "execution_time": float
        }

    Raises:
        Retry on failure, up to max_retries
    """
    import time
    import json
    start_time = time.time()

    logger.info(f"[B3.5] Starting prompt forge for {episode_id} (attempt {self.request.retries + 1})")

    try:
        # Execute B3.5 prompt forge
        result = subprocess.run(
            ["python3", "/root/video_factory/app/services/prompt_forge_b3_5.py", episode_id],
            check=True,
            capture_output=True,
            text=True,
            timeout=3450,
            cwd="/root/video_factory"
        )

        execution_time = time.time() - start_time

        # Verify output exists and count prompts
        output_path = Path(f"/root/video_factory/workspace/{episode_id}/prompts_forge.json")
        if not output_path.exists():
            raise FileNotFoundError(f"B3.5 output not found: {output_path}")

        # Count prompts generated
        with open(output_path, 'r', encoding='utf-8') as f:
            prompts_data = json.load(f)
            prompt_count = len(prompts_data.get('prompts', []))

        logger.info(f"[B3.5] Success for {episode_id} in {execution_time:.2f}s ({prompt_count} prompts)")

        return {
            "status": "success",
            "episode_id": episode_id,
            "output_path": str(output_path),
            "prompt_count": prompt_count,
            "execution_time": execution_time,
            "stdout": result.stdout[-500:] if result.stdout else "",
        }

    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as exc:
        execution_time = time.time() - start_time
        logger.error(f"[B3.5] Failed for {episode_id} after {execution_time:.2f}s: {exc}")

        countdown = min(300 * (2 ** self.request.retries), 1800)
        raise self.retry(exc=exc, countdown=countdown)

    except Exception as exc:
        logger.critical(f"[B3.5] Unexpected error for {episode_id}: {exc}", exc_info=True)
        raise
