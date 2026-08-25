#!/usr/bin/env python3
"""Scene Metadata Consistency Gate (story_beat vs beat class of bug).

General pattern: any scene JSON can have a CANONICAL field (written by the
story/Notion layer, e.g. "beat") that gets mirrored/duplicated into a nested
sub-object consumed by a downstream renderer (e.g. "remotion.story_beat" used
by the Remotion visual-card layer). If the story layer edits the canonical
field later (re-arc, re-order) but the mirrored copy is never re-synced, the
two drift apart silently -- no gate catches it because both fields are
individually "valid", just inconsistent with each other.

This script audits (and optionally fixes) exactly that class of drift for one
episode's scenes_manifest.json. Read-only by default; use --apply to write.

Usage:
  python3 scripts/validate_scene_beats.py <episode_dir> [--apply]

Example:
  python3 scripts/validate_scene_beats.py /var/vf/episodes/toys-r-us-2026-ep004
  python3 scripts/validate_scene_beats.py /var/vf/episodes/toys-r-us-2026-ep004 --apply

Safety (Rule 31 / Rule 44):
  - Never overwrites without a timestamped backup of the manifest first.
  - Dry-run always prints the exact count + full mismatch list before --apply
    is honoured; --apply re-checks the same count after writing (must be 0).
  - Idempotent: a second run with --apply after a clean fix reports
    mismatch_count 0 and makes no changes (no backup created on a no-op run).
"""
from __future__ import annotations

import json
import shutil
import sys
from datetime import datetime, timezone
from pathlib import Path


def audit(manifest_path: Path):
    data = json.loads(manifest_path.read_text())
    scenes = data.get("scenes", [])
    mismatches = []
    for i, s in enumerate(scenes):
        canonical_beat = s.get("beat")
        remotion = s.get("remotion") or {}
        mirrored_beat = remotion.get("story_beat")
        if canonical_beat is not None and mirrored_beat is not None and canonical_beat != mirrored_beat:
            mismatches.append({
                "scene_index": i,
                "arc_index": s.get("arc_index"),
                "canonical_beat": canonical_beat,
                "mirrored_story_beat": mirrored_beat,
            })
    return data, scenes, mismatches


def main():
    if len(sys.argv) < 2:
        print("Usage: validate_scene_beats.py <episode_dir> [--apply]", file=sys.stderr)
        sys.exit(2)
    episode_dir = Path(sys.argv[1])
    apply = "--apply" in sys.argv[2:]
    manifest_path = episode_dir / "scenes_manifest.json"
    if not manifest_path.exists():
        print("NOT FOUND: " + str(manifest_path), file=sys.stderr)
        sys.exit(1)

    data, scenes, mismatches = audit(manifest_path)
    print("episode_dir", str(episode_dir))
    print("total_scenes", len(scenes))
    print("mismatch_count", len(mismatches))
    for m in mismatches:
        print(m)

    if not apply:
        print("DRY-RUN ONLY (no changes written). Re-run with --apply to fix.")
        return

    if not mismatches:
        print("NO-OP: nothing to apply, mismatch_count already 0.")
        return

    ts = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    backup_path = manifest_path.with_suffix(manifest_path.suffix + ".bak." + ts)
    shutil.copyfile(manifest_path, backup_path)
    print("BACKUP created:", str(backup_path))

    for i, s in enumerate(scenes):
        canonical_beat = s.get("beat")
        remotion = s.get("remotion") or {}
        if "story_beat" in remotion and remotion.get("story_beat") != canonical_beat:
            remotion["story_beat"] = canonical_beat

    manifest_path.write_text(json.dumps(data, indent=2, ensure_ascii=False))

    _, _, remaining = audit(manifest_path)
    print("post_apply_mismatch_count", len(remaining))
    if remaining:
        print("WARNING: mismatches remain after apply -- investigate.", file=sys.stderr)
        sys.exit(1)
    print("APPLIED OK")


if __name__ == "__main__":
    main()
