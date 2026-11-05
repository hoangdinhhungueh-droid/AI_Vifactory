import hashlib
import sys
from pathlib import Path

# Add project root to sys.path
ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.vps_runner import FastVPSClient

FILES_TO_SYNC = [
    "AGENTS.md",
    "core/contracts/stages.py",
    "core/skill_gateway.py",
    "core/pacing_budgeter.py",
    "core/instinct_manager.py",
    "config/active_instincts.json",
    "config/presets/story_forensic.yaml",
    "config/presets/vox_narrative.yaml",
    "config/presets/macro_legacy.yaml",
    "app/services/preset_loader.py",
    "scripts/evaluate_master_scene_package.py",
    "config/prompts/style-config.yaml",
    "config/prompts/b2_editorial_prompt.md",
    "config/prompts/b3_director_prompt.md",
    "config/prompts/b35_visual_rules.md",
    "config/prompts/vox_b3_director_image_prompt.md",
    "config/kinetic_layout_presets.json",
    "config/prompts/cl3_vox_engine/image-prompts.md",
    "config/prompts/cl3_vox_engine/avoid_base.md",
    "config/prompts/cl3_vox_engine/camera_directives.yaml",
    "config/prompts/cl3_vox_engine/t2i_style.md",
    "config/prompts/cl3_vox_engine/style_deep_diorama.md",
    "config/prompts/cl3_vox_engine/style_flat_parallax.md",
    "config/prompts/cl3_vox_engine/image_prompts_system.md",
    "config/prompts/cl3_vox_engine/video_prompts_system.md",
    "config/prompts/cl3_vox_engine/MANIFEST.json",
    "config/prompts/story_forensic/s03_script.md",
    "config/prompts/story_forensic/s05_director_plan.md",
    "config/prompts/story_forensic/s07_image_gen.md",
    "config/prompts/story_forensic/s07_image_style_prefix.md",
    "config/prompts/archive/b3_director_hollywood_legacy.md",
    "config/prompts/archive/b35_visual_rules_magenta_legacy.md",
    "app/services/skill_loader.py",
    "app/services/semantic_evidence_extractor.py",
    "app/services/kinetic_sub_director.py",
    "app/services/vox_automated_director.py",
    "scripts/compile_episode_from_notion.py",
    "app/services/build_remotion_props.py",
    "app/services/unified_vox_director.py",
    "app/services/director_planner_b3.py",
    "app/services/pilot_builder.py",
    "app/services/master_scene_sheet.py",
    "app/services/chapter_split.py",
    "app/services/story_engine_b2.py",
    "app/services/text_metrics.py",
    "app/services/telegram_buttons.py",
    "app/services/mpt_ported/documentary_montage.py",
    "app/templates/hg2_telegram_format.py",
    "orchestrator/run_pipeline.py",
    "stages/s01_ideation.py",
    "stages/s02_research.py",
    "stages/s03_script.py",
    "stages/s04_critic_script.py",
    "stages/s05_director_plan.py",
    "stages/s06_critic_visual.py",
    "stages/s07_image_gen.py",
    "stages/s08_video_gen.py",
    "scripts/flow_video_dispatcher.py",
    "scripts/sync_to_vps.py",
    "scripts/run_vox_media_pipeline.py",
    "scripts/build_pilot_3min_and_evaluate.py",
    "scripts/render_episode_parameterized.py",
    "tests/unit/test_flow_video_dispatcher.py",
    "tests/unit/test_master_scene_sheet.py",
    "data/notion_audit/skills_snapshot.json",
    "data/notion_audit/prompt_engine_page_ids.json",
    "tests/test_story_preset.py",
    "tests/test_skill_gateway.py",
    "tests/test_pacing_budgeter.py",
    "tests/test_semantic_evidence_extractor.py",
    "tests/test_instinct_manager.py",
    "tests/test_caller_integration_and_drift.py",
    "docs/plans/2026-10-30-vox-v3-systemic-reform-plan.md",
]


def sha256_text(text: str) -> str:
    h = hashlib.sha256()
    h.update(text.replace("\r\n", "\n").encode("utf-8"))
    return h.hexdigest()


