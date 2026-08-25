# app/tasks.py
# VF Celery tasks — imported by celery_app via include=["app.tasks"]
import os
import logging
from app.celery_app import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(
    bind=True,
    max_retries=3,
    default_retry_delay=30,
    queue="default",
    name="app.tasks.run_pipeline_stage",
)
def run_pipeline_stage(self, stage: str, episode_id: str, payload: dict = None):
    """
    Generic pipeline stage runner.
    Called by n8n workflows via /api/v1/pipeline/run endpoint.
    """
    try:
        logger.info(f"[task] run_pipeline_stage stage={stage} episode_id={episode_id}")
        # Stage dispatch
        if stage == "S1":
            from app.s1_score import score_pipeline_run
            return score_pipeline_run(payload or {})
        elif stage == "S7_upload":
            logger.info(f"[task] S7 upload queued for {episode_id}")
            return {"status": "queued", "episode_id": episode_id, "stage": stage}
        elif stage == "S9_dreaming":
            logger.info(f"[task] S9 dreaming loop triggered")
            return {"status": "ok", "stage": "S9"}
        else:
            logger.info(f"[task] stage={stage} queued (not yet implemented)")
            return {"status": "queued", "stage": stage, "episode_id": episode_id}
    except Exception as exc:
        logger.error(f"[task] FAILED stage={stage}: {exc}")
        raise self.retry(exc=exc, countdown=30)


@celery_app.task(
    bind=True,
    max_retries=2,
    default_retry_delay=60,
    queue="video_heavy",
    name="app.tasks.video.render_episode",
)
def render_episode(self, episode_id: str, market_code: str = "US", options: dict = None):
    """
    Heavy render task — runs in video_heavy queue (c=1, timeout=7200s).
    """
    try:
        logger.info(f"[task] render_episode episode_id={episode_id} market={market_code}")
        # TODO: integrate MPT-G4 video_render.py when available
        return {"status": "ok", "episode_id": episode_id, "market_code": market_code}
    except Exception as exc:
        logger.error(f"[task] render FAILED {episode_id}: {exc}")
        raise self.retry(exc=exc, countdown=60)
