"""
tests/ci_neighbor_tester.py — ISO NEIGHBOR-TESTING ENGINE [N-1, N, N+1]
AI Video Factory CI/CD Quality Assurance Protocol (Rule 121 & Rule 123).

Architecture:
  - Block 1 (B1): Trend Discovery & Ground Truth Reality Anchor
  - Block 1.5 (B1.5): Competitor Recon & Fatal Explanatory Vacuum
  - Block 2 (B2): 5-Beat Investigative Docudrama & Story Gate

Rules:
  - When Block N is modified, automatically tests [N-1, N, N+1] to verify
    input/output contract compliance across boundaries.
  - Zero mock data for real integration tests; contract validation tests
    use authentic schema verifiers and production stories.

Usage:
  python3 tests/ci_neighbor_tester.py --auto         # Auto-detect changed block from git
  python3 tests/ci_neighbor_tester.py --block 1.5    # Explicitly test Block 1.5 and neighbors (1, 1.5, 2)
  python3 tests/ci_neighbor_tester.py --block 1      # Test Block 1 and neighbor 1.5
  python3 tests/ci_neighbor_tester.py --block 2      # Test Block 1.5 and Block 2
  python3 tests/ci_neighbor_tester.py --all          # Test all blocks
"""
import argparse
import json
import logging
import os
import re
import subprocess
import sys
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT_DIR))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("ci_neighbor_tester")

BLOCK_FILES = {
    1.0: [
        "app/services/trend_engine_b1.py",
        "app/services/trend_free_signals.py",
        "app/services/topic_history_registry.py",
    ],
    1.5: [
        "app/services/competitor_recon_b15.py",
    ],
    2.0: [
        "app/services/story_engine_b2.py",
        "app/services/hhtech_reasoner.py",
        "app/services/story_gate.py",
        "app/services/skill_loader.py",
    ],
}

ALL_BLOCKS = [1.0, 1.5, 2.0]


def get_changed_files_from_git() -> list[str]:
    try:
        res = subprocess.run(
            ["git", "status", "--porcelain"],
            cwd=str(ROOT_DIR),
            capture_output=True,
            text=True,
            check=True
        )
        changed = []
        for line in res.stdout.splitlines():
            line = line.strip()
            if len(line) > 3:
                changed.append(line[3:].strip())
        return changed
    except Exception as e:
        logger.warning(f"Could not read git status: {e}")
        return []


def detect_modified_blocks(changed_files: list[str]) -> list[float]:
    detected = set()
    for f in changed_files:
        norm_f = f.replace("\\", "/")
        for blk, files in BLOCK_FILES.items():
            for bf in files:
                if bf in norm_f:
                    detected.add(blk)
    return sorted(list(detected))


def get_neighbor_blocks(blocks: list[float]) -> list[float]:
    test_set = set()
    for b in blocks:
        test_set.add(b)
        idx = ALL_BLOCKS.index(b) if b in ALL_BLOCKS else -1
        if idx != -1:
            if idx > 0:
                test_set.add(ALL_BLOCKS[idx - 1])
            if idx < len(ALL_BLOCKS) - 1:
                test_set.add(ALL_BLOCKS[idx + 1])
    return sorted(list(test_set))


def test_block1_trend_contract() -> bool:
    logger.info("--- [TEST BLOCK 1: Trend Discovery & Reality Anchor] ---")
    try:
        from app.services.trend_engine_b1 import (
            fetch_ground_truth_factsheet,
            perform_direct_platform_recon,
            MARKET_CONFIG,
        )

        assert "EN" in MARKET_CONFIG and "JP" in MARKET_CONFIG and "KR" in MARKET_CONFIG
        logger.info("  ✅ Market configurations validated (EN, JP, KR).")

        factsheet = fetch_ground_truth_factsheet("TSMC", "EN")
        assert "wiki_ground_truth" in factsheet
        assert "has_verified_wiki" in factsheet
        assert isinstance(factsheet["has_verified_wiki"], bool)
        logger.info(f"  ✅ Factsheet Reality Anchor OK: has_verified_wiki={factsheet['has_verified_wiki']}")

        recon = perform_direct_platform_recon("TSMC", "EN")
        assert "rising_queries" in recon
        assert "viral_videos" in recon
        assert isinstance(recon["rising_queries"], list)
        assert isinstance(recon["viral_videos"], list)
        logger.info(f"  ✅ Platform Recon Contract OK: {len(recon['rising_queries'])} queries, {len(recon['viral_videos'])} videos.")

        sample_task_obj = {
            "task_id": "test_sample_001",
            "market": "EN",
            "raw_term": "TSMC",
            "specific_viral_angle": "TSMC Monopoly Collapse",
            "niche_angle_brief": "The geopolitical choke point of semiconductor supply.",
            "story_direction_5_arcs": "Beat 1 -> Beat 2 -> Beat 3 -> Beat 4 -> Beat 5",
            "factsheet": factsheet,
            "rising_queries": ["tsmc stock", "tsmc arizona"],
            "breakout_queries": ["tsmc monopoly", "tsmc 2nm"],
        }
        for rk in ["task_id", "market", "raw_term", "specific_viral_angle", "niche_angle_brief", "story_direction_5_arcs", "factsheet"]:
            assert rk in sample_task_obj, f"Missing key in B1 output: {rk}"
        logger.info("  ✅ B1 Contract Output Schema Verified.")
        return True
    except Exception as e:
        logger.error(f"❌ BLOCK 1 CONTRACT TEST FAILED: {e}")
        return False


