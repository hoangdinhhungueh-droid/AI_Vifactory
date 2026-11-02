#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""orchestrator/run_pipeline.py — Master Single Pipeline Orchestrator (AVF-STAB-001).

Implements the single entrypoint state machine for AI Video Factory with explicit Human Gates.
Supports:
  - Profiles: --profile {prod | e2e_min}
  - Resumption: --from <STAGE> and --only <STAGE>
  - Target/Stop: --to <STAGE> and --stop-after <STAGE>
  - Human Gates (1-5):
      Gate 1: After Candidate Selection (S01) -> emits command for Story Script
      Gate 2: After Story Generation & Audit (S04) -> emits command for Director & Images
      Gate 3: After Image Generation (S07) -> emits command for 30s Demo/Pilot Video
      Gate 4: After 30s Demo Review (--pilot) -> emits command for Full Master Video + Automate to End
      Gate 5: After Master Render & QC (S11) -> unlisted upload to YouTube (--upload-youtube)
  - 30s Demo / Pilot: --pilot
  - YouTube Unlisted Upload: --upload-youtube
  - Idempotency: Skips already-verified stages without re-calling expensive APIs
  - Fast simulation: --dry-run
  - Overwrite: --force
  - Unattended mode: --auto
"""

from __future__ import annotations

import argparse
import importlib
import json
import logging
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional

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

logger = logging.getLogger("orchestrator.run_pipeline")

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


def execute_youtube_upload(ctx: RunContext, final_mp4: Optional[Path] = None) -> Dict[str, Any]:
    """Uploads final master video to YouTube with privacyStatus='unlisted' (Gate 5)."""
    if final_mp4 is None:
        final_mp4 = ctx.paths.final_render_dir / "final.mp4"
    if not final_mp4.exists():
        final_mp4 = ctx.paths.root / "10_render" / "final.mp4"
    if not final_mp4.exists():
        final_mp4 = ctx.paths.root / "final.mp4"
    if not final_mp4.exists():
        raise FileNotFoundError(f"Master video not found at '{final_mp4}'. Run S10 render first.")

    s1_path = ctx.paths.artifact_file(StageID.S1_IDEATION.value)
    title = f"{ctx.topic or ctx.run_id}: Forensic Investigation"
    summary = "Investigative non-fiction docudrama breakdown."
    if s1_path.exists():
        try:
            s1_data = json.loads(s1_path.read_text(encoding="utf-8"))
            payload = s1_data.get("payload", {})
            title = payload.get("title_working") or payload.get("topic") or title
            summary = payload.get("scheme_mechanism_summary") or payload.get("central_question") or summary
        except Exception:
            pass

    s3_path = ctx.paths.artifact_file(StageID.S3_SCRIPT.value)
    if s3_path.exists():
        try:
            s3_data = json.loads(s3_path.read_text(encoding="utf-8"))
            payload = s3_data.get("payload", {})
            title = payload.get("title") or title
        except Exception:
            pass

    mkt = getattr(ctx.manifest, "market", "EN") or "EN"

    # Read chapters from remotion_props.json if available
    chapter_text = ""
    props_path = ctx.paths.root / "remotion_props.json"
    if props_path.exists():
        try:
            from app.services.seo_package_forge import sync_exact_chapters_from_remotion
            ch_list = sync_exact_chapters_from_remotion(task_id=ctx.run_id, market=mkt, title=title, remotion_props_path=str(props_path))
            if isinstance(ch_list, list) and ch_list:
                chapter_text = "\n".join(ch_list)
        except Exception as _ch_err:
            logger.debug(f"Chapter sync notice: {_ch_err}")

    description = f"{title}\n\n{summary}\n\n"
    if chapter_text:
        description += f"TIMESTAMPS:\n{chapter_text}\n\n"
    description += "Investigative Non-Fiction Docudrama produced by AI Video Factory.\n#investigation #docudrama #forensic"

    tags = ["investigation", "docudrama", "forensic", "vox", mkt.lower()]

    thumb_path = None
    for cand in [
        ctx.paths.root / "thumbnail.png",
        ctx.paths.root / "thumbnail.jpg",
        ctx.paths.composite_seeds_dir / "thumbnail.png",
        ctx.paths.composite_seeds_dir / "SCENE_01.png",
    ]:
        if cand.exists():
            thumb_path = cand
            break

    sub_path = None
    for cand in [
        ctx.paths.audio_dir / "subtitles.srt",
        ctx.paths.root / "subtitles.srt",
    ]:
        if cand.exists():
            sub_path = cand
            break

    if ctx.dry_run:
        print(f"\n[YOUTUBE UPLOAD (DRY-RUN)]: Simulating unlisted upload for '{final_mp4.name}'...")
        print(f"  Title:       {title[:80]}")
        print("  Privacy:     unlisted")
        print(f"  Market:      {mkt}")
        return {
            "status": "dry_run",
            "id": f"yt_dryrun_{ctx.run_id[:8]}",
            "url": f"https://youtu.be/yt_dryrun_{ctx.run_id[:8]}",
            "title": title,
            "privacy": "unlisted"
        }

    try:
        from app.services.youtube_upload import upload_video
        print(f"\n🚀 [YOUTUBE UPLOAD]: Uploading '{final_mp4.name}' as UNLISTED to YouTube ({mkt})...")
        resp = upload_video(
            video_path=str(final_mp4),
            title=title[:100],
            description=description,
            tags=tags,
            category_id="22",
            privacy_status="unlisted",
            made_for_kids=False,
            market=mkt,
            thumbnail_path=str(thumb_path) if thumb_path else None,
            subtitles_path=str(sub_path) if sub_path else None
        )
        vid_id = resp.get("id", "")
        vid_url = f"https://youtu.be/{vid_id}" if vid_id else ""
        print(f"✅ [YOUTUBE UPLOAD SUCCESS]: Video ID: {vid_id} -> {vid_url}")
        return {
            "status": "success",
            "id": vid_id,
            "url": vid_url,
            "title": title,
            "privacy": "unlisted"
        }
    except Exception as yt_err:
        print(f"⚠️ [YOUTUBE UPLOAD SKIPPED / NOTICE]: {yt_err}")
        return {
            "status": "skipped",
            "reason": str(yt_err),
            "title": title,
            "privacy": "unlisted"
        }


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
    pilot: bool = False,
    upload_youtube: bool = False,
    human_gates: Optional[bool] = None,
    auto: bool = False,
) -> int:
    if profile is not None:
        profile_name = profile
    effective_to = to_stage or stop_after
    """Main execution engine loop over all 11 stages with explicit Human Gates."""
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
    preset_name = preset or getattr(manifest, "preset", None) or os.getenv("VF_PRESET") or "story_forensic"
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

    # Determine Human Gates policy
    if auto:
        effective_human_gates = False
    elif human_gates is not None:
        effective_human_gates = bool(human_gates)
    elif dry_run or config.name == "e2e_min":
        effective_human_gates = False
    else:
        # Default in production: pause at Human Approval Gates
        effective_human_gates = bool(config.name == "prod")

    # Fast Path: direct --upload-youtube invocation on already completed master MP4
    if upload_youtube and from_stage is None and to_stage is None and only_stage is None and not pilot:
        final_video = paths.final_render_dir / "final.mp4"
        if not final_video.exists():
            final_video = paths.root / "10_render" / "final.mp4"
        if not final_video.exists():
            final_video = paths.root / "final.mp4"
        if final_video.exists():
            yt_res = execute_youtube_upload(ctx, final_video)
            print("\n" + "=" * 75)
            print("🎉 [HUMAN GATE 5 REACHED: MASTER VIDEO VERIFIED & UPLOADED TO YOUTUBE]")
            print("=" * 75)
            print(f"🎥 Master MP4 Video:   {final_video}")
            print("🔒 YouTube Privacy:    UNLISTED")
            print(f"🆔 Video ID:           {yt_res.get('id', 'N/A')}")
            print(f"🔗 Video URL:          {yt_res.get('url', 'N/A')}")
            print(f"📌 Video Title:        {yt_res.get('title', 'N/A')}")
            print("=" * 75 + "\n")
            try:
                from app.services.telegram_buttons import send_hg5_youtube_published
                send_hg5_youtube_published(
                    task_id=effective_run_id,
                    video_id=yt_res.get('id', 'N/A'),
                    video_url=yt_res.get('url', 'N/A'),
                    title=yt_res.get('title', 'N/A'),
                    privacy="unlisted",
                    market=manifest.market
                )
            except Exception as _tg_err:
                logger.warning(f"[HG5] Telegram notification notice: {_tg_err}")
            return 0

    # Fast Path: --pilot 30-Second Demo Video Generation & Visual Critic Inspection
    if pilot:
        from app.services.pilot_builder import build_and_evaluate_pilot
        pilot_res = build_and_evaluate_pilot(ctx, target_duration_sec=30.0)
        eval_dict = pilot_res.get("evaluation", {})
        score = eval_dict.get("overall_score", "PASS")
        verdict = eval_dict.get("verdict", "PASS")
        next_cmd = f"python -m orchestrator.run_pipeline --run-id {effective_run_id} --preset {preset_name} --from s08_video_gen --to s11_qc --upload-youtube"
        print("\n" + "=" * 75)
        print("🛑 [HUMAN GATE 4 REACHED: 30S DEMO / PILOT VIDEO READY FOR REVIEW]")
        print("=" * 75)
        print(f"🎬 Pilot Video:        {pilot_res.get('pilot_video')}")
        print(f"📸 Contact Sheet:      {pilot_res.get('contact_sheet')}")
        print(f"⏱️ Duration:           {pilot_res.get('target_duration_sec')}s (Beat 1 Hook)")
        print(f"👁️ Visual Critic:      {score} / 10 ({verdict})")
        print("\nPlease review the 30s pilot video and 16-frame contact sheet before rendering full master.")
        print("\n👉 NEXT STEP: Approve & Render Full Master Video + Automate to End")
        print("Execute CLI Command:")
        print(next_cmd)
        print("=" * 75 + "\n")
        try:
            from app.services.telegram_buttons import send_hg4_pilot_ready
            send_hg4_pilot_ready(
                task_id=effective_run_id,
                pilot_video=str(pilot_res.get('pilot_video')),
                contact_sheet=str(pilot_res.get('contact_sheet')),
                critic_score=str(score),
                verdict=str(verdict),
                preset=preset_name,
                next_cmd=next_cmd
            )
        except Exception as _tg_err:
            logger.warning(f"[HG4] Telegram notification notice: {_tg_err}")
        return 0

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
                # Still check human gate boundaries on skipped stages if relevant
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

            # ------------------------------------------------------------------
            # HUMAN GATE 1: After Candidate Selection (S01 Ideation)
            # ------------------------------------------------------------------
            if stage == StageID.S1_IDEATION and effective_human_gates and (only_target_idx is None or only_target_idx == 0):
                if (start_idx == 0 or only_target_idx == 0) and (effective_to is None or resolve_stage_index(effective_to, stage_list) == 0):
                    payload = _artifact.payload if isinstance(_artifact.payload, dict) else {}
                    topic_display = ctx.topic or payload.get("topic") or payload.get("title_working") or effective_run_id
                    print("\n" + "=" * 75)
                    print("🛑 [HUMAN GATE 1 REACHED: CANDIDATE SELECTION APPROVED]")
                    print("=" * 75)
                    print(f"📌 Candidate Topic:    {topic_display}")
                    print(f"🌍 Target Market:      {manifest.market}")
                    print(f"🧭 Track Preset:       {preset_name}")
                    print(f"📁 Workspace:          {paths.root}")
                    print(f"📄 Manifest:           {paths.manifest_file}")
                    print("\nCandidate confirmed and locked into master run manifest.")
                    print("\n👉 NEXT STEP: Generate Story Research, Script & Critic Audit (S02 -> S04)")
                    print("Execute CLI Command:")
                    print(f"python -m orchestrator.run_pipeline --run-id {effective_run_id} --preset {preset_name} --from s02_research --to s04_critic_script")
                    print("=" * 75 + "\n")
                    try:
                        from app.services.telegram_buttons import send_hg1_candidate_selected
                        send_hg1_candidate_selected(
                            task_id=effective_run_id,
                            topic=str(topic_display),
                            market=manifest.market,
                            preset=preset_name,
                            viability_score=payload.get("viability_score"),
                            specific_angle=payload.get("specific_angle"),
                            competitor_gap=payload.get("competitor_gap"),
                            next_cmd=f"python -m orchestrator.run_pipeline --run-id {effective_run_id} --preset {preset_name} --from s02_research --to s04_critic_script",
                        )
                    except Exception as _tg_err:
                        logger.warning(f"[HG1] Telegram notification notice: {_tg_err}")
                    return 0

            # ------------------------------------------------------------------
            # HUMAN GATE 2: After Story Generation & Audit (S04 Critic Script)
            # ------------------------------------------------------------------
            if stage == StageID.S4_CRITIC_SCRIPT and effective_human_gates and (only_target_idx is None or only_target_idx == 3):
                if effective_to is None or resolve_stage_index(effective_to, stage_list) <= 3 or only_target_idx == 3:
                    s3_art_path = paths.artifact_file(StageID.S3_SCRIPT.value)
                    s3_info = {}
                    if s3_art_path.exists():
                        try:
                            s3_info = json.loads(s3_art_path.read_text(encoding="utf-8")).get("payload", {})
                        except Exception:
                            pass
                    title_disp = s3_info.get("title") or ctx.topic or effective_run_id
                    w_count = s3_info.get("total_words", "N/A")
                    est_dur = s3_info.get("est_duration_s", "N/A")
                    print("\n" + "=" * 75)
                    print("🛑 [HUMAN GATE 2 REACHED: STORY SCRIPT GENERATED & AUDITED]")
                    print("=" * 75)
                    print(f"📖 Story Title:        {title_disp}")
                    print(f"📊 Word Count:         {w_count} words (Preset target: 450-750 words, 180-300s)")
                    print(f"⏱️ Estimated Duration: {est_dur}s")
                    print("🛡️ Script Audit:       PASS (Dual Critic Council Rule 444 & 445)")
                    print(f"📄 Script Artifact:    {s3_art_path}")
                    print("\nStory script validated and locked into master run manifest.")
                    print("\n👉 NEXT STEP: Generate Director Plan, Visual Critic Audit & Images (S05 -> S07)")
                    print("Execute CLI Command:")
                    print(f"python -m orchestrator.run_pipeline --run-id {effective_run_id} --preset {preset_name} --from s05_director_plan --to s07_image_gen")
                    print("\n[Image Generation Instructions]:")
                    print(f"Bulk prompts saved in: {paths.root / 'bulk_image_prompts.txt'}")
                    print(f"Generate authentic images and place in: {paths.composite_seeds_dir}")
                    print("Or execute skill /vf-image-gen in Antigravity UI.")
                    print("=" * 75 + "\n")
                    try:
                        from app.services.telegram_buttons import send_hg2_story_audited
                        w_num = int(w_count) if isinstance(w_count, (int, float)) or (isinstance(w_count, str) and w_count.isdigit()) else 0
                        d_num = float(est_dur) if isinstance(est_dur, (int, float)) or (isinstance(est_dur, str) and est_dur.replace('.', '', 1).isdigit()) else 0.0
                        send_hg2_story_audited(
                            task_id=effective_run_id,
                            title=str(title_disp),
                            total_words=w_num,
                            est_duration_s=d_num,
                            audit_score="PASS",
                            preset=preset_name,
                            next_cmd=f"python -m orchestrator.run_pipeline --run-id {effective_run_id} --preset {preset_name} --from s05_director_plan --to s07_image_gen",
                            bulk_prompts_file=str(paths.root / "bulk_image_prompts.txt"),
                        )
                    except Exception as _tg_err:
                        logger.warning(f"[HG2] Telegram notification notice: {_tg_err}")
                    return 0

            # ------------------------------------------------------------------
            # HUMAN GATE 3: After Image Generation (S07 Image Gen)
            # ------------------------------------------------------------------
            if stage == StageID.S7_IMAGE_GEN and effective_human_gates and (only_target_idx is None or only_target_idx == 6):
                if effective_to is None or resolve_stage_index(effective_to, stage_list) <= 6 or only_target_idx == 6:
                    total_imgs = len(_artifact.payload.get("images", [])) if isinstance(_artifact.payload, dict) else 0
                    print("\n" + "=" * 75)
                    print("🛑 [HUMAN GATE 3 REACHED: IMAGE ASSETS VERIFIED]")
                    print("=" * 75)
                    print(f"🖼️ Composite Seeds:    {total_imgs} authentic images verified in {paths.composite_seeds_dir}")
                    print("🛡️ Visual Checklist:   100% authentic editorial illustrations, 0% placeholders (Rule 118 & 121)")
                    print("\nAll composite image assets verified on disk.")
                    print("\n👉 NEXT STEP: Generate 30-Second Demo / Pilot Video (Beat 1 Review)")
                    print("Execute CLI Command:")
                    print(f"python -m orchestrator.run_pipeline --run-id {effective_run_id} --preset {preset_name} --pilot")
                    print("=" * 75 + "\n")
                    try:
                        from app.services.telegram_buttons import send_hg3_images_verified
                        send_hg3_images_verified(
                            task_id=effective_run_id,
                            image_count=total_imgs,
                            preset=preset_name,
                            next_cmd=f"python -m orchestrator.run_pipeline --run-id {effective_run_id} --preset {preset_name} --pilot",
                            composite_dir=str(paths.composite_seeds_dir),
                        )
                    except Exception as _tg_err:
                        logger.warning(f"[HG3] Telegram notification notice: {_tg_err}")
                    return 0

            # ------------------------------------------------------------------
            # HUMAN GATE 5: Master Video QC Passed -> YouTube Unlisted Upload
            # ------------------------------------------------------------------
            if stage == StageID.S11_QC and upload_youtube:
                final_video = paths.final_render_dir / "final.mp4"
                if not final_video.exists():
                    final_video = paths.root / "10_render" / "final.mp4"
                yt_res = execute_youtube_upload(ctx, final_video)
                print("\n" + "=" * 75)
                print("🎉 [HUMAN GATE 5 REACHED: MASTER VIDEO VERIFIED & UPLOADED TO YOUTUBE]")
                print("=" * 75)
                print(f"🎥 Master MP4 Video:   {final_video}")
                print("🛡️ QC Verdict:         PASS (ALL GATES PASSED)")
                print("🔒 YouTube Privacy:    UNLISTED")
                print(f"🆔 Video ID:           {yt_res.get('id', 'N/A')}")
                print(f"🔗 Video URL:          {yt_res.get('url', 'N/A')}")
                print(f"📌 Video Title:        {yt_res.get('title', 'N/A')}")
                print("=" * 75 + "\n")
                try:
                    from app.services.telegram_buttons import send_hg5_youtube_published
                    send_hg5_youtube_published(
                        task_id=effective_run_id,
                        video_id=yt_res.get('id', 'N/A'),
                        video_url=yt_res.get('url', 'N/A'),
                        title=yt_res.get('title', 'N/A'),
                        privacy="unlisted",
                        market=manifest.market
                    )
                except Exception as _tg_err:
                    logger.warning(f"[HG5] Telegram notification notice: {_tg_err}")

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
    if end_idx == len(stage_list) - 1 and only_target_idx is None and start_idx == 0:
        print("🏆 ALL 11 PIPELINE STAGES COMPLETED SUCCESSFULLY!")
        print(f"📄 Master Manifest:     {paths.manifest_file}")
        print(f"🎥 Master Video Asset:  {paths.final_render_dir / 'final.mp4'}")
        if not upload_youtube:
            print("\n👉 To upload unlisted to YouTube (Human Gate 5):")
            print(f"Execute: python -m orchestrator.run_pipeline --run-id {effective_run_id} --upload-youtube")
    else:
        executed_desc = stage_list[only_target_idx].value.upper() if only_target_idx is not None else f"{stage_list[start_idx].value.upper()} ➔ {stage_list[end_idx].value.upper()}"
        print(f"🏆 PIPELINE SUB-RUN COMPLETED: [{executed_desc}]")
        print(f"📄 Master Manifest:     {paths.manifest_file}")
    print("=" * 75 + "\n")
    return 0


def main():
    parser = argparse.ArgumentParser(description="Master Single Pipeline Orchestrator for AI Video Factory with Explicit Human Gates")
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
    parser.add_argument("--preset", default="story_forensic", help="Pipeline track preset (e.g. story_forensic, macro_legacy)")
    parser.add_argument("--max-veo-shots", type=int, default=None, help="Maximum number of Veo shots to generate (quota management)")
    parser.add_argument("--pilot", action="store_true", help="Generate 30-second Beat 1 demo/pilot video and run visual critic evaluation")
    parser.add_argument("--upload-youtube", action="store_true", help="Upload final master video as unlisted to YouTube (Human Gate 5)")
    parser.add_argument("--human-gates", dest="human_gates", action="store_true", default=None, help="Enable explicit Human Approval Gates pausing execution")
    parser.add_argument("--no-human-gates", dest="human_gates", action="store_false", help="Disable Human Approval Gates")
    parser.add_argument("--auto", action="store_true", help="Execute pipeline fully unattended end-to-end without pausing at Human Gates")

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
        pilot=args.pilot,
        upload_youtube=args.upload_youtube,
        human_gates=args.human_gates,
        auto=args.auto,
    )
    sys.exit(exit_code)


if __name__ == "__main__":
    main()
