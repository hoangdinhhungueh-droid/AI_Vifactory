"""Generate a gradient background clip via FFmpeg when no stock clips available."""
import asyncio, os
from pathlib import Path

ASPECT_SIZES = {"9:16": (1080,1920), "16:9": (1920,1080), "1:1": (1080,1080)}

async def make_fallback_clip(output_path: str, duration_s: float = 60.0,
                             aspect: str = "9:16", color: str = "0x1a1a2e") -> str:
    """Create a solid-color background video of given duration."""
    w, h = ASPECT_SIZES.get(aspect, (1080, 1920))
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y",
        "-f", "lavfi",
        "-i", f"color=c={color}:s={w}x{h}:r=24",
        "-t", str(duration_s),
        "-c:v", "libx264", "-preset", "ultrafast", "-an",
        output_path
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"fallback_clip failed: {stderr.decode()[-200:]}")
    return output_path
