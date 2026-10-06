# app/services/beat_bgm_engine.py
"""Beat-Level Adaptive BGM Orchestration Engine.

Mục tiêu & Kiến Trúc:
1. Phối đa tầng theo 5 Beat kịch bản Docudrama (Beat 1 Hook -> Beat 2 Buildup -> Beat 3 Forensic -> Beat 4 Climax -> Beat 5 Reflection).
2. Tuyển chọn từ kho nhạc YouTube Audio Library / CC-BY Royalty-Free sạch 100% bản quyền Content ID.
3. Đồng bộ chuẩn mili-giây với các mốc Beat từ `audio_beats/` hoặc `whisper_segments.json`.
4. Áp dụng kỹ thuật chuyển âm điện ảnh `acrossfade=d=2.5` tại các khoảng nghỉ giữa Beat, đảm bảo tổng thời lượng BGM khớp 100% với Master Audio.
5. Tạo báo cáo siêu dữ liệu bản quyền (attribution license) để tự động nhúng vào mô tả YouTube B10.
"""
from __future__ import annotations

import os
import sys
import json
import logging
import hashlib
import subprocess
import re
from pathlib import Path
from typing import Dict, List, Any, Optional, Tuple

logger = logging.getLogger("vf.beat_bgm_engine")

REPO_ROOT = Path(os.getenv("VF_REPO_DIR") or Path(__file__).resolve().parent.parent.parent)
CATALOG_PATH = Path(os.getenv("BGM_CATALOG_PATH", str(REPO_ROOT / "assets" / "bgm_curated" / "catalog.json")))
CURATED_DIR = Path(os.getenv("BGM_CURATED_DIR", str(REPO_ROOT / "assets" / "bgm_curated")))
LEGACY_DIR = Path(os.getenv("BGM_DIR", str(REPO_ROOT / "assets" / "bgm")))

EMBEDDED_FALLBACK_CATALOG = [
    {"beat_index": 1, "beat_name": "beat_1_hook", "track_id": "investigations", "title": "Investigations", "artist": "Kevin MacLeod", "duration_s": 93.5, "file_path": str(CURATED_DIR / "beat_1_hook" / "investigations.mp3"), "license": "Creative Commons: By Attribution 3.0 License", "source": "YouTube Audio Library Certified"},
    {"beat_index": 2, "beat_name": "beat_2_buildup", "track_id": "covert_affair", "title": "Covert Affair", "artist": "Kevin MacLeod", "duration_s": 194.2, "file_path": str(CURATED_DIR / "beat_2_buildup" / "covert_affair.mp3"), "license": "Creative Commons: By Attribution 3.0 License", "source": "YouTube Audio Library Certified"},
    {"beat_index": 3, "beat_name": "beat_3_investigation", "track_id": "stay_the_course", "title": "Stay the Course", "artist": "Kevin MacLeod", "duration_s": 272.1, "file_path": str(CURATED_DIR / "beat_3_investigation" / "stay_the_course.mp3"), "license": "Creative Commons: By Attribution 3.0 License", "source": "YouTube Audio Library Certified"},
    {"beat_index": 4, "beat_name": "beat_4_climax", "track_id": "black_vortex", "title": "Black Vortex", "artist": "Kevin MacLeod", "duration_s": 169.7, "file_path": str(CURATED_DIR / "beat_4_climax" / "black_vortex.mp3"), "license": "Creative Commons: By Attribution 3.0 License", "source": "YouTube Audio Library Certified"},
    {"beat_index": 5, "beat_name": "beat_5_reflection", "track_id": "heartbreaking", "title": "Heartbreaking", "artist": "Kevin MacLeod", "duration_s": 96.0, "file_path": str(CURATED_DIR / "beat_5_reflection" / "heartbreaking.mp3"), "license": "Creative Commons: By Attribution 3.0 License", "source": "YouTube Audio Library Certified"},
]

BEAT_MOOD_MAP = {
    1: "beat_1_hook",
    2: "beat_2_buildup",
    3: "beat_3_investigation",
    4: "beat_4_climax",
    5: "beat_5_reflection",
}

DEFAULT_BEAT_RATIOS = [0.15, 0.25, 0.25, 0.20, 0.15]


