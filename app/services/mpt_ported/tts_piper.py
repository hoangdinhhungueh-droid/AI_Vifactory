
"""MPT-G2-3 - Piper TTS offline fallback."""
import asyncio, os, subprocess
from pathlib import Path
from typing import Optional

PIPER_MODELS_DIR = "/var/vf/models/piper"
DEFAULT_MODELS = {
    "vi": f"{PIPER_MODELS_DIR}/vi_VN-vais1000-medium.onnx",
    "en": f"{PIPER_MODELS_DIR}/en_US-lessac-medium.onnx",
}


async def synthesize_piper(
    text: str,
    model_path: Optional[str] = None,
    output_path: str = "/tmp/vf/piper.wav",
    lang_code: str = "en",
    length_scale: float = 1.0,
) -> str:
    """Synthesize text using Piper TTS. Returns output_path (wav)."""
    if model_path is None:
        model_path = DEFAULT_MODELS.get(lang_code, DEFAULT_MODELS["en"])

    if not Path(model_path).exists():
        raise FileNotFoundError(f"Piper model not found: {model_path}")

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        "piper",
        "--model", model_path,
        "--length_scale", str(length_scale),
        "--output_file", output_path,
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd,
        stdin=asyncio.subprocess.PIPE,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate(input=text.encode("utf-8"))
    if proc.returncode != 0:
        raise RuntimeError(f"piper failed (rc={proc.returncode}): {stderr.decode()[:200]}")

    size = os.path.getsize(output_path)
    if size < 1024:
        raise ValueError(f"Piper output too small: {size} bytes")
    return output_path