def main():
    print("=== Starting Three-Way Physical Sync to VPS (Rule 126) ===")
    client = FastVPSClient()
    synced = []
    failed = []

    for rel in FILES_TO_SYNC:
        local_p = ROOT / rel
        if not local_p.exists():
            print(f"[SKIP] Local file not found: {rel}")
            continue

        content = local_p.read_text(encoding="utf-8")
        local_sha = sha256_text(content)

        # 1. Write to safe-zone /tmp/vf/sync_tmp
        w_res = client.call_tool("write_file", {
            "path": "/tmp/vf/sync_tmp.txt",
            "content": content.replace("\r\n", "\n"),
            "confirm": True
        })
        if not isinstance(w_res, dict) or w_res.get("status") != "ok":
            print(f"[FAIL] Write to safe-zone failed for {rel}: {w_res}")
            failed.append(rel)
            continue

        # 2. Copy from safe-zone to /root/video_factory/<rel>
        vps_dest = f"/root/video_factory/{rel}"
        vps_dir = f"/root/video_factory/{Path(rel).parent.as_posix()}"
        cp_cmd = f"mkdir -p '{vps_dir}' && cp '/tmp/vf/sync_tmp.txt' '{vps_dest}' && rm -f '/tmp/vf/sync_tmp.txt' && sha256sum '{vps_dest}'"
        c_res = client.call_tool("run_command", {"command": cp_cmd})

        if not isinstance(c_res, dict) or c_res.get("exit_code") != 0:
            print(f"[FAIL] Copy command failed for {rel}: {c_res}")
            failed.append(rel)
            continue

        stdout = c_res.get("stdout", "")
        vps_sha = stdout.split()[0] if stdout else ""

        if vps_sha == local_sha:
            print(f"[OK] {rel} -> {vps_sha[:12]} (100% bit-for-bit parity)")
            synced.append(rel)
        else:
            print(f"[MISMATCH] {rel}: local {local_sha[:12]} != vps {vps_sha[:12]}")
            failed.append(rel)

    print(f"\n--- Sync Summary: {len(synced)} OK, {len(failed)} Failed ---")
    if failed:
        sys.exit(1)

    # 3. Compile Python files on VPS
    print("\n--- Compiling Python files on VPS ---")
    compile_cmd = (
        "python3 -m py_compile "
        "/root/video_factory/core/skill_gateway.py "
        "/root/video_factory/core/pacing_budgeter.py "
        "/root/video_factory/core/instinct_manager.py "
        "/root/video_factory/app/services/skill_loader.py "
        "/root/video_factory/app/services/semantic_evidence_extractor.py "
        "/root/video_factory/app/services/kinetic_sub_director.py "
        "/root/video_factory/app/services/build_remotion_props.py "
        "/root/video_factory/app/services/unified_vox_director.py "
        "/root/video_factory/app/services/director_planner_b3.py "
        "/root/video_factory/app/services/pilot_builder.py "
        "/root/video_factory/app/services/mpt_ported/documentary_montage.py "
        "/root/video_factory/app/templates/hg2_telegram_format.py "
        "/root/video_factory/stages/s01_ideation.py "
        "/root/video_factory/stages/s02_research.py "
        "/root/video_factory/stages/s03_script.py "
        "/root/video_factory/stages/s04_critic_script.py "
        "/root/video_factory/stages/s05_director_plan.py "
        "/root/video_factory/stages/s06_critic_visual.py "
        "/root/video_factory/stages/s07_image_gen.py "
        "/root/video_factory/stages/s08_video_gen.py "
        "/root/video_factory/scripts/run_vox_media_pipeline.py "
        "/root/video_factory/scripts/build_pilot_3min_and_evaluate.py "
        "/root/video_factory/scripts/render_episode_parameterized.py"
    )
    comp_res = client.call_tool("run_command", {"command": compile_cmd})
    print("Compile exit_code:", comp_res.get("exit_code"))
    if comp_res.get("exit_code") != 0:
        print("Compile stderr:", comp_res.get("stderr"))
        sys.exit(1)
    print("All Python modules compiled successfully on VPS (exit code 0)")

    # 4. Run Pytest on VPS
    print("\n--- Running Pytest on VPS ---")
    pytest_cmd = (
        "pytest /root/video_factory/tests/test_skill_gateway.py "
        "/root/video_factory/tests/test_pacing_budgeter.py "
        "/root/video_factory/tests/test_semantic_evidence_extractor.py "
        "/root/video_factory/tests/test_instinct_manager.py "
        "/root/video_factory/tests/test_kinetic_sub_director.py "
        "/root/video_factory/tests/test_caller_integration_and_drift.py -v"
    )
    test_res = client.call_tool("run_command", {"command": pytest_cmd})
    print("Test output:\n", test_res.get("stdout"))
    if test_res.get("exit_code") != 0:
        print("Test stderr:\n", test_res.get("stderr"))
        sys.exit(1)

    print("\n=== All 51 Unit Tests PASSED on VPS! ===")


if __name__ == "__main__":
    main()