def _probe_duration(file_path: str) -> float:
    """Probe audio duration in seconds using ffprobe."""
    if not file_path or not os.path.exists(file_path):
        return 0.0
    try:
        cmd = [
            "ffprobe", "-v", "error",
            "-show_entries", "format=duration",
            "-of", "default=noprint_wrappers=1:nokey=1",
            file_path
        ]
        res = subprocess.run(cmd, capture_output=True, text=True, check=True)
        return float(res.stdout.strip() or 0.0)
    except Exception as e:
        logger.warning("[beat_bgm_engine] ffprobe failed for %s: %s", file_path, e)
        return 0.0


def load_bgm_catalog() -> List[Dict[str, Any]]:
    """Load curated BGM catalog. Fallback to scanning directory if catalog.json is missing."""
    try:
        if CATALOG_PATH.exists():
            with open(CATALOG_PATH, "r", encoding="utf-8") as f:
                return json.load(f)
    except (PermissionError, OSError, Exception) as e:
        logger.warning("[beat_bgm_engine] Failed to read catalog.json (%s), checking filesystem", e)

    # Fallback: scan CURATED_DIR
    catalog = []
    if CURATED_DIR.exists():
        for beat_idx, b_name in BEAT_MOOD_MAP.items():
            b_dir = CURATED_DIR / b_name
            if b_dir.exists():
                for mp3 in b_dir.glob("*.mp3"):
                    dur = _probe_duration(str(mp3))
                    catalog.append({
                        "beat_index": beat_idx,
                        "beat_name": b_name,
                        "track_id": mp3.stem,
                        "title": mp3.stem.replace("_", " ").title(),
                        "artist": "Kevin MacLeod",
                        "duration_s": dur,
                        "file_path": str(mp3),
                        "license": "Creative Commons: By Attribution 3.0 License",
                        "license_url": "http://creativecommons.org/licenses/by/3.0/",
                        "source": "YouTube Audio Library Certified"
                    })
    if not catalog:
        return EMBEDDED_FALLBACK_CATALOG
    return catalog


def get_beat_durations(episode_id: str, out_dir: Optional[str] = None, total_dur: Optional[float] = None) -> List[float]:
    """Determine the duration in seconds for each beat (1..5).
    Priority:
      1. audio_beats/beat_1.mp3 .. beat_5.mp3 probe
      2. whisper_segments.json grouped by beat_index
      3. Total audio duration partitioned by standard 5-Act ratios
    """
    out_dir = out_dir or f"/var/vf/episodes/{episode_id}"
    beats_dir = Path(out_dir) / "audio_beats"

    # Strategy 1: Check audio_beats folder from beat_tts_engine
    durations = []
    if beats_dir.exists():
        for i in range(1, 6):
            bp = beats_dir / f"beat_{i}.mp3"
            if bp.exists():
                d = _probe_duration(str(bp))
                if d > 0.5:
                    durations.append(d)
                else:
                    break
            else:
                break
        if len(durations) == 5:
            logger.info("[beat_bgm_engine] Resolved 5 Beat durations from audio_beats: %s", [round(x, 1) for x in durations])
            return durations

    # Strategy 1.5: Check remotion_props.json or director_plan.json for exact scene-rendered beat timing
    props_path = Path(out_dir) / "remotion_props.json"
    if props_path.exists():
        try:
            with open(props_path, "r", encoding="utf-8") as pf:
                pdata = json.load(pf)
            scenes = pdata.get("scenes", [])
            beat_scene_durs: Dict[int, float] = {1: 0.0, 2: 0.0, 3: 0.0, 4: 0.0, 5: 0.0}
            fps = float(pdata.get("fps") or 30.0)
            for sc in scenes:
                b_idx = int(sc.get("beat_index") or 1)
                if b_idx in beat_scene_durs:
                    frames = float(sc.get("durationInFrames") or (float(sc.get("duration_sec") or 4.0) * fps))
                    beat_scene_durs[b_idx] += frames / fps
            if all(beat_scene_durs[b] > 0 for b in range(1, 6)):
                exact_durs = [beat_scene_durs[b] for b in range(1, 6)]
                logger.info("[beat_bgm_engine] Resolved exact 5 Beat durations from remotion_props.json: %s", [round(x, 1) for x in exact_durs])
                return exact_durs
        except Exception as e:
            logger.warning("[beat_bgm_engine] Failed to parse remotion_props.json: %s", e)

    # Strategy 2: Check whisper_segments.json
    seg_path = Path(out_dir) / "whisper_segments.json"
    if seg_path.exists():
        try:
            with open(seg_path, "r", encoding="utf-8") as sf:
                segments = json.load(sf)
            beat_groups: Dict[int, List[Dict]] = {}
            for s in segments:
                b_idx = int(s.get("beat_index") or 1)
                beat_groups.setdefault(b_idx, []).append(s)
            
            if len(beat_groups) >= 3:
                seg_durations = []
                for i in sorted(beat_groups.keys()):
                    segs = beat_groups[i]
                    s_min = min(int(x.get("start_ms", 0)) for x in segs)
                    s_max = max(int(x.get("end_ms", 0)) for x in segs)
                    seg_durations.append(max(1.0, (s_max - s_min) / 1000.0))
                if len(seg_durations) == 5:
                    logger.info("[beat_bgm_engine] Resolved 5 Beat durations from whisper_segments: %s", [round(x, 1) for x in seg_durations])
                    return seg_durations
        except Exception as e:
            logger.warning("[beat_bgm_engine] Failed to parse whisper_segments: %s", e)

    # Strategy 3: Partition total duration
    if total_dur is None or total_dur <= 0.0:
        for a_name in ["audio_norm.mp3", "tts_out.mp3"]:
            ap = Path(out_dir) / a_name
            if ap.exists():
                total_dur = _probe_duration(str(ap))
                if total_dur > 0:
                    break
    total_dur = total_dur or 600.0
    fallback_durations = [total_dur * r for r in DEFAULT_BEAT_RATIOS]
    logger.info("[beat_bgm_engine] Partitioned total duration %.1fs into 5 beats: %s", total_dur, [round(x, 1) for x in fallback_durations])
    return fallback_durations


