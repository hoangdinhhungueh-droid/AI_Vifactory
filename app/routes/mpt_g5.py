import os, tempfile
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from typing import Optional

router = APIRouter(prefix="/api/v1", tags=["mpt-g5"])

# LOCK 17/08/2026 (user decision): ALWAYS male voice, every market/lang.
LANG_VOICE = {
    "en": "en-US-GuyNeural",
    "vi": "vi-VN-NamMinhNeural",
    "zh": "zh-CN-YunxiNeural",
    "ja": "ja-JP-KeitaNeural",
    "ko": "ko-KR-InJoonNeural",
}

class TTSPiperRequest(BaseModel):
    text: str
    lang_code: str = "en"
    voice: Optional[str] = None
    backend: str = "auto"

@router.post("/tts-piper")
async def tts_piper(req: TTSPiperRequest):
    try:
        from app.services.mpt_ported.tts_edge import synthesize_with_fallback
        out_path = tempfile.mktemp(suffix=".mp3", dir="/tmp")
        voice = req.voice or LANG_VOICE.get(req.lang_code, "en-US-GuyNeural")
        result = await synthesize_with_fallback(
            text=req.text, voice=voice, output_path=out_path, backend=req.backend)
        size = os.path.getsize(out_path) if os.path.exists(out_path) else 0
        return {"status": "ok", "output_path": out_path, "size_bytes": size,
                "backend": result.get("backend", "unknown"), "voice": voice}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class SubtitleAlignRequest(BaseModel):
    audio_path: str
    transcript: Optional[str] = None
    lang_code: str = "en"
    backend: str = "auto"
    output_srt: Optional[str] = None

@router.post("/subtitle-align")
async def subtitle_align(req: SubtitleAlignRequest):
    try:
        from app.services.mpt_ported.subtitle_align import align_subtitles
        if not os.path.exists(req.audio_path):
            raise HTTPException(status_code=400, detail="audio_path not found: " + req.audio_path)
        segments = await align_subtitles(
            audio_path=req.audio_path, transcript=req.transcript,
            lang_code=req.lang_code, backend=req.backend)
        out_srt = req.output_srt or tempfile.mktemp(suffix=".srt", dir="/tmp")
        with open(out_srt, "w") as fout:
            for i, seg in enumerate(segments, 1):
                s = int(seg.get("start", 0) * 1000)
                e = int(seg.get("end", 0) * 1000)
                def ts(ms):
                    h, r = divmod(ms, 3600000)
                    m, r = divmod(r, 60000)
                    s2, ms2 = divmod(r, 1000)
                    return "%02d:%02d:%02d,%03d" % (h, m, s2, ms2)
                fout.write("%d\n%s --> %s\n%s\n\n" % (i, ts(s), ts(e), seg.get("text", "")))
        return {"status": "ok", "output_srt": out_srt, "segments": len(segments)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class SubtitleKaraokeRequest(BaseModel):
    video_path: str
    segments: list
    lang_code: str = "en"
    position: str = "bottom"
    font_size: int = 52
    output_path: Optional[str] = None

@router.post("/subtitle-karaoke")
async def subtitle_karaoke(req: SubtitleKaraokeRequest):
    try:
        from app.services.mpt_ported.subtitle_karaoke import render_karaoke
        if not os.path.exists(req.video_path):
            raise HTTPException(status_code=400, detail="video_path not found: " + req.video_path)
        out_path = req.output_path or tempfile.mktemp(suffix=".mp4", dir="/tmp")
        result_path = render_karaoke(
            video_path=req.video_path, segments=req.segments,
            output_path=out_path, lang_code=req.lang_code,
            position=req.position, font_size=req.font_size)
        return {"status": "ok", "output_path": result_path, "segments": len(req.segments)}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class BGMSelectRequest(BaseModel):
    mood: str = "calm"
    duration_sec: float = 60.0
    episode_id: Optional[str] = None

@router.post("/bgm-select")
async def bgm_select(req: BGMSelectRequest):
    try:
        from app.services.mpt_ported.bgm_selector import select_bgm
        result = await select_bgm(
            mood=req.mood, duration_s=req.duration_sec, episode_id=req.episode_id)
        return {"status": "ok", **result}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
