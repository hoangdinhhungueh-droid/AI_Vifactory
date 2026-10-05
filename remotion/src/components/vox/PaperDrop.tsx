import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { useStopMotion } from "./useStopMotion";

export interface PaperDropProps {
  children: React.ReactNode;
  dropFrame?: number;
  baseRotation?: number;
  seed?: number;
  stopFps?: number;
  jitterPx?: number;
  style?: React.CSSProperties;
  useShadowFilter?: boolean;
}

/**
 * Physical Paper Drop Wrapper (Vox Tabletop Collage Physics)
 * Simulates an evidence clipping or cutout dropping onto a corkboard/tabletop:
 * - Scale decelerates from 1.14 -> 1.0
 * - Shadow tightens from diffused aerial shadow to crisp tabletop contact shadow
 * - Settles into 12fps stepped stop-motion micro-life
 */
export const PaperDrop: React.FC<PaperDropProps> = ({
  children,
  dropFrame = 0,
  baseRotation = 0,
  seed = 1,
  stopFps = 12,
  jitterPx = 0.85,
  style,
  useShadowFilter = true,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { dx, dy, dRot } = useStopMotion(stopFps, jitterPx, seed);

  const relFrame = frame - dropFrame;
  if (relFrame < 0) return null;

  const p = spring({
    frame: relFrame,
    fps: fps || 30,
    config: { damping: 14, stiffness: 135, mass: 0.72 },
  });

  const scale = interpolate(p, [0, 1], [1.14, 1.0]);
  const translateY = interpolate(p, [0, 1], [-42, 0]);
  const rot = interpolate(p, [0, 1], [baseRotation - 4.5, baseRotation]);
  const opacity = interpolate(relFrame, [0, 4], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Shrinking shadow physics as paper contacts tabletop
  const shadowY = Math.round(interpolate(p, [0, 1], [28, 9]));
  const shadowBlur = Math.round(interpolate(p, [0, 1], [34, 14]));
  const shadowAlpha = interpolate(p, [0, 1], [0.22, 0.44]).toFixed(2);

  const landedWeight = relFrame > 14 ? 1 : 0;
  const finalX = dx * landedWeight;
  const finalY = translateY + dy * landedWeight;
  const finalRot = rot + dRot * landedWeight;

  return (
    <div
      style={{
        ...style,
        opacity,
        transform: `${style?.transform ? style.transform + " " : ""}translate(${finalX.toFixed(1)}px, ${finalY.toFixed(1)}px) scale(${scale.toFixed(3)}) rotate(${finalRot.toFixed(2)}deg)`,
        filter: useShadowFilter
          ? `drop-shadow(0 ${shadowY}px ${shadowBlur}px rgba(35, 22, 10, ${shadowAlpha}))`
          : style?.filter,
      }}
    >
      {children}
    </div>
  );
};
