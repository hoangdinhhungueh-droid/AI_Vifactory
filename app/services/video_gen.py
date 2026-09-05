"""
video_gen.py - DEPRECATED (03/07, Decisions Log Moc 1 Item 1.13).

Kie.ai Veo 3 Fast (paid image-to-video, ~$0.05/s) and the Credit Gate ($25/mo cap)
were removed from the real Visual Engine per CONTENT SPEC v1.1: NO paid video AI,
FREE-only images (Antigravity Google Image) + Ken Burns motion on
stills (see app/pipeline/stages/s5_visuals.py::_gen_ai_clip / _antigravity_kenburns_clip).

This module is kept only as a hard-disabled stub so any stale caller fails loudly
instead of silently billing Kie.ai. Do not re-enable without a new Decisions Log
entry + explicit "toa" propagation.
"""
from typing import List, Optional


async def generate_video_kie_veo(
    prompt: str,
    image_url: Optional[str] = None,
    image_urls: Optional[List[str]] = None,
    duration: Optional[int] = None,
    resolution: Optional[str] = None,
    aspect_ratio: Optional[str] = None,
    model: Optional[str] = None,
    enable_fallback: bool = False,
    poll_interval: int = 15,
    max_wait: int = 600,
) -> dict:
    raise RuntimeError(
        "[Veo] DISABLED per Decisions Log Moc 1 Item 1.13 (03/07): paid video AI "
        "(Kie Veo) and Credit Gate were removed from the real Visual Engine. "
        "Use the FREE image + Ken Burns pipeline in s5_visuals.py instead."
    )


async def test_kie_connection() -> bool:
    return False
