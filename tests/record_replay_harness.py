#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/record_replay_harness.py — Zero-Token Resilient Record & Replay Test Harness.

Mandated by Rule 121 (Strict Verification Protocol),
Rule 127 (Live Runtime Gate), and Inspired by Video 1 (AI E2E Semantic Testing).

Architecture:
  1. RECORD MODE: Captures golden execution traces and snapshots for pipeline stages.
  2. REPLAY MODE: Replays cached traces with semantic contract invariants (0 LLM tokens, 0.05s execution).
  3. SEMANTIC ASSERTIONS: Resilient against superficial format/class changes;
     tests core business invariants (5-Beat structure, timestamp monotonicity, layer integrity).
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional, Tuple

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")
if hasattr(sys.stderr, "reconfigure"):
    sys.stderr.reconfigure(encoding="utf-8")


class SemanticAssertionError(AssertionError):
    """Raised when a semantic contract invariant is violated."""
    pass


class RecordReplayHarness:
    """Manages recording, replaying, and semantic verification of pipeline outputs."""

    def __init__(self, records_dir: Optional[Path] = None):
        if records_dir is None:
            self.records_dir = Path(__file__).resolve().parent / "golden_records"
        else:
            self.records_dir = Path(records_dir).resolve()
        self.records_dir.mkdir(parents=True, exist_ok=True)

    def _get_record_path(self, stage_id: str) -> Path:
        safe_id = stage_id.replace("/", "_").replace("\\", "_")
        return self.records_dir / f"{safe_id}_golden_trace.json"

    def record_trace(self, stage_id: str, inputs: Dict[str, Any], output: Dict[str, Any], metadata: Optional[Dict[str, Any]] = None) -> Path:
        """Saves a golden execution trace to disk."""
        record_file = self._get_record_path(stage_id)
        payload = {
            "stage_id": stage_id,
            "recorded_at": time.strftime("%Y-%m-%d %H:%M:%S UTC", time.gmtime()),
            "inputs_hash": hashlib.sha256(json.dumps(inputs, sort_keys=True).encode("utf-8")).hexdigest()[:16],
            "inputs": inputs,
            "output": output,
            "metadata": metadata or {},
        }
        record_file.write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
        return record_file

    def replay_trace(self, stage_id: str) -> Dict[str, Any]:
        """Loads and replays a cached golden trace without invoking LLM or heavy render."""
        record_file = self._get_record_path(stage_id)
        if not record_file.exists():
            raise FileNotFoundError(f"Golden trace for stage '{stage_id}' not found at {record_file}. Run with --mode record first.")
        payload = json.loads(record_file.read_text(encoding="utf-8"))
        return payload.get("output", {})

    # =========================================================================
    # SEMANTIC INVARIANT VERIFIERS (Resilient against superficial changes)
    # =========================================================================

    @staticmethod
    def verify_5_beat_script(script_data: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Verifies 5-Beat Docudrama Script contract (Rule 131) without fragile regex."""
        issues = []
        scenes = script_data.get("scenes") or script_data.get("beats") or []
        if not scenes:
            issues.append("Missing scenes/beats list in script data.")
            return False, issues

        # Check total beats count (Canonical: 5 beats)
        beat_indices = {s.get("beat_index") or s.get("beat") for s in scenes if (s.get("beat_index") or s.get("beat"))}
        if len(beat_indices) < 5 and len(scenes) < 5:
            issues.append(f"Expected at least 5 distinct beats/scenes, found {len(beat_indices or scenes)}.")

        # Check Hook presence (Beat 1 Cold Strike, 0-60s)
        beat_1 = next((s for s in scenes if (s.get("beat_index") == 1 or s.get("beat") == 1)), scenes[0])
        text_b1 = beat_1.get("narration") or beat_1.get("story_text") or ""
        if len(text_b1.split()) < 10:
            issues.append("Beat 1 narration is too brief to form a valid High-Stakes Hook.")

        return len(issues) == 0, issues

    @staticmethod
    def verify_audio_spine_continuity(audio_spine: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Verifies word-level karaoke timestamps monotonicity (Rule 120)."""
        issues = []
        words = audio_spine.get("words") or audio_spine.get("subtitles") or []
        if not words:
            # Check duration
            total_duration = audio_spine.get("total_duration_sec") or audio_spine.get("duration") or 0.0
            if total_duration <= 0.0:
                issues.append("Audio spine total duration is 0 or negative.")
            return len(issues) == 0, issues

        last_end = 0.0
        for idx, w in enumerate(words):
            start = w.get("start", 0.0)
            end = w.get("end", 0.0)
            if start < 0.0 or end <= start:
                issues.append(f"Invalid timestamp span at word {idx}: start={start}, end={end}")
                break
            if start < last_end - 0.5:  # Allow 0.5s soft overlap tolerance
                issues.append(f"Negative timestamp drift at word {idx}: start={start} < previous_end={last_end}")
                break
            last_end = end

        return len(issues) == 0, issues

    @staticmethod
    def verify_remotion_props(props: Dict[str, Any]) -> Tuple[bool, List[str]]:
        """Verifies Remotion composition props (Rule 135 & Rule 136)."""
        issues = []
        scenes = props.get("scenes") or props.get("chunks") or []
        if not scenes:
            issues.append("Remotion props has no scenes or chunks array.")
            return False, issues

        for idx, scene in enumerate(scenes):
            duration_frames = scene.get("durationInFrames") or scene.get("duration_frames") or 0
            if duration_frames <= 0:
                issues.append(f"Scene {idx} has invalid durationInFrames: {duration_frames}")

            # Check layer presence
            bg = scene.get("background") or scene.get("layer_bg") or scene.get("bg_image")
            if not bg:
                issues.append(f"Scene {idx} missing Layer 1 Background.")

        return len(issues) == 0, issues


def run_self_test(mode: str = "auto") -> bool:
    """Executes a self-test of the RecordReplayHarness."""
    harness = RecordReplayHarness()
    stage_id = "demo_5beat_editorial_pipeline"

    sample_inputs = {
        "market": "EN",
        "topic": "The South Sea Bubble Forensic Collapse",
        "timestamp": 1720000000,
    }

    sample_output = {
        "title": "The £100,000,000 Illusion: How Isaac Newton Lost a Fortune",
        "scenes": [
            {"beat_index": 1, "title": "Cold Strike", "narration": "In the spring of 1720, the British Empire mortgaged its national debt to a trading company that owned no ships.", "duration_sec": 18.5},
            {"beat_index": 2, "title": "False Narrative", "narration": "Brokers promised endless South American gold, inflating stock by 800% in six months.", "duration_sec": 24.0},
            {"beat_index": 3, "title": "Forensic Paper Trail", "narration": "Parliamentary records reveal insiders began liquidating their positions in August.", "duration_sec": 30.2},
            {"beat_index": 4, "title": "Smoking Gun", "narration": "The bubble burst overnight. Sir Isaac Newton dumped his stock, having lost £20,000.", "duration_sec": 22.0},
            {"beat_index": 5, "title": "Modern Mirror", "narration": "Three centuries later, every liquidity trap still follows the exact South Sea blueprint.", "duration_sec": 26.1},
        ],
        "total_duration_sec": 120.8,
    }

    sample_audio_spine = {
        "total_duration_sec": 120.8,
        "words": [
            {"word": "In", "start": 0.0, "end": 0.2},
            {"word": "the", "start": 0.2, "end": 0.4},
            {"word": "spring", "start": 0.4, "end": 0.8},
            {"word": "of", "start": 0.8, "end": 1.0},
            {"word": "1720", "start": 1.0, "end": 1.6},
        ],
    }

    sample_remotion_props = {
        "fps": 30,
        "width": 1920,
        "height": 1080,
        "scenes": [
            {"scene_id": 1, "durationInFrames": 555, "background": "bg_1720_exchange.png", "foreground": "fg_director_newton.png"},
            {"scene_id": 2, "durationInFrames": 720, "background": "bg_london_parliament.png", "foreground": "fg_director_trader.png"},
            {"scene_id": 3, "durationInFrames": 906, "background": "bg_forensic_ledger.png", "foreground": "fg_director_auditor.png"},
            {"scene_id": 4, "durationInFrames": 660, "background": "bg_crash_stock_exchange.png", "foreground": "fg_director_newton_panic.png"},
            {"scene_id": 5, "durationInFrames": 783, "background": "bg_modern_wall_street.png", "foreground": "fg_director_modern_mirror.png"},
        ]
    }

    print(f"\n--- Running RecordReplayHarness Test [Stage: {stage_id}] [Mode: {mode}] ---")

    if mode in {"record", "auto"}:
        t0 = time.perf_counter()
        trace_path = harness.record_trace(stage_id, sample_inputs, sample_output)
        t_record = (time.perf_counter() - t0) * 1000
        print(f"✅ RECORD SUCCESS: Created Golden Trace at {trace_path.name} in {t_record:.2f}ms")

    # Replay test
    t0 = time.perf_counter()
    replayed = harness.replay_trace(stage_id)
    t_replay = (time.perf_counter() - t0) * 1000
    print(f"⚡ REPLAY SUCCESS: Loaded in {t_replay:.2f}ms (ZERO TOKENS USED)")

    # Semantic Contract Invariant Audits
    pass_b, issues_b = harness.verify_5_beat_script(replayed)
    pass_a, issues_a = harness.verify_audio_spine_continuity(sample_audio_spine)
    pass_r, issues_r = harness.verify_remotion_props(sample_remotion_props)

    all_passed = pass_b and pass_a and pass_r
    if all_passed:
        print("🛡️ ALL 3 SEMANTIC CONTRACT INVARIANTS PASSED:")
        print("   1. 5-Beat Docudrama Completeness: PASS")
        print("   2. Word-Level Audio Spine Continuity: PASS")
        print("   3. Two-Layer Remotion Compositions: PASS")
    else:
        print("❌ CONTRACT INVARIANT FAILURES:")
        for err in issues_b + issues_a + issues_r:
            print(f"   - {err}")

    return all_passed


def main():
    parser = argparse.ArgumentParser(description="🛡️ Record & Replay Resilient Test Harness")
    parser.add_argument("--mode", choices=["record", "replay", "auto"], default="auto", help="Execution mode")
    args = parser.parse_args()

    success = run_self_test(args.mode)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
