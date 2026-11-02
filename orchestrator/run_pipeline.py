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

import argparse
import importlib
import os
import re
import sys
from pathlib import Path
from typing import List, Optional

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

from core.config import RunContext, load_profile
from core.contracts.stages import StageID
from core.gates import GateError, compute_file_sha256
from core.paths import new_run_paths, resolve_run_paths
from core.run_manifest import RunManifest

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


def resolve_stage_index(token: Optional[str], stage_list: List[StageID]) -> Optional[int]:
    """Resolves CLI stage identifier (e.g. 's1', 's01', 's01_ideation', 'ideation', '1') to stage_list index."""
    if not token or not str(token).strip():
        return None
    raw = str(token).strip().lower()

    # Numeric index (1-based: '1' -> 0)
    if raw.isdigit():
        num = int(raw)
        if 1 <= num <= len(stage_list):
            return num - 1

    # Shorthand s1..s9 -> s01..s09
    m = re.match(r"^s(\d)$", raw)
    if m:
        raw = f"s0{m.group(1)}"

    # 1. Exact match on enum value or name
    for i, s in enumerate(stage_list):
        if raw == s.value.lower() or raw == s.name.lower():
            return i

    # 2. Prefix match on stage value (e.g. 's01', 's02', 's10')
    for i, s in enumerate(stage_list):
        if s.value.lower().startswith(raw):
            return i

    # 3. Substring match on stage value (e.g. 'ideation', 'research', 'critic_script')
    for i, s in enumerate(stage_list):
        if raw in s.value.lower():
            return i

    return None


