#!/usr/bin/env python3
"""vox/ffmpeg_utils.py — Dynamic FFmpeg & FFprobe Resolution Utility (AVF-VOX-001).

Resolves ffmpeg and ffprobe executable paths across Windows and Linux VPS.
"""

from __future__ import annotations

import json
import logging
import shutil
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def get_ffmpeg_binary() -> str:
    """Returns path to ffmpeg executable."""
    found = shutil.which("ffmpeg")
    if found:
        return found
    try:
        import imageio_ffmpeg
        return imageio_ffmpeg.get_ffmpeg_exe()
    except Exception as _ff_err:
        logger.debug("imageio_ffmpeg lookup notice: %s", _ff_err)
    return "ffmpeg"


def get_ffprobe_binary() -> str:
    """Returns path to ffprobe executable."""
    found = shutil.which("ffprobe")
    if found:
        return found
    # Check if ffprobe is alongside ffmpeg
    ffmpeg_path = get_ffmpeg_binary()
    if ffmpeg_path != "ffmpeg":
        p = Path(ffmpeg_path).parent / "ffprobe.exe"
        if p.exists():
            return str(p)
    return "ffprobe"


def build_twopass_loudnorm_filter(
    ffmpeg_bin: str,
    media_path: Path,
    target_i: float = -16.0,
    target_tp: float = -2.5,
    target_lra: float = 7.0,
) -> str:
    """Runs FFmpeg pass-1 loudnorm analysis and returns calibrated pass-2 filter string."""
    base_filter = f"loudnorm=I={target_i}:TP={target_tp}:LRA={target_lra}"
    pass1_cmd = [
        ffmpeg_bin, "-y",
        "-i", str(media_path),
        "-af", f"{base_filter}:print_format=json",
        "-f", "null", "-",
    ]
    p1_res = subprocess.run(pass1_cmd, capture_output=True, text=True, check=False, timeout=120)
    err_out = p1_res.stderr or ""
    json_start = err_out.rfind("{")
    json_end = err_out.rfind("}")
    if json_start == -1 or json_end <= json_start:
        logger.debug("[ffmpeg_utils] Pass-1 loudnorm stats unavailable, falling back to 1-pass filter")
        return base_filter
    try:
        p1_data = json.loads(err_out[json_start:json_end + 1])
        m_i = p1_data.get("input_i", str(target_i))
        m_tp = p1_data.get("input_tp", str(target_tp))
        m_lra = p1_data.get("input_lra", str(target_lra))
        m_thresh = p1_data.get("input_thresh", "-26.0")
        offset = p1_data.get("target_offset", "0.0")
        return (
            f"{base_filter}:measured_I={m_i}:measured_TP={m_tp}:"
            f"measured_LRA={m_lra}:measured_thresh={m_thresh}:offset={offset}:linear=true"
        )
    except (json.JSONDecodeError, TypeError, ValueError) as exc:
        logger.warning("[ffmpeg_utils] Failed parsing pass-1 loudnorm stats: %s", exc)
        return base_filter


def normalize_audio_ebur128(
    media_path: Path,
    target_i: float = -16.0,
    target_tp: float = -2.5,
    target_lra: float = 7.0,
) -> Path:
    """Normalizes an audio file in-place via two-pass EBU R128 loudnorm at 48kHz."""
    ffmpeg_bin = get_ffmpeg_binary()
    filt = build_twopass_loudnorm_filter(
        ffmpeg_bin, media_path, target_i=target_i, target_tp=target_tp, target_lra=target_lra
    )
    tmp_out = media_path.with_name(f".loudnorm_{media_path.name}")
    codec_args = ["-c:a", "libmp3lame", "-b:a", "192k"] if media_path.suffix.lower() == ".mp3" else ["-c:a", "aac", "-b:a", "192k"]
    cmd = [
        ffmpeg_bin, "-y",
        "-i", str(media_path),
        "-ar", "48000",
        "-af", filt,
        *codec_args,
        str(tmp_out),
    ]
    subprocess.run(cmd, capture_output=True, check=True, timeout=180)
    if tmp_out.exists() and tmp_out.stat().st_size > 1000:
        tmp_out.replace(media_path)
    return media_path


_FOLEY_RECIPES: dict[str, tuple[str, float]] = {
    "stamp_thud": ("sine=frequency={f}:sample_rate=48000:duration=0.16,lowpass=f=380,afade=t=in:d=0.004,afade=t=out:st=0.03:d=0.13", 112.0),
    "caliper_click": ("sine=frequency={f}:sample_rate=48000:duration=0.045,highpass=f=1200,afade=t=in:d=0.002,afade=t=out:st=0.008:d=0.037", 2140.0),
    "loupe_whoosh": ("anoisesrc=color=pink:sample_rate=48000:duration=0.22:seed={s},bandpass=f=1150:width_type=h:w=900,afade=t=in:d=0.04,afade=t=out:st=0.09:d=0.13", 0.0),
    "gavel_strike": ("sine=frequency={f}:sample_rate=48000:duration=0.14,lowpass=f=520,afade=t=in:d=0.003,afade=t=out:st=0.025:d=0.115", 162.0),
    "vault_clunk": ("sine=frequency={f}:sample_rate=48000:duration=0.20,lowpass=f=320,afade=t=in:d=0.005,afade=t=out:st=0.04:d=0.16", 88.0),
    "paper_fold": ("anoisesrc=color=white:sample_rate=48000:duration=0.15:seed={s},highpass=f=1400,lowpass=f=6200,afade=t=in:d=0.015,afade=t=out:st=0.04:d=0.11", 0.0),
}


