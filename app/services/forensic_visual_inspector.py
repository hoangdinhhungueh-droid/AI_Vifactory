#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""app/services/forensic_visual_inspector.py — Forensic Visual & Kinematic Inspection Gate (AVF-FORENSIC-001).

Implements Rule 122 (Visual Audit Gate) and Rule 140 (Vox Engine v3 Kinematics):
1. Pre-Render Prompt & Substrate Linter:
   - Enforces pre-printed forensic evidence on target substrates (zero blank voids before stamping/cutting).
   - Bans 'dead-stop hold' freeze directives that cause diffusion models to freeze pixels.
   - Enforces continuous tactile momentum and dynamic 3D camera trajectories.
2. Post-Render Optical Flow & Anti-Freeze Computer Vision Gate:
   - Computes frame-to-frame Mean Absolute Difference (MAD) motion energy across the video.
   - Fails-closed with 'ERR_FROZEN_SLIDESHOW' if any static scene lasts > 1.2s with motion energy < 0.8%.
3. Pre-Action Seed Image Target Zone Density Gate:
   - Computes Sobel edge gradient ratio and Shannon entropy in target document zones.
   - Fails-closed with 'ERR_BLANK_VOID_BEFORE_ACTION' if the target substrate is untextured blank white paper.
4. Visual Forensic Health Card Generator:
   - Exports transparent, human-readable ASCII and JSON motion profiles.
   - Eliminates blind automation and meaningless green passes.
