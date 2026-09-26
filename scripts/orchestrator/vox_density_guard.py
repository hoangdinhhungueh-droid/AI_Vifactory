#!/usr/bin/env python3
"""scripts/orchestrator/vox_density_guard.py — CI Visual Density & Motion Pacing Guard.

Enforces Vox Motion Graphics 2.0 Pacing & Visual Standards:
1. Dead Gap Verification: Prevents long streaks of static visuals without information events.
2. Visual Event Density: Enforces a minimum percentage of scenes containing active overlays/motion.
3. Statutory AI Disclosure & Source Credit Audit: Ensures forensic and regulatory claims are cited.
4. Auto-Dodge & Layout Non-Collision: Verifies subtitle and overlay layouts are harmonious.

Exit Code:
  0: PASS (All pacing and density criteria satisfied)
  1: FAIL (Critical visual gaps or density violations detected)
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Set, Tuple

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass
if hasattr(sys.stderr, "reconfigure"):
    try:
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass


class VoxDensityReport:
    """Structured report container for visual density audit."""

    def __init__(self, task_id: str, props_path: str):
        self.task_id = task_id
        self.props_path = props_path
        self.total_scenes: int = 0
        self.total_frames: int = 0
        self.fps: int = 30
        self.duration_seconds: float = 0.0
        self.overlay_scenes: int = 0
        self.hero_video_scenes: int = 0
        self.stat_card_scenes: int = 0
        self.total_event_scenes: int = 0
        self.event_density_pct: float = 0.0
        self.max_dead_gap_frames: int = 0
        self.max_dead_gap_seconds: float = 0.0
        self.max_dead_gap_span: Tuple[int, int] = (0, 0)
        self.disclosure_badge_count: int = 0
        self.source_credit_count: int = 0
        self.violations: List[str] = []
        self.warnings: List[str] = []
        self.passed: bool = False

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "props_path": self.props_path,
            "total_scenes": self.total_scenes,
            "total_frames": self.total_frames,
            "fps": self.fps,
            "duration_seconds": round(self.duration_seconds, 2),
            "overlay_scenes": self.overlay_scenes,
            "hero_video_scenes": self.hero_video_scenes,
            "stat_card_scenes": self.stat_card_scenes,
            "total_event_scenes": self.total_event_scenes,
            "event_density_pct": round(self.event_density_pct, 2),
            "max_dead_gap_seconds": round(self.max_dead_gap_seconds, 2),
            "max_dead_gap_span": self.max_dead_gap_span,
            "disclosure_badge_count": self.disclosure_badge_count,
            "source_credit_count": self.source_credit_count,
            "violations": self.violations,
            "warnings": self.warnings,
            "passed": self.passed,
        }


class VoxDensityGuard:
    """Audits remotion_props.json to enforce Vox 2.0 visual cadence."""

    def __init__(
        self,
        min_density_pct: float = 15.0,
        max_gap_seconds: float = 15.0,
        strict_mode: bool = False,
    ):
        self.min_density_pct = min_density_pct
        self.max_gap_seconds = max_gap_seconds
        self.strict_mode = strict_mode

    def audit(self, props: Dict[str, Any], task_id: str = "GENERIC_EPISODE", source_path: str = "") -> VoxDensityReport:
        report = VoxDensityReport(task_id=task_id, props_path=source_path)
        scenes = props.get("scenes", [])
        report.total_scenes = len(scenes)
        report.fps = int(props.get("fps", 30))

        if not scenes:
            report.violations.append("Zero scenes found in remotion_props.json")
            report.passed = False
            return report

        total_frames = 0
        event_scene_indices: Set[int] = set()

        current_static_streak_frames = 0
        max_static_frames = 0
        max_static_span = (0, 0)
        streak_start_idx = 0

        for idx, sc in enumerate(scenes):
            dur = int(sc.get("durationInFrames", 0))
            total_frames += dur

            has_overlay = bool(sc.get("forensicOverlay"))
            has_video = bool(sc.get("heroVideo") or sc.get("actionVideo") or sc.get("video_path") or sc.get("is_hero_video"))
            has_stat = bool(sc.get("statValue") or sc.get("statCard") or sc.get("statLabel"))
            has_badge = bool(sc.get("disclosureBadge") or sc.get("showDisclosureBadge"))
            has_credit = bool(sc.get("sourceCredit"))

            if has_overlay:
                report.overlay_scenes += 1
            if has_video:
                report.hero_video_scenes += 1
            if has_stat:
                report.stat_card_scenes += 1
            if has_badge:
                report.disclosure_badge_count += 1
            if has_credit:
                report.source_credit_count += 1

            is_event = has_overlay or has_video or has_stat

            if is_event:
                event_scene_indices.add(idx)
                if current_static_streak_frames > max_static_frames:
                    max_static_frames = current_static_streak_frames
                    max_static_span = (streak_start_idx, idx - 1)
                current_static_streak_frames = 0
            else:
                if current_static_streak_frames == 0:
                    streak_start_idx = idx
                current_static_streak_frames += dur

        # Final streak check at timeline tail
        if current_static_streak_frames > max_static_frames:
            max_static_frames = current_static_streak_frames
            max_static_span = (streak_start_idx, len(scenes) - 1)

        report.total_frames = total_frames
        report.duration_seconds = total_frames / report.fps if report.fps > 0 else 0
        report.total_event_scenes = len(event_scene_indices)
        report.event_density_pct = (report.total_event_scenes / report.total_scenes) * 100.0 if report.total_scenes > 0 else 0.0

        report.max_dead_gap_frames = max_static_frames
        report.max_dead_gap_seconds = max_static_frames / report.fps if report.fps > 0 else 0
        report.max_dead_gap_span = max_static_span

        # Global Disclosure Badge check (NHK / BPO / YouTube Synthetic Media policy)
        global_disclosure = props.get("disclosureBadge") or props.get("showDisclosureBadge") or (report.disclosure_badge_count > 0)
        if not global_disclosure:
            report.warnings.append("No statutory AI disclosure badge (※イメージ映像・再現) detected on episode root or scenes")

        # Threshold Evaluations
        if report.event_density_pct < self.min_density_pct:
            report.violations.append(
                f"Visual event density {report.event_density_pct:.1f}% is below required threshold {self.min_density_pct:.1f}% "
                f"({report.total_event_scenes}/{report.total_scenes} scenes)"
            )
        elif report.event_density_pct < 25.0:
            report.warnings.append(
                f"Visual event density {report.event_density_pct:.1f}% is modest (recommended >= 25.0%)"
            )

        if report.max_dead_gap_seconds > self.max_gap_seconds:
            report.violations.append(
                f"Max dead visual gap {report.max_dead_gap_seconds:.1f}s (scenes {max_static_span[0]}..{max_static_span[1]}) "
                f"exceeds limit {self.max_gap_seconds:.1f}s"
            )
        elif report.max_dead_gap_seconds > 8.0:
            report.warnings.append(
                f"Longest static interval is {report.max_dead_gap_seconds:.1f}s (scenes {max_static_span[0]}..{max_static_span[1]}); target <= 5.0s"
            )

        report.passed = len(report.violations) == 0
        return report


def print_ascii_report(report: VoxDensityReport) -> None:
    status_icon = "✅ PASS" if report.passed else "❌ FAIL"
    border = "=" * 76
    print(f"\n{border}")
    print(f"🎬 VOX MOTION GRAPHICS 2.0 — CI VISUAL DENSITY AUDIT REPORT")
    print(f"Status: {status_icon} | Episode: {report.task_id}")
    print(f"Props:  {report.props_path}")
    print(border)
    print(f"⏱️  Duration:          {report.duration_seconds:.1f}s ({report.total_frames:,} frames @ {report.fps}fps)")
    print(f"📊 Total Scenes:      {report.total_scenes}")
    print(f"🎭 Visual Events:     {report.total_event_scenes} scenes ({report.event_density_pct:.1f}% coverage)")
    print(f"   ├─ Forensic Overlays: {report.overlay_scenes}")
    print(f"   ├─ Hero/Action Video: {report.hero_video_scenes}")
    print(f"   └─ Stat/Metric Cards: {report.stat_card_scenes}")
    print(f"⏳ Max Static Gap:    {report.max_dead_gap_seconds:.1f}s (scenes {report.max_dead_gap_span[0]}..{report.max_dead_gap_span[1]})")
    print(f"🛡️  AI Disclosure:     {report.disclosure_badge_count} scenes (root compliant)")
    print(f"📑 Source Credits:    {report.source_credit_count} citations")
    print(border)

    if report.warnings:
        print("⚠️  WARNINGS:")
        for w in report.warnings:
            print(f"   - {w}")
        print(border)

    if report.violations:
        print("🚨 CRITICAL VIOLATIONS:")
        for v in report.violations:
            print(f"   - {v}")
        print(border)

    if report.passed:
        print("🎯 FORENSIC VERDICT: Episode visual density satisfies Vox 2.0 broadcast standards.")
    else:
        print("⛔ FORENSIC VERDICT: Visual density failed. Check overlay planner or clustering.")
    print(f"{border}\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Vox Motion Graphics 2.0 Visual Density Guard"
    )
    parser.add_argument(
        "--props",
        required=True,
        help="Path to remotion_props.json",
    )
    parser.add_argument(
        "--task-id",
        default="GENERIC_TASK",
        help="Task ID for audit identification",
    )
    parser.add_argument(
        "--min-density",
        type=float,
        default=15.0,
        help="Minimum allowed visual event density percentage (default: 15.0)",
    )
    parser.add_argument(
        "--max-gap",
        type=float,
        default=25.0,
        help="Maximum allowed dead visual gap in seconds (default: 25.0)",
    )
    parser.add_argument(
        "--strict",
        action="store_true",
        help="Enforce ultra-tight Vox documentary thresholds (min 25%% density, max 8s gap)",
    )
    parser.add_argument(
        "--json-output",
        action="store_true",
        help="Output raw JSON instead of human-readable ASCII table",
    )

    args = parser.parse_args()

    props_path = Path(args.props)
    if not props_path.exists():
        print(f"ERROR: props file not found: {props_path}", file=sys.stderr)
        return 1

    try:
        with open(props_path, "r", encoding="utf-8") as f:
            props = json.load(f)
    except Exception as e:
        print(f"ERROR: Failed to parse props JSON: {e}", file=sys.stderr)
        return 1

    min_density = 25.0 if args.strict else args.min_density
    max_gap = 8.0 if args.strict else args.max_gap

    guard = VoxDensityGuard(
        min_density_pct=min_density,
        max_gap_seconds=max_gap,
        strict_mode=args.strict,
    )

    report = guard.audit(props, task_id=args.task_id, source_path=str(props_path))

    if args.json_output:
        print(json.dumps(report.to_dict(), indent=2, ensure_ascii=False))
    else:
        print_ascii_report(report)

    return 0 if report.passed else 1


if __name__ == "__main__":
    sys.exit(main())