def _extract_story_context(episode_id: str, out_dir: Optional[str] = None) -> Dict[str, Any]:
    """Extract topic, market, and 5-beat story narrative from episode directory if available."""
    out_dir = out_dir or f"/var/vf/episodes/{episode_id}"
    ep_path = Path(out_dir)
    context: Dict[str, Any] = {"topic": episode_id, "market": "EN", "pillar": "", "beats": {}}

    # 1. Try brain_input.json
    brain_path = ep_path / "brain_input.json"
    if brain_path.exists():
        try:
            with open(brain_path, "r", encoding="utf-8") as f:
                bdata = json.load(f)
            context["topic"] = bdata.get("topic") or bdata.get("title_a") or bdata.get("raw_term") or episode_id
            context["market"] = bdata.get("market", "EN")
            context["pillar"] = bdata.get("niche_angle_brief") or bdata.get("pillar", "")
        except Exception as e:
            logger.debug("[beat_bgm_engine] Error reading brain_input.json: %s", e)

    # 2. Try story.txt
    story_path = ep_path / "story.txt"
    if story_path.exists():
        try:
            with open(story_path, "r", encoding="utf-8") as f:
                content = f.read()
            act_patterns = [
                r"===\s*ACT\s*I\s*===(.*?)(?====\s*ACT\s*II\s*===|\Z)",
                r"===\s*ACT\s*II\s*===(.*?)(?====\s*ACT\s*III\s*===|\Z)",
                r"===\s*ACT\s*III\s*===(.*?)(?====\s*ACT\s*IV\s*===|\Z)",
                r"===\s*ACT\s*IV\s*===(.*?)(?====\s*ACT\s*V\s*===|\Z)",
                r"===\s*ACT\s*V\s*===(.*?)(?=\Z)"
            ]
            for idx, pat in enumerate(act_patterns, start=1):
                m = re.search(pat, content, re.DOTALL | re.IGNORECASE)
                if m:
                    text_snippet = m.group(1).strip()[:500]
                    context["beats"][idx] = text_snippet
        except Exception as e:
            logger.debug("[beat_bgm_engine] Error reading story.txt: %s", e)

    return context


