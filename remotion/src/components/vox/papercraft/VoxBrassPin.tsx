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

/**
 * VoxBrassPin: Realistic 3D Metallic Pushpin / Map Tack Component.
 *
 * Implements Rule 122 & Vox Documentary Benchmark Parity:
 * - Authentic 3D spherical dome with metallic brass gradient and specular glint
 * - Outer beveled collar ring with realistic metal sheen
 * - Deep directional contact shadow piercing through the paper layer
 * - Needle puncture hole shadow at the pin base
 * - Spring tack placement physics with tactile micro-settle
 */
export const VoxBrassPin: React.FC<VoxBrassPinProps> = ({
  x = 0,
  y = 0,
  size = 28,
  rotation = 0,
  color = "brass",
  dropFrame = 0,
  shadowDirection = "bottom_right",
  style,
}) => {
  const frame = useCurrentFrame();
  const { fps = 30 } = useVideoConfig();

  const relFrame = Math.max(0, frame - dropFrame);
  const pinSpring = spring({
    frame: relFrame,
    fps,
    config: { damping: 11, mass: 0.38, stiffness: 210 },
  });

  const scale = dropFrame > 0 ? interpolate(pinSpring, [0, 1], [2.1, 1.0]) : 1.0;
  const opacity = dropFrame > 0 ? interpolate(pinSpring, [0, 0.25, 1], [0, 0.92, 1.0]) : 1.0;

  // Shadow vectors
  const shadowX = shadowDirection === "bottom_left" ? -5 : shadowDirection === "bottom" ? 0 : 6;
  const shadowY = 8;

  // 3D Metallic Material Gradient Profiles
  let headGradient =
    "radial-gradient(circle at 32% 30%, #fffde7 0%, #fef08a 22%, #eab308 52%, #a16207 78%, #451a03 100%)";
  let collarGradient =
    "linear-gradient(135deg, #fef9c3 0%, #ca8a04 45%, #713f12 85%, #fde047 100%)";
  let rimColor = "rgba(254, 240, 138, 0.75)";

  if (color === "silver") {
    headGradient =
      "radial-gradient(circle at 32% 30%, #ffffff 0%, #f1f5f9 25%, #94a3b8 55%, #475569 82%, #0f172a 100%)";
    collarGradient =
      "linear-gradient(135deg, #ffffff 0%, #64748b 50%, #334155 85%, #cbd5e1 100%)";
    rimColor = "rgba(255, 255, 255, 0.85)";
  } else if (color === "crimson") {
    headGradient =
      "radial-gradient(circle at 32% 30%, #fee2e2 0%, #f87171 25%, #dc2626 55%, #991b1b 82%, #450a0a 100%)";
    collarGradient =
      "linear-gradient(135deg, #fca5a5 0%, #b91c1c 50%, #7f1d1d 85%, #ef4444 100%)";
    rimColor = "rgba(254, 202, 202, 0.75)";
  } else if (color === "black") {
    headGradient =
      "radial-gradient(circle at 32% 30%, #94a3b8 0%, #334155 30%, #1e293b 60%, #0f172a 85%, #020617 100%)";
    collarGradient =
      "linear-gradient(135deg, #64748b 0%, #1e293b 50%, #020617 85%, #475569 100%)";
    rimColor = "rgba(148, 163, 184, 0.5)";
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
        zIndex: 48,
        pointerEvents: "none",
        ...style,
      }}
    >
      {/* 1. NEEDLE PUNCTURE HOLE IN THE PAPER LAYER */}
      <div
        style={{
          position: "absolute",
          left: "50%",
          top: "50%",
          width: Math.max(3, size * 0.16),
          height: Math.max(3, size * 0.16),
          borderRadius: "50%",
          backgroundColor: "rgba(15, 10, 5, 0.75)",
          transform: "translate(-50%, -50%)",
          boxShadow: "0 0 2px rgba(0,0,0,0.8)",
          zIndex: 1,
        }}
      />

      {/* 2. DIRECTIONAL SOFT PAPER CONTACT SHADOW */}
      <div
        style={{
          position: "absolute",
          left: shadowX,
          top: shadowY,
          width: size * 1.1,
          height: size * 0.9,
          borderRadius: "50%",
          backgroundColor: "rgba(25, 15, 10, 0.48)",
          filter: "blur(4.5px)",
          transform: "scaleY(0.68)",
          zIndex: 2,
        }}
      />

      {/* 3. OUTER METALLIC BEVEL COLLAR RING */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          borderRadius: "50%",
          background: collarGradient,
          boxShadow: `inset 0 1px 2px ${rimColor}, 0 2px 5px rgba(0,0,0,0.45)`,
          zIndex: 3,
        }}
      />

      {/* 4. SPHERICAL CONVEX DOME HEAD */}
      <div
        style={{
          position: "absolute",
          inset: Math.max(2, size * 0.08),
          borderRadius: "50%",
          background: headGradient,
          boxShadow: "inset 0 -2px 4px rgba(0,0,0,0.55), inset 0 1px 2px rgba(255,255,255,0.7)",
          zIndex: 4,
        }}
      />

      {/* 5. HOT SPECULAR GLINT HIGHLIGHT */}
      <div
        style={{
          position: "absolute",
          top: size * 0.20,
          left: size * 0.22,
          width: size * 0.28,
          height: size * 0.18,
          borderRadius: "50%",
          backgroundColor: "rgba(255, 255, 255, 0.92)",
          transform: "rotate(-32deg)",
          filter: "blur(0.5px)",
          zIndex: 5,
        }}
      />
    </div>
  );
};
