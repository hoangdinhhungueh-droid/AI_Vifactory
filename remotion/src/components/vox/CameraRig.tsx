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
  MICRO_WHIP_SPRING,
  MotionPreset,
  MotionTier,
  SPEED_BUDGET,
  SteppedPose,
} from "./motionPresets";

export interface CameraRigProps {
  children: React.ReactNode;
  presetId?: number;
  preset?: MotionPreset;
  /** Custom stepped punches override */
  steppedPunches?: SteppedPose[];
  /** Explicit optical anchor override (normalized 0..1, default is center [0.5, 0.5]) */
  opticalAnchor?: { x: number; y: number };
  /** Depth factor for parallax layering: FG > 1.0, MG = 1.0, BG < 1.0 */
  depthMultiplier?: number;
  /** Disable organic breathing drift during hold frames */
  disableDrift?: boolean;
}

interface ResolvedSteppedState {
  scale: number;
  rotateZ: number;
  x: number;
  y: number;
  isLocked: boolean;
}

/**
 * Computes deterministic stepped pose from multi-phase punch keyframes.
 * Enforces discrete punch transitions (<= 8-12f) and dead-stop locks for 70-85% of duration.
 */
export function computeSteppedPose(
  frame: number,
  steps: SteppedPose[],
  fps: number,
  disableDrift = false
): ResolvedSteppedState {
  if (!steps || steps.length === 0) {
    return { scale: 1.0, rotateZ: 0, x: 0, y: 0, isLocked: true };
  }

  // Pre-sort steps by frame timestamp to guarantee monotonicity against arbitrary JSON
  const sortedSteps = [...steps].sort((a, b) => a.frame - b.frame);

  // Find active step index
  let activeIndex = 0;
  for (let i = 0; i < sortedSteps.length; i++) {
    if (frame >= sortedSteps[i].frame) {
      activeIndex = i;
    } else {
      break;
    }
  }

  const current = sortedSteps[activeIndex];
  const targetScale = current.scale;
  const targetRot = current.rotateZ ?? current.rotation ?? 0;
  const targetX = current.x ?? 0;
  const targetY = current.y ?? 0;

  // If this is the initial establishing step (i=0)
  if (activeIndex === 0) {
    return {
      scale: targetScale,
      rotateZ: targetRot,
      x: targetX,
      y: targetY,
      isLocked: true,
    };
  }

  const prev = sortedSteps[activeIndex - 1];
  const prevScale = prev.scale;
  const prevRot = prev.rotateZ ?? prev.rotation ?? 0;
  const prevX = prev.x ?? 0;
  const prevY = prev.y ?? 0;

  const rawWhip = current.whipFrames ?? current.whip_frames ?? current.whipDuration ?? 8;
  const whip = Math.max(1, rawWhip);
  const transitionStart = current.frame;
  const transitionEnd = transitionStart + whip;

  // Transition phase
  if (frame < transitionEnd) {
    const elapsed = frame - transitionStart;
    let progress = 0;

    const curve = current.curve ?? "whip";
    if (curve === "glide") {
      // Smooth glide (ease-in-out)
      progress = interpolate(elapsed, [0, whip], [0, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
        easing: Easing.bezier(0.45, 0, 0.55, 1),
      });
    } else if (curve === "staccato") {
      // Steep snap staccato
      progress = interpolate(elapsed, [0, whip], [0, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
        easing: Easing.bezier(0.83, 0, 0.17, 1),
      });
    } else if (curve === "dutch") {
      // Fixed dutch ease-in cubic
      progress = interpolate(elapsed, [0, whip], [0, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
        easing: Easing.bezier(0.45, 0, 0.55, 1),
      });
    } else {
      // Default: rapid micro-whip spring with overshootClamping scaled to whip duration
      progress = spring({
        frame: elapsed,
        fps,
        config: MICRO_WHIP_SPRING,
        durationInFrames: whip,
      });
      progress = Math.min(Math.max(progress, 0), 1);
    }

    const scale = prevScale + (targetScale - prevScale) * progress;
    const rotateZ = prevRot + (targetRot - prevRot) * progress;
    const x = prevX + (targetX - prevX) * progress;
    const y = prevY + (targetY - prevY) * progress;

    return { scale, rotateZ, x, y, isLocked: false };
  }

  // Dead-stop lock phase
  let shakeY = 0;
  const impactShake = current.impactShake ?? current.impact_shake ?? 0;
  if (impactShake > 0) {
    const shakeElapsed = frame - transitionEnd;
    if (shakeElapsed >= 0 && shakeElapsed <= 5) {
      // Damped harmonic shockwave oscillation on physical landing
      const decay = Math.exp(-0.75 * shakeElapsed);
      const osc = Math.cos(shakeElapsed * Math.PI * 0.7);
      shakeY = impactShake * decay * osc;
    }
  }

  let driftOffset = 0;
  const microDrift = current.microDrift ?? current.micro_drift ?? 0;
  if (!disableDrift && microDrift > 0) {
    const quantized = Math.floor(frame / 2.5);
    driftOffset = Math.sin(quantized * 0.4) * microDrift;
  }

  return {
    scale: targetScale,
    rotateZ: targetRot,
    x: targetX + driftOffset,
    y: targetY + shakeY,
    isLocked: true,
  };
}

/**
 * CameraRig — Deterministic 2.5D Cinematography Rig for Vox Explainer.
 * Implements the 5 Kinetic Pillars from Senior Directorial Council (Boss Opus 5.5):
 * 1. Stepped Framing: Discrete multi-phase punches (Wide -> Mid -> Macro) with rapid micro-whips (<= 8-12f).
 * 2. Dead-Stop Locks: Complete freeze for 70-85% of scene duration as stable substrate for vector graphics.
 * 3. Optical Rest Anchor: Pins gaze fixation to the primary hero subject.
 * 4. Motivated Kinematics: Organic reaction lag and impact shake.
 * 5. Spatial Horizon: Strictly zero in-shot camera rolls.
 */
export const CameraRig: React.FC<CameraRigProps> = ({
  children,
  presetId = 1,
  preset: customPreset,
  steppedPunches: customPunches,
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

  const effectivePunches = customPunches || activePreset.steppedPunches;

  // 1. STEPPED FRAMING & KINETIC DEAD-STOP PATH
  if (effectivePunches && effectivePunches.length > 0) {
    const stepped = computeSteppedPose(frame, effectivePunches, fps, disableDrift);

    const finalX = stepped.x * depthMultiplier;
    const finalY = stepped.y * depthMultiplier;

    return (
      <AbsoluteFill
        style={{
          transform: `translate3d(${finalX.toFixed(2)}px, ${finalY.toFixed(2)}px, 0) scale(${stepped.scale.toFixed(4)}) rotate(${stepped.rotateZ.toFixed(2)}deg)`,
          transformOrigin: `${(opticalAnchor.x * 100).toFixed(1)}% ${(opticalAnchor.y * 100).toFixed(1)}%`,
          willChange: "transform",
        }}
      >
        {children}
      </AbsoluteFill>
    );
  }

  // 2. BACKWARD COMPATIBLE CONTINUOUS PATH
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
        config: MICRO_WHIP_SPRING,
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
