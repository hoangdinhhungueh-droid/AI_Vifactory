#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""app/services/hg3_visual_audit.py — Systemic HG3 Visual Telemetry Gate ("Mắt Thần HG3").

Evaluates rendered HG3 representative still frames deterministically with PIL and NumPy
to fail-closed on under-exposure (crushed black caves), over-exposure (blown-out white),
dark horizon voids, flat low-contrast frames, and empty low-detail renders.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from PIL import Image


@dataclass(frozen=True)
class HG3VisualThresholds:
    """Deterministic luminance, exposure, contrast, and edge-detail bounds for HG3 stills."""

    min_width: int = 1280
    min_height: int = 720
    min_mean_luma: float = 78.0
    max_mean_luma: float = 208.0
    min_median_luma: float = 60.0
    max_median_luma: float = 220.0
    max_crushed_black_pct: float = 18.0
    max_blown_white_pct: float = 16.0
    min_top30_luma: float = 45.0
    min_center_luma: float = 75.0
    min_dynamic_range: float = 45.0
    min_edge_energy: float = 4.5
    max_failed_frame_ratio: float = 0.0


def analyze_still_frame(
    img_path: Path,
    thresholds: Optional[HG3VisualThresholds] = None,
) -> Dict[str, Any]:
    """Computes Rec.709 luminance, exposure, contrast, and edge telemetry for one PNG/JPEG still."""
    cfg = thresholds or HG3VisualThresholds()
    if not img_path.exists() or img_path.stat().st_size == 0:
        return {
            "file": img_path.name,
            "path": str(img_path),
            "passed": False,
            "metrics": {},
            "violations": [f"Missing or empty still image: {img_path}"],
        }

    with Image.open(img_path) as im:
        rgb = np.asarray(im.convert("RGB"), dtype=np.float32)

    height, width = int(rgb.shape[0]), int(rgb.shape[1])
    y = 0.2126 * rgb[:, :, 0] + 0.7152 * rgb[:, :, 1] + 0.0722 * rgb[:, :, 2]

    mean_luma = float(np.mean(y))
    p10_luma = float(np.percentile(y, 10))
    p50_luma = float(np.percentile(y, 50))
    p90_luma = float(np.percentile(y, 90))
    dynamic_range = float(p90_luma - p10_luma)
    crushed_black_pct = float(np.mean(y < 20.0) * 100.0)
    blown_white_pct = float(np.mean(y > 244.0) * 100.0)

    top_h = max(1, int(height * 0.30))
    y0, y1 = int(height * 0.20), max(int(height * 0.20) + 1, int(height * 0.80))
    x0, x1 = int(width * 0.20), max(int(width * 0.20) + 1, int(width * 0.80))
    top30_luma = float(np.mean(y[:top_h, :]))
    center_luma = float(np.mean(y[y0:y1, x0:x1]))

    dx = float(np.mean(np.abs(np.diff(y, axis=1)))) if width > 1 else 0.0
    dy = float(np.mean(np.abs(np.diff(y, axis=0)))) if height > 1 else 0.0
    edge_energy = float(dx + dy)

    metrics = {
        "width": width,
        "height": height,
        "mean_luma": round(mean_luma, 2),
        "p10_luma": round(p10_luma, 2),
        "p50_luma": round(p50_luma, 2),
        "p90_luma": round(p90_luma, 2),
        "dynamic_range": round(dynamic_range, 2),
        "crushed_black_pct": round(crushed_black_pct, 2),
        "blown_white_pct": round(blown_white_pct, 2),
        "top30_luma": round(top30_luma, 2),
        "center_luma": round(center_luma, 2),
        "edge_energy": round(edge_energy, 3),
    }

    violations: List[str] = []
    if width < cfg.min_width or height < cfg.min_height:
        violations.append(
            f"resolution {width}x{height} below minimum {cfg.min_width}x{cfg.min_height}"
        )
    if mean_luma < cfg.min_mean_luma:
        violations.append(
            f"underexposed mean_luma={mean_luma:.1f} < {cfg.min_mean_luma:.1f}"
        )
    if mean_luma > cfg.max_mean_luma:
        violations.append(
            f"overexposed mean_luma={mean_luma:.1f} > {cfg.max_mean_luma:.1f}"
        )
    if p50_luma < cfg.min_median_luma:
        violations.append(
            f"dark median p50_luma={p50_luma:.1f} < {cfg.min_median_luma:.1f}"
        )
    if p50_luma > cfg.max_median_luma:
        violations.append(
            f"bright median p50_luma={p50_luma:.1f} > {cfg.max_median_luma:.1f}"
        )
    if crushed_black_pct > cfg.max_crushed_black_pct:
        violations.append(
            f"crushed_black_pct={crushed_black_pct:.1f}% > {cfg.max_crushed_black_pct:.1f}%"
        )
    if blown_white_pct > cfg.max_blown_white_pct:
        violations.append(
            f"blown_white_pct={blown_white_pct:.1f}% > {cfg.max_blown_white_pct:.1f}%"
        )
    if top30_luma < cfg.min_top30_luma:
        violations.append(
            f"dark horizon void top30_luma={top30_luma:.1f} < {cfg.min_top30_luma:.1f}"
        )
    if center_luma < cfg.min_center_luma:
        violations.append(
            f"dark subject center_luma={center_luma:.1f} < {cfg.min_center_luma:.1f}"
        )
    if dynamic_range < cfg.min_dynamic_range:
        violations.append(
            f"flat dynamic_range={dynamic_range:.1f} < {cfg.min_dynamic_range:.1f}"
        )
    if edge_energy < cfg.min_edge_energy:
        violations.append(
            f"low detail edge_energy={edge_energy:.2f} < {cfg.min_edge_energy:.2f}"
        )

    return {
        "file": img_path.name,
        "path": str(img_path),
        "passed": len(violations) == 0,
        "metrics": metrics,
        "violations": violations,
    }


