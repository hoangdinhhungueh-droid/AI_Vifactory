import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame } from "remotion";

/**
 * VoxParallaxLayer - Advanced 3D Multi-Plane Parallax Depth Container.
 * Creates authentic stereoscopic Vox paper-collage diorama depth:
 * - 5 Depth Planes:
 *   * "deep_background"  : 0.40x motion (distant cadastral maps, blueprints, shallow DoF blur)
 *   * "background"       : 0.70x motion (archival desk, newsprint broadsheets)
 *   * "midground"        : 1.00x baseline focal plane (primary exhibits, ledgers, dossiers)
 *   * "foreground"       : 1.38x enhanced motion (tactile tools, character cutouts, stamps, calipers)
 *   * "macro_foreground" : 1.70x extreme foreground (passing lens rims, magnifying glass, macro edge)
 * - Tactile 12fps Stop-Motion Stepping ("on twos") for authentic physical papercraft feel.
 * - Dynamic 3D lighting drop shadow based on camera perspective.
 * - Optical Depth of Field (DoF) shallow softness.
 * - Zero external dependencies, 100% deterministic on headless Linux CPU.
 */
export type ParallaxDepth =
  | "deep_background"
  | "background"
  | "midground"
  | "foreground"
  | "macro_foreground";

export const VoxParallaxLayer: React.FC<{
  depth: ParallaxDepth;
  cameraMovement?: string;
  durationInFrames: number;
  children: React.ReactNode;
  style?: React.CSSProperties;
  stopMotion?: boolean;
  enableDepthOfField?: boolean;
}> = ({
  depth,
  cameraMovement = "slow_push_in",
  durationInFrames,
  children,
  style,
  stopMotion = true,
  enableDepthOfField = false,
}) => {
  const rawFrame = useCurrentFrame();
  const dur = Math.max(1, durationInFrames);

  // Tactile Stop-Motion Stepping ("on twos" 12fps at 24/30fps) for authentic papercraft diorama
  const frame = stopMotion ? Math.floor(rawFrame / 2) * 2 : rawFrame;

  // Parallax physical metrics per depth tier
  const depthFactor =
    depth === "deep_background"
      ? 0.40
      : depth === "background"
      ? 0.70
      : depth === "midground"
      ? 1.00
      : depth === "foreground"
      ? 1.38
      : 1.70; // macro_foreground

  const cam = (cameraMovement || "slow_push_in").toLowerCase().trim();
  const isLocked = cam === "locked" || cam === "static" || cam === "none";

  const zPlane = isLocked
    ? 0
    : depth === "deep_background"
    ? -140
    : depth === "background"
    ? -80
    : depth === "midground"
    ? 0
    : depth === "foreground"
    ? 70
    : 130; // macro_foreground

  // Optical Depth of Field (DoF) shallow blur
  const dofBlur = enableDepthOfField
    ? depth === "deep_background"
      ? 1.2
      : depth === "background"
      ? 0.5
      : depth === "macro_foreground"
      ? 0.8
      : 0
    : 0;

  // Compute 3D differential translation & rotation
  let offsetX = 0;
  let offsetY = 0;
  let rotX = 0;
  let rotY = 0;
  let scaleAdjust = 1.0;

  if (cam === "cinematic_pan") {
    offsetX = interpolate(frame, [0, dur], [-26 * depthFactor, 26 * depthFactor], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    rotY = interpolate(
      frame,
      [0, dur],
      [depthFactor > 1.0 ? -2.0 : 0.9, depthFactor > 1.0 ? 2.0 : -0.9],
      { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
    );
  } else if (cam === "lateral_parallax_pan" || cam === "parallax_left") {
    // Left-to-right differential tracking: FG moves fast, BG moves slow
    offsetX = interpolate(frame, [0, dur], [32 * depthFactor, -32 * depthFactor], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    rotY = interpolate(
      frame,
      [0, dur],
      [depthFactor > 1.0 ? -2.2 : 0.8, depthFactor > 1.0 ? 2.2 : -0.8],
      { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
    );
  } else if (cam === "parallax_right") {
    // Right-to-left differential tracking
    offsetX = interpolate(frame, [0, dur], [-32 * depthFactor, 32 * depthFactor], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    rotY = interpolate(
      frame,
      [0, dur],
      [depthFactor > 1.0 ? 2.2 : -0.8, depthFactor > 1.0 ? -2.2 : 0.8],
      { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
    );
  } else if (cam === "macro_tilt") {
    offsetY = interpolate(frame, [0, dur], [-18 * depthFactor, 18 * depthFactor], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    rotX = interpolate(
      frame,
      [0, dur],
      [depthFactor > 1.0 ? 1.6 : -0.8, depthFactor > 1.0 ? -1.6 : 0.8],
      { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
    );
  } else if (cam === "slow_push_in" || cam === "snap_zoom" || cam === "dramatic_push") {
    const pushAmount = cam === "dramatic_push" ? 0.075 : 0.045;
    scaleAdjust = interpolate(frame, [0, dur], [1.0, 1.0 + pushAmount * depthFactor], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    if (cam === "dramatic_push") {
      offsetY = interpolate(frame, [0, dur], [0, -10 * depthFactor], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      });
    }
  } else if (cam === "slow_pull_out") {
    scaleAdjust = interpolate(frame, [0, dur], [1.0 + 0.045 * depthFactor, 1.0], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
  } else if (cam === "continuous_drift" || cam === "subtle_drift") {
    offsetX = interpolate(frame, [0, dur], [-18 * depthFactor, 18 * depthFactor], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    offsetY = interpolate(frame, [0, dur], [-8 * depthFactor, 8 * depthFactor], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    rotY = interpolate(
      frame,
      [0, dur],
      [depthFactor > 1.0 ? -1.4 : 0.7, depthFactor > 1.0 ? 1.4 : -0.7],
      { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
    );
    scaleAdjust = interpolate(frame, [0, dur], [1.0, 1.0 + 0.035 * depthFactor], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
  } else if (cam === "seamless_whip_pan" || cam === "split_whip") {
    const whipFrames = Math.min(8, Math.round(dur * 0.25));
    offsetX = interpolate(frame, [0, whipFrames, dur], [48 * depthFactor, 0, -12 * depthFactor], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    rotY = interpolate(frame, [0, whipFrames, dur], [-3.2 * depthFactor, 0, 1.0 * depthFactor], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
  } else if (cam === "macro_orbit" || cam === "cinematic_orbit") {
    const angle = (frame / dur) * Math.PI * 0.75;
    offsetX = Math.sin(angle) * 22 * depthFactor;
    offsetY = (1 - Math.cos(angle)) * 11 * depthFactor;
    rotY = Math.sin(angle) * (depthFactor > 1.0 ? 2.4 : -1.1);
    rotX = (1 - Math.cos(angle)) * (depthFactor > 1.0 ? -1.4 : 0.7);
    scaleAdjust = interpolate(frame, [0, dur], [1.0, 1.0 + 0.04 * depthFactor], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
  } else if (cam === "high_angle_diorama") {
    rotX = interpolate(frame, [0, dur], [9, 13], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    offsetY = interpolate(frame, [0, dur], [-12 * depthFactor, 12 * depthFactor], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
  } else if (cam === "forensic_lock") {
    // Subtle living breathing hold
    scaleAdjust = interpolate(frame, [0, dur], [1.0, 1.0 + 0.018 * depthFactor], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
  }

  // Dynamic 3D lighting drop shadow for elevated layers (foreground & macro_foreground)
  let dynamicShadow: string | undefined = undefined;
  if (depth === "foreground" || depth === "macro_foreground") {
    const sX = (-offsetX * 0.25).toFixed(1);
    const sY = (depth === "macro_foreground" ? 18 : 12 + offsetY * 0.15).toFixed(1);
    const sBlur = depth === "macro_foreground" ? 28 : 20;
    const sOpacity = depth === "macro_foreground" ? 0.38 : 0.30;
    dynamicShadow = `drop-shadow(${sX}px ${sY}px ${sBlur}px rgba(0,0,0,${sOpacity}))`;
  }

  const combinedFilter = [dofBlur > 0 ? `blur(${dofBlur}px)` : null, dynamicShadow]
    .filter(Boolean)
    .join(" ");

  return (
    <AbsoluteFill
      style={{
        transform: isLocked
          ? "none"
          : `perspective(1200px) translate3d(${offsetX.toFixed(2)}px, ${offsetY.toFixed(2)}px, ${zPlane}px) rotateX(${rotX.toFixed(2)}deg) rotateY(${rotY.toFixed(2)}deg) scale(${scaleAdjust.toFixed(3)})`,
        transformOrigin: "center center",
        transformStyle: isLocked ? undefined : "preserve-3d",
        filter: combinedFilter || undefined,
        pointerEvents: "none",
        ...style,
      }}
    >
      {children}
    </AbsoluteFill>
  );
};
