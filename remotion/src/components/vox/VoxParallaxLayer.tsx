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
  style?: React.CSSProperties;
}> = ({ depth, cameraMovement = "slow_push_in", durationInFrames, children, style }) => {
  const frame = useCurrentFrame();
  const dur = Math.max(1, durationInFrames);

  // Parallax scale multiplier per plane
  // background: distant plane (0.72x motion, pushed back in Z)
  // midground: neutral focal plane (1.0x motion, Z=0)
  // foreground: hero plane (1.35x motion, popped forward in Z)
  const depthFactor = depth === "background" ? 0.72 : depth === "foreground" ? 1.35 : 1.0;
  const zPlane = depth === "background" ? -80 : depth === "foreground" ? 60 : 0;

  // Compute slight differential translation based on camera movement
  let offsetX = 0;
  let offsetY = 0;
  let rotX = 0;
  let rotY = 0;
  let scaleAdjust = 1.0;

  if (cameraMovement === "cinematic_pan") {
    offsetX = interpolate(frame, [0, dur], [-24 * depthFactor, 24 * depthFactor], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    rotY = interpolate(frame, [0, dur], [depth === "foreground" ? -1.8 : 0.8, depth === "foreground" ? 1.8 : -0.8], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
  } else if (cameraMovement === "macro_tilt") {
    offsetY = interpolate(frame, [0, dur], [-16 * depthFactor, 16 * depthFactor], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    rotX = interpolate(frame, [0, dur], [depth === "foreground" ? 1.4 : -0.7, depth === "foreground" ? -1.4 : 0.7], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
  } else if (cameraMovement === "slow_push_in" || cameraMovement === "snap_zoom") {
    scaleAdjust = interpolate(frame, [0, dur], [1.0, 1.0 + 0.045 * depthFactor], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
  } else if (cameraMovement === "slow_pull_out") {
    scaleAdjust = interpolate(frame, [0, dur], [1.0 + 0.045 * depthFactor, 1.0], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
  } else if (cameraMovement === "continuous_drift") {
    offsetX = interpolate(frame, [0, dur], [-18 * depthFactor, 18 * depthFactor], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    offsetY = interpolate(frame, [0, dur], [-8 * depthFactor, 8 * depthFactor], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    rotY = interpolate(frame, [0, dur], [depth === "foreground" ? -1.2 : 0.6, depth === "foreground" ? 1.2 : -0.6], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    scaleAdjust = interpolate(frame, [0, dur], [1.0, 1.0 + 0.035 * depthFactor], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
  } else if (cameraMovement === "seamless_whip_pan") {
    offsetX = interpolate(frame, [0, 6, dur], [42 * depthFactor, 0, -12 * depthFactor], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    rotY = interpolate(frame, [0, 6, dur], [-3.0 * depthFactor, 0, 1.0 * depthFactor], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
  } else if (cameraMovement === "macro_orbit" || cameraMovement === "cinematic_orbit") {
    const angle = (frame / dur) * Math.PI * 0.75;
    offsetX = Math.sin(angle) * 20 * depthFactor;
    offsetY = (1 - Math.cos(angle)) * 10 * depthFactor;
    rotY = Math.sin(angle) * (depth === "foreground" ? 2.2 : -1.0);
    rotX = (1 - Math.cos(angle)) * (depth === "foreground" ? -1.2 : 0.6);
    scaleAdjust = interpolate(frame, [0, dur], [1.0, 1.0 + 0.04 * depthFactor], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
  }

  return (
    <AbsoluteFill
      style={{
        transform: `perspective(1200px) translate3d(${offsetX.toFixed(2)}px, ${offsetY.toFixed(2)}px, ${zPlane}px) rotateX(${rotX.toFixed(2)}deg) rotateY(${rotY.toFixed(2)}deg) scale(${scaleAdjust.toFixed(3)})`,
        transformOrigin: "center center",
        transformStyle: "preserve-3d",
        pointerEvents: "none",
        ...style,
      }}
    >
      {children}
    </AbsoluteFill>
  );
};
