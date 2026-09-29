import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig, Easing } from "remotion";

export type CameraIntent = "reveal" | "compare" | "focus" | "push" | "pull" | "pan_left" | "pan_right";

export interface LivingCameraProps {
  children: React.ReactNode;
  sceneIndex?: number;
  from?: number;
  to?: number;
  driftX?: number;
  direction?: CameraIntent;
  windowMode?: CameraIntent;
  parallaxLayer?: "bg" | "fg" | "none";
  plateWidth?: number;
}

/**
 * LivingCamera Wrapper (Vox Masterclass Standard)
 * Upgraded with Narrative-Intent Camera Windows (Reveal, Compare, Focus)
 * and authentic 2.5D Parallax depth scaling (FG: 1.3x, BG: 0.7x).
 */
export const LivingCamera: React.FC<LivingCameraProps> = ({
  children,
  sceneIndex = 0,
  from = 1.0,
  to = 1.08,
  driftX = 140, // Upgraded from 12px micro-jitter to authentic Vox camera travel
  direction,
  windowMode,
  parallaxLayer = "none",
}) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  // Intent resolution: prioritize explicit windowMode, then direction, then rhythmic rotation
  const mode: CameraIntent =
    windowMode ||
    direction ||
    (sceneIndex % 4 === 0
      ? "reveal"
      : sceneIndex % 4 === 1
      ? "focus"
      : sceneIndex % 4 === 2
      ? "compare"
      : "pull");

  // Smooth organic easing curve (Rule 122 Cinematic Standard)
  const t = interpolate(frame, [0, Math.max(1, durationInFrames)], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.cubic),
  });

  // Parallax motion multipliers
  const parallaxMultiplier =
    parallaxLayer === "fg" ? 1.3 : parallaxLayer === "bg" ? 0.7 : 1.0;

  let scale = from;
  let x = 0;
  let y = 0;

  switch (mode) {
    case "reveal":
      // Window A: Left-to-Right panoramic reveal
      scale = from + (to - from) * 0.3 * t;
      x = (driftX * (0.5 - t)) * parallaxMultiplier;
      break;

    case "compare":
      // Window B: Right-to-Left evidentiary counter-pan
      scale = from + (to - from) * 0.3 * t;
      x = (-driftX * (0.5 - t)) * parallaxMultiplier;
      break;

    case "focus":
      // Window C: Center push-in with macro focus
      scale = from + (to * 1.15 - from) * t;
      x = (driftX * 0.2 * (t - 0.5)) * parallaxMultiplier;
      y = (-20 * t) * parallaxMultiplier;
      break;

    case "push":
      scale = from + (to - from) * t;
      x = (driftX * 0.4 * (t - 0.5)) * parallaxMultiplier;
      break;

    case "pull":
      scale = to - (to - from) * t;
      x = (-driftX * 0.4 * (t - 0.5)) * parallaxMultiplier;
      break;

    case "pan_left":
      scale = from + (to - from) * 0.4;
      x = (driftX * (0.5 - t)) * parallaxMultiplier;
      break;

    case "pan_right":
    default:
      scale = from + (to - from) * 0.4;
      x = (-driftX * (0.5 - t)) * parallaxMultiplier;
      break;
  }

  return (
    <AbsoluteFill
      style={{
        transform: `translate3d(${x.toFixed(2)}px, ${y.toFixed(2)}px, 0) scale(${scale.toFixed(4)})`,
        transformOrigin: "center center",
        willChange: "transform",
      }}
    >
      {children}
    </AbsoluteFill>
  );
};