def _llm_select_tracks(
    episode_id: str,
    catalog: List[Dict[str, Any]],
    story_context: Dict[str, Any],
    out_dir: Optional[str] = None,
    model_override: Optional[str] = None
) -> Optional[List[Dict[str, Any]]]:
    """Use HHTech LLM (gpt-6-astra / claude-opus-5-5) to curate BGM tracks based on story tone."""
    try:
        from app.services.model_gateway import get_global_gateway
        gateway = get_global_gateway()
    except Exception as e:
        logger.warning("[beat_bgm_engine] ModelGateway unavailable: %s", e)
        return None

    model = model_override or os.getenv("BGM_SELECTOR_MODEL", "gpt-6-astra")
    out_dir = out_dir or f"/var/vf/episodes/{episode_id}"

    # Group candidate tracks by beat index
    candidates_by_beat: Dict[int, List[Dict[str, Any]]] = {}
    for t in catalog:
        b_idx = int(t.get("beat_index", 1))
        candidates_by_beat.setdefault(b_idx, []).append(t)

    # Build candidate descriptions
    candidates_prompt_text = ""
    for b_idx in range(1, 6):
        candidates = candidates_by_beat.get(b_idx, [])
        candidates_prompt_text += f"\n--- BEAT {b_idx} CANDIDATE TRACKS ---\n"
        for c in candidates:
            mood_tags = ", ".join(c.get("mood_tags", [])) or "cinematic"
            candidates_prompt_text += (
                f"  • track_id: \"{c['track_id']}\" | Title: \"{c['title']}\" | "
                f"BPM: {c.get('bpm', 100)} | Vibe: {c.get('vibe', '')} | Tags: [{mood_tags}]\n"
            )

    system_prompt = (
        "You are an award-winning Hollywood Documentary Music Supervisor and Sound Director. "
        "Your task is to select the perfect background score (BGM) track for each of the 5 Beats "
        "of an investigative docudrama episode.\n\n"
        "Editorial Principles:\n"
        "- Beat 1 (Hook / Cold Strike): Tension, curiosity, immediate hook pacing.\n"
        "- Beat 2 (False Narrative / Buildup): Creeping doubt, subtle suspense, or ticking clock.\n"
        "- Beat 3 (Forensic Paper Trail): Steady, analytical investigative rhythm, focus, minimal distraction.\n"
        "- Beat 4 (Climax / Smoking Gun): High stakes, peak dramatic tension, decisive reveal.\n"
        "- Beat 5 (Living Warning / Reflection): Somber resolution, lingering tragedy, philosophical aftermath.\n\n"
        "You must select EXACTLY ONE valid track_id from the candidate tracks for each beat (1 to 5).\n"
        "Return STRICT JSON only without markdown code blocks:\n"
        "{\n"
        '  "narrative_mood_analysis": "<Brief analysis of the episode tone>",\n'
        '  "selections": [\n'
        '    {"beat_index": 1, "track_id": "<ID>", "rationale": "<Why this track matches Beat 1>"},\n'
        '    {"beat_index": 2, "track_id": "<ID>", "rationale": "<Why this track matches Beat 2>"},\n'
        '    {"beat_index": 3, "track_id": "<ID>", "rationale": "<Why this track matches Beat 3>"},\n'
        '    {"beat_index": 4, "track_id": "<ID>", "rationale": "<Why this track matches Beat 4>"},\n'
        '    {"beat_index": 5, "track_id": "<ID>", "rationale": "<Why this track matches Beat 5>"}\n'
        '  ]\n'
        "}"
    )

    prompt = (
        f"Episode: {story_context.get('topic')}\n"
        f"Market: {story_context.get('market')}\n"
        f"Pillar / Angle: {story_context.get('pillar')}\n\n"
        "=== 5-BEAT STORY SUMMARY ===\n"
    )
    for b_idx in range(1, 6):
        b_summary = story_context.get("beats", {}).get(b_idx, f"Beat {b_idx} narrative")
        prompt += f"[Beat {b_idx}]: {b_summary}\n"

    prompt += f"\n=== AVAILABLE BGM CANDIDATE TRACKS ===\n{candidates_prompt_text}\n"
    prompt += "Select the optimal soundtrack tracks now (strict JSON):"

    try:
        raw_res = gateway.call_llm(
            prompt=prompt,
            model=model,
            system_prompt=system_prompt,
            max_tokens=1000,
            temperature=0.2,
            timeout=30.0
        )
        if not raw_res:
            return None

        clean_json = raw_res.strip()
        if clean_json.startswith("```"):
            clean_json = re.sub(r"^```[a-zA-Z]*\n?", "", clean_json)
            clean_json = re.sub(r"\n?```$", "", clean_json)

        data = json.loads(clean_json)
        selections = data.get("selections", [])
        if len(selections) != 5:
            logger.warning("[beat_bgm_engine] LLM returned %d selections instead of 5", len(selections))
            return None

        catalog_by_id = {t["track_id"]: t for t in catalog}
        chosen_tracks = []
        for s in selections:
            tid = s.get("track_id")
            if tid in catalog_by_id:
                track = dict(catalog_by_id[tid])
                track["director_rationale"] = s.get("rationale", "")
                chosen_tracks.append(track)
            else:
                logger.warning("[beat_bgm_engine] Unknown track_id '%s' returned by LLM", tid)
                return None

        if len(chosen_tracks) == 5:
            try:
                dec_path = Path(out_dir) / "bgm_director_decision.json"
                dec_path.parent.mkdir(parents=True, exist_ok=True)
                with open(dec_path, "w", encoding="utf-8") as df:
                    json.dump({
                        "episode_id": episode_id,
                        "model": model,
                        "narrative_mood_analysis": data.get("narrative_mood_analysis"),
                        "selections": selections
                    }, df, indent=2, ensure_ascii=False)
                logger.info("[beat_bgm_engine] Saved AI Music Supervisor decision to %s", dec_path)
            except Exception as pe:
                logger.warning("[beat_bgm_engine] Failed to save bgm_director_decision.json: %s", pe)

            return chosen_tracks

    except Exception as e:
        logger.warning("[beat_bgm_engine] LLM track curation failed (%s), will fallback", e)

    return None


