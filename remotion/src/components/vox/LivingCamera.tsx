import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig, Easing } from "remotion";

export type CameraIntent =
  | "reveal"
  | "compare"
  | "focus"
  | "push"
  | "pull"
  | "pan_left"
  | "pan_right"
  | "snap_focus"
  | "document_inspect"
  | "whip_transition";

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
 * Upgraded with Narrative-Intent Camera Windows (Reveal, Compare, Focus, Snap-Focus, Document-Inspect)
 * and authentic 2.5D Parallax depth scaling (FG: 1.3x, BG: 0.7x).
 */
export const LivingCamera: React.FC<LivingCameraProps> = ({
  children,
  sceneIndex = 0,
  from = 1.0,
  to = 1.022,
  driftX = 3.5, // Calibrated to Vox Masterclass: max 2-4px subtle organic micro-drift
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
    (sceneIndex % 5 === 0
      ? "reveal"
      : sceneIndex % 5 === 1
      ? "snap_focus"
      : sceneIndex % 5 === 2
      ? "focus"
      : sceneIndex % 5 === 3
      ? "document_inspect"
      : "compare");

  // Smooth organic easing curve (Rule 122 Cinematic Standard)
  const t = interpolate(frame, [0, Math.max(1, durationInFrames)], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.cubic),
  });

  // Parallax motion multipliers (subtle paper depth)
  const parallaxMultiplier =
    parallaxLayer === "fg" ? 1.15 : parallaxLayer === "bg" ? 0.85 : 1.0;

  let scale = from;
  let x = 0;
  let y = 0;
  let rotateX = 0;
  let rotateY = 0;

  switch (mode) {
    case "snap_focus":
      // Rapid impact snap-zoom into evidence in first 6 frames, then permanently locked
      const snapT = interpolate(frame, [0, 6], [0, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
        easing: Easing.bezier(0.16, 1, 0.3, 1),
      });
      scale = from + (1.05 - from) * snapT;
      x = (driftX * 0.3 * (t - 0.5)) * parallaxMultiplier;
      y = (-1.5 * t) * parallaxMultiplier;
      break;

    case "document_inspect":
      // Tactical archival inspection with subtle 3D tilt perspective (< 1 deg)
      scale = from + (to - from) * 0.6 * t;
      rotateX = interpolate(frame, [0, 12], [0, 0.8], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      });
      rotateY = interpolate(frame, [0, 15], [0, -0.6], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      });
      x = (driftX * 0.4 * (0.5 - t)) * parallaxMultiplier;
      break;

    case "whip_transition":
      // Subtle fast editorial transition
      const whipT = interpolate(frame, [0, 8], [0, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
        easing: Easing.bezier(0.25, 0.1, 0.25, 1),
      });
      scale = from + 0.015 * (1 - whipT);
      x = (driftX * (1 - whipT)) * parallaxMultiplier;
      break;

    case "reveal":
      // Left-to-Right panoramic reveal (< 3px drift)
      scale = from + (to - from) * 0.5 * t;
      x = (driftX * (0.5 - t)) * parallaxMultiplier;
      break;

    case "compare":
      // Right-to-Left evidentiary counter-pan (< 3px drift)
      scale = from + (to - from) * 0.5 * t;
      x = (-driftX * (0.5 - t)) * parallaxMultiplier;
      break;

    case "focus":
      // Center push-in with macro focus
      scale = from + (to - from) * t;
      x = (driftX * 0.2 * (t - 0.5)) * parallaxMultiplier;
      y = (-2 * t) * parallaxMultiplier;
      break;

    case "push":
      scale = from + (to - from) * t;
      x = (driftX * 0.3 * (t - 0.5)) * parallaxMultiplier;
      break;

    case "pull":
      scale = to - (to - from) * t;
      x = (-driftX * 0.3 * (t - 0.5)) * parallaxMultiplier;
      break;

    case "pan_left":
      scale = from + (to - from) * 0.3;
      x = (driftX * (0.5 - t)) * parallaxMultiplier;
      break;

    case "pan_right":
    default:
      scale = from + (to - from) * 0.3;
      x = (-driftX * (0.5 - t)) * parallaxMultiplier;
      break;
  }

  const rotStr = rotateX !== 0 || rotateY !== 0 ? ` perspective(1000px) rotateX(${rotateX.toFixed(2)}deg) rotateY(${rotateY.toFixed(2)}deg)` : "";

  return (
    <AbsoluteFill
      style={{
        transform: `translate3d(${x.toFixed(2)}px, ${y.toFixed(2)}px, 0) scale(${scale.toFixed(4)})${rotStr}`,
        transformOrigin: "center center",
        willChange: "transform",
      }}
    >
      {children}
    </AbsoluteFill>
  );
};

