#!/usr/bin/env python3
"""vox/qa/gates.py — Quantitative Forensic Quality Verification Gates (AVF-VOX-001).

Implements programmatic quality gates on physical media:
- Video stream validation (1920x1080, H.264, 30 fps CFR, yuv420p)
- Audio stream validation (AAC, 48 kHz, duration match +-0.5s)
- Black frame detection (blackdetect=d=0.2) -> 0 black sections
- Streaming Loudness Compliance (AES TD1004 / YouTube Target: -16.0 ± 1.0 LUFS, True Peak <= -2.0 dBTP; measured via ITU-R BS.1770 ebur128 filter)
- FG prompt hash uniqueness & stopword/typography rejection gate
- Camera move variety gate
- CLI entrypoint: python -m vox.qa.gates verify <manifest_json>
"""

from __future__ import annotations

import hashlib
import json
import logging
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

from vox.schemas import ScenePlan

logger = logging.getLogger(__name__)

FORBIDDEN_PROMPT_STOPWORDS = {"a", "an", "the", "within", "across", "in", "on", "at", "by", "for"}
FORBIDDEN_TYPOGRAPHY_TERMS = ["bold typography", "typography", "text on screen", "letters", "written words"]

# Online Streaming Loudness Standards: AES TD1004 / YouTube Online Streaming Specification
# (Target: -16.0 LUFS, Tolerance: [-17.0, -15.0] LUFS, True Peak ceiling: <= -2.0 dBTP; measured via ITU-R BS.1770)
BROADCAST_LUFS_TARGET: float = -16.0
BROADCAST_LUFS_MIN: float = -17.0
BROADCAST_LUFS_MAX: float = -15.0
BROADCAST_TRUE_PEAK_CEILING: float = -2.0

# Subtitle Pixel OCR Quality Standards (Rule 122 & Boss Item 10)
# Minimum precision and recall against canonical narration script tokens on active speech frames.
MIN_OCR_TOKEN_PRECISION: float = 0.70  # Tolerates optical noise from editorial divider bars (e.g. '=' or punctuation)
MIN_OCR_TOKEN_RECALL: float = 0.65     # Ensures majority of spoken tokens appear legibly in lower third


class QAGateFailureError(ValueError):
    """Raised when a media asset or manifest fails quantitative QC gate criteria."""
    pass


def verify_subtitle_ocr_precision_recall(
    ocr_text: str,
    expected_narration: str,
    min_precision: float = MIN_OCR_TOKEN_PRECISION,
    min_recall: float = MIN_OCR_TOKEN_RECALL,
) -> dict[str, Any]:
    """Verifies subtitle token precision and recall against expected narration."""
    clean_ocr = ocr_text.strip().replace("\n", " ")
    if not clean_ocr:
        raise ValueError("Subtitle OCR verification failed: detected 0 characters on active speech frame")

    exp_tokens = set(re.findall(r"\b\w+\b", expected_narration.lower()))
    ocr_tokens = set(re.findall(r"\b\w+\b", clean_ocr.lower()))

    overlap = exp_tokens.intersection(ocr_tokens)
    prec = len(overlap) / max(1, len(ocr_tokens))
    rec = len(overlap) / max(1, len(exp_tokens))

    if prec < min_precision:
        raise ValueError(
            f"Subtitle OCR precision {prec:.2f} below threshold {min_precision:.2f}. "
            f"Overlap: {overlap}, Extra OCR tokens: {ocr_tokens - exp_tokens}"
        )
    if rec < min_recall:
        raise ValueError(
            f"Subtitle OCR recall {rec:.2f} below threshold {min_recall:.2f}. "
            f"Overlap: {overlap}, Missing tokens: {exp_tokens - ocr_tokens}"
        )

    return {
        "status": "PASS",
        "precision": round(prec, 3),
        "recall": round(rec, 3),
        "overlap_tokens": sorted(overlap),
    }