def _atomic_write_json(report_path: Path, payload: Dict[str, Any]) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    tmp_path = report_path.with_suffix(".tmp")
    tmp_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
    if report_path.exists():
        report_path.unlink()
    tmp_path.replace(report_path)


def audit_hg3_stills(
    still_paths: List[Path],
    report_path: Optional[Path] = None,
    thresholds: Optional[HG3VisualThresholds] = None,
) -> Dict[str, Any]:
    """Audits all HG3 stills fail-closed and writes a structured visual telemetry report."""
    cfg = thresholds or HG3VisualThresholds()
    if not still_paths:
        report = {
            "passed": False,
            "total_stills": 0,
            "passed_stills": 0,
            "failed_stills": 0,
            "failed_ratio": 1.0,
            "thresholds": asdict(cfg),
            "summary": {},
            "violations": ["No HG3 still images were provided to audit_hg3_stills"],
            "frames": [],
        }
        if report_path is not None:
            _atomic_write_json(report_path, report)
        return report

    frames = [analyze_still_frame(Path(p), cfg) for p in still_paths]
    total = len(frames)
    passed_cnt = sum(1 for f in frames if f["passed"])
    failed_cnt = total - passed_cnt
    failed_ratio = round(failed_cnt / total, 4)

    valid_metrics = [f["metrics"] for f in frames if f["metrics"]]
    summary: Dict[str, Any] = {}
    if valid_metrics:
        summary = {
            "mean_luma_min": min(m["mean_luma"] for m in valid_metrics),
            "mean_luma_max": max(m["mean_luma"] for m in valid_metrics),
            "p50_luma_min": min(m["p50_luma"] for m in valid_metrics),
            "crushed_black_pct_max": max(m["crushed_black_pct"] for m in valid_metrics),
            "blown_white_pct_max": max(m["blown_white_pct"] for m in valid_metrics),
            "top30_luma_min": min(m["top30_luma"] for m in valid_metrics),
            "center_luma_min": min(m["center_luma"] for m in valid_metrics),
            "dynamic_range_min": min(m["dynamic_range"] for m in valid_metrics),
            "edge_energy_min": min(m["edge_energy"] for m in valid_metrics),
        }

    top_violations = [
        f"{f['file']}: {', '.join(f['violations'])}"
        for f in frames
        if not f["passed"]
    ]
    overall_passed = failed_cnt == 0 or (failed_ratio <= cfg.max_failed_frame_ratio and passed_cnt > 0)

    report: Dict[str, Any] = {
        "passed": bool(overall_passed),
        "total_stills": total,
        "passed_stills": passed_cnt,
        "failed_stills": failed_cnt,
        "failed_ratio": failed_ratio,
        "thresholds": asdict(cfg),
        "summary": summary,
        "violations": top_violations,
        "frames": frames,
    }
    if report_path is not None:
        _atomic_write_json(report_path, report)
    return report
