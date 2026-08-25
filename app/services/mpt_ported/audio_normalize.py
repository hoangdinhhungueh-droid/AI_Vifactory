"""MPT-G4-2 - Audio loudness normalization per platform (FFmpeg loudnorm 2-pass)."""
import asyncio, json, re
from pathlib import Path

LUFS_TARGETS = {
    "spotify":     -14.0,
    "youtube":     -14.0,
    "tiktok":      -14.0,
    "dailymotion": -16.0,
    "default":     -16.0,
}
TRUE_PEAK_MAX = -1.0


async def normalize_audio(
    input_path: str,
    output_path: str,
    platform: str = "default",
    true_peak: float = TRUE_PEAK_MAX,
) -> dict:
    """Normalize audio to platform LUFS target. Returns dict with output_path, measured_lufs, target_lufs."""
    target_lufs = LUFS_TARGETS.get(platform, LUFS_TARGETS["default"])
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    # Pass 1: measure
    cmd1 = [
        "ffmpeg", "-y", "-i", input_path,
        "-af", f"loudnorm=I={target_lufs}:TP={true_peak}:LRA=11:print_format=json",
        "-f", "null", "-",
    ]
    proc1 = await asyncio.create_subprocess_exec(
        *cmd1, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    _, stderr1 = await proc1.communicate()
    if proc1.returncode != 0:
        raise RuntimeError(f"loudnorm pass1 failed: {stderr1.decode()[-200:]}")

    stderr_text = stderr1.decode()
    match = re.search(r"\{[^{}]+\"measured_i\"[^{}]+\}", stderr_text, re.DOTALL)
    if not match:
        af = f"loudnorm=I={target_lufs}:TP={true_peak}:LRA=11"
        measured_lufs = target_lufs
    else:
        stats = json.loads(match.group())
        mi = stats.get("measured_i", str(target_lufs))
        mlra = stats.get("measured_lra", "11.0")
        mtp = stats.get("measured_tp", "-1.0")
        mthresh = stats.get("measured_thresh", "-26.0")
        offset = stats.get("offset", "0.0")
        af = (
            f"loudnorm=I={target_lufs}:TP={true_peak}:LRA=11:"
            f"measured_I={mi}:measured_LRA={mlra}:measured_TP={mtp}:"
            f"measured_thresh={mthresh}:offset={offset}:linear=true:print_format=none"
        )
        measured_lufs = float(mi)

    # Pass 2: apply
    cmd2 = [
        "ffmpeg", "-y", "-i", input_path,
        "-af", af,
        "-ar", "44100", "-ac", "2",
        output_path
    ]
    proc2 = await asyncio.create_subprocess_exec(
        *cmd2, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    _, stderr2 = await proc2.communicate()
    if proc2.returncode != 0:
        raise RuntimeError(f"loudnorm pass2 failed: {stderr2.decode()[-200:]}")

    return {
        "output_path": output_path,
        "measured_lufs": measured_lufs,
        "target_lufs": target_lufs,
        "platform": platform,
    }
