import React from "react";
import { useCurrentFrame, useVideoConfig, interpolate, spring, Easing } from "remotion";

export interface MotionWaypoint {
  frame: number;
  x_pct: number;       // 0 - 100% of canvas width (can be < 0 or > 100 for offscreen entrance/exit)
  y_pct: number;       // 0 - 100% of canvas height
  z_depth?: number;    // 0.2 (far back) to 1.5 (foreground hero close-up)
  scale?: number;      // Scale multiplier, default 1.0
  rot_deg?: number;    // Rotation in degrees, e.g. -5 to +5
  opacity?: number;    // Opacity 0 to 1, default 1.0
  easing?: "spring" | "spring_overshoot" | "bezier" | "anticipation" | "impact_slam" | "settle_lock" | "micro_breathing" | "linear";
}

export interface ProceduralMotionFollowerProps {
  motionPath?: MotionWaypoint[];
  width?: number;
  height?: number;
  zIndex?: number;
  children: React.ReactNode;
}

export const evaluateMotionPath = (
  waypoints: MotionWaypoint[] | undefined,
  currentFrame: number,
  fps: number = 30
): {
  xPct: number;
  yPct: number;
  scale: number;
  rotDeg: number;
  opacity: number;
  zDepth: number;
} => {
  if (!waypoints || waypoints.length === 0) {
    return { xPct: 50, yPct: 50, scale: 1.0, rotDeg: 0, opacity: 1.0, zDepth: 1.0 };
  }

  // Sort waypoints by frame
  const sorted = [...waypoints].sort((a, b) => a.frame - b.frame);

  // Before first waypoint
  if (currentFrame <= sorted[0].frame) {
    const first = sorted[0];
    return {
      xPct: first.x_pct,
      yPct: first.y_pct,
      scale: first.scale ?? 1.0,
      rotDeg: first.rot_deg ?? 0,
      opacity: first.opacity ?? 0,
      zDepth: first.z_depth ?? 1.0,
    };
  }

  // After last waypoint
  if (currentFrame >= sorted[sorted.length - 1].frame) {
    const last = sorted[sorted.length - 1];
    // Add subtle micro-breathing to prevent static dead freeze (Rule 122)
    const relEnd = currentFrame - last.frame;
    const breatheX = Math.sin(relEnd * 0.08) * 0.3;
    const breatheY = Math.cos(relEnd * 0.08) * 0.3;
    const breatheRot = Math.sin(relEnd * 0.05) * 0.15;
    const breatheScale = 1.0 + Math.sin(relEnd * 0.06) * 0.008;

    return {
      xPct: last.x_pct + breatheX,
      yPct: last.y_pct + breatheY,
      scale: (last.scale ?? 1.0) * breatheScale,
      rotDeg: (last.rot_deg ?? 0) + breatheRot,
      opacity: last.opacity ?? 1.0,
      zDepth: last.z_depth ?? 1.0,
    };
  }

  // Find active segment [p0, p1]
  let p0 = sorted[0];
  let p1 = sorted[1];
  for (let i = 0; i < sorted.length - 1; i++) {
    if (currentFrame >= sorted[i].frame && currentFrame <= sorted[i + 1].frame) {
      p0 = sorted[i];
      p1 = sorted[i + 1];
      break;
    }
  }

  const span = Math.max(1, p1.frame - p0.frame);
  const rel = currentFrame - p0.frame;
  const easingType = p1.easing || p0.easing || "spring";

  let progress = rel / span;

  if (easingType === "spring" || easingType === "spring_overshoot") {
    progress = spring({
      frame: rel,
      fps,
      config: {
        damping: easingType === "spring_overshoot" ? 10 : 14,
        stiffness: 120,
        mass: 0.6,
      },
    });
  } else if (easingType === "impact_slam") {
    progress = spring({
      frame: rel,
      fps,
      config: { damping: 9, stiffness: 220, mass: 0.4 },
    });
  } else if (easingType === "anticipation") {
    progress = interpolate(rel, [0, span], [0, 1], {
      easing: Easing.bezier(0.6, -0.28, 0.735, 0.045),
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
  } else if (easingType === "bezier" || easingType === "settle_lock") {
    progress = interpolate(rel, [0, span], [0, 1], {
      easing: Easing.bezier(0.16, 1, 0.3, 1),
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
  } else {
    progress = Math.min(1, Math.max(0, progress));
  }

  const xPct = p0.x_pct + (p1.x_pct - p0.x_pct) * progress;
  const yPct = p0.y_pct + (p1.y_pct - p0.y_pct) * progress;
  const s0 = p0.scale ?? 1.0;
  const s1 = p1.scale ?? 1.0;
  const scale = s0 + (s1 - s0) * progress;
  const r0 = p0.rot_deg ?? 0;
  const r1 = p1.rot_deg ?? 0;
  const rotDeg = r0 + (r1 - r0) * progress;
  const o0 = p0.opacity ?? 1.0;
  const o1 = p1.opacity ?? 1.0;
  const opacity = o0 + (o1 - o0) * Math.min(1, Math.max(0, rel / span));
  const z0 = p0.z_depth ?? 1.0;
  const z1 = p1.z_depth ?? 1.0;
  const zDepth = z0 + (z1 - z0) * progress;

  return { xPct, yPct, scale, rotDeg, opacity, zDepth };
};

export const ProceduralMotionFollower: React.FC<ProceduralMotionFollowerProps> = ({
  motionPath,
  width = 1920,
  height = 1080,
  zIndex = 15,
  children,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const { xPct, yPct, scale, rotDeg, opacity, zDepth } = evaluateMotionPath(
    motionPath,
    frame,
    fps
  );

  const xPx = (xPct / 100) * width;
  const yPx = (yPct / 100) * height;

  // Depth of field blur emulation (objects far away or very close blur slightly)
  const depthBlur = zDepth < 0.5 ? (0.5 - zDepth) * 6 : zDepth > 1.2 ? (zDepth - 1.2) * 4 : 0;

  return (
    <div
      style={{
        position: "absolute",
        left: 0,
        top: 0,
        transform: `translate3d(${xPx.toFixed(1)}px, ${yPx.toFixed(1)}px, 0) translate(-50%, -50%) rotate(${rotDeg.toFixed(2)}deg) scale(${scale.toFixed(3)})`,
        opacity: Math.max(0, Math.min(1, opacity)),
        zIndex,
        filter: depthBlur > 0.1 ? `blur(${depthBlur.toFixed(1)}px)` : undefined,
        willChange: "transform, opacity",
        pointerEvents: "none",
      }}
    >
      {children}
    </div>
  );
};
