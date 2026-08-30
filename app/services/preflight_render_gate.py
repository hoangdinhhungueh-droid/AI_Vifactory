"""Pre-render materials + pipeline audit gate (Rule 72).

WHY THIS EXISTS (EP005 QC feedback, 07/08/2026): four real defects
(background not removed, wrong voice, literal SSML/tags read aloud, missing
core/foreground image) were only discovered AFTER a full render completed,
wasting a full render cycle each time. The user explicitly asked for a
system/tool that audits materials + wiring BEFORE render, not after.

This module is the reusable, importable gate. It is called from
app/pipeline/run_episode.py::run_pipeline() right before the S4 TTS stage
starts (i.e. before ANY TTS/render work happens), and can also be run
standalone via scripts/preflight_render_gate.py for a manual audit of an
episode dir that already has materials pulled (manifest.json + brain_input
/ remotion_props already written by the S4.5 two-layer prep step).

Mode: VF_PREFLIGHT_GATE=block|warn|off (default: block). Unlike
story_judge (default warn, uncalibrated), this gate defaults to BLOCK
because every check below maps to a concrete defect the user already hit
in production, not a speculative quality heuristic.

Checks (append to blocks[] = hard fail, or warns[] = informational):
  1. manifest file integrity      - every manifest.json local_path exists,
                                     non-empty.
  2. scene material completeness  - every scene's background_reuse_key
                                     (and foreground_reuse_key, if set)
                                     resolves to a manifest row whose file
                                     exists. Catches "missing core image"
                                     silently falling back/blank.
  3. background-removal (alpha)   - every Foreground/Overlay manifest row
                                     must be an RGBA file with a sane
                                     transparent ratio. A flat .jpg/.jpeg
                                     (physically cannot carry alpha) is an
                                     automatic block.
  4. simulated/placeholder assets - no "<path>.simulated.json" sidecar next
                                     to any resolved asset (Rule 70 gate,
                                     reused here so it also fires pre-render).
  5. voice-lock                   - the voice actually RESOLVED for this
                                     episode's own lang_code (LANG_VOICE
                                     entry, or DEFAULT_VOICE fallback) must
                                     not be a known-female voice, since the
                                     locked spec (Decisions Log) is a
                                     middle-aged MALE voice. Only the
                                     resolved voice for THIS episode's
                                     language is checked -- other
                                     languages' own default voices (e.g. vi,
                                     zh, ja, ko) are untouched by this lock.
  6. SSML-leak risk (static)      - tts_edge.synthesize() must not feed a
                                     build_ssml()-produced string into
                                     edge_tts.Communicate(); that double-
                                     escapes/reads tags aloud (the exact
                                     07/08 "mat ma" bug).
  7. SSML-leak (data, if present) - if this episode dir already has a
                                     subtitles.srt from a previous run,
                                     scan it for literal SSML/XML tokens.
  8. SEO regression                - seo_metadata.py source must not contain
                                     the retired "sleep story" fallback
                                     string (previously-fixed regression
                                     guard).

Writes <out_dir>/preflight_render_report.json every run.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Optional

REPO = Path("/root/video_factory")

# Locked spec: middle-aged MALE voice ("Voice giong dan ong trung nien"),
# per Decisions Log 07/08/2026 lock + s4_tts.py / tts_edge.py FIX comments.
# This lock applies to the EPISODE'S OWN language voice only (currently "en"
# for this channel) -- NOT to other languages' own native default voices.
# Extend these sets if new edge-tts voices are ever adopted.
KNOWN_MALE_VOICES = {
    "en-US-GuyNeural", "en-US-ChristopherNeural", "en-US-EricNeural",
    "en-US-RogerNeural", "en-US-SteffanNeural", "en-US-BrianNeural",
    "en-GB-RyanNeural", "vi-VN-NamMinhNeural",
}
KNOWN_FEMALE_VOICES = {
    "en-US-AriaNeural", "en-US-JennyNeural", "en-US-MichelleNeural",
    "en-US-AvaNeural", "en-US-EmmaNeural", "en-GB-SoniaNeural",
    "vi-VN-HoaiMyNeural", "zh-CN-XiaoxiaoNeural", "ja-JP-NanamiNeural",
    "ko-KR-SunHiNeural",
}

# Languages this male-voice lock currently applies to. Only "en" is locked
# today (this channel's narration language); other languages keep whatever
# native default voice LANG_VOICE already configures for them.
LOCKED_MALE_VOICE_LANGS = {"en"}

# IMPORTANT: when SSML leaks into edge_tts.Communicate(), the TTS engine
# does not read literal "<" "tag" ">" syntax -- it SPEAKS the tag/attribute
# names as English words (Whisper then transcribes those spoken words
# verbatim into subtitles.srt). So detection must match the SPOKEN/
# transcribed word forms, not just literal XML syntax. Keep both forms.
SSML_LEAK_TOKENS = [
    # literal XML syntax (in case leak reaches a text sink un-spoken)
    "<speak", "</speak>", "<voice ", "</voice>", "<prosody", "</prosody>",
    "<emphasis", "</emphasis>", "xmlns=",
    # spoken/transcribed word forms (the actual EP005 "mat ma" bug shape,
    # confirmed verbatim in a real subtitles.srt: "Speak version equals 1.0
    # xmlns equals ... mstts equals ... voicename equals ... prosityrate
    # equals ... emphasis level equals moderate")
    "xmlns", "mstts", "voicename", "prosityrate", "prosody rate",
    "emphasis level", "speak version", "w3.org",
]

BANNED_LEGACY_STRINGS = ["sleep story"]


def gate_mode() -> str:
    return os.getenv("VF_PREFLIGHT_GATE", "block").strip().lower()


def _read_json(path: Path):
    if not path.exists():
        return None
    try:
        return json.loads(path.read_text())
    except Exception as e:
        return {"__error__": str(e)}


def _resolve_manifest(out_dir: Path, blocks: list, warns: list):
    """Returns dict reuse_key -> manifest row (with _exists/_size added)."""
    manifest_path = out_dir / "images" / "manifest.json"
    by_key = {}
    if not manifest_path.exists():
        warns.append("manifest: images/manifest.json not found (material checks skipped)")
        return by_key
    rows = _read_json(manifest_path)
    if not isinstance(rows, list):
        warns.append("manifest: unexpected shape (expected a list of rows)")
        return by_key
    for i, row in enumerate(rows):
        key = row.get("reuse_key")
        p = row.get("local_path")
        if not key or not p:
            warns.append(f"manifest[{i}]: missing reuse_key or local_path")
            continue
        fp = Path(p)
        exists = fp.exists()
        size = fp.stat().st_size if exists else 0
        if not exists or size == 0:
            blocks.append(f"manifest[{key}] ({row.get('layer_type')}): file missing/empty at {p}")
        row["_exists"] = exists
        row["_size"] = size
        by_key[key] = row
    return by_key


def _check_foreground_alpha(by_key: dict, blocks: list, warns: list):
    try:
        from PIL import Image
    except Exception as e:
        warns.append(f"alpha-check: Pillow unavailable, skipped ({e})")
        return
    for key, row in by_key.items():
        if row.get("layer_type") != "Foreground/Overlay" or not row.get("_exists"):
            continue
        path = row["local_path"]
        ext = Path(path).suffix.lower()
        if ext in (".jpg", ".jpeg", ".bmp"):
            blocks.append(
                f"background-removal[{key}]: Foreground/Overlay asset is a flat {ext} "
                f"(no alpha channel possible) -> background was NOT removed: {path}")
            continue
        try:
            im = Image.open(path)
            if im.mode != "RGBA":
                blocks.append(f"background-removal[{key}]: mode={im.mode} (expected RGBA): {path}")
                continue
            # Sample the alpha channel cheaply (every ~9th pixel) instead of
            # loading the full-res buffer per pixel.
            alpha = im.getchannel("A")
            w, h = alpha.size
            step_x = max(1, w // 120)
            step_y = max(1, h // 120)
            px = alpha.load()
            total = 0
            transparent = 0
            for y in range(0, h, step_y):
                for x in range(0, w, step_x):
                    total += 1
                    if px[x, y] < 250:
                        transparent += 1
            ratio = transparent / total if total else 0
            row["_transparent_ratio"] = round(ratio, 3)
            if ratio < 0.03:
                blocks.append(
                    f"background-removal[{key}]: RGBA but only {ratio:.1%} pixels have any "
                    f"transparency (looks fully opaque, background likely NOT removed): {path}")
            elif ratio > 0.985:
                blocks.append(
                    f"background-removal[{key}]: {ratio:.1%} pixels fully transparent "
                    f"(subject may have been keyed out too, check the cutout): {path}")
        except Exception as e:
            blocks.append(f"background-removal[{key}]: could not open/verify image ({e}): {path}")


def _check_scene_materials(brain: Optional[dict], by_key: dict, blocks: list, warns: list):
    if not isinstance(brain, dict):
        warns.append("scenes: brain_input.json not found/unreadable, scene-completeness check skipped")
        return
    scenes = brain.get("scenes") or []
    for i, s in enumerate(scenes):
        idx = s.get("scene_index", s.get("scene_idx", i))
        bg_key = s.get("background_reuse_key")
        fg_key = s.get("foreground_reuse_key")
        if not bg_key:
            blocks.append(f"scene[{idx}]: no background_reuse_key set (scene would render blank)")
        elif bg_key not in by_key:
            blocks.append(f"scene[{idx}]: background_reuse_key '{bg_key}' has no matching manifest row "
                          f"(missing/unapproved background image)")
        elif by_key[bg_key].get("layer_type") != "Background":
            blocks.append(f"scene[{idx}]: background_reuse_key '{bg_key}' resolves to a "
                          f"{by_key[bg_key].get('layer_type')} row, not Background")
        if fg_key:
            if fg_key not in by_key:
                blocks.append(f"scene[{idx}]: foreground_reuse_key '{fg_key}' has no matching manifest row "
                              f"-- this is exactly the 'missing core image' defect class")
            elif by_key[fg_key].get("layer_type") != "Foreground/Overlay":
                blocks.append(f"scene[{idx}]: foreground_reuse_key '{fg_key}' resolves to a "
                              f"{by_key[fg_key].get('layer_type')} row, not Foreground/Overlay")


def _check_simulated_sidecars(by_key: dict, blocks: list):
    try:
        from scripts.simulated_asset_gate import is_simulated  # type: ignore
    except Exception:
        import sys
        sys.path.insert(0, str(REPO / "scripts"))
        try:
            from simulated_asset_gate import is_simulated  # type: ignore
        except Exception:
            return
    for key, row in by_key.items():
        if not row.get("_exists"):
            continue
        info = is_simulated(row["local_path"])
        if info is not None:
            blocks.append(f"simulated-asset[{key}]: marked simulated/placeholder ({info.get('reason')}), "
                          f"would have reached render silently: {row['local_path']}")


def _check_voice_lock(lang_code: str, blocks: list, warns: list):
    """Only checks the voice actually RESOLVED for this episode's own
    lang_code -- never flags other languages' own native default voices.
    """
    tts_edge = REPO / "app/services/mpt_ported/tts_edge.py"
    s4 = REPO / "app/pipeline/stages/s4_tts.py"
    if not tts_edge.exists() or not s4.exists():
        warns.append("voice-lock: tts_edge.py or s4_tts.py not found, skipped")
        return
    if lang_code not in LOCKED_MALE_VOICE_LANGS:
        return
    default_voice = None
    m = re.search(r'DEFAULT_VOICE\s*=\s*"([^"]+)"', tts_edge.read_text())
    if m:
        default_voice = m.group(1)
    lang_voice_map = {}
    s4_src = s4.read_text()
    m2 = re.search(r"LANG_VOICE\s*=\s*\{(.*?)\}", s4_src, re.DOTALL)
    if m2:
        for lk, lv in re.findall(r'"(\w+)"\s*:\s*"([^"]+)"', m2.group(1)):
            lang_voice_map[lk] = lv
    resolved = lang_voice_map.get(lang_code) or default_voice
    if not resolved:
        warns.append(f"voice-lock: could not resolve configured voice for lang_code={lang_code}")
        return
    if resolved in KNOWN_FEMALE_VOICES:
        blocks.append(f"voice-lock: configured voice for lang_code='{lang_code}' is '{resolved}', a "
                      f"known-FEMALE voice, but the locked spec requires a middle-aged MALE voice")
    elif resolved not in KNOWN_MALE_VOICES:
        warns.append(f"voice-lock: configured voice for lang_code='{lang_code}' is '{resolved}', not in "
                     f"the known male/female list -- verify gender manually")


def _check_ssml_leak_risk_static(blocks: list, warns: list):
    tts_edge = REPO / "app/services/mpt_ported/tts_edge.py"
    if not tts_edge.exists():
        warns.append(f"ssml-leak: {tts_edge} not found")
        return
    src = tts_edge.read_text()
    m = re.search(r"async def synthesize\b.*?(?=\nasync def |\ndef |\Z)", src, re.DOTALL)
    body = m.group(0) if m else src
    # Heuristic: find `Communicate(...text=<VAR>...)` and check whether VAR was
    # assigned from build_ssml(...) anywhere earlier in the same function body.
    comm_call = re.search(r"Communicate\([^)]*text\s*=\s*([A-Za-z_][A-Za-z0-9_]*)", body)
    if comm_call:
        var = comm_call.group(1)
        assign_re = re.search(rf"{re.escape(var)}\s*=\s*build_ssml\(", body)
        if assign_re:
            blocks.append("ssml-leak: synthesize() passes a build_ssml()-built string directly into "
                          "edge_tts.Communicate(text=...) -- this double-escapes SSML and reads tags "
                          "aloud (the exact 'mat ma' bug). Strip SSML before calling Communicate().")
    elif "Communicate(" not in body:
        warns.append("ssml-leak: could not locate a Communicate(...) call inside synthesize() to verify")


def _check_existing_srt_for_leak(out_dir: Path, blocks: list):
    srt = out_dir / "subtitles.srt"
    if not srt.exists():
        return
    try:
        text = srt.read_text(errors="ignore")
    except Exception:
        return
    low = text.lower()
    hits = [tok for tok in SSML_LEAK_TOKENS if tok.lower() in low]
    if hits:
        snippet = text.strip().splitlines()[:6]
        blocks.append(
            f"ssml-leak: existing subtitles.srt/audio contains literal-or-spoken SSML token(s) {hits} "
            f"-- this episode dir's TTS/subtitle output was produced BEFORE the SSML fix and is STALE. "
            f"It must be re-synthesized (S4 TTS + S6 subtitle re-run), never reused as-is, at render time. "
            f"First lines found: {snippet}")


def _check_seo_regression(warns: list):
    seo = REPO / "app/services/seo_metadata.py"
    if not seo.exists():
        return
    src = seo.read_text().lower()
    hits = [s for s in BANNED_LEGACY_STRINGS if s in src]
    if hits:
        warns.append(f"seo-regression: retired legacy string(s) {hits} reappeared in seo_metadata.py "
                     f"(informational -- verify it is not a live fallback path before publishing)")


def run_preflight_gate(out_dir, brain_input_path: Optional[str] = None, brain: Optional[dict] = None) -> dict:
    """Run every check and write <out_dir>/preflight_render_report.json.

    Returns {"verdict": "PASS"|"BLOCKED", "blocks": [...], "warns": [...], "checked_at": iso}.
    """
    import time
    out_dir = Path(out_dir)
    brain_input_path = Path(brain_input_path) if brain_input_path else (out_dir / "brain_input.json")

    blocks: list = []
    warns: list = []

    if brain is None:
        brain = _read_json(brain_input_path)
    lang_code = (brain or {}).get("lang_code") or "en"
    if isinstance(lang_code, list):
        lang_code = lang_code[0] if lang_code else "en"

    by_key = _resolve_manifest(out_dir, blocks, warns)
    _check_scene_materials(brain, by_key, blocks, warns)
    _check_foreground_alpha(by_key, blocks, warns)
    _check_simulated_sidecars(by_key, blocks)
    _check_voice_lock(lang_code, blocks, warns)
    _check_ssml_leak_risk_static(blocks, warns)
    _check_existing_srt_for_leak(out_dir, blocks)
    _check_seo_regression(warns)

    verdict = "BLOCKED" if blocks else "PASS"
    report = {
        "episode_dir": str(out_dir),
        "lang_code": lang_code,
        "verdict": verdict,
        "n_checks_run": 8,
        "blocks": blocks,
        "warns": warns,
        "checked_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
    }
    try:
        (out_dir / "preflight_render_report.json").write_text(
            json.dumps(report, indent=2, ensure_ascii=False))
    except Exception:
        pass
    return report
