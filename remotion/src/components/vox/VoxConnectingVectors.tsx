import React from "react";
import { interpolate, useCurrentFrame, Easing } from "remotion";
import { VoxConnectionItem } from "./VoxCompositeStage";

export const VoxConnectingVectors: React.FC<{
  connections?: VoxConnectionItem[];
  width?: number;
  height?: number;
}> = ({ connections = [], width = 1920, height = 1080 }) => {
  const frame = useCurrentFrame();
  if (!connections || !Array.isArray(connections) || connections.length === 0) return null;

  return (
    <svg
      width={width}
      height={height}
      viewBox={`0 0 ${width} ${height}`}
      style={{ position: "absolute", top: 0, left: 0, pointerEvents: "none", zIndex: 28 }}
    >
      <defs>
        <filter id="vectorGlow" x="-20%" y="-20%" width="140%" height="140%">
          <feGaussianBlur stdDeviation="3" result="blur" />
          <feComposite in="SourceGraphic" in2="blur" operator="over" />
        </filter>
      </defs>
      {connections.map((conn, cIdx) => {
        const drawStart = conn.drawStartFrame ?? (15 + cIdx * 6);
        const drawDur = conn.drawDuration ?? 20;
        const drawProgress = interpolate(frame, [drawStart, drawStart + drawDur], [0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
          easing: Easing.bezier(0.16, 1, 0.3, 1),
        });

        if (drawProgress < 0.02) return null;

        const x1 = ((conn.fromX ?? 30) / 100) * width;
        const y1 = ((conn.fromY ?? 50) / 100) * height;
        const x2 = ((conn.toX ?? 70) / 100) * width;
        const y2 = ((conn.toY ?? 40) / 100) * height;

        const midX = (x1 + x2) / 2;
        const midY = (y1 + y2) / 2;
        const dx = x2 - x1;
        const dy = y2 - y1;
        const dist = Math.hypot(dx, dy);

        let cx: number;
        let cy: number;
        if (conn.isYarn) {
          // Natural gravitational sag for yarn strings
          cx = midX;
          cy = midY + 14 + (cIdx % 3) * 8;
        } else {
          // Alternating curve bulge for organic trajectory
          const curveBulge = cIdx % 2 === 0 ? -40 : 40;
          const nx = -dy / (dist || 1);
          const ny = dx / (dist || 1);
          cx = midX + nx * curveBulge;
          cy = midY + ny * curveBulge;
        }

        const pathD = `M ${x1} ${y1} Q ${cx} ${cy} ${x2} ${y2}`;
        const approxLen = dist * 1.15;
        const dashOffset = approxLen * (1 - drawProgress);

        const tangentX = x2 - cx;
        const tangentY = y2 - cy;
        const angleDeg = (Math.atan2(tangentY, tangentX) * 180) / Math.PI;

        const isDrawn = drawProgress >= 0.98;
        const pulseT = ((frame - (drawStart + drawDur)) * 0.04) % 1;
        const pulsePos = Math.max(0, pulseT);
        const pulseX = (1 - pulsePos) * (1 - pulsePos) * x1 + 2 * (1 - pulsePos) * pulsePos * cx + pulsePos * pulsePos * x2;
        const pulseY = (1 - pulsePos) * (1 - pulsePos) * y1 + 2 * (1 - pulsePos) * pulsePos * cy + pulsePos * pulsePos * y2;

        const strokeColor = conn.color || "#ef4444";
        const hasLabel = Boolean(conn.label && conn.label.trim().length > 0);

        return (
          <g key={cIdx}>
            {/* Soft Shadow Underlying */}
            <path
              d={pathD}
              fill="none"
              stroke="rgba(0, 0, 0, 0.45)"
              strokeWidth={conn.isYarn ? 7 : 5}
              strokeDasharray={approxLen}
              strokeDashoffset={dashOffset}
              transform="translate(2, 4)"
            />

            {/* Glowing Neon or Textured Red Yarn Body */}
            <path
              d={pathD}
              fill="none"
              stroke={strokeColor}
              strokeWidth={conn.isYarn ? 3.5 : 2.5}
              strokeDasharray={conn.isYarn ? "8,5" : `${approxLen}`}
              strokeDashoffset={dashOffset}
              strokeLinecap="round"
              filter="url(#vectorGlow)"
            />

            {/* Leading Pulse Kinetic Energy Particle */}
            {isDrawn && !conn.isYarn ? (
              <circle
                cx={pulseX}
                cy={pulseY}
                r={4.5}
                fill="#ffffff"
                filter="url(#vectorGlow)"
              />
            ) : null}

            {/* Pin Tack for Yarn or Solid Arrowhead for Vectors */}
            {drawProgress > 0.4 ? (
              conn.isYarn ? (
                <circle
                  cx={x2}
                  cy={y2}
                  r={4.5}
                  fill={strokeColor}
                  stroke="#ffffff"
                  strokeWidth={1.5}
                  filter="url(#vectorGlow)"
                />
              ) : (
                <path
                  d="M -12 -7 L 0 0 L -12 7 Z"
                  fill={strokeColor}
                  transform={`translate(${x2}, ${y2}) rotate(${angleDeg}) scale(${drawProgress})`}
                  filter="url(#vectorGlow)"
                />
              )
            ) : null}

            {/* Floating Vector Telemetry Badge */}
            {hasLabel && isDrawn ? (
              <g transform={`translate(${cx}, ${cy})`}>
                <rect
                  x={-(((conn.label?.length || 0) * 8 + 24) / 2)}
                  y={-14}
                  width={(conn.label?.length || 0) * 8 + 24}
                  height={28}
                  rx={6}
                  fill="rgba(15, 23, 42, 0.95)"
                  stroke={strokeColor}
                  strokeWidth={1.5}
                />
                <text
                  x={0}
                  y={4}
                  textAnchor="middle"
                  fill={strokeColor}
                  fontSize={11}
                  fontWeight={900}
                  letterSpacing={1.2}
                  fontFamily="'Courier New', monospace"
                >
                  {conn.label}
                </text>
              </g>
            ) : null}
          </g>
        );
      })}
    </svg>
  );
};