def select_5_beat_tracks(
    episode_id: str,
    catalog: Optional[List[Dict[str, Any]]] = None,
    out_dir: Optional[str] = None,
    story_context: Optional[Dict[str, Any]] = None,
    use_llm: Optional[bool] = None
) -> List[Dict[str, Any]]:
    """Select 5 cohesive tracks for beats 1..5.
    
    Priority:
      1. LLM AI Music Supervisor (via HHTech gpt-6-astra / claude-opus-5-5) if story exists & use_llm is True
      2. Deterministic hash-modulo fallback (Rule 125 single truth, zero downtime)
    """
    catalog = catalog or load_bgm_catalog()
    if not catalog:
        raise RuntimeError("No BGM tracks found in curated catalog or assets/bgm_curated!")

    out_dir = out_dir or f"/var/vf/episodes/{episode_id}"

    if use_llm is None:
        use_llm = os.getenv("BGM_USE_LLM", "true").lower() in ("true", "1", "yes")

    if use_llm:
        context = story_context or _extract_story_context(episode_id, out_dir=out_dir)
        # Only invoke LLM if we have actual story beats
        if context.get("beats") and len(context["beats"]) >= 3:
            llm_tracks = _llm_select_tracks(episode_id, catalog, context, out_dir=out_dir)
            if llm_tracks and len(llm_tracks) == 5:
                logger.info("[beat_bgm_engine] AI Music Supervisor successfully selected 5 Beat tracks for %s", episode_id)
                return llm_tracks

    # Deterministic fallback (hash-based)
    logger.info("[beat_bgm_engine] Using deterministic fallback track selection for %s", episode_id)
    selected_tracks = []
    # Seed by episode_id to ensure deterministic consistency across re-runs
    seed_int = int(hashlib.md5(episode_id.encode("utf-8")).hexdigest()[:8], 16)

    for beat_idx in range(1, 6):
        candidates = [t for t in catalog if int(t.get("beat_index", 1)) == beat_idx]
        if not candidates:
            # Fallback to any track
            candidates = catalog
        chosen = candidates[(seed_int + beat_idx) % len(candidates)]
        selected_tracks.append(chosen)

    return selected_tracks