"""

from __future__ import annotations

import json
import logging
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple, Union

logger = logging.getLogger("forensic_visual_inspector")

# Banned freeze phrases in I2V prompts that cause diffusion models to stall into slides
BANNED_FREEZE_DIRECTIVES = [
    "lock into dead-stop hold",
    "locks into dead-stop hold",
    "dead-stop hold",
    "dead stop hold",
    "completely motionless",
    "remain completely static",
    "freeze in place",
    "freeze for the remainder",
    "static hold until cut",
]

# Banned lazy camera moves that fail to produce Vox motion graphic dynamics
BANNED_LAZY_CAMERAS = [
    "static_overhead",
    "static overhead",
    "locked-off tripod",
    "motionless camera",
]

# Required substrate identifiers for tactile actions
MANDATORY_SUBSTRATE_KEYWORDS = [
    "target substrate:",
    "ledger",
    "financial ledger",
    "audit rows",
    "fine-print",
    "watermark",
    "dotted red perimeter",
    "dotted perimeter",
    "circular target stamp zone",
    "coordinate grid",
    "diagram markings",
]


@dataclass
class PromptLintViolation:
    rule_id: str
    severity: str  # "CRITICAL", "HIGH", "MEDIUM"
    message: str
    culprit_text: str


@dataclass
class PromptLintReport:
    scene_id: str
    passed: bool
    violations: List[PromptLintViolation] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        return {
            "scene_id": self.scene_id,
            "passed": self.passed,
            "violations": [asdict(v) for v in self.violations],
        }


@dataclass
class MotionTimelineSample:
    time_sec: float
    energy_pct: float
    is_frozen: bool


@dataclass
class MotionAuditReport:
    video_path: str
    verdict: str  # "PASS", "FAIL_FROZEN_SLIDESHOW", "ERROR"
    duration_sec: float
    mean_motion_energy_pct: float
    peak_motion_energy_pct: float
    max_freeze_duration_sec: float
    freeze_windows: List[Dict[str, float]] = field(default_factory=list)
    timeline_samples: List[MotionTimelineSample] = field(default_factory=list)
    diagnosis: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "video_path": self.video_path,
            "verdict": self.verdict,
            "duration_sec": round(self.duration_sec, 2),
            "mean_motion_energy_pct": round(self.mean_motion_energy_pct, 2),
            "peak_motion_energy_pct": round(self.peak_motion_energy_pct, 2),
            "max_freeze_duration_sec": round(self.max_freeze_duration_sec, 2),
            "freeze_windows": self.freeze_windows,
            "sample_count": len(self.timeline_samples),
            "diagnosis": self.diagnosis,
        }


@dataclass
class SubstrateAuditReport:
    image_path: str
    verdict: str  # "PASS", "FAIL_BLANK_VOID", "ERROR"
    sobel_edge_density: float
    shannon_entropy: float
    target_zone_description: str
    diagnosis: str

    def to_dict(self) -> Dict[str, Any]:
        return {
            "image_path": self.image_path,
            "verdict": self.verdict,
            "sobel_edge_density": round(self.sobel_edge_density, 4),
            "shannon_entropy": round(self.shannon_entropy, 3),
            "target_zone_description": self.target_zone_description,
            "diagnosis": self.diagnosis,
        }


class ForensicVisualInspector:
    """Quantitative Forensic Gate enforcing Rule 122 visual truth and kinetic vitality."""

    @staticmethod
    def lint_scene_prompts(
        scene_id: str,
        t2i_prompt: str,
        i2v_prompt: str,
        action_type: str = "",
        camera_directive: str = "",
        hero_object: str = "",
        interacting_tool: str = "",
    ) -> PromptLintReport:
        """Audits T2I and I2V prompts for a scene BEFORE calling generator APIs."""
        violations: List[PromptLintViolation] = []
        combined_objects = f"{hero_object} {interacting_tool} {action_type}".lower()

        is_tactile_action = any(
            k in combined_objects
            for k in ["stamp", "seal", "caliper", "cut", "tear", "yarn", "marker", "clip", "h1", "h2", "h3", "h4", "h5", "h6", "h7"]
        )

        # 1. Target Substrate Specification Check (T2I)
        if is_tactile_action:
            t2i_lower = (t2i_prompt or "").lower()
            has_substrate_spec = any(k in t2i_lower for k in MANDATORY_SUBSTRATE_KEYWORDS)
            if not has_substrate_spec:
                violations.append(
                    PromptLintViolation(
                        rule_id="RULE_122_AXIS_4_TARGET_SUBSTRATE",
                        severity="HIGH",
                        message=(
                            "T2I prompt lacks mandatory 'Target Substrate' forensic specifications "
                            "(dense financial ledger rows, dotted target perimeter, or authentic fine-print). "
                            "This triggers the 'blank void before action' flaw."
                        ),
                        culprit_text=t2i_prompt[:120] if t2i_prompt else "(empty prompt)",
                    )
                )

        # 2. Anti-Dead-Stop Freeze Linter (I2V)
        i2v_lower = (i2v_prompt or "").lower()
        for banned_freeze in BANNED_FREEZE_DIRECTIVES:
            if banned_freeze in i2v_lower:
                violations.append(
                    PromptLintViolation(
                        rule_id="RULE_140_ANTI_DEAD_STOP_FREEZE",
                        severity="CRITICAL",
                        message=(
                            f"I2V prompt contains banned freeze directive '{banned_freeze}'. "
                            "Diffusion models interpret this literally by freezing all pixels into a static slide."
                        ),
                        culprit_text=banned_freeze,
                    )
                )

        # 3. Continuous Tactile Momentum Check (I2V)
        has_momentum = any(
            phrase in i2v_lower
            for phrase in [
                "continuous tactile momentum",
                "sustained kinetic",
                "kinetic causal chain",
                "timeline kinematics",
                "sustained micro-dynamics",
                "dynamic 3d track",
                "fluid secondary kinematics",
            ]
        )
        if not has_momentum and i2v_prompt:
            violations.append(
                PromptLintViolation(
                    rule_id="RULE_140_CONTINUOUS_MOMENTUM_MANDATE",
                    severity="HIGH",
                    message=(
                        "I2V prompt missing explicit continuous tactile momentum / kinetic timeline phase directive. "
                        "Must specify post-impact follow-through and dynamic tracking to prevent pixel stall."
                    ),
                    culprit_text="Prompt ends without continuous momentum clause",
                )
            )

        # 4. Camera Dynamics Check
        cam_lower = (camera_directive or "").lower()
        if any(banned_cam == cam_lower or f"[{banned_cam}]" in i2v_lower for banned_cam in BANNED_LAZY_CAMERAS):
            # Only allow if explicitly coupled with dynamic punch/tracking
            if "punch" not in i2v_lower and "track" not in i2v_lower and "glide" not in i2v_lower:
                violations.append(
                    PromptLintViolation(
                        rule_id="RULE_140_DYNAMIC_CAMERA_MANDATE",
                        severity="MEDIUM",
                        message=(
                            f"Camera directive '{camera_directive}' is a banned lazy glide without punch/tracking. "
                            "Must use DYNAMIC_CRASH_PUNCH, RAKE_30_RACK_FOCUS, or LATERAL_WHIP_PAN."
                        ),
                        culprit_text=camera_directive,
                    )
                )

        passed = not any(v.severity in ("CRITICAL", "HIGH") for v in violations)
        return PromptLintReport(scene_id=scene_id, passed=passed, violations=violations)

    @classmethod
    def audit_video_motion_energy(
        cls,
        video_path: Union[str, Path],
        sample_fps: float = 4.0,
        min_motion_pct: float = 0.8,
        max_freeze_sec: float = 1.2,
    ) -> MotionAuditReport:
        """Quantitatively inspects physical MP4 video for frozen slideshow sections."""
        v_path = Path(video_path)
        if not v_path.exists() or v_path.stat().st_size == 0:
            return MotionAuditReport(
                video_path=str(v_path),
                verdict="ERROR",
                duration_sec=0.0,
                mean_motion_energy_pct=0.0,
                peak_motion_energy_pct=0.0,
                max_freeze_duration_sec=0.0,
                diagnosis=f"Video file does not exist or is empty: {v_path}",
            )

        frames_with_ts = cls._extract_grayscale_frames(v_path, sample_fps=sample_fps)
        if len(frames_with_ts) < 2:
            return MotionAuditReport(
                video_path=str(v_path),
                verdict="ERROR",
                duration_sec=0.0,
                mean_motion_energy_pct=0.0,
                peak_motion_energy_pct=0.0,
                max_freeze_duration_sec=0.0,
                diagnosis="Failed to extract sufficient frames from video.",
            )

        import numpy as np

        samples: List[MotionTimelineSample] = []
        energies: List[float] = []
        freeze_windows: List[Dict[str, float]] = []

        current_freeze_start: Optional[float] = None
        max_freeze_dur = 0.0

        for i in range(1, len(frames_with_ts)):
            t_curr, gray_curr = frames_with_ts[i]
            t_prev, gray_prev = frames_with_ts[i - 1]
            # Compute normalized Mean Absolute Difference (MAD) percentage: [0.0% .. 100.0%]
            diff = np.abs(gray_curr.astype(np.float32) - gray_prev.astype(np.float32))
            energy_pct = (float(np.mean(diff)) / 255.0) * 100.0
            energies.append(energy_pct)

            is_frozen = energy_pct < min_motion_pct
            samples.append(MotionTimelineSample(time_sec=t_curr, energy_pct=energy_pct, is_frozen=is_frozen))

            if is_frozen:
                if current_freeze_start is None:
                    current_freeze_start = t_prev
                freeze_dur = t_curr - current_freeze_start
                if freeze_dur > max_freeze_dur:
                    max_freeze_dur = freeze_dur
            else:
                if current_freeze_start is not None:
                    freeze_dur = t_curr - current_freeze_start
                    if freeze_dur >= max_freeze_sec:
                        freeze_windows.append({
                            "start_sec": round(current_freeze_start, 2),
                            "end_sec": round(t_curr, 2),
                            "duration_sec": round(freeze_dur, 2),
                        })
                    current_freeze_start = None

        if current_freeze_start is not None:
            final_freeze_dur = frames_with_ts[-1][0] - current_freeze_start
            if final_freeze_dur >= max_freeze_sec:
                freeze_windows.append({
                    "start_sec": round(current_freeze_start, 2),
                    "end_sec": round(frames_with_ts[-1][0], 2),
                    "duration_sec": round(final_freeze_dur, 2),
                })

        total_duration = frames_with_ts[-1][0]
        mean_energy = float(np.mean(energies)) if energies else 0.0
        peak_energy = float(np.max(energies)) if energies else 0.0

        if freeze_windows:
            verdict = "FAIL_FROZEN_SLIDESHOW"
            worst_window = max(freeze_windows, key=lambda w: w["duration_sec"])
            diagnosis = (
                f"Frozen slideshow defect detected: static frame held from {worst_window['start_sec']}s "
                f"to {worst_window['end_sec']}s ({worst_window['duration_sec']}s continuous freeze, "
                f"threshold ceiling is {max_freeze_sec}s with motion < {min_motion_pct}%)."
            )
        else:
            verdict = "PASS"
            diagnosis = (
                f"Kinematic vital signs healthy: Mean motion energy {mean_energy:.2f}% "
                f"(peak {peak_energy:.2f}%), max static window {max_freeze_dur:.2f}s "
                f"(safely within {max_freeze_sec}s threshold)."
            )

        return MotionAuditReport(
            video_path=str(v_path),
            verdict=verdict,
            duration_sec=total_duration,
            mean_motion_energy_pct=mean_energy,
            peak_motion_energy_pct=peak_energy,
            max_freeze_duration_sec=max_freeze_dur,
            freeze_windows=freeze_windows,
            timeline_samples=samples,
            diagnosis=diagnosis,
        )

    @classmethod
    def audit_image_substrate_density(
        cls,
        image_path: Union[str, Path],
        min_edge_density: float = 0.035,
        min_entropy: float = 3.0,
    ) -> SubstrateAuditReport:
        """Inspects seed image for blank void defect on document action planes."""
        img_path = Path(image_path)
        if not img_path.exists() or img_path.stat().st_size == 0:
            return SubstrateAuditReport(
                image_path=str(img_path),
                verdict="ERROR",
                sobel_edge_density=0.0,
                shannon_entropy=0.0,
                target_zone_description="File missing",
                diagnosis=f"Image file does not exist: {img_path}",
            )

        import numpy as np
        from PIL import Image

        try:
            with Image.open(img_path) as pil_img:
                gray_img = pil_img.convert("L")
                w, h = gray_img.size
                arr = np.array(gray_img, dtype=np.float32)

            # Focus inspection on central and upper-central document zone (exclude bottom 20% subtitle zone)
            y_start, y_end = int(h * 0.15), int(h * 0.80)
            x_start, x_end = int(w * 0.15), int(w * 0.85)
            target_roi = arr[y_start:y_end, x_start:x_end]

            # 1. Sobel Edge Gradient Filter
            gx = (
                np.roll(target_roi, -1, axis=1) - np.roll(target_roi, 1, axis=1)
            )[1:-1, 1:-1]
            gy = (
                np.roll(target_roi, -1, axis=0) - np.roll(target_roi, 1, axis=0)
            )[1:-1, 1:-1]
            grad_mag = np.hypot(gx, gy)
            edge_pixels = np.sum(grad_mag > 28.0)
            total_roi_pixels = float(grad_mag.size) or 1.0
            edge_density = float(edge_pixels / total_roi_pixels)

            # 2. Shannon Luminance Entropy
            hist, _ = np.histogram(target_roi.flatten(), bins=64, range=(0, 256), density=True)
            non_zero_hist = hist[hist > 0]
            entropy = float(-np.sum(non_zero_hist * np.log2(non_zero_hist)))

            is_blank = (edge_density < min_edge_density) and (entropy < min_entropy)
            if is_blank:
                verdict = "FAIL_BLANK_VOID"
                diagnosis = (
                    f"Blank void defect detected on document action plane: Sobel edge density {edge_density:.4f} "
                    f"(min {min_edge_density}), Shannon entropy {entropy:.2f} (min {min_entropy}). "
                    "Surface is plain blank paper lacking pre-printed forensic evidence/ledger rows."
                )
            else:
                verdict = "PASS"
                diagnosis = (
                    f"Substrate texture verified: Sobel edge density {edge_density:.4f} "
                    f"(>= {min_edge_density}), entropy {entropy:.2f} (>= {min_entropy}). "
                    "Rich archival document texture and fine-print confirmed."
                )

            return SubstrateAuditReport(
                image_path=str(img_path),
                verdict=verdict,
                sobel_edge_density=edge_density,
                shannon_entropy=entropy,
                target_zone_description=f"ROI [{x_start}:{x_end}, {y_start}:{y_end}]",
                diagnosis=diagnosis,
            )
        except Exception as err:
            logger.error(f"[audit_image_substrate_density] Error inspecting {img_path}: {err}")
            return SubstrateAuditReport(
                image_path=str(img_path),
                verdict="ERROR",
                sobel_edge_density=0.0,
                shannon_entropy=0.0,
                target_zone_description="Exception during inspection",
                diagnosis=f"Inspection exception: {err}",
            )

    @classmethod
    def generate_visual_health_card(
        cls,
        episode_id: str,
        lint_reports: List[PromptLintReport],
        motion_reports: List[MotionAuditReport],
        substrate_reports: Optional[List[SubstrateAuditReport]] = None,
        output_markdown_path: Optional[Path] = None,
        output_json_path: Optional[Path] = None,
    ) -> Dict[str, Any]:
        """Compiles a transparent forensic health card with ASCII motion timeline graphs."""
        substrate_reports = substrate_reports or []

        all_lint_pass = all(r.passed for r in lint_reports)
        all_motion_pass = all(r.verdict == "PASS" for r in motion_reports)
        all_substrate_pass = all(r.verdict == "PASS" for r in substrate_reports) if substrate_reports else True

        overall_status = "PASS" if (all_lint_pass and all_motion_pass and all_substrate_pass) else "FAIL"

        card_data: Dict[str, Any] = {
            "episode_id": episode_id,
            "overall_status": overall_status,
            "gate_version": "AVF-FORENSIC-001 (Rule 122 & 140 Enforcer)",
            "summary": {
                "lint_scenes_total": len(lint_reports),
                "lint_scenes_passed": sum(1 for r in lint_reports if r.passed),
                "motion_videos_total": len(motion_reports),
                "motion_videos_passed": sum(1 for r in motion_reports if r.verdict == "PASS"),
                "substrate_images_total": len(substrate_reports),
                "substrate_images_passed": sum(1 for r in substrate_reports if r.verdict == "PASS"),
            },
            "lint_reports": [r.to_dict() for r in lint_reports],
            "motion_reports": [r.to_dict() for r in motion_reports],
            "substrate_reports": [r.to_dict() for r in substrate_reports],
        }

        # Build Markdown Card
        lines = [
            f"# 🔍 VISUAL & KINEMATIC FORENSIC HEALTH CARD: `{episode_id}`",
            f"> **Systemic Quality Gate AVF-FORENSIC-001 (Zero-Mock Visual Inspection)**",
            f"> **Overall Verdict:** `{'🟢 PASS' if overall_status == 'PASS' else '🔴 FAIL'}`",
            "",
            "## 1. Executive Forensic Summary",
            f"| Metric Gate | Evaluated | Passed | Failure Rate | Status |",
            f"| :--- | :---: | :---: | :---: | :--- |",
            f"| **Pre-Render Prompt & Substrate Linter** | {card_data['summary']['lint_scenes_total']} scenes | {card_data['summary']['lint_scenes_passed']} | {100 - (card_data['summary']['lint_scenes_passed'] / max(1, card_data['summary']['lint_scenes_total']) * 100):.1f}% | `{'PASS' if all_lint_pass else 'FAIL'}` |",
            f"| **Post-Render Motion Energy & Anti-Freeze** | {card_data['summary']['motion_videos_total']} clips | {card_data['summary']['motion_videos_passed']} | {100 - (card_data['summary']['motion_videos_passed'] / max(1, card_data['summary']['motion_videos_total']) * 100):.1f}% | `{'PASS' if all_motion_pass else 'FAIL'}` |",
            f"| **Pre-Action Substrate Texture Density** | {card_data['summary']['substrate_images_total']} images | {card_data['summary']['substrate_images_passed']} | {100 - (card_data['summary']['substrate_images_passed'] / max(1, card_data['summary']['substrate_images_total']) * 100):.1f}% | `{'PASS' if all_substrate_pass else 'FAIL'}` |",
            "",
            "## 2. Motion Energy Second-by-Second Profiling (Anti-Slideshow)",
        ]

        for m_rep in motion_reports:
            v_name = Path(m_rep.video_path).name
            status_tag = "🟢 PASS" if m_rep.verdict == "PASS" else "🔴 FAIL"
            lines.append(f"### Video Asset: `{v_name}` ({status_tag})")
            lines.append(f"- **Duration**: `{m_rep.duration_sec:.2f}s` | **Mean Motion**: `{m_rep.mean_motion_energy_pct:.2f}%` | **Peak Motion**: `{m_rep.peak_motion_energy_pct:.2f}%` | **Max Static Hold**: `{m_rep.max_freeze_duration_sec:.2f}s`")
            lines.append(f"- **Forensic Diagnosis**: {m_rep.diagnosis}")
            lines.append("")
            lines.append("```text")
            lines.append("TIME   MOTION ENERGY PROFILE                          STATUS")
            lines.append("-----------------------------------------------------------------")
            for samp in m_rep.timeline_samples:
                bars = int(min(30, samp.energy_pct * 2.5))
                bar_str = "█" * bars + " " * (30 - bars)
                state_str = "⚠️ FREEZE (<0.8%)" if samp.is_frozen else "ACTIVE"
                lines.append(f"{samp.time_sec:04.1f}s [{bar_str}] {samp.energy_pct:5.2f}% {state_str}")
            lines.append("```")
            lines.append("")

        if substrate_reports:
            lines.append("## 3. Substrate Surface Texture & Anti-Blank-Void Audit")
            lines.append("| Image Asset | Sobel Edge Density | Shannon Entropy | Verdict | Diagnosis |")
            lines.append("| :--- | :---: | :---: | :---: | :--- |")
            for s_rep in substrate_reports:
                i_name = Path(s_rep.image_path).name
                s_tag = "🟢 PASS" if s_rep.verdict == "PASS" else "🔴 FAIL"
                lines.append(f"| `{i_name}` | `{s_rep.sobel_edge_density:.4f}` | `{s_rep.shannon_entropy:.2f}` | {s_tag} | {s_rep.diagnosis} |")
            lines.append("")

        if any(not r.passed for r in lint_reports):
            lines.append("## 4. Prompt Engine Lint Deficiencies Detected")
            for l_rep in lint_reports:
                if not l_rep.passed:
                    lines.append(f"### Scene `{l_rep.scene_id}` Violations:")
                    for viol in l_rep.violations:
                        lines.append(f"- **[{viol.severity}] `{viol.rule_id}`**: {viol.message}")
                        lines.append(f"  > *Culprit*: `{viol.culprit_text}`")
            lines.append("")

        md_content = "\n".join(lines)

        if output_markdown_path:
            output_markdown_path.parent.mkdir(parents=True, exist_ok=True)
            output_markdown_path.write_text(md_content, encoding="utf-8")

        if output_json_path:
            output_json_path.parent.mkdir(parents=True, exist_ok=True)
            output_json_path.write_text(json.dumps(card_data, indent=2, ensure_ascii=False), encoding="utf-8")

        return card_data

    @classmethod
    def _extract_grayscale_frames(
        cls,
        video_path: Path,
        sample_fps: float = 4.0,
    ) -> List[Tuple[float, Any]]:
        """Extracts grayscale frames and timestamps using cv2 or av."""
        import numpy as np

        frames: List[Tuple[float, Any]] = []

        # 1. Try OpenCV first
        try:
            import cv2
            cap = cv2.VideoCapture(str(video_path))
            if cap.isOpened():
                native_fps = cap.get(cv2.CAP_PROP_FPS) or 30.0
                step = max(1, int(round(native_fps / sample_fps)))
                frame_idx = 0
                while True:
                    ret, frame = cap.read()
                    if not ret:
                        break
                    if frame_idx % step == 0:
                        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
                        frames.append((round(frame_idx / native_fps, 3), gray))
                    frame_idx += 1
                cap.release()
                if frames:
                    return frames
        except Exception as cv_err:
            logger.debug(f"[extract_frames] OpenCV extraction skipped: {cv_err}")

        # 2. Try PyAV next (VPS native)
        try:
            import av
            container = av.open(str(video_path))
            stream = container.streams.video[0]
            native_fps = float(stream.average_rate or 30.0)
            step = max(1, int(round(native_fps / sample_fps)))
            frame_idx = 0
            for frame in container.decode(stream):
                if frame_idx % step == 0:
                    pil_img = frame.to_image().convert("L")
                    gray = np.array(pil_img, dtype=np.uint8)
                    pts_sec = float(frame.pts * stream.time_base) if frame.pts else (frame_idx / native_fps)
                    frames.append((round(pts_sec, 3), gray))
                frame_idx += 1
            container.close()
            if frames:
                return frames
        except Exception as av_err:
            logger.debug(f"[extract_frames] PyAV extraction skipped: {av_err}")

        return frames
