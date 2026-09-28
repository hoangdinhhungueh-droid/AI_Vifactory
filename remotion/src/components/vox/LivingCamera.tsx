import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig, Easing } from "remotion";

export interface LivingCameraProps {
  children: React.ReactNode;
  sceneIndex?: number;
  from?: number;
  to?: number;
  driftX?: number;
  direction?: "push" | "pull" | "pan_left" | "pan_right";
}

/**
 * LivingCamera Wrapper (Vox Masterclass Standard)
 * Ensures no scene is ever a dead/static card. Provides continuous organic
 * push-in / pull-out and subtle parallax drift while keeping GPU composite light.
 */
export const LivingCamera: React.FC<LivingCameraProps> = ({
  children,
  sceneIndex = 0,
  from = 1.0,
  to = 1.05,
  driftX = 12,
  direction,
}) => {
  const frame = useCurrentFrame();
  const { durationInFrames } = useVideoConfig();

  // Alternate movement modes between scenes for rhythmic visual energy
  const mode = direction || (sceneIndex % 3 === 0 ? "push" : sceneIndex % 3 === 1 ? "pull" : "pan_left");

  const t = interpolate(frame, [0, Math.max(1, durationInFrames)], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.inOut(Easing.sin),
  });

  let scale = from;
  let x = 0;

  if (mode === "push") {
    scale = from + (to - from) * t;
    x = driftX * (t - 0.5);
  } else if (mode === "pull") {
    scale = to - (to - from) * t;
    x = -driftX * (t - 0.5);
  } else {
    // pan
    scale = from + (to - from) * 0.5;
    x = -driftX * (t - 0.5) * 1.5;
  }

  return (
    <AbsoluteFill
      style={{
        transform: `translate3d(${x.toFixed(2)}px, 0, 0) scale(${scale.toFixed(4)})`,
        transformOrigin: "center center",
        willChange: "transform",
      }}
    >
      {children}
    </AbsoluteFill>
  );
};