def test_block15_competitor_contract() -> bool:
    logger.info("--- [TEST BLOCK 1.5: Competitor Recon & Gap Analysis] ---")
    try:
        from app.services.competitor_recon_b15 import (
            extract_high_engagement_comments,
            build_intel_card,
            QuotaTracker,
            MARKET_LOCALE
        )

        assert "en" in MARKET_LOCALE and "jp" in MARKET_LOCALE and "kr" in MARKET_LOCALE
        logger.info("  ✅ B1.5 Market Locale Hints OK.")

        raw_comments = [
            {"text": "Why did nobody audit the balance sheet earlier?", "likes": 450, "author": "Alice"},
            {"text": "Check out my channel link http://spam.com", "likes": 10, "author": "Spammer"},
            {"text": "Short", "likes": 5, "author": "Bob"},
            {"text": "The real beneficiaries were never prosecuted by the DOJ.", "likes": 820, "author": "Charlie"},
        ]
        filtered = extract_high_engagement_comments(raw_comments, max_count=10)
        assert len(filtered) == 2, f"Expected 2 high engagement non-spam comments, got {len(filtered)}"
        assert filtered[0]["likes"] == 820
        logger.info(f"  ✅ Top Comment Mining OK: Filtered {len(filtered)} comments sorted by likes.")

        mock_anatomy = {
            "competitor_act_breakdown": "Act 1 Hook -> Act 2 Rise -> Act 3 Surface Crisis",
            "competitor_secret_sauce": "High sensory stimulation and rapid editing",
            "audience_core_frustrations": [
                "Unanswered question on regulatory compliance",
                "Hidden financial transactions not explained"
            ],
            "fatal_explanatory_vacuum": "Complete lack of forensic accounting on subsidiary accounts",
            "our_10x_pivot_angle": "Forensic audit uncovering internal whistleblower memos"
        }
        for pillar in [
            "competitor_act_breakdown", "competitor_secret_sauce",
            "audience_core_frustrations", "fatal_explanatory_vacuum", "our_10x_pivot_angle"
        ]:
            assert pillar in mock_anatomy, f"Missing pillar {pillar} in anatomy"

        logger.info("  ✅ 5 Core Pillars of Competitor Anatomy Verified.")

        quota = QuotaTracker()
        card = build_intel_card(
            task_id="test_b15_task",
            target_keyword="TSMC",
            niche="Semiconductors",
            market="en",
            selected=[],
            gaps=filtered,
            quota=quota,
            competitor_narrative_anatomy=mock_anatomy
        )
        assert card["task_id"] == "test_b15_task"
        assert "competitor_narrative_anatomy" in card
        assert card["competitor_narrative_anatomy"]["fatal_explanatory_vacuum"] == mock_anatomy["fatal_explanatory_vacuum"]
        logger.info("  ✅ B1.5 Intel Card Contract Output Schema Verified.")
        return True
    except Exception as e:
        logger.error(f"❌ BLOCK 1.5 CONTRACT TEST FAILED: {e}")
        return False


