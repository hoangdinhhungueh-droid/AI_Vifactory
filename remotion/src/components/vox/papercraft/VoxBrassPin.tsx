import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

export interface VoxBrassPinProps {
  x?: number | string;
  y?: number | string;
  size?: number;
  rotation?: number;
  color?: "brass" | "silver" | "crimson" | "black";
  dropFrame?: number;
  shadowDirection?: "bottom_right" | "bottom_left" | "bottom";
  className?: string;
  style?: React.CSSProperties;
}

export const VoxBrassPin: React.FC<VoxBrassPinProps> = ({
  x = 0,
  y = 0,
  size = 26,
  rotation = 0,
  color = "brass",
  dropFrame = 0,
  shadowDirection = "bottom_right",
  style,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const relFrame = Math.max(0, frame - dropFrame);
  const pinSpring = spring({
    frame: relFrame,
    fps,
    config: { damping: 10, mass: 0.35, stiffness: 220 },
  });

  const scale = dropFrame > 0 ? interpolate(pinSpring, [0, 1], [2.4, 1.0]) : 1.0;
  const opacity = dropFrame > 0 ? interpolate(pinSpring, [0, 0.2, 1], [0, 0.9, 1.0]) : 1.0;

  // Shadow vectors
  const shadowX = shadowDirection === "bottom_left" ? -4 : shadowDirection === "bottom" ? 0 : 5;
  const shadowY = 7;

  // Color schemes
  let headGradient = "radial-gradient(circle at 35% 32%, #fff9c4 0%, #fbc02d 38%, #b58104 70%, #5d4037 100%)";
  let ringGradient = "linear-gradient(135deg, #fef08a 0%, #b45309 100%)";

  if (color === "silver") {
    headGradient = "radial-gradient(circle at 35% 32%, #ffffff 0%, #cbd5e1 45%, #64748b 78%, #334155 100%)";
    ringGradient = "linear-gradient(135deg, #f1f5f9 0%, #475569 100%)";
  } else if (color === "crimson") {
    headGradient = "radial-gradient(circle at 35% 32%, #fca5a5 0%, #dc2626 45%, #991b1b 80%, #450a0a 100%)";
    ringGradient = "linear-gradient(135deg, #ef4444 0%, #7f1d1d 100%)";
  } else if (color === "black") {
    headGradient = "radial-gradient(circle at 35% 32%, #64748b 0%, #1e293b 50%, #0f172a 85%, #020617 100%)";
    ringGradient = "linear-gradient(135deg, #475569 0%, #0f172a 100%)";
  }

  const posX = typeof x === "number" ? `${x}px` : x;
  const posY = typeof y === "number" ? `${y}px` : y;

  return (
    <div
      style={{
        position: "absolute",
        left: posX,
        top: posY,
        width: size,
        height: size,
        transform: `translate(-50%, -50%) scale(${scale}) rotate(${rotation}deg)`,
        opacity,
        zIndex: 45,
        pointerEvents: "none",
        ...style,
      }}
    >
      {/* Directional Soft Pin Shadow */}
      <div
        style={{
          position: "absolute",
          left: shadowX,
          top: shadowY,
          width: size,
          height: size * 0.85,
          borderRadius: "50%",
          backgroundColor: "rgba(0, 0, 0, 0.45)",
          filter: "blur(4px)",
          transform: "scaleY(0.7)",
        }}
      />

      {/* Outer Metal Collar Ring */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          borderRadius: "50%",
          background: ringGradient,
          boxShadow: "inset 0 1px 2px rgba(255,255,255,0.6), 0 2px 4px rgba(0,0,0,0.35)",
        }}
      />

      {/* Dome Head with Spherical Gradient */}
      <div
        style={{
          position: "absolute",
          inset: 2,
          borderRadius: "50%",
          background: headGradient,
          boxShadow: "inset 0 -2px 4px rgba(0,0,0,0.4)",
        }}
      />

      {/* Specular Glint Highlight */}
      <div
        style={{
          position: "absolute",
          top: size * 0.22,
          left: size * 0.24,
          width: size * 0.26,
          height: size * 0.18,
          borderRadius: "50%",
          backgroundColor: "rgba(255, 255, 255, 0.85)",
          transform: "rotate(-35deg)",
          filter: "blur(0.5px)",
        }}
      />
    </div>
  );
};