def build_procedural_foley_inputs_and_filter(
    foley_cues: list[dict],
    duration_sec: float,
    seed: int = 42,
    voice_input_idx: int = 0,
) -> tuple[list[str], str]:
    """Builds zero-asset seeded FFmpeg lavfi foley inputs and adelay filter_complex graph."""
    valid_cues = [
        c for c in (foley_cues or [])
        if isinstance(c, dict) and 0.0 <= float(c.get("time_sec", -1.0)) <= max(0.05, float(duration_sec))
    ]
    if not valid_cues:
        return [], ""

    kinds_used: list[str] = []
    for cue in valid_cues:
        kind = str(cue.get("sfx_kind") or "paper_fold")
        if kind not in _FOLEY_RECIPES:
            kind = "paper_fold"
        if kind not in kinds_used:
            kinds_used.append(kind)

    ff_inputs: list[str] = []
    kind_to_input_idx: dict[str, int] = {}
    base_idx = voice_input_idx + 1
    for i, kind in enumerate(kinds_used):
        tmpl, base_freq = _FOLEY_RECIPES[kind]
        freq = round(base_freq + ((seed + i * 7) % 19), 2)
        src = tmpl.format(f=freq, s=int(seed) + i * 17)
        ff_inputs.extend(["-f", "lavfi", "-i", src])
        kind_to_input_idx[kind] = base_idx + i

    cues_by_kind: dict[str, list[tuple[int, dict]]] = {k: [] for k in kinds_used}
    for idx, cue in enumerate(valid_cues):
        kind = str(cue.get("sfx_kind") or "paper_fold")
        if kind not in cues_by_kind:
            kind = "paper_fold"
        cues_by_kind[kind].append((idx, cue))

    filter_parts: list[str] = [
        f"[{voice_input_idx}:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=mono[v_mono]"
    ]
    delayed_labels: list[str] = []

    for kind in kinds_used:
        in_idx = kind_to_input_idx[kind]
        items = cues_by_kind[kind]
        norm_lbl = f"src_{kind}"
        filter_parts.append(
            f"[{in_idx}:a]aformat=sample_fmts=fltp:sample_rates=48000:channel_layouts=mono[{norm_lbl}]"
        )
        if len(items) == 1:
            split_labels = [f"{norm_lbl}_s0"]
            filter_parts.append(f"[{norm_lbl}]anull[{split_labels[0]}]")
        else:
            split_labels = [f"{norm_lbl}_s{k}" for k in range(len(items))]
            filter_parts.append(
                f"[{norm_lbl}]asplit={len(items)}" + "".join(f"[{lbl}]" for lbl in split_labels)
            )
        for lbl, (cue_idx, cue) in zip(split_labels, items):
            delay_ms = max(0, int(round(float(cue["time_sec"]) * 1000.0)))
            gain = 0.24 + ((cue_idx + seed) % 5) * 0.025
            d_lbl = f"d_{cue_idx}"
            filter_parts.append(f"[{lbl}]volume={gain:.3f},adelay={delay_ms}:all=1[{d_lbl}]")
            delayed_labels.append(f"[{d_lbl}]")

    total_mix = 1 + len(delayed_labels)
    filter_parts.append(
        "[v_mono]" + "".join(delayed_labels) + f"amix=inputs={total_mix}:normalize=0:duration=first[aout]"
    )
    return ff_inputs, ";".join(filter_parts)


def mix_papertrails_foley_sfx(
    voice_path: Path,
    output_audio: Path,
    foley_cues: list[dict],
    duration_sec: float,
    target_i: float = -15.5,
    target_tp: float = -2.5,
    seed: int = 42,
) -> Path:
    """Mixes seeded procedural FFmpeg foley onto voice track and normalizes EBU R128."""
    ffmpeg_bin = get_ffmpeg_binary()
    ff_inputs, filter_complex = build_procedural_foley_inputs_and_filter(
        foley_cues=foley_cues,
        duration_sec=duration_sec,
        seed=seed,
        voice_input_idx=0,
    )
    output_audio.parent.mkdir(parents=True, exist_ok=True)
    tmp_mix = output_audio.with_name(f".foley_mix_{output_audio.stem}.wav")
    try:
        if ff_inputs and filter_complex:
            cmd = [
                ffmpeg_bin, "-y",
                "-i", str(voice_path),
                *ff_inputs,
                "-filter_complex", filter_complex,
                "-map", "[aout]",
                "-ar", "48000",
                "-c:a", "pcm_s16le",
                str(tmp_mix),
            ]
        else:
            cmd = [
                ffmpeg_bin, "-y",
                "-i", str(voice_path),
                "-ar", "48000",
                "-c:a", "pcm_s16le",
                str(tmp_mix),
            ]
        subprocess.run(cmd, capture_output=True, check=True, timeout=180)
        loudnorm_filter = build_twopass_loudnorm_filter(
            ffmpeg_bin, tmp_mix, target_i=target_i, target_tp=target_tp, target_lra=7.0
        )
        cmd_norm = [
            ffmpeg_bin, "-y",
            "-i", str(tmp_mix),
            "-ar", "48000",
            "-af", loudnorm_filter,
            "-c:a", "aac",
            "-b:a", "192k",
            str(output_audio),
        ]
        subprocess.run(cmd_norm, capture_output=True, check=True, timeout=180)
    finally:
        if tmp_mix.exists():
            tmp_mix.unlink(missing_ok=True)
    return output_audio
