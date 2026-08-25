"""VPS Visual Engine - PERMANENTLY DISABLED (Rule 120 / Decision 22/08/2026).

All visual assets (Layer 1 Background 16:9 & Layer 2 Foreground 1:1 Chroma-key)
are 100% generated via Google Image Native Forge in Antigravity UI (B4)
following prompts forged in B3.5 (Notion Prompt Library DB).
Zero fallback on VPS.
"""
from typing import Optional
from loguru import logger

async def gen_reference_image(*args, **kwargs):
    raise RuntimeError(
        "VPS Visual Engine is OFF (Rule 120). All images must be generated via Google Image in Antigravity UI (B4) and synced to Notion Image Asset Library."
    )

async def gen_scene_image(*args, **kwargs):
    raise RuntimeError(
        "VPS Visual Engine is OFF (Rule 120). All images must be generated via Google Image in Antigravity UI (B4) and synced to Notion Image Asset Library."
    )
