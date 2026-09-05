"""
B9 Quality Probe - Celery Task Wrapper
Stage: B9 (Video Quality Verification)
Input: Final video from B8
Output: Quality report JSON in workspace
Timeout: 20 minutes
Retries: 3 with exponential backoff
"""

from app.celery_app import celery_app
import subprocess
import logging
from pathlib import Path

logger = logging.getLogger(__name__)

@celery_app.task(
    bind=True,
    name='vf.b9.quality_probe',
    max_retries=3,
    default_retry_delay=180,  # 3 min base (quick stage)
    autoretry_for=(subprocess.CalledProcessError, subprocess.TimeoutExpired),
    retry_backoff=True,
    retry_backoff_max=900,
    retry_jitter=True,
    time_limit=1200,  # 20 min hard limit
    soft_time_limit=1080,  # 18 min soft limit
)
def run_b9_quality_probe(self, episode_id: str):
    """
    Execute B9 quality verification for an episode.

    Args:
        episode_id: Episode identifier (e.g., "EN_EP0251")

    Returns:
        dict: {
            "status": "success",
            "episode_id": str,
            "quality_report_path": str,
            "quality_score": float,
            "issues_found": int,
            "execution_time": float
        }

    Raises:
        Retry on failure, up to max_retries
    """
    import time
    import json
    start_time = time.time()

    logger.info(f"[B9] Starting quality probe for {episode_id} (attempt {self.request.retries + 1})")

    try:
        # Execute B9 quality probe
        result = subprocess.run(
            ["python3", "/root/video_factory/app/services/quality_probe_b9.py", episode_id],
            check=True,
            capture_output=True,
            text=True,
            timeout=1080,
            cwd="/root/video_factory"
        )

        execution_time = time.time() - start_time

        # Verify quality report exists
        workspace = Path(f"/root/video_factory/workspace/{episode_id}")
        quality_report = workspace / "quality_report.json"

        if not quality_report.exists():
            raise FileNotFoundError(f"B9 quality report not found: {quality_report}")

        # Parse quality metrics
        with open(quality_report, 'r', encoding='utf-8') as f:
            quality_data = json.load(f)
            quality_score = quality_data.get('overall_score', 0.0)
            issues_found = len(quality_data.get('issues', []))

        logger.info(f"[B9] Success for {episode_id} in {execution_time:.2f}s (score: {quality_score}, issues: {issues_found})")

        return {
            "status": "success",
            "episode_id": episode_id,
            "quality_report_path": str(quality_report),
            "quality_score": quality_score,
            "issues_found": issues_found,
            "execution_time": execution_time,
            "stdout": result.stdout[-500:] if result.stdout else "",
        }

    except (subprocess.CalledProcessError, subprocess.TimeoutExpired, FileNotFoundError) as exc:
        execution_time = time.time() - start_time
        logger.error(f"[B9] Failed for {episode_id} after {execution_time:.2f}s: {exc}")

        countdown = min(180 * (2 ** self.request.retries), 900)
        raise self.retry(exc=exc, countdown=countdown)

    except Exception as exc:
        logger.critical(f"[B9] Unexpected error for {episode_id}: {exc}", exc_info=True)
        raise
