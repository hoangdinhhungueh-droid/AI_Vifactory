"""POST /api/v1/run-episode — full S2->S7 production pipeline."""
import asyncio, logging
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

from app.pipeline.run_episode import run_pipeline

logger = logging.getLogger(__name__)
router = APIRouter()

class RunEpisodeRequest(BaseModel):
    episode_id: Optional[str] = None
    niche: str = "betrayal revenge"
    lang_code: str = "en"
    tts_backend: str = "auto"

@router.post("/api/v1/run-episode")
async def run_episode_endpoint(req: RunEpisodeRequest):
    """Kick off full pipeline: story -> TTS -> visuals -> subtitle -> render."""
    try:
        result = await run_pipeline(
            episode_id=req.episode_id,
            niche=req.niche,
            lang_code=req.lang_code,
            tts_backend=req.tts_backend,
        )
        return {"status": "ok", "result": result}
    except Exception as e:
        logger.exception("[run_episode] pipeline failed")
        raise HTTPException(status_code=500, detail=str(e))