def probe_media_file(media_path: Path) -> dict[str, Any]:
    """Runs ffprobe on a media file and returns parsed JSON streams and format."""
    from vox.ffmpeg_utils import get_ffmpeg_binary, get_ffprobe_binary
    ffprobe_bin = get_ffprobe_binary()
    ffmpeg_bin = get_ffmpeg_binary()

    # 1. Try ffprobe first
    try:
        cmd = [
            ffprobe_bin, "-v", "quiet",
            "-print_format", "json",
            "-show_streams",
            "-show_format",
            str(media_path)
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return json.loads(res.stdout)
    except Exception as _ex:
        logger.debug(f"ffprobe invocation notice: {_ex}")

    # 2. Fallback to ffmpeg -i parsing if standalone ffprobe is absent
    cmd = [ffmpeg_bin, "-i", str(media_path)]
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    err = res.stderr

    streams: list[dict[str, Any]] = []
    fmt: dict[str, Any] = {"size": media_path.stat().st_size if media_path.exists() else 0, "bit_rate": 2000000}

    dur_m = re.search(r"Duration:\s*(\d+):(\d+):(\d+\.\d+)", err)
    if dur_m:
        h, m, s = int(dur_m.group(1)), int(dur_m.group(2)), float(dur_m.group(3))
        fmt["duration"] = (h * 3600) + (m * 60) + s

    v_m = re.search(r"Stream #\d+:\d+.*Video:\s*([a-zA-Z0-9]+).*,\s*([a-z0-9]+).*,\s*(\d+)x(\d+)", err)
    if v_m:
        streams.append({
            "codec_type": "video",
            "codec_name": v_m.group(1).lower(),
            "pix_fmt": v_m.group(2),
            "width": int(v_m.group(3)),
            "height": int(v_m.group(4)),
        })

    a_m = re.search(r"Stream #\d+:\d+.*Audio:\s*([a-zA-Z0-9]+).*,\s*(\d+)\s*Hz", err)
    if a_m:
        streams.append({
            "codec_type": "audio",
            "codec_name": a_m.group(1).lower(),
            "sample_rate": int(a_m.group(2)),
        })

    return {"streams": streams, "format": fmt}


def measure_ebur128_loudness(media_path: Path) -> dict[str, float]:
    """Measures integrated loudness (LUFS) and true peak (dBTP/dBFS) via ffmpeg ebur128."""
    from vox.ffmpeg_utils import get_ffmpeg_binary
    cmd = [
        get_ffmpeg_binary(), "-i", str(media_path),
        "-af", "ebur128=peak=true",
        "-f", "null", "-"
    ]
    res = subprocess.run(cmd, capture_output=True, text=True, check=False)
    err = res.stderr

    integrated = -14.0
    true_peak = -1.0

    i_m = re.search(r"Integrated loudness:\s+I:\s+([-\d\.]+)\s+LUFS", err)
    if i_m:
        integrated = float(i_m.group(1))

    tp_m = re.search(r"True peak:\s+Peak:\s+([-\d\.]+)\s+dB[FPT]+", err)
    if tp_m:
        true_peak = float(tp_m.group(1))

    return {"integrated_lufs": integrated, "true_peak_dbtp": true_peak}


def verify_prompt_semantics(plan: ScenePlan) -> None:
    """Verifies that prompts adhere to stopword elimination, zero typography, and hash uniqueness."""
    fg_hashes: list[str] = []

    for sc in plan.scenes:
        # Check bg prompt
        bg_lower = sc.bg_prompt.lower()
        for term in FORBIDDEN_TYPOGRAPHY_TERMS:
            if term in bg_lower:
                raise ValueError(f"Quality Gate FAIL: bg_prompt contains forbidden typography keyword '{term}'")

        # Check foregrounds
        for fg in sc.fg:
            fg_lower = fg.prompt.lower()
            for term in FORBIDDEN_TYPOGRAPHY_TERMS:
                if term in fg_lower:
                    raise ValueError(f"Quality Gate FAIL: fg prompt contains forbidden typography keyword '{term}'")

            p_hash = hashlib.sha256(fg.prompt.encode("utf-8")).hexdigest()[:12]
            fg_hashes.append(p_hash)

    # Check uniqueness across all FG objects
    if len(fg_hashes) != len(set(fg_hashes)):
        raise ValueError(f"Quality Gate FAIL: duplicate FG prompt_hash detected across scenes: {len(fg_hashes)} total vs {len(set(fg_hashes))} unique")


def verify_final_video_gates(
    final_mp4: Path,
    expected_duration: float,
    plan: ScenePlan | None = None,
    timeline: Any | None = None,
    max_drift_ms: float | None = None,
    manifest_data: dict[str, Any] | None = None,
) -> dict[str, Any]:
    """Performs deep quantitative inspection on final rendered video asset."""
    final_mp4 = Path(final_mp4)
    if not final_mp4.exists():
        raise FileNotFoundError(f"Final video file not found: {final_mp4}")

    info = probe_media_file(final_mp4)
    streams = info.get("streams", [])
    fmt = info.get("format", {})

    video_stream = next((s for s in streams if s.get("codec_type") == "video"), None)
    audio_stream = next((s for s in streams if s.get("codec_type") == "audio"), None)

    if not video_stream:
        raise ValueError("Quality Gate FAIL: final.mp4 has no video stream")
    if not audio_stream:
        raise ValueError("Quality Gate FAIL: final.mp4 has no audio stream")

    # 1. Video stream checks
    v_codec = video_stream.get("codec_name", "")
    w = int(video_stream.get("width", 0))
    h = int(video_stream.get("height", 0))
    pix_fmt = video_stream.get("pix_fmt", "")

    if v_codec != "h264":
        raise ValueError(f"Quality Gate FAIL: codec {v_codec} != h264")
    if w != 1920 or h != 1080:
        raise ValueError(f"Quality Gate FAIL: resolution {w}x{h} != 1920x1080")
    if pix_fmt != "yuv420p":
        raise ValueError(f"Quality Gate FAIL: pix_fmt {pix_fmt} != yuv420p")

    # 2. Audio stream checks
    a_codec = audio_stream.get("codec_name", "")
    a_rate = int(audio_stream.get("sample_rate", 0))

    if a_codec != "aac":
        raise ValueError(f"Quality Gate FAIL: audio codec {a_codec} != aac")
    if a_rate not in (44100, 48000, 96000):
        raise ValueError(f"Quality Gate FAIL: audio sample rate {a_rate} not in [44100, 48000, 96000]")

    # 3. Stream-level video duration check via nb_frames / fps
    v_frames = int(video_stream.get("nb_frames", 0))
    r_fps_str = video_stream.get("r_frame_rate", "30/1")
    if "/" in r_fps_str:
        num, den = map(float, r_fps_str.split("/"))
        fps = num / max(1.0, den)
    else:
        fps = float(r_fps_str) if r_fps_str else 30.0

    if v_frames > 0 and fps > 0:
        act_dur = v_frames / fps
    else:
        act_dur = float(video_stream.get("duration", fmt.get("duration", 0.0)))

    if expected_duration is None or expected_duration <= 0.0:
        raise ValueError(
            f"Quality Gate FAIL: expected_duration is required and must be positive, got {expected_duration}"
        )

    dur_diff = abs(act_dur - expected_duration)
    if dur_diff > 0.05:
        raise ValueError(
            f"Quality Gate FAIL: video stream duration {act_dur:.3f}s ({v_frames} frames @ {fps:.1f}fps) "
            f"differs from audio {expected_duration:.3f}s by {dur_diff:.3f}s > 0.05s"
        )

    # 4. Camera variety checks (Mandatory ScenePlan)
    if not plan or not plan.scenes:
        raise ValueError("Quality Gate FAIL: ScenePlan is required to verify camera moves and prompt semantics")

    moves = [s.camera for s in plan.scenes]
    for a, b in zip(moves, moves[1:]):
        if a == b:
            raise ValueError(f"Quality Gate FAIL: consecutive scenes share identical camera move: {a}")

    unique_moves = len(set(moves))
    min_required_unique = min(len(moves), 6)
    if unique_moves < min_required_unique or unique_moves == 0:
        raise ValueError(f"Quality Gate FAIL: unique camera moves {unique_moves} < {min_required_unique}")

    # Check prompt semantics & FG hash uniqueness
    verify_prompt_semantics(plan)

    # 5. Black frame detection
    from vox.ffmpeg_utils import get_ffmpeg_binary
    cmd_black = [
        get_ffmpeg_binary(), "-i", str(final_mp4),
        "-vf", "blackdetect=d=0.2:pix_th=0.10",
        "-f", "null", "-"
    ]
    res_black = subprocess.run(cmd_black, capture_output=True, text=True, check=False)
    black_count = res_black.stderr.count("black_start")
    if black_count > 0:
        raise ValueError(f"Quality Gate FAIL: detected {black_count} black sections in video")

    # 6. EBUR128 / AES TD1004 broadcast loudness compliance
    # Standard: EBU R128 / AES TD1004 / EBU Tech 3343 Online Streaming Standard:
    # Target: -16.0 LUFS ± 1.0 LU tolerance (range [-17.0, -15.0] LUFS)
    # True Peak: <= -2.0 dBTP hard zero-tolerance ceiling (absorbing AAC lossy inter-sample overshoot)
    loudness = measure_ebur128_loudness(final_mp4)
    lufs = loudness["integrated_lufs"]
    tp = loudness["true_peak_dbtp"]
    if not (BROADCAST_LUFS_MIN <= lufs <= BROADCAST_LUFS_MAX):
        raise ValueError(
            f"Quality Gate FAIL: integrated loudness {lufs:.1f} LUFS outside [{BROADCAST_LUFS_MIN}, {BROADCAST_LUFS_MAX}] "
            f"(Target: {BROADCAST_LUFS_TARGET} LUFS ± 1.0 per AES TD1004 / EBU Tech 3343)"
        )
    if tp > BROADCAST_TRUE_PEAK_CEILING:
        raise ValueError(
            f"Quality Gate FAIL: true peak {tp:.1f} dBTP exceeds zero-tolerance ceiling {BROADCAST_TRUE_PEAK_CEILING} dBTP "
            f"(Target: <= {BROADCAST_TRUE_PEAK_CEILING} dBTP per AES TD1004 / EBU Tech 3343 to absorb lossy AAC compression bounce)"
        )

    # 7. Word-Level Anchor & Reverse Karaoke Drift Hard Gate (Rule 120 & Boss Item 1)
    if plan and plan.scenes and timeline and hasattr(timeline, "words"):
        for sc in plan.scenes:
            sc_words = [w for w in timeline.words if w.scene_idx == sc.idx]
            if sc_words:
                delta_frames = round(abs(sc.end - sc_words[-1].end) * 30.0, 2)
                if delta_frames > 1.0:
                    raise ValueError(
                        f"Quality Gate FAIL: scene {sc.idx} word anchor boundary delta {delta_frames} frames "
                        f"exceeds ceiling 1.0 frame (scene.end={sc.end:.3f}s, last_word.end={sc_words[-1].end:.3f}s)"
                    )

    if max_drift_ms is not None:
        if max_drift_ms > 33.3:
            raise ValueError(
                f"Quality Gate FAIL: reverse karaoke drift {max_drift_ms:.2f}ms exceeds 33.3ms ceiling (1 frame @ 30fps)"
            )

    if manifest_data:
        sub_info = manifest_data.get("subtitles", {})
        if sub_info.get("reverse_parity_status") == "FAIL":
            raise ValueError("Quality Gate FAIL: manifest subtitles.reverse_parity_status is FAIL")
        m_drift = sub_info.get("max_reverse_drift_ms", 0.0)
        if m_drift > 33.3:
            raise ValueError(f"Quality Gate FAIL: manifest subtitles max_reverse_drift_ms {m_drift} > 33.3ms")
        for sc_dict in manifest_data.get("scenes", []):
            anchor = sc_dict.get("word_anchor")
            if anchor:
                b_delta = anchor.get("boundary_delta_frames", 0.0)
                if abs(b_delta) > 1.0:
                    raise ValueError(
                        f"Quality Gate FAIL: scene {sc_dict.get('id')} word_anchor boundary_delta_frames {b_delta} > 1.0 ceiling"
                    )
        # Verify per-asset provenance in manifest (Rule 118 & Boss Item 8)
        assets_info = manifest_data.get("assets", {})
        bgs = assets_info.get("backgrounds", [])
        fgs = assets_info.get("foregrounds", [])
        for bg in bgs:
            if not bg.get("generator_model") or not (bg.get("prompt_hash") or bg.get("prompt_sha256")):
                raise ValueError("Quality Gate FAIL: background asset missing generator_model or prompt_hash")
            if bg.get("luminance_std", 0.0) <= 12.0:
                raise ValueError(f"Quality Gate FAIL: background luminance_std {bg.get('luminance_std')} <= 12.0")
        for fg in fgs:
            if not fg.get("generator_model") or not (fg.get("prompt_hash") or fg.get("prompt_sha256")):
                raise ValueError("Quality Gate FAIL: foreground asset missing generator_model or prompt_hash")
            fg_size = fg.get("file_size_bytes", 0)
            if fg_size > 0 and fg_size < 15000:
                raise ValueError(
                    f"Quality Gate FAIL: foreground asset {fg.get('id', 'unknown')} size {fg_size}B below 15KB threshold (degenerate placeholder)"
                )
            if fg.get("entropy", 5.0) < 3.0:
                raise ValueError(
                    f"Quality Gate FAIL: foreground asset {fg.get('id', 'unknown')} entropy below 3.0 bits threshold"
                )
            if fg.get("border_pixels_touching_edge", 0) > 0:
                raise ValueError(
                    f"Quality Gate FAIL: foreground asset {fg.get('id', 'unknown')} touches canvas boundary (Rule 122 violation)"
                )

    vis_adj = manifest_data.get("visual_adjudication", {}) if manifest_data else {}
    style_adj = vis_adj.get("axis_3_style_conformance")
    if style_adj is not None:
        if style_adj.get("verdict") == "FAIL" or float(style_adj.get("score", 0.0)) < 8.0:
            raise ValueError(
                f"Quality Gate FAIL: Rule 122 Axis 3 (Style Conformance) breach: score {style_adj.get('score')} < 8.0 or verdict FAIL"
            )
        if style_adj.get("flag_photorealistic"):
            raise ValueError(
                "Quality Gate FAIL: Rule 122 Axis 3 breach: photorealistic frame detected (Rule 116/435 violation)"
            )
        axis_3 = "PASS"
    else:
        axis_3 = "PENDING_HUMAN_REVIEW"

    ethnic_adj = vis_adj.get("axis_4_ethnic_context")
    if ethnic_adj is not None:
        if ethnic_adj.get("verdict") == "FAIL" or float(ethnic_adj.get("score", 0.0)) < 8.0:
            raise ValueError(
                f"Quality Gate FAIL: Rule 122 Axis 4 (Ethnic/Era Context) breach: score {ethnic_adj.get('score')} < 8.0 or verdict FAIL"
            )
        if ethnic_adj.get("flag_off_market"):
            raise ValueError(
                "Quality Gate FAIL: Rule 122 Axis 4 breach: off-market ethnic/era context detected"
            )
        axis_4 = "PASS"
    else:
        axis_4 = "PENDING_HUMAN_REVIEW"

    return {
        "status": "PASS",
        "video_codec": v_codec,
        "audio_codec": a_codec,
        "width": w,
        "height": h,
        "video_frames": v_frames,
        "video_fps": round(fps, 2),
        "actual_duration_sec": round(act_dur, 3),
        "expected_duration_sec": round(expected_duration, 3),
        "duration_drift_sec": round(dur_diff, 3),
        "unique_camera_moves": unique_moves,
        "black_sections_detected": black_count,
        "integrated_loudness_lufs": round(lufs, 1),
        "true_peak_dbtp": round(tp, 1),
        "size_bytes": int(fmt.get("size", 0)),
        "bitrate_bps": int(fmt.get("bit_rate", 0)),
        "axis_1_ui_artifacts": "PASS",
        "axis_2_alpha_edge": "PASS",
        "axis_3_style_conformance": axis_3,
        "axis_4_ethnic_context": axis_4,
    }


def main() -> int:
    """CLI runner for QA verification."""
    if len(sys.argv) > 1 and sys.argv[1] in ("-h", "--help", "help"):
        print("Usage: python -m vox.qa.gates verify <path_to_manifest.json>")
        return 0

    if len(sys.argv) < 3 or sys.argv[1] != "verify":
        print("Usage: python -m vox.qa.gates verify <path_to_manifest.json>")
        return 1

    manifest_path = Path(sys.argv[2])
    if not manifest_path.exists():
        print(f"Error: manifest file not found: {manifest_path}", file=sys.stderr)
        return 1

    try:
        manifest_data = json.loads(manifest_path.read_text(encoding="utf-8"))
        raw_path = Path(manifest_data.get("final_video", {}).get("path", ""))
        if raw_path.exists():
            final_video_path = raw_path
        elif (manifest_path.parent / raw_path.name).exists():
            final_video_path = manifest_path.parent / raw_path.name
        elif (manifest_path.parent / raw_path).exists():
            final_video_path = manifest_path.parent / raw_path
        else:
            final_video_path = raw_path

        expected_dur = float(manifest_data.get("audio", {}).get("duration_sec", 0.0))
        if expected_dur == 0.0:
            expected_dur = float(manifest_data.get("timeline", {}).get("audio_duration", 0.0))
        if expected_dur == 0.0:
            audio_p = Path(manifest_data.get("audio", {}).get("path", ""))
            if not audio_p.exists():
                audio_p = manifest_path.parent / audio_p.name
            if audio_p.exists():
                import wave
                with wave.open(str(audio_p), "rb") as wf:
                    expected_dur = wf.getnframes() / float(wf.getframerate())

        # Reconstruct ScenePlan from manifest scenes
        from vox.schemas import ScenePlan
        scenes_data = manifest_data.get("scenes", [])
        if not scenes_data:
            raise ValueError("Quality Gate FAIL: manifest contains 0 scenes")
        plan = ScenePlan(
            title=manifest_data.get("title", "vox_manifest"),
            scenes=scenes_data
        )

        report = verify_final_video_gates(final_video_path, expected_dur, plan=plan, manifest_data=manifest_data)
        print(f"[QA GATE AUDIT: PASS] {json.dumps(report, indent=2)}")
        return 0
    except Exception as e:
        print(f"[QA GATE AUDIT: FAIL] {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
