import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";

/**
 * VoxParallaxLayer - 2.5D Multi-Plane Parallax Depth Container.
 * Creates documentary stereoscopic depth akin to BBC/Netflix and Veo 2:
 * - Depth Planes:
 *   * "background" : 0.8x motion dampening (distant canvas feel)
 *   * "midground"  : 1.0x baseline (evidence props, documents, maps)
 *   * "foreground" : 1.25x enhanced motion (character cutouts pop forward)
 * - Frame-driven, zero external dependencies, 100% stable on headless Linux CPU.
 */
export type ParallaxDepth = "background" | "midground" | "foreground";

export const VoxParallaxLayer: React.FC<{
  depth: ParallaxDepth;
  cameraMovement?: string;
  durationInFrames: number;
  children: React.ReactNode;
}> = ({ depth, cameraMovement = "slow_push_in", durationInFrames, children }) => {
  const frame = useCurrentFrame();
  const dur = Math.max(1, durationInFrames);

  // Parallax scale multiplier per plane
  const depthFactor = depth === "background" ? 0.8 : depth === "foreground" ? 1.25 : 1.0;

  // Compute slight differential translation based on camera movement
  let offsetX = 0;
  let offsetY = 0;
  let scaleAdjust = 1.0;

  if (cameraMovement === "cinematic_pan") {
    offsetX = interpolate(frame, [0, dur], [-18 * depthFactor, 18 * depthFactor], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
  } else if (cameraMovement === "macro_tilt") {
    offsetY = interpolate(frame, [0, dur], [-12 * depthFactor, 12 * depthFactor], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
  } else if (cameraMovement === "slow_push_in" || cameraMovement === "snap_zoom") {
    scaleAdjust = interpolate(frame, [0, dur], [1.0, 1.0 + 0.035 * depthFactor], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
  } else if (cameraMovement === "slow_pull_out") {
    scaleAdjust = interpolate(frame, [0, dur], [1.0 + 0.035 * depthFactor, 1.0], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
  }

  return (
    <AbsoluteFill
      style={{
        transform: `translate(${offsetX.toFixed(2)}px, ${offsetY.toFixed(2)}px) scale(${scaleAdjust.toFixed(3)})`,
        transformOrigin: "center center",
        pointerEvents: "none",
      }}
    >
      {children}
    </AbsoluteFill>
  );
};