def execute_pipeline(
    profile_name: str = "prod",
    run_id: Optional[str] = None,
    from_stage: Optional[str] = None,
    to_stage: Optional[str] = None,
    only_stage: Optional[str] = None,
    dry_run: bool = False,
    force: bool = False,
    topic: Optional[str] = None,
    profile: Optional[str] = None,
    market: Optional[str] = None,
    preset: Optional[str] = None,
    stop_after: Optional[str] = None,
    max_veo_shots: Optional[int] = None,
) -> int:
    if profile is not None:
        profile_name = profile
    effective_to = to_stage or stop_after
    """Main execution engine loop over all 11 stages."""
    print("=" * 75)
    print("🎬 AI VIDEO FACTORY — MASTER PIPELINE ORCHESTRATOR 2.0")
    print("=" * 75)

    # 1. Resolve Configuration, Presets & Paths
    config = load_profile(profile_name, repo_root=ROOT_DIR)

    if run_id:
        paths = resolve_run_paths(run_id, repo_root=ROOT_DIR)
    else:
        clean_prefix = re.sub(r"[^a-zA-Z0-9_-]+", "_", topic.lower()).strip("_")[:30] if topic else ""
        prefix = f"RUN_{clean_prefix}" if clean_prefix else "RUN"
        paths = new_run_paths(prefix=prefix, repo_root=ROOT_DIR)

    # 2. Load or Create Manifest State Machine
    manifest = RunManifest.load_or_create(paths, profile=config.name)
    preset_name = preset or getattr(manifest, "preset", None) or os.getenv("VF_PRESET") or "macro_legacy"
    manifest.preset = preset_name

    from app.services.preset_loader import load_preset
    loaded_preset = None
    try:
        loaded_preset = load_preset(preset_name, repo_root=ROOT_DIR)
    except Exception as _pe:
        print(f"⚠️ Notice: could not load preset '{preset_name}': {_pe}")

    effective_run_id = paths.run_id
    print(f"📌 Run ID:             {effective_run_id}")
    print(f"⚙️ Profile:            {config.name} (v{config.pipeline_version})")
    print(f"🧭 Preset:             {preset_name}")
    print(f"📁 Workspace Root:     {paths.root}")
    print(f"🚦 Mode:               {'DRY-RUN' if dry_run else 'LIVE EXECUTION'}")
    print("-" * 75)
    from core.market_resolver import resolve_canonical_market

    raw_m = market or os.getenv("VF_MARKET") or os.getenv("MARKET") or getattr(loaded_preset, "market", "EN") or "EN"
    canonical_m = resolve_canonical_market(raw_m)
    manifest.market = canonical_m
    if config is not None:
        config.market = canonical_m
    manifest.save_atomic(paths)

    ctx = RunContext(
        run_id=effective_run_id,
        paths=paths,
        manifest=manifest,
        config=config,
        force=force,
        dry_run=dry_run,
        preset=loaded_preset,
        topic=topic,
        max_veo_shots=max_veo_shots,
    )

    stage_list = list(StageID)
    start_idx = 0
    if from_stage:
        resolved_from = resolve_stage_index(from_stage, stage_list)
        if resolved_from is None:
            print(f"❌ [CONFIGURATION ERROR]: Unknown --from stage '{from_stage}'. Available: {[s.value for s in stage_list]}")
            return 1
        start_idx = resolved_from

    end_idx = len(stage_list) - 1
    if effective_to:
        resolved_to = resolve_stage_index(effective_to, stage_list)
        if resolved_to is None:
            print(f"❌ [CONFIGURATION ERROR]: Unknown target stage '{effective_to}'. Available: {[s.value for s in stage_list]}")
            return 1
        end_idx = resolved_to

    only_target_idx = None
    if only_stage:
        only_target_idx = resolve_stage_index(only_stage, stage_list)
        if only_target_idx is None:
            print(f"❌ [CONFIGURATION ERROR]: Unknown --only stage '{only_stage}'. Available: {[s.value for s in stage_list]}")
            return 1

    # 3. Stage Execution Loop
    for idx, stage in enumerate(stage_list):
        if only_target_idx is not None:
            if idx != only_target_idx:
                continue
        else:
            if idx < start_idx:
                continue
            if idx > end_idx:
                break

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
            _artifact = stage_mod.run(ctx)

            if isinstance(_artifact.payload, dict) and _artifact.payload.get("verdict") in ("fail", "rejected"):
                raise GateError(
                    stage,
                    f"Stage '{stage_name}' critic audit rejected artifact with verdict '{_artifact.payload.get('verdict')}'",
                    details=_artifact.payload.get("violations") or {}
                )

            sha_new = compute_file_sha256(art_path) if art_path.exists() else "none"
            manifest.mark(stage, "done", artifact_sha256=sha_new)
            manifest.save_atomic(paths)
            try:
                print(f"   ✅ PASS (Artifact emitted: {art_path.name})")
            except (BrokenPipeError, OSError):
                pass

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
    parser.add_argument("--to", dest="to_stage", default=None, help="Stop execution after specified stage")
    parser.add_argument("--stop-after", dest="stop_after", default=None, help="Alias for --to: stop execution after specified stage")
    parser.add_argument("--only", dest="only_stage", default=None, help="Execute only the specified stage")
    parser.add_argument("--dry-run", action="store_true", help="Fast execution simulation without external API calls")
    parser.add_argument("--force", action="store_true", help="Force re-generation of all artifacts ignoring cache")
    parser.add_argument("--topic", default=None, help="Optional topic seed string")
    parser.add_argument("--market", default=None, help="Canonical market (EN, JA, KR, VN)")
    parser.add_argument("--preset", default="macro_legacy", help="Pipeline track preset (e.g. story_forensic, macro_legacy)")
    parser.add_argument("--max-veo-shots", type=int, default=None, help="Maximum number of Veo shots to generate (quota management)")

    args = parser.parse_args()

    exit_code = execute_pipeline(
        profile_name=args.profile,
        run_id=args.run_id,
        from_stage=args.from_stage,
        to_stage=args.to_stage or args.stop_after,
        only_stage=args.only_stage,
        dry_run=args.dry_run,
        force=args.force,
        topic=args.topic,
        market=args.market,
        preset=args.preset,
        stop_after=args.stop_after,
        max_veo_shots=args.max_veo_shots,
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
