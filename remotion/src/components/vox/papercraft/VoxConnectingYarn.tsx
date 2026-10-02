import React from "react";
import { Easing, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

export interface VoxConnectingYarnProps {
  fromX: number; // % of canvas width
  fromY: number; // % of canvas height
  toX: number;   // % of canvas width
  toY: number;   // % of canvas height
  color?: string; // default #dc2626 (crimson red yarn)
  yarnThickness?: number; // default 4.5
  sagAmount?: number;     // catenary curve sag in px (default 35)
  drawStartFrame?: number; // default 20
  drawDuration?: number;   // default 25
  label?: string;          // optional pinned evidence label
  width?: number;
  height?: number;
  style?: React.CSSProperties;
}

export const VoxConnectingYarn: React.FC<VoxConnectingYarnProps> = ({
  fromX,
  fromY,
  toX,
  toY,
  color = "#dc2626",
  yarnThickness = 4.5,
  sagAmount = 35,
  drawStartFrame = 20,
  drawDuration = 25,
  label,
  width: customW,
  height: customH,
  style,
}) => {
  const frame = useCurrentFrame();
  const { width: configW = 1920, height: configH = 1080 } = useVideoConfig();
  const width = customW || configW;
  const height = customH || configH;

  const drawProgress = interpolate(frame, [drawStartFrame, drawStartFrame + drawDuration], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });

  if (drawProgress < 0.01) return null;

  // Pixel coordinates
  const x1 = (fromX / 100) * width;
  const y1 = (fromY / 100) * height;
  const x2 = (toX / 100) * width;
  const y2 = (toY / 100) * height;

  // Catenary midpoint calculation with gravitational sag
  const midX = (x1 + x2) / 2;
  const midY = (y1 + y2) / 2;
  const dx = x2 - x1;
  const dy = y2 - y1;
  const dist = Math.hypot(dx, dy);

  // Downward gravity sag
  const cx = midX;
  const cy = midY + sagAmount;

  const pathD = `M ${x1} ${y1} Q ${cx} ${cy} ${x2} ${y2}`;
  const approxLen = dist * 1.18;
  const dashOffset = approxLen * (1 - drawProgress);

  // Label bounce
  const labelRel = Math.max(0, frame - (drawStartFrame + Math.round(drawDuration * 0.6)));
  const labelSpring = spring({
    frame: labelRel,
    fps: 30,
    config: { damping: 11, mass: 0.4, stiffness: 180 },
  });

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      style={{
        position: "absolute",
        top: 0,
        left: 0,
        pointerEvents: "none",
        zIndex: 24,
        ...style,
      }}
    >
      <defs>
        <filter id={`yarnShadow-${fromX}-${toX}`} x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur in="SourceAlpha" stdDeviation="3.5" />
          <feOffset dx="2" dy="6" result="offsetblur" />
          <feComponentTransfer>
            <feFuncA type="linear" slope="0.35" />
          </feComponentTransfer>
          <feMerge>
            <feMergeNode />
            <feMergeNode in="SourceGraphic" />
          </feMerge>
        </filter>
      </defs>

      {/* Shadow Layer */}
      <path
        d={pathD}
        fill="none"
        stroke="rgba(0, 0, 0, 0.35)"
        strokeWidth={yarnThickness + 2}
        strokeDasharray={approxLen}
        strokeDashoffset={dashOffset}
        transform="translate(2, 6)"
      />

      {/* Primary Twisted Yarn Texture (Crimson Base) */}
      <path
        d={pathD}
        fill="none"
        stroke={color}
        strokeWidth={yarnThickness}
        strokeDasharray={approxLen}
        strokeDashoffset={dashOffset}
        strokeLinecap="round"
      />

      {/* Yarn Fiber Braiding Overlay */}
      <path
        d={pathD}
        fill="none"
        stroke="rgba(255, 255, 255, 0.4)"
        strokeWidth={yarnThickness * 0.3}
        strokeDasharray="4,2"
        strokeDashoffset={dashOffset}
        strokeLinecap="round"
      />

      {/* Connection Anchor Nodes (Micro Metal Rings) */}
      {drawProgress >= 0.05 ? (
        <circle cx={x1} cy={y1} r={yarnThickness * 0.9} fill="#5D4037" stroke="#FFE082" strokeWidth="1" />
      ) : null}
      {drawProgress >= 0.95 ? (
        <circle cx={x2} cy={y2} r={yarnThickness * 0.9} fill="#5D4037" stroke="#FFE082" strokeWidth="1" />
      ) : null}

      {/* Pinned Evidence Label along the Curve */}
      {label && labelSpring > 0.05 ? (
        <g transform={`translate(${cx}, ${cy - 12}) scale(${labelSpring})`}>
          <rect
            x={-((label.length * 8 + 26) / 2)}
            y={-14}
            width={label.length * 8 + 26}
            height={28}
            rx={4}
            fill="#FAF7EE"
            stroke="#1E293B"
            strokeWidth="1.2"
            filter="drop-shadow(0 3px 6px rgba(0,0,0,0.3))"
          />
          <text
            x={0}
            y={4}
            textAnchor="middle"
            fill="#0F172A"
            fontSize={11}
            fontWeight={900}
            letterSpacing={1.2}
            fontFamily="'Courier New', Courier, monospace"
          >
            {label}
          </text>
        </g>
      ) : null}
    </svg>
  );
};
