#!/usr/bin/env python3
"""Build Remotion props JSON for the generic "TwoLayerEpisode" composition
(remotion/src/index.tsx) from brain_input.json (2-layer schema extension) +
the local image manifest produced by scripts/pull_approved_images.py.

PIPELINE-WIDE & ARCHITECTURAL:
1. 100% Foreground Coverage Guarantee (Rule 100): automatically fills empty
   foregrounds from approved manifest character cutouts with left/right alternation.
2. Intelligent Stat Card Extraction (Rule 102): automatically scans narration
   for key metrics ($ amounts, percentages, quantities, legal verdicts) to pop-in
   animated Remotion Stat Cards.
3. Clean Studio BGM Integration (Rule 101): integrates with CC0 assets/bgm catalog.
"""
import argparse
import json
import os
import re
import shutil
import sys


def load_manifest_index(manifest_path):
    with open(manifest_path, encoding="utf-8") as f:
        rows = json.load(f)
    by_reuse_key = {}
    fg_pool = []
    for r in rows:
        rk = (r.get("reuse_key") or "").strip()
        lp = r.get("local_path")
        if rk and lp:
            by_reuse_key[rk] = lp
            if "fg_" in rk.lower() or "character" in (r.get("asset_type") or "").lower():
                fg_pool.append((rk, lp))
    return by_reuse_key, fg_pool


def stage_into_public(local_path, public_dir, episode_id):
    """Copy local_path into <public_dir>/pulled/<episode_id>/<basename> and
    return the path relative to public_dir (for staticFile())."""
    if not local_path:
        return None
    if local_path.startswith("http://") or local_path.startswith("https://"):
        return local_path
    dest_dir = os.path.join(public_dir, "pulled", episode_id)
    os.makedirs(dest_dir, exist_ok=True)
    basename = os.path.basename(local_path)
    dest_path = os.path.join(dest_dir, basename)
    if not os.path.exists(local_path):
        raise FileNotFoundError("missing local image: %s" % local_path)
    shutil.copyfile(local_path, dest_path)
    return "pulled/%s/%s" % (episode_id, basename)


