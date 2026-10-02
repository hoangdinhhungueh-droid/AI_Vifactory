import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

export interface VoxWashiTapeProps {
  x?: number | string;
  y?: number | string;
  width?: number;
  height?: number;
  rotation?: number;
  color?: "cream" | "manila" | "crimson" | "translucent_white";
  dropFrame?: number;
  corner?: "top_left" | "top_right" | "bottom_left" | "bottom_right" | "center" | "none";
  style?: React.CSSProperties;
}

export const VoxWashiTape: React.FC<VoxWashiTapeProps> = ({
  x = 0,
  y = 0,
  width = 110,
  height = 32,
  rotation = -8,
  color = "cream",
  dropFrame = 0,
  corner = "none",
  style,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const relFrame = Math.max(0, frame - dropFrame);
  const snapSpring = spring({
    frame: relFrame,
    fps,
    config: { damping: 12, mass: 0.45, stiffness: 180 },
  });

  const scale = dropFrame > 0 ? interpolate(snapSpring, [0, 1], [0.6, 1.0]) : 1.0;
  const opacity = dropFrame > 0 ? interpolate(snapSpring, [0, 0.25, 1], [0, 0.85, 1.0]) : 1.0;

  // Color profiles
  let bgColor = "rgba(246, 238, 206, 0.82)"; // classic yellowish masking tape
  let borderColor = "rgba(180, 160, 120, 0.4)";

  if (color === "manila") {
    bgColor = "rgba(220, 195, 155, 0.85)";
    borderColor = "rgba(150, 125, 85, 0.45)";
  } else if (color === "crimson") {
    bgColor = "rgba(220, 38, 38, 0.78)";
    borderColor = "rgba(153, 27, 27, 0.5)";
  } else if (color === "translucent_white") {
    bgColor = "rgba(255, 255, 255, 0.72)";
    borderColor = "rgba(200, 200, 200, 0.35)";
  }

  // Preset corner placement rotations
  let appliedRotation = rotation;
  if (corner === "top_left") appliedRotation = -32;
  else if (corner === "top_right") appliedRotation = 32;
  else if (corner === "bottom_left") appliedRotation = 28;
  else if (corner === "bottom_right") appliedRotation = -28;

  const posX = typeof x === "number" ? `${x}px` : x;
  const posY = typeof y === "number" ? `${y}px` : y;

  // Jagged zigzag SVG tape ends
  return (
    <div
      style={{
        position: "absolute",
        left: posX,
        top: posY,
        width,
        height,
        transform: `translate(-50%, -50%) scale(${scale}) rotate(${appliedRotation}deg)`,
        opacity,
        zIndex: 40,
        pointerEvents: "none",
        ...style,
      }}
    >
      <svg
        width={width}
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        style={{
          overflow: "visible",
          filter: "drop-shadow(0 2px 5px rgba(0, 0, 0, 0.22))",
        }}
      >
        <defs>
          <linearGradient id={`tapeGrad-${width}`} x1="0%" y1="0%" x2="100%" y2="100%">
            <stop offset="0%" stopColor={bgColor} />
            <stop offset="50%" stopColor={bgColor} />
            <stop offset="100%" stopColor={bgColor} stopOpacity={0.9} />
          </linearGradient>
        </defs>

        {/* Serrated Washi Tape Polygon with Jagged Teeth on Left and Right Ends */}
        <polygon
          points={`
            0,0 
            ${width},0 
            ${width - 3},${height * 0.25} 
            ${width},${height * 0.5} 
            ${width - 4},${height * 0.75} 
            ${width},${height} 
            0,${height} 
            4,${height * 0.75} 
            0,${height * 0.5} 
            3,${height * 0.25}
          `}
          fill={`url(#tapeGrad-${width})`}
          stroke={borderColor}
          strokeWidth="0.8"
        />

        {/* Faint Paper Fiber / Tape Crease Lines */}
        <line
          x1={width * 0.2}
          y1={0}
          x2={width * 0.23}
          y2={height}
          stroke="rgba(255, 255, 255, 0.35)"
          strokeWidth="0.75"
        />
        <line
          x1={width * 0.65}
          y1={0}
          x2={width * 0.68}
          y2={height}
          stroke="rgba(0, 0, 0, 0.08)"
          strokeWidth="0.6"
        />
      </svg>
    </div>
  );
};
