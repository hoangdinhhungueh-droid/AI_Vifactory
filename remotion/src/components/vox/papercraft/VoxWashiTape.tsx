import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

export interface VoxWashiTapeProps {
  x?: number | string;
  y?: number | string;
  width?: number;
  height?: number;
  rotation?: number;
  color?: "cream" | "manila" | "crimson" | "yellow" | "translucent_white" | string;
  dropFrame?: number;
  corner?: "top_left" | "top_right" | "bottom_left" | "bottom_right" | "center" | "none";
  style?: React.CSSProperties;
}

/**
 * VoxWashiTape: Authentic Semi-Translucent Crepe Washi Tape Strip.
 *
 * Implements Rule 122 & Vox Visual Benchmark Parity:
 * - mixBlendMode: "multiply" allowing underlying ink, photos, and textures to show through
 * - Organic ragged micro-torn teeth on both tape edges
 * - Faint crepe paper fiber striations and subtle surface wrinkles
 * - Realistic adhesive tape shadow and spring placement snap
 */
export const VoxWashiTape: React.FC<VoxWashiTapeProps> = ({
  x = 0,
  y = 0,
  width = 100,
  height = 32,
  rotation = -8,
  color = "cream",
  dropFrame = 0,
  corner = "none",
  style,
}) => {
  const frame = useCurrentFrame();
  const { fps = 30 } = useVideoConfig();

  const relFrame = Math.max(0, frame - dropFrame);
  const snapSpring = spring({
    frame: relFrame,
    fps,
    config: { damping: 13, mass: 0.45, stiffness: 190 },
  });

  const scale = dropFrame > 0 ? interpolate(snapSpring, [0, 1], [0.75, 1.0]) : 1.0;
  const opacity = dropFrame > 0 ? interpolate(snapSpring, [0, 0.2, 1], [0, 0.88, 1.0]) : 1.0;

  // Authentic Color & Adhesive Transparency Palettes
  let bgColor = "rgba(250, 243, 218, 0.84)"; // classic yellowish-ivory masking tape
  let borderColor = "rgba(180, 155, 110, 0.45)";
  let fiberColor = "rgba(140, 115, 75, 0.18)";

  if (color === "yellow") {
    bgColor = "rgba(254, 240, 138, 0.85)"; // vibrant yellow masking tape
    borderColor = "rgba(202, 138, 4, 0.45)";
    fiberColor = "rgba(161, 98, 7, 0.22)";
  } else if (color === "manila") {
    bgColor = "rgba(225, 204, 166, 0.88)"; // craft paper brown tape
    borderColor = "rgba(155, 125, 85, 0.5)";
    fiberColor = "rgba(120, 90, 50, 0.24)";
  } else if (color === "crimson") {
    bgColor = "rgba(239, 68, 68, 0.78)"; // red evidence security tape
    borderColor = "rgba(185, 28, 28, 0.55)";
    fiberColor = "rgba(127, 29, 29, 0.25)";
  } else if (color === "translucent_white") {
    bgColor = "rgba(255, 255, 255, 0.76)"; // archival document mending tape
    borderColor = "rgba(203, 213, 225, 0.4)";
    fiberColor = "rgba(148, 163, 184, 0.16)";
  }

  // Preset corner placements
  let appliedRotation = rotation;
  if (corner === "top_left") appliedRotation = -32;
  else if (corner === "top_right") appliedRotation = 32;
  else if (corner === "bottom_left") appliedRotation = 28;
  else if (corner === "bottom_right") appliedRotation = -28;

  const posX = typeof x === "number" ? `${x}px` : x;
  const posY = typeof y === "number" ? `${y}px` : y;

  const w = width;
  const h = height;

  // Generate multi-tooth organic serrated ripped tape ends
  const leftTorn = [
    `0,0`,
    `3,${h * 0.15}`,
    `1,${h * 0.3}`,
    `4,${h * 0.45}`,
    `0,${h * 0.6}`,
    `3,${h * 0.75}`,
    `1,${h * 0.88}`,
    `0,${h}`,
  ].join(" ");

  const rightTorn = [
    `${w},${h}`,
    `${w - 3},${h * 0.88}`,
    `${w - 1},${h * 0.72}`,
    `${w - 4},${h * 0.55}`,
    `${w - 1},${h * 0.38}`,
    `${w - 4},${h * 0.2}`,
    `${w - 2},${h * 0.08}`,
    `${w},0`,
  ].join(" ");

  const polygonPoints = `0,0 ${w},0 ${rightTorn} ${leftTorn}`;

  return (
    <div
      style={{
        position: "absolute",
        left: posX,
        top: posY,
        width: w,
        height: h,
        transform: `translate(-50%, -50%) scale(${scale}) rotate(${appliedRotation}deg)`,
        opacity,
        zIndex: 42,
        pointerEvents: "none",
        mixBlendMode: "multiply", // Critical for realistic semi-transparent overlay onto paper/photos
        filter: "drop-shadow(0 2px 4px rgba(35, 22, 10, 0.28))",
        ...style,
      }}
    >
      <svg
        width={w}
        height={h}
        viewBox={`0 0 ${w} ${h}`}
        style={{
          overflow: "visible",
          display: "block",
        }}
      >
        <defs>
          <linearGradient id={`washiGrad-${Math.round(w)}`} x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor={bgColor} />
            <stop offset="45%" stopColor={bgColor} />
            <stop offset="100%" stopColor={bgColor} stopOpacity={0.92} />
          </linearGradient>
        </defs>

        {/* 1. PRIMARY MULTI-TOOTH TORN TAPE BODY */}
        <polygon
          points={polygonPoints}
          fill={`url(#washiGrad-${Math.round(w)})`}
          stroke={borderColor}
          strokeWidth="0.75"
        />

        {/* 2. CREPE PAPER VERTICAL FIBER STRIATIONS */}
        <line
          x1={w * 0.18}
          y1={1}
          x2={w * 0.20}
          y2={h - 1}
          stroke="rgba(255, 255, 255, 0.45)"
          strokeWidth="0.8"
        />
        <line
          x1={w * 0.38}
          y1={1}
          x2={w * 0.39}
          y2={h - 1}
          stroke={fiberColor}
          strokeWidth="0.65"
        />
        <line
          x1={w * 0.62}
          y1={1}
          x2={w * 0.64}
          y2={h - 1}
          stroke="rgba(255, 255, 255, 0.4)"
          strokeWidth="0.75"
        />
        <line
          x1={w * 0.82}
          y1={1}
          x2={w * 0.81}
          y2={h - 1}
          stroke={fiberColor}
          strokeWidth="0.6"
        />

        {/* 3. DIAGONAL AIR POCKET / TAPE SURFACE HIGHLIGHT */}
        <line
          x1={w * 0.25}
          y1={h * 0.2}
          x2={w * 0.75}
          y2={h * 0.3}
          stroke="rgba(255, 255, 255, 0.35)"
          strokeWidth="0.6"
          strokeDasharray="12 8"
        />
      </svg>
    </div>
  );
};