def generate_beat_adaptive_bgm(
    episode_id: str,
    out_dir: Optional[str] = None,
    audio_path: Optional[str] = None,
    crossfade_s: float = 2.5,
    force: bool = False
) -> Dict[str, Any]:
    """Assemble a 5-Beat adaptive cinematic soundtrack matching the episode's narration timeline.
    
    Returns:
      {
        "bgm_path": "/var/vf/episodes/<id>/bgm_master.mp3",
        "total_duration_s": float,
        "tracks": List[Dict],
        "attribution_text": str
      }
    """
    out_dir = out_dir or f"/var/vf/episodes/{episode_id}"
    os.makedirs(out_dir, exist_ok=True)
    target_bgm_path = os.path.join(out_dir, "bgm_master.mp3")

    # Resolve master audio duration
    audio_path = audio_path or os.path.join(out_dir, "audio_norm.mp3")
    if not os.path.exists(audio_path):
        audio_path = os.path.join(out_dir, "tts_out.mp3")
    
    total_audio_dur = _probe_duration(audio_path)
    if total_audio_dur <= 0.0:
        total_audio_dur = 600.0

    # Idempotency check: reuse if existing bgm_master.mp3 matches duration within 1.5s
    if not force and os.path.exists(target_bgm_path) and os.path.getsize(target_bgm_path) > 100000:
        existing_dur = _probe_duration(target_bgm_path)
        if abs(existing_dur - total_audio_dur) <= 2.0:
            logger.info("[beat_bgm_engine] Reusing existing valid bgm_master.mp3 (%.1fs) for %s", existing_dur, episode_id)
            tracks = select_5_beat_tracks(episode_id, out_dir=out_dir)
            attr_lines = [f"• {t['title']} by {t.get('artist', 'Kevin MacLeod')} ({t.get('license', 'CC-BY')})" for t in tracks]
            return {
                "bgm_path": target_bgm_path,
                "total_duration_s": existing_dur,
                "tracks": tracks,
                "attribution_text": "Music: " + " | ".join(attr_lines)
            }

    beat_durations = get_beat_durations(episode_id, out_dir=out_dir, total_dur=total_audio_dur)
    selected_tracks = select_5_beat_tracks(episode_id, out_dir=out_dir)

    num_beats = len(beat_durations)
    logger.info("[beat_bgm_engine] Assembling 5-Beat BGM for %s (target total=%.1fs, %d beats)...", episode_id, total_audio_dur, num_beats)

    # Build FFmpeg command
    # Each segment i (0-indexed) has duration:
    # If i < num_beats - 1: dur_i + crossfade_s
    # If i == num_beats - 1: dur_i
    inputs = []
    filter_chains = []
    
    for i in range(num_beats):
        track = selected_tracks[i]
        track_path = track["file_path"]
        if not os.path.exists(track_path):
            raise FileNotFoundError(f"BGM track file not found: {track_path}")
        
        inputs.extend(["-stream_loop", "-1", "-i", track_path])
        
        b_dur = beat_durations[i]
        seg_dur = b_dur + crossfade_s if i < num_beats - 1 else b_dur
        # Trim each stream
        filter_chains.append(f"[{i}:a]atrim=0:{seg_dur:.3f},asetpts=PTS-STARTPTS[seg{i}]")

    # Chain acrossfades
    # [seg0][seg1]acrossfade=d=2.5:c1=tri:c2=tri[m1]
    # [m1][seg2]acrossfade=d=2.5:c1=tri:c2=tri[m2]
    # ...
    curr_label = "seg0"
    for i in range(1, num_beats):
        next_label = f"seg{i}"
        merged_label = f"m{i}" if i < num_beats - 1 else "crossfaded_raw"
        filter_chains.append(
            f"[{curr_label}][{next_label}]acrossfade=d={crossfade_s:.2f}:c1=tri:c2=tri[{merged_label}]"
        )
        curr_label = merged_label

    # Final normalization & duration capping to exact total_audio_dur
    filter_chains.append(
        f"[{curr_label}]atrim=0:{total_audio_dur:.3f},afade=t=in:st=0:d=1.5,afade=t=out:st={max(0, total_audio_dur - 3.0):.3f}:d=3.0,volume=0.9[aout]"
    )

    filter_complex = ";".join(filter_chains)

    cmd = [
        "ffmpeg", "-y",
        *inputs,
        "-filter_complex", filter_complex,
        "-map", "[aout]",
        "-c:a", "libmp3lame",
        "-b:a", "192k",
        target_bgm_path
    ]

    logger.info("[beat_bgm_engine] Running FFmpeg BGM compilation...")
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        logger.error("[beat_bgm_engine] FFmpeg BGM compilation failed: %s", proc.stderr[-1000:])
        raise RuntimeError(f"FFmpeg BGM assembly failed: {proc.stderr[-500:]}")

    final_dur = _probe_duration(target_bgm_path)
    file_size = os.path.getsize(target_bgm_path)
    logger.info("[beat_bgm_engine] SUCCESS: Created %s (%.1fs, %d bytes, 5 Beats acrossfaded)", target_bgm_path, final_dur, file_size)

    attr_lines = [f"{t['title']} by {t.get('artist', 'Kevin MacLeod')} ({t.get('license', 'CC-BY')})" for t in selected_tracks]
    attribution_text = "Music Credits: " + " | ".join(attr_lines)

    return {
        "bgm_path": target_bgm_path,
        "total_duration_s": final_dur,
        "tracks": selected_tracks,
        "attribution_text": attribution_text
    }


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate 5-Beat Adaptive BGM for Episode")
    parser.add_argument("--episode-id", required=True)
    parser.add_argument("--out-dir", default=None)
    parser.add_argument("--force", action="store_true")
    args = parser.parse_args()

    logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
    res = generate_beat_adaptive_bgm(args.episode_id, out_dir=args.out_dir, force=args.force)
    print("RESULT:", json.dumps(res, indent=2, ensure_ascii=False))
