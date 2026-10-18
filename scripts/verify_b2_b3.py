#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""scripts/verify_b2_b3.py — Independent Forensic Verifier for B2->B3/B3.5 Handoff (Boss TASK_1792304389).

Verifies cryptographic parity, zero-mock canary protection, object-action decomposition,
and I2V prompt readiness across any episode.
Returns exit code 0 on PASS, 1 on FAIL.
"""

import argparse
import hashlib
import json
import sys
import unicodedata
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8", errors="replace")

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

from core.contracts.b2_b3_contract import load_spoken_script
from core.paths import RunPaths

CANARY_MOCK_STRINGS = [
    "in late 2026, an unprecedented regulatory decision",
    "permanently overturned the status quo",
    "the shock verdict",
    "a monumental legal document torn cleanly",
    "the false front",
    "two asymmetrical scale weights",
    "65% offshore drain",
    "the legal vacuum",
    "the living warning",
]


def verify_episode(episode_id_or_path: str, repo_root: Path = ROOT_DIR) -> bool:
    """Rigorous forensic verification of B2 to B3 handoff."""
    print("=" * 70)
    print(f"🔍 VERIFYING B2 -> B3 HANDOFF: {episode_id_or_path}")
    print("=" * 70)

    target_path = Path(episode_id_or_path)
    if target_path.exists():
        paths = RunPaths(target_path, repo_root=repo_root)
    else:
        paths = RunPaths(episode_id_or_path, repo_root=repo_root)
    ep_dir = paths.root

    if not ep_dir.exists():
        print(f"❌ FAIL: Episode directory does not exist: {ep_dir}", file=sys.stderr)
        return False

    # 1. Load B2 Spoken Script (Ground Truth)
    try:
        spoken = load_spoken_script(ep_dir, episode_id=paths.run_id)
        print(f"✅ B2 Ground Truth loaded: {spoken.total_beats} beats from {Path(spoken.source_path).name}")
        print(f"   SHA256: {spoken.source_sha256}")
    except Exception as e:
        print(f"❌ FAIL: Could not load B2 ground truth: {e}", file=sys.stderr)
        return False

    # 2. Load B3 Director Plan Artifact
    b3_artifact_path = paths.artifact_file("s05_director_plan")
    alt_b3_path = ep_dir / "director_plan.json"
    target_b3_file = None

    if b3_artifact_path.exists():
        target_b3_file = b3_artifact_path
    elif alt_b3_path.exists():
        target_b3_file = alt_b3_path
    else:
        print(f"❌ FAIL: No B3 director plan artifact found at {b3_artifact_path} or {alt_b3_path}", file=sys.stderr)
        return False

    try:
        raw_b3 = json.loads(target_b3_file.read_text(encoding="utf-8"))
        payload = raw_b3.get("payload") if "payload" in raw_b3 else raw_b3
        scenes = payload.get("scenes", [])
        print(f"✅ B3 Artifact loaded: {len(scenes)} scenes from {target_b3_file.name}")
    except Exception as e:
        print(f"❌ FAIL: Could not parse B3 artifact: {e}", file=sys.stderr)
        return False

    errors = []

    # 3. Verify Scene Count Parity
    if len(scenes) != spoken.total_beats:
        errors.append(f"Scene count mismatch: B2 has {spoken.total_beats} beats, B3 has {len(scenes)} scenes.")

    # 4. Verify Cryptographic Lineage Hash
    source_meta = payload.get("source", {})
    recorded_sha = source_meta.get("b2_sha256") or payload.get("b2_source_sha256", "")
    if not recorded_sha:
        errors.append("B3 artifact is missing cryptographic lineage hash 'b2_sha256'.")
    elif recorded_sha != spoken.source_sha256:
        errors.append(f"Lineage Hash Mismatch: recorded {recorded_sha[:16]}, actual {spoken.source_sha256[:16]}")
    else:
        print(f"✅ Cryptographic Lineage Hash VERIFIED: {recorded_sha[:16]}... matches B2 file.")

    # 5. Scene-by-Scene Forensic Inspection
    canary_hits = 0
    missing_object_hits = 0
    missing_action_hits = 0
    missing_i2v_hits = 0
    narration_mismatches = 0

    for idx, sc in enumerate(scenes):
        sc_id = sc.get("scene_id", f"SCENE_{idx+1:02d}")
        sc_narration = unicodedata.normalize("NFKC", sc.get("narration", "")).strip()

        # Check Canary Mock Strings
        lower_narr = sc_narration.lower()
        for c in CANARY_MOCK_STRINGS:
            if c in lower_narr:
                canary_hits += 1
                errors.append(f"Canary Violation in {sc_id}: detected mock string '{c}'")

        # Compare Narration with B2 Beat Verbatim
        if idx < len(spoken.beats):
            expected_text = unicodedata.normalize("NFKC", spoken.beats[idx].text).strip()
            if sc_narration != expected_text:
                narration_mismatches += 1
                if narration_mismatches <= 3:
                    errors.append(f"Narration Mismatch in {sc_id}: expected '{expected_text[:40]}...', got '{sc_narration[:40]}...'")

        # Check Objects Decomposition
        objs = sc.get("objects", [])
        if not objs or len(objs) < 1:
            missing_object_hits += 1
        else:
            primary_objs = [o for o in objs if o.get("role") == "primary"]
            if not primary_objs:
                errors.append(f"{sc_id}: objects has no primary role element")

        # Check Actions Decomposition
        actions = sc.get("actions", [])
        if not actions or len(actions) < 1:
            missing_action_hits += 1
        else:
            obj_ids = {o.get("id") for o in objs}
            primary_actions = [a for a in actions if a.get("role") == "primary"]
            if len(primary_actions) != 1:
                errors.append(f"{sc_id}: expected exactly 1 primary action, found {len(primary_actions)}")
            for a in actions:
                subj = a.get("subject")
                if subj and subj not in obj_ids:
                    errors.append(f"{sc_id}: action subject '{subj}' references non-existent object")

        # Check I2V Prompts
        omni_p = sc.get("i2v_prompt_omni") or ""
        gf_p = sc.get("i2v_prompt_google_flow") or ""
        if not omni_p or not gf_p:
            missing_i2v_hits += 1

    if missing_object_hits > 0:
        errors.append(f"{missing_object_hits}/{len(scenes)} scenes lack decomposed objects.")
    if missing_action_hits > 0:
        errors.append(f"{missing_action_hits}/{len(scenes)} scenes lack decomposed actions.")
    if missing_i2v_hits > 0:
        errors.append(f"{missing_i2v_hits}/{len(scenes)} scenes lack Omni or Google Flow I2V prompts.")

    # 6. Final Verdict
    print("-" * 70)
    if errors:
        print(f"❌ VERIFICATION FAILED WITH {len(errors)} ERROR(S):", file=sys.stderr)
        for err in errors[:10]:
            print(f"   • {err}", file=sys.stderr)
        if len(errors) > 10:
            print(f"   ... and {len(errors) - 10} more error(s).", file=sys.stderr)
        return False
    else:
        print("🎉 ALL FORENSIC CHECKS PASSED (100% Zero-Mock & Parity Verified)!")
        print(f"   • {len(scenes)} scenes fully decomposed with physical objects & kinematics.")
        print(f"   • 100% narration preservation without alterations.")
        print(f"   • Zero mock canary remnants detected.")
        print(f"   • Both Omni and Google Flow I2V prompts ready for production.")
        return True


def main():
    parser = argparse.ArgumentParser(description="Verify B2 to B3 handoff integrity")
    parser.add_argument("--episode", required=True, help="Episode ID or path e.g. JP_EP0002_us_deficit_refunds")
    args = parser.parse_args()

    success = verify_episode(args.episode)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
