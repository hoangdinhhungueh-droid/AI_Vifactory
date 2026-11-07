import React from "react";
import {
  AbsoluteFill,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
  Easing,
} from "remotion";
import {
  CameraPose,
  CANONICAL_MOTION_PRESETS,
  MotionPreset,
  MotionTier,
  SPEED_BUDGET,
} from "./motionPresets";

export interface CameraRigProps {
  children: React.ReactNode;
  presetId?: number;
  preset?: MotionPreset;
  /** Explicit optical anchor override (normalized 0..1, default is center [0.5, 0.5]) */
  opticalAnchor?: { x: number; y: number };
  /** Depth factor for parallax layering: FG > 1.0, MG = 1.0, BG < 1.0 */
  depthMultiplier?: number;
  /** Disable organic breathing drift during hold frames */
  disableDrift?: boolean;
}

/**
 * CameraRig — Deterministic 2.5D Cinematography Rig for Vox Explainer.
 * Implements the 4 Golden Cinematography Laws from Senior Directorial Council:
 * 1. Optical Rest Anchor: pins gaze fixation to the primary hero subject.
 * 2. Velocity Budget & Asymmetric Deceleration: 30% acc, 70% dec, ends in steady hold (v=0).
 * 3. Motivated Kinematics: natural reaction lag (2-4 frames) after physical contact.
 * 4. Spatial Horizon: strictly zero in-shot camera roll; rolls are static subtle rakes (-5..5 deg).
 */
export const CameraRig: React.FC<CameraRigProps> = ({
  children,
  presetId = 1,
  preset: customPreset,
  opticalAnchor = { x: 0.5, y: 0.5 },
  depthMultiplier = 1.0,
  disableDrift = false,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames, width, height } = useVideoConfig();

  const activePreset: MotionPreset =
    customPreset ||
    CANONICAL_MOTION_PRESETS[presetId] ||
    CANONICAL_MOTION_PRESETS[1];

  const {
    from,
    to,
    holdInFrames,
    holdOutFrames,
    reactDelayFrames,
    settle,
    driftAmplitude,
    tier,
  } = activePreset;

  const motionStart = Math.max(0, holdInFrames + reactDelayFrames);
  const motionEnd = Math.max(motionStart + 1, durationInFrames - holdOutFrames);
  const motionFrames = motionEnd - motionStart;

  // Velocity Budget Enforcement (Rule 122 & Law 2)
  const maxDisplacement = Math.hypot(to.cx - from.cx, to.cy - from.cy);
  const maxAllowedSpeed = SPEED_BUDGET[tier as MotionTier] || 0.15; // fraction of width/sec
  const minRequiredFrames = Math.round((maxDisplacement / maxAllowedSpeed) * fps);
  const effectiveMotionFrames = Math.max(motionFrames, minRequiredFrames, 12);

  // Compute interpolation progress [0..1]
  let progress = 0;

  if (frame <= motionStart) {
    progress = 0;
  } else if (frame >= motionEnd) {
    progress = 1;
  } else {
    const elapsed = frame - motionStart;
    if (settle === "spring") {
      progress = spring({
        frame: elapsed,
        fps,
        config: {
          damping: 200,
          stiffness: 120,
          mass: 1,
        },
      });
      // Clamp overshoot to strictly [0..1] to prevent vertigo bounce
      progress = Math.min(Math.max(progress, 0), 1);
    } else {
      // Asymmetric deceleration: 30% acceleration, 70% deceleration
      progress = interpolate(elapsed, [0, effectiveMotionFrames], [0, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
        easing: Easing.bezier(0.3, 0, 0, 1),
      });
    }
  }

  // Interpolate camera pose
  const currentCx = from.cx + (to.cx - from.cx) * progress;
  const currentCy = from.cy + (to.cy - from.cy) * progress;
  const currentZoom = from.zoom + (to.zoom - from.zoom) * progress;
  const currentRoll = from.roll + (to.roll - from.roll) * progress;

  // Translation based on optical rest anchor and camera center
  // Positive delta cx shifts content in opposite direction
  const transX = -(currentCx - opticalAnchor.x) * width * depthMultiplier;
  const transY = -(currentCy - opticalAnchor.y) * height * depthMultiplier;

  // Micro-drift organic breathing on twos (12fps step-like vibration)
  let driftX = 0;
  let driftY = 0;
  if (!disableDrift) {
    // Quantize frame to twos (12fps) for stop-motion feeling
    const quantizedFrame = Math.floor(frame / 2.5);
    const wave1 = Math.sin(quantizedFrame * 0.12);
    const wave2 = Math.cos(quantizedFrame * 0.08);
    driftX = wave1 * driftAmplitude * width * depthMultiplier;
    driftY = wave2 * driftAmplitude * height * depthMultiplier;
  }

  const finalTransX = transX + driftX;
  const finalTransY = transY + driftY;

  return (
    <AbsoluteFill
      style={{
        transform: `translate3d(${finalTransX.toFixed(2)}px, ${finalTransY.toFixed(2)}px, 0) scale(${currentZoom.toFixed(4)}) rotate(${currentRoll.toFixed(2)}deg)`,
        transformOrigin: `${(opticalAnchor.x * 100).toFixed(1)}% ${(opticalAnchor.y * 100).toFixed(1)}%`,
        willChange: "transform",
      }}
    >
      {children}
    </AbsoluteFill>
  );
};