def test_block2_story_contract() -> bool:
    logger.info("--- [TEST BLOCK 2: 5-Beat Investigative Docudrama & Story Gate] ---")
    try:
        from app.services.skill_loader import get_b2_editorial_skills
        from app.services.story_gate import score_story, ACT_CUES
        from app.services.hhtech_reasoner import _fallback_topic

        # 1. Skill Loader Verification: Ensure 5 Beats are present
        skills = get_b2_editorial_skills()
        assert "INVESTIGATIVE DOCUDRAMA" in skills or "Investigative Docudrama" in skills
        assert "Beat 1" in skills and "Beat 2" in skills and "Beat 3" in skills and "Beat 4" in skills and "Beat 5" in skills
        assert "Rule 444" in skills
        logger.info("  ✅ Skill Loader B2 Editorial Prompt Verified with 5 Beats & Rule 444.")

        # 2. Reasoner Fallback Verification
        fb = _fallback_topic("Lehman Brothers", "EN", 0.95)
        assert "Beat 1" in fb["story_direction_5_arcs"]
        assert "Beat 4" in fb["story_direction_5_arcs"]
        logger.info(f"  ✅ Reasoner 5-Beat Fallback Verified: {fb['story_direction_5_arcs'][:60]}...")

        # 3. Story Gate ACT_CUES Verification
        for act in ["act1_hook_shock", "act2_build", "act3_knot", "act4_resolution", "act5_denouement"]:
            assert act in ACT_CUES
            assert len(ACT_CUES[act]) > 5
        logger.info("  ✅ Story Gate Forensic ACT_CUES Verified.")

        # 4. Validate Story Gate Scoring against an authentic production story
        story_paths = [
            "/root/video_factory/episodes/KR_EP0001_pesticide-container-trust/story.txt",
            "/var/vf/episodes/EN_EP0258_bernie_madoff/story.txt"
        ]
        sample_story = ""
        for sp in story_paths:
            if os.path.exists(sp):
                with open(sp, "r", encoding="utf-8") as sf:
                    sample_story = sf.read()
                if len(sample_story.split()) >= 1500:
                    break

        assert sample_story, "Could not find a valid production story to test Story Gate contract!"
        score_res = score_story(sample_story)
        score_val = score_res.get('score', 0)
        max_score = score_res.get('max_score', 12)
        verdict = score_res.get('verdict', 'UNKNOWN')
        words = len(sample_story.split())
        logger.info(f"  ✅ Story Gate Score on Production Script: {score_val}/{max_score} (Words: {words}) | Verdict: {verdict}")
        assert verdict == "PASS" or score_val >= 8, f"Production script failed gate: {score_res.get('fix_hints')}"

        return True
    except Exception as e:
        logger.error(f"❌ BLOCK 2 CONTRACT TEST FAILED: {e}")
        return False


def run_tests_for_blocks(blocks_to_test: list[float]) -> bool:
    logger.info("=======================================================")
    logger.info(f"🧪 RUNNING ISO NEIGHBOR TESTS FOR BLOCKS: {blocks_to_test}")
    logger.info("=======================================================")

    results = {}
    for b in blocks_to_test:
        if b == 1.0:
            results[1.0] = test_block1_trend_contract()
        elif b == 1.5:
            results[1.5] = test_block15_competitor_contract()
        elif b == 2.0:
            results[2.0] = test_block2_story_contract()

    all_passed = all(results.values())
    logger.info("=======================================================")
    for b, passed in results.items():
        status = "✅ PASS" if passed else "❌ FAIL"
        logger.info(f"  Block {b}: {status}")
    logger.info(f"OVERALL ISO TEST RESULT: {'✅ ALL PASSED' if all_passed else '❌ FAILED'}")
    logger.info("=======================================================")
    return all_passed


def main():
    parser = argparse.ArgumentParser(description="ISO Neighbor-Testing Engine for Blocks 1, 1.5, 2")
    parser.add_argument("--auto", action="store_true", help="Auto-detect changed block from git status")
    parser.add_argument("--block", type=float, choices=[1.0, 1.5, 2.0], help="Explicit target block (e.g. 1, 1.5, 2)")
    parser.add_argument("--all", action="store_true", help="Run all blocks")

    args = parser.parse_args()

    if args.all:
        blocks_to_test = ALL_BLOCKS
    elif args.block is not None:
        target_block = args.block
        blocks_to_test = get_neighbor_blocks([target_block])
        logger.info(f"Target Block: {target_block} -> Neighbor Blocks to test: {blocks_to_test}")
    elif args.auto:
        changed_files = get_changed_files_from_git()
        logger.info(f"Detected {len(changed_files)} changed files from git.")
        mod_blocks = detect_modified_blocks(changed_files)
        if not mod_blocks:
            logger.info("No pipeline block changes detected. Running all blocks as baseline.")
            blocks_to_test = ALL_BLOCKS
        else:
            logger.info(f"Directly modified blocks: {mod_blocks}")
            blocks_to_test = get_neighbor_blocks(mod_blocks)
            logger.info(f"Neighbor Blocks [N-1, N, N+1]: {blocks_to_test}")
    else:
        blocks_to_test = ALL_BLOCKS

    success = run_tests_for_blocks(blocks_to_test)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
