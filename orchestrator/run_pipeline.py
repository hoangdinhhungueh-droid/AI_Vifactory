#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""orchestrator/run_pipeline.py — Master Single Pipeline Orchestrator (AVF-STAB-001).

Implements the single entrypoint state machine for AI Video Factory.
Supports:
  - Profiles: --profile {prod | e2e_min}
  - Resumption: --from <STAGE> and --only <STAGE>
  - Idempotency: Skips already-verified stages without re-calling expensive APIs
  - Fast simulation: --dry-run
  - Overwrite: --force
"""

from __future__ import annotations

import sys
import os
import time
import argparse
import importlib
from pathlib import Path
from typing import Dict, Any, List, Optional

ROOT_DIR = Path(__file__).resolve().parent.parent
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
except Exception:
    pass

from core.paths import resolve_run_paths, new_run_paths
from core.contracts.stages import StageID, StageArtifact
from core.run_manifest import RunManifest
from core.config import load_profile, RunContext
from core.gates import GateError, compute_file_sha256

# Stage modules registry
STAGE_MODULES = {
    StageID.S1_IDEATION: "stages.s01_ideation",
    StageID.S2_RESEARCH: "stages.s02_research",
    StageID.S3_SCRIPT: "stages.s03_script",
    StageID.S4_CRITIC_SCRIPT: "stages.s04_critic_script",
    StageID.S5_DIRECTOR_PLAN: "stages.s05_director_plan",
    StageID.S6_CRITIC_VISUAL: "stages.s06_critic_visual",
    StageID.S7_IMAGE_GEN: "stages.s07_image_gen",
    StageID.S8_VIDEO_GEN: "stages.s08_video_gen",
    StageID.S9_VOICE_TTS: "stages.s09_voice_tts",
    StageID.S10_RENDER: "stages.s10_render",
    StageID.S11_QC: "stages.s11_qc",
}


def execute_pipeline(
    profile_name: str = "prod",
    run_id: Optional[str] = None,
    from_stage: Optional[str] = None,
    only_stage: Optional[str] = None,
    dry_run: bool = False,
    force: bool = False
) -> int:
    """Main execution engine loop over all 11 stages."""
    print("=" * 75)
    print("🎬 AI VIDEO FACTORY — MASTER PIPELINE ORCHESTRATOR 2.0")
    print("=" * 75)

    # 1. Resolve Configuration & Paths
    config = load_profile(profile_name, repo_root=ROOT_DIR)
    if run_id:
        paths = resolve_run_paths(run_id, repo_root=ROOT_DIR)
    else:
        paths = new_run_paths(prefix="RUN", repo_root=ROOT_DIR)

    effective_run_id = paths.run_id
    print(f"📌 Run ID:             {effective_run_id}")
    print(f"⚙️ Profile:            {config.name} (v{config.pipeline_version})")
    print(f"📁 Workspace Root:     {paths.root}")
    print(f"🚦 Mode:               {'DRY-RUN' if dry_run else 'LIVE EXECUTION'}")
    print("-" * 75)

    # 2. Load or Create Manifest State Machine
    manifest = RunManifest.load_or_create(paths, profile=config.name)
    ctx = RunContext(
        run_id=effective_run_id,
        paths=paths,
        manifest=manifest,
        config=config,
        force=force,
        dry_run=dry_run
    )

    stage_list = list(StageID)
    start_idx = 0
    if from_stage:
        clean_from = from_stage.lower()
        matched = next((i for i, s in enumerate(stage_list) if clean_from in s.value), None)
        if matched is not None:
            start_idx = matched

    # 3. Stage Execution Loop
    for idx, stage in enumerate(stage_list):
        if idx < start_idx:
            continue

        if only_stage:
            clean_only = only_stage.lower()
            if clean_only not in stage.value:
                continue

        stage_name = stage.value
        mod_name = STAGE_MODULES.get(stage)
        if not mod_name:
            print(f"[-] Unknown stage: {stage_name}")
            return 1

        print(f"\n▶ [{idx+1}/{len(stage_list)}] Executing Stage: {stage_name.upper()}...")

        # 4. Idempotency Check: if already done and artifact valid, skip!
        state = manifest.stages.get(stage)
        art_path = paths.artifact_file(stage_name)
        if not force and state and state.status == "done" and art_path.exists():
            sha_now = compute_file_sha256(art_path)
            if state.artifact_sha256 and state.artifact_sha256 == sha_now:
                print(f"   ⏩ SKIPPED (Idempotent artifact verified: {sha_now[:10]}...)")
                manifest.mark(stage, "skipped", artifact_sha256=sha_now)
                manifest.save_atomic(paths)
                continue

        manifest.mark(stage, "running")
        manifest.save_atomic(paths)

        try:
            stage_mod = importlib.import_module(mod_name)
            artifact = stage_mod.run(ctx)
            
            sha_new = compute_file_sha256(art_path) if art_path.exists() else "none"
            manifest.mark(stage, "done", artifact_sha256=sha_new)
            manifest.save_atomic(paths)
            print(f"   ✅ PASS (Artifact emitted: {art_path.name})")

        except GateError as ge:
            manifest.mark(stage, "failed", error=str(ge))
            manifest.save_atomic(paths)
            print(f"\n❌ [GATE BLOCKED at {stage_name}]: {ge}")
            print(f"   Details: {ge.details}")
            print(f"   Resume command: python -m orchestrator.run_pipeline --run-id {effective_run_id} --from {stage_name}")
            return 1

        except Exception as ex:
            manifest.mark(stage, "failed", error=str(ex))
            manifest.save_atomic(paths)
            print(f"\n❌ [UNEXPECTED ERROR at {stage_name}]: {ex}")
            import traceback
            traceback.print_exc()
            print(f"   Resume command: python -m orchestrator.run_pipeline --run-id {effective_run_id} --from {stage_name}")
            return 1

    print("\n" + "=" * 75)
    print("🏆 ALL 11 PIPELINE STAGES COMPLETED SUCCESSFULLY!")
    print(f"📄 Master Manifest:     {paths.manifest_file}")
    print(f"🎥 Master Video Asset:  {paths.final_render_dir / 'final.mp4'}")
    print("=" * 75 + "\n")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Master Single Pipeline Orchestrator for AI Video Factory")
    parser.add_argument("--profile", default="prod", choices=["prod", "e2e_min"], help="Profile to execute (default: prod)")
    parser.add_argument("--run-id", default=None, help="Optional existing Run ID or Episode ID to resume")
    parser.add_argument("--from", dest="from_stage", default=None, help="Resume execution starting from specified stage")
    parser.add_argument("--only", dest="only_stage", default=None, help="Execute only the specified stage")
    parser.add_argument("--dry-run", action="store_true", help="Fast execution simulation without external API calls")
    parser.add_argument("--force", action="store_true", help="Force re-generation of all artifacts ignoring cache")

    args = parser.parse_args()

    exit_code = execute_pipeline(
        profile_name=args.profile,
        run_id=args.run_id,
        from_stage=args.from_stage,
        only_stage=args.only_stage,
        dry_run=args.dry_run,
        force=args.force
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
