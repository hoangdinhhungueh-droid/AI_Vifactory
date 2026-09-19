"""
scripts/reprocess_kr0003.py — Complete Re-synthesis of KR_EP0003_gimpo_fc_audit_failure.
Enforces Hollywood Audio Spine (Edge-TTS), Director Plan timecode lock,
Corporate Noir archetype detection, Prompt Forge, and DACL visual convergence.
"""
import os
import sys
import json
import asyncio
import logging
from pathlib import Path

ROOT_DIR = Path("/root/video_factory")
sys.path.insert(0, str(ROOT_DIR))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("reprocess_kr0003")

EPISODE_ID = "KR_EP0003_gimpo_fc_audit_failure"
EP_DIR = Path(f"/var/vf/episodes/{EPISODE_ID}")

def main():
    logger.info("=== STEP 1: PURGING CORRUPTED B3/B3.5 FILES ===")
    corrupt_files = [
        EP_DIR / "director_plan.json",
        EP_DIR / "dp_plan.json",
        EP_DIR / "prompts.json",
        EP_DIR / "prompts_forge.json",
        EP_DIR / "visual_convergence_audit.json",
    ]
    for cf in corrupt_files:
        if cf.exists():
            cf.unlink()
            logger.info(f"  Removed corrupted: {cf.name}")

    logger.info("=== STEP 2: SYNTHESIZING HOLLYWOOD AUDIO SPINE (EDGE-TTS KO) ===")
    from app.services.beat_tts_engine import synthesize_beat_tts_pipeline
    tts_res = asyncio.run(synthesize_beat_tts_pipeline(EPISODE_ID, out_dir=str(EP_DIR), force=True))
    logger.info(f"  Audio master: {tts_res['audio_path']} ({tts_res['size_bytes']} bytes, {tts_res['total_duration_sec']}s)")
    logger.info(f"  Segments: {len(tts_res['segments'])} sentences timecode-locked.")

    logger.info("=== STEP 3: GENERATING DIRECTOR PLAN (CORPORATE NOIR & TIMECODE-LOCKED) ===")
    from app.services.director_planner_b3 import generate_director_plan
    plan = generate_director_plan(EPISODE_ID)
    scenes = plan.get("scenes", [])
    logger.info(f"  Director Plan generated: {len(scenes)} scenes.")
    logger.info(f"  Archetype: {plan.get('director_archetype') or plan.get('archetype', {}).get('director')}")
    durations = [sc.get("duration_frames") for sc in scenes[:5]]
    logger.info(f"  First 5 scenes duration_frames: {durations}")
    total_frames = sum(sc.get("duration_frames", 0) for sc in scenes)
    logger.info(f"  Total frames: {total_frames} (~{round(total_frames / 30.0, 2)}s)")

    logger.info("=== STEP 4: PROMPT FORGE (LAYER 1 BG + LAYER 2 FG) ===")
    # Ensure prompts_forge.json exists
    pf_file = EP_DIR / "prompts_forge.json"
    if not pf_file.exists():
        from app.services.prompt_forge import generate_scene_prompts
        dp_plan_file = EP_DIR / "dp_plan.json"
        dp_plan = json.loads(dp_plan_file.read_text(encoding="utf-8"))
        forged = generate_scene_prompts(
            bg_dict=dp_plan.get("background_roster", {}),
            fg_dict=dp_plan.get("foreground_roster", {}),
            story_title=EPISODE_ID,
            scenes=scenes,
            market="KR"
        )
        pf_file.write_text(json.dumps(forged, ensure_ascii=False, indent=2), encoding="utf-8")
        logger.info(f"  Forged {len(forged.get('backgrounds', {}))} BG and {len(forged.get('foregrounds', {}))} FG prompts.")

    logger.info("=== STEP 5: B3.6 VISUAL CONVERGENCE DACL AUDIT ===")
    from app.services.b36_visual_convergence import run_b36_visual_convergence
    dacl_res = run_b36_visual_convergence(EPISODE_ID)
    logger.info(f"  DACL Audit verdict: {dacl_res.get('verdict')} (Score: {dacl_res.get('overall_score')})")

    logger.info("=== STEP 6: DISPATCHING UPDATED HUMAN GATE 2 CARD ===")
    from app.services.telegram_notify import send_gate2_card
    card_res = send_gate2_card(EPISODE_ID)
    logger.info(f"  Gate 2 dispatch result: {card_res}")

    logger.info("🎉 KR_EP0003 COMPLETELY RE-SYNTHESIZED AND LOCKED TO HOLLYWOOD AUDIO SPINE!")

if __name__ == "__main__":
    main()