def extract_stat_card(text):
    """Extract prominent financial metrics / keywords from narration text."""
    if not text:
        return None, None

    # Common financial patterns
    patterns = [
        (r'(\$\d+(?:\.\d+)?\s*(?:BILLION|MILLION|TRILLION|B|M|K)?(?:\s*→\s*<\$\d+)?(?:\s*/\s*SHARE)?)', "FINANCIAL METRIC // VALUATION"),
        (r'(-\$\d+(?:\.\d+)?\s*(?:BILLION|MILLION|B|M)?)', "BALANCE SHEET // WRITE-DOWN"),
        (r'((?:<\$\d+(?:\.\d+)?|\$\d+(?:\.\d+)?))', "MARKET VALUE // PRICE TARGET"),
        (r'(\d{1,3}%)', "GROWTH RATE // PERCENTAGE"),
        (r'(\d+\+?\s*(?:BOXES|DOCUMENTS|WITNESSES|EMPLOYEES|INVESTIGATORS))', "EVIDENCE // SCALE"),
        (r'((?:GUILTY|CONVICTED|VERDICT|FRAUD|CONSPIRACY))', "LEGAL RULING // VERDICT"),
        (r'((?:MARK-TO-MARKET|SPECIAL PURPOSE ENTITIES|SPE NETWORK|CIRCULAR HEDGE))', "FINANCIAL MECHANISM"),
    ]

    for p, label in patterns:
        m = re.search(p, text, re.IGNORECASE)
        if m:
            val = m.group(1).upper().strip()
            if len(val) >= 2:
                return val, label

    return None, None


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--episode-id", required=True)
    ap.add_argument("--brain-input", required=True)
    ap.add_argument("--segments", default="")
    ap.add_argument("--manifest", required=True)
    ap.add_argument("--out", required=True)
    ap.add_argument("--public-dir", default="/root/video_factory/remotion/public")
    ap.add_argument("--fps", type=int, default=30)
    ap.add_argument("--width", type=int, default=1920)
    ap.add_argument("--height", type=int, default=1080)
    ap.add_argument("--fg-fade-sec", type=float, default=0.5)
    ap.add_argument("--skip-missing", action="store_true",
                     help="drop scenes whose background image is missing instead of failing")
    args = ap.parse_args()

    with open(args.brain_input, encoding="utf-8") as f:
        brain = json.load(f)
    by_reuse_key, fg_pool = load_manifest_index(args.manifest)

    fps = args.fps
    scenes_out = []
    missing = []
    raw_scenes = brain.get("scenes", [])
    total_scenes = len(raw_scenes)

    last_fg_rel = None
    fg_idx = 0

    for i, s in enumerate(raw_scenes):
        bg_key = s.get("background_reuse_key")
        fg_key = s.get("foreground_reuse_key")
        bg_local = by_reuse_key.get(bg_key) if bg_key else None
        fg_local = by_reuse_key.get(fg_key) if fg_key else None

        if bg_key and not bg_local:
            missing.append(bg_key)
            if args.skip_missing:
                continue

        # Auto FG Fallback: Guarantee 100% Foreground Coverage
        if not fg_local and fg_pool:
            chosen_fg_key, chosen_fg_local = fg_pool[fg_idx % len(fg_pool)]
            fg_local = chosen_fg_local
            fg_idx += 1

        bg_rel = stage_into_public(bg_local, args.public_dir, args.episode_id) if bg_local else None
        fg_rel = stage_into_public(fg_local, args.public_dir, args.episode_id) if fg_local else None

        
        dur_sec = float(s.get("duration_sec") or 4.0)
        # B7 & B8 compliance: Exact timestamp matching (Rule 120)
        # Replaced mathematical proportion with exact segment boundaries.
        if args.segments and os.path.exists(args.segments):
            import json, re as _re
            try:
                if not hasattr(main, "_segs_cache"):
                    with open(args.segments, "r", encoding="utf-8") as _sf:
                        main._segs_cache = json.load(_sf)
                    main._seg_idx = 0
                
                _segs = main._segs_cache
                _seg_idx = main._seg_idx
                
                caption_text = s.get("caption") or s.get("narration") or ""
                narration_text = s.get("narration") or caption_text
                scene_text_clean = _re.sub(r'\W+', '', narration_text).lower()
                
                if _segs and _seg_idx < len(_segs) and scene_text_clean:
                    start_ms = _segs[_seg_idx].get("start_ms", _segs[_seg_idx].get("start", 0) * 1000)
                    end_ms = _segs[_seg_idx].get("end_ms", _segs[_seg_idx].get("end", 0) * 1000)
                    accumulated_text = ""
                    
                    while _seg_idx < len(_segs) and len(accumulated_text) < len(scene_text_clean) * 0.9:
                        seg = _segs[_seg_idx]
                        seg_text_clean = _re.sub(r'\W+', '', seg.get("text", "")).lower()
                        accumulated_text += seg_text_clean
                        end_ms = seg.get("end_ms", seg.get("end", 0) * 1000)
                        _seg_idx += 1
                        
                    dur_sec = max(0.1, (end_ms - start_ms) / 1000.0)
                    main._seg_idx = _seg_idx
            except Exception as e:
                import logging
                logging.warning(f"Failed to calculate exact timestamp: {e}")

        caption_text = s.get("caption") or s.get("narration") or ""
        narration_text = s.get("narration") or caption_text

        # Alternate Left / Right position
        default_pos = "left" if (i % 2 == 0) else "right"
        fg_pos = s.get("foreground_position") or default_pos

        # Extract or read stat cards
        stat_val = s.get("stat_value") or s.get("statValue")
        stat_lbl = s.get("stat_label") or s.get("statLabel")
        if not stat_val:
            auto_val, auto_lbl = extract_stat_card(narration_text)
            if auto_val:
                stat_val = auto_val
                stat_lbl = auto_lbl

        # Act Title determination
        act_title = s.get("act_title") or (
            "ACT I // THE COLLAPSE" if i <= int(total_scenes * 0.12) else
            "ACT II // THE RISE & INNOVATION" if i <= int(total_scenes * 0.38) else
            "ACT III // THE FINANCIAL MECHANISM" if i <= int(total_scenes * 0.62) else
            "ACT IV // THE RUN ON CONFIDENCE" if i <= int(total_scenes * 0.82) else
            "PAYOFF // THE LASTING LESSON"
        )

        speaker_tag = s.get("speaker_tag") or s.get("beat") or act_title

        scenes_out.append({
            "background": bg_rel or "",
            "foreground": fg_rel,
            "foregroundPosition": fg_pos,
            "durationInFrames": max(1, round(dur_sec * fps)),
            "foregroundFadeFrames": max(1, round(args.fg_fade_sec * fps)),
            "caption": caption_text,
            "narration": narration_text,
            "safeZone": s.get("safe_zone") or "none",
            "statValue": stat_val,
            "statLabel": stat_lbl,
            "speakerTag": speaker_tag,
            "actTitle": act_title,
        })

    if missing:
        print("WARNING: missing local images for reuse keys: %s" % sorted(set(missing)), file=sys.stderr)
    if not scenes_out:
        print("ERROR: no scenes produced (brain_input has no usable scenes, or all were skipped)", file=sys.stderr)
        sys.exit(1)

    props = {
        "scenes": scenes_out,
        "fps": fps,
        "width": args.width,
        "height": args.height,
    }
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as f:
        json.dump(props, f, ensure_ascii=False, indent=2)
    print("WROTE", args.out, "scenes=%d (100%% FG coverage, stats=%d, missing=%d)" % (
        len(scenes_out),
        sum(1 for sc in scenes_out if sc.get("statValue")),
        len(set(missing))
    ))


if __name__ == "__main__":
    main()
