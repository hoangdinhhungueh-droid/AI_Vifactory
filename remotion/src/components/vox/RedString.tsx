import React from "react";
import { Easing, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { useStopMotion } from "./useStopMotion";

export interface RedStringConnection {
  fromX: number;
  fromY: number;
  toX: number;
  toY: number;
  label?: string;
  color?: string;
  drawStartFrame?: number;
  drawDuration?: number;
  isYarn?: boolean;
  dashed?: boolean;
  uncertain?: boolean;
}

export const RedString: React.FC<{
  connections?: RedStringConnection[];
  width?: number;
  height?: number;
}> = ({ connections = [], width = 1920, height = 1080 }) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const { dx, dy } = useStopMotion(12, 0.65, 7);

  if (!connections || !Array.isArray(connections) || connections.length === 0) {
    return null;
  }

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
        zIndex: 28,
      }}
    >
      {connections.map((conn, cIdx) => {
        const drawStart = conn.drawStartFrame ?? 12 + cIdx * 7;
        const drawDur = conn.drawDuration ?? 18;
        const drawProgress = interpolate(
          frame,
          [drawStart, drawStart + drawDur],
          [0, 1],
          {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.bezier(0.16, 1, 0.3, 1),
          }
        );

        if (drawProgress < 0.02) return null;

        const pinStartSpring = spring({
          frame: Math.max(0, frame - Math.max(0, drawStart - 3)),
          fps: fps || 30,
          config: { damping: 12, stiffness: 160, mass: 0.5 },
        });
        const pinEndSpring = spring({
          frame: Math.max(0, frame - (drawStart + Math.round(drawDur * 0.65))),
          fps: fps || 30,
          config: { damping: 12, stiffness: 160, mass: 0.5 },
        });

        const x1 = ((conn.fromX ?? 30) / 100) * width;
        const y1 = ((conn.fromY ?? 50) / 100) * height;
        const x2 = ((conn.toX ?? 70) / 100) * width;
        const y2 = ((conn.toY ?? 40) / 100) * height;

        const midX = (x1 + x2) / 2;
        const midY = (y1 + y2) / 2;
        const dxVec = x2 - x1;
        const dyVec = y2 - y1;
        const dist = Math.hypot(dxVec, dyVec);

        // Natural gravitational sag for physical red yarn on investigation board
        const sagAmount = Math.min(55, Math.max(18, dist * 0.08)) + (cIdx % 3) * 8;
        const cx = midX + dx * 0.8;
        const cy = midY + sagAmount + dy * 0.8;

        // Current tip interpolation along quadratic Bezier for progressive string pull
        const t = drawProgress;
        const curX =
          (1 - t) * (1 - t) * x1 + 2 * (1 - t) * t * cx + t * t * x2;
        const curY =
          (1 - t) * (1 - t) * y1 + 2 * (1 - t) * t * cy + t * t * y2;
        const ctrlX = (1 - t) * x1 + t * cx;
        const ctrlY = (1 - t) * y1 + t * cy;

        const partialPathD = `M ${x1.toFixed(1)} ${y1.toFixed(1)} Q ${ctrlX.toFixed(1)} ${ctrlY.toFixed(1)} ${curX.toFixed(1)} ${curY.toFixed(1)}`;

        const isUncertain = Boolean(
          conn.dashed ||
            conn.uncertain ||
            (conn.label &&
              (conn.label.includes("?") ||
                conn.label.includes("不明") ||
                conn.label.includes("UNCLEAR") ||
                conn.label.includes("UNVERIFIED")))
        );

        const strokeColor = conn.color || (isUncertain ? "#d97706" : "#b91c1c");
        const hasLabel = Boolean(conn.label && conn.label.trim().length > 0);
        const labelText = isUncertain && conn.label && !conn.label.includes("?")
          ? `? ${conn.label}`
          : conn.label || "";

        const tangentX = x2 - cx;
        const tangentY = y2 - cy;
        const angleDeg = (Math.atan2(tangentY, tangentX) * 180) / Math.PI;
        const isDrawn = drawProgress >= 0.92;

        // Midpoint on actual quadratic curve at t=0.5
        const midCurveX = 0.25 * x1 + 0.5 * cx + 0.25 * x2;
        const midCurveY = 0.25 * y1 + 0.5 * cy + 0.25 * y2;
        const tagWidth = Math.max(88, labelText.length * 10 + 32);

        return (
          <g key={`red-string-${cIdx}`}>
            {/* Tabletop Drop Shadow of the String */}
            <path
              d={partialPathD}
              fill="none"
              stroke="rgba(30, 18, 8, 0.38)"
              strokeWidth={4.5}
              strokeDasharray={isUncertain ? "12,9" : undefined}
              strokeLinecap="round"
              transform="translate(2, 6)"
            />

            {/* Main Physical Red Yarn / Marker Line */}
            <path
              d={partialPathD}
              fill="none"
              stroke={strokeColor}
              strokeWidth={3.8}
              strokeDasharray={isUncertain ? "12,9" : undefined}
              strokeLinecap="round"
            />

            {/* Subtle Yarn Fiber Highlight */}
            <path
              d={partialPathD}
              fill="none"
              stroke="rgba(255, 220, 220, 0.35)"
              strokeWidth={1.2}
              strokeDasharray={isUncertain ? "12,9" : "6,8"}
              strokeLinecap="round"
            />

            {/* Origin Brass/Red Push-Pin */}
            <g
              transform={`translate(${x1.toFixed(1)}, ${y1.toFixed(1)}) scale(${pinStartSpring.toFixed(3)})`}
            >
              <circle cx={2} cy={3} r={7} fill="rgba(0,0,0,0.4)" />
              <circle
                cx={0}
                cy={0}
                r={6.5}
                fill="#991b1b"
                stroke="#fef2f2"
                strokeWidth={1.5}
              />
              <circle cx={-2} cy={-2} r={2} fill="rgba(255,255,255,0.65)" />
            </g>

            {/* Target Push-Pin or Marker Arrowhead */}
            {drawProgress > 0.65 ? (
              conn.isYarn !== false ? (
                <g
                  transform={`translate(${x2.toFixed(1)}, ${y2.toFixed(1)}) scale(${pinEndSpring.toFixed(3)})`}
                >
                  <circle cx={2} cy={3} r={7} fill="rgba(0,0,0,0.4)" />
                  <circle
                    cx={0}
                    cy={0}
                    r={6.5}
                    fill={strokeColor}
                    stroke="#fef2f2"
                    strokeWidth={1.5}
                  />
                  <circle cx={-2} cy={-2} r={2} fill="rgba(255,255,255,0.65)" />
                </g>
              ) : (
                <path
                  d="M -14 -7 L 0 0 L -14 7 Z"
                  fill={strokeColor}
                  transform={`translate(${x2.toFixed(1)}, ${y2.toFixed(1)}) rotate(${angleDeg.toFixed(1)}) scale(${pinEndSpring.toFixed(3)})`}
                />
              )
            ) : null}

            {/* Tactile Masking-Tape Evidence Label on String */}
            {hasLabel && isDrawn ? (
              <g
                transform={`translate(${midCurveX.toFixed(1)}, ${midCurveY.toFixed(1)}) rotate(${(cIdx % 2 === 0 ? -2.2 : 2.2).toFixed(1)})`}
              >
                {/* Drop shadow */}
                <rect
                  x={-tagWidth / 2 + 2}
                  y={-13}
                  width={tagWidth}
                  height={30}
                  rx={3}
                  fill="rgba(30, 18, 8, 0.35)"
                />
                {/* Masking tape strip */}
                <rect
                  x={-tagWidth / 2}
                  y={-15}
                  width={tagWidth}
                  height={30}
                  rx={3}
                  fill="#FAF6EC"
                  stroke={isUncertain ? "#d97706" : "#b91c1c"}
                  strokeWidth={1.8}
                  strokeDasharray={isUncertain ? "5,3" : undefined}
                />
                <text
                  x={0}
                  y={5}
                  textAnchor="middle"
                  fill={isUncertain ? "#92400e" : "#7f1d1d"}
                  fontSize={13}
                  fontWeight={900}
                  letterSpacing={1.2}
                  fontFamily="'Courier Prime', 'Courier New', monospace"
                >
                  {labelText}
                </text>
              </g>
            ) : null}
          </g>
        );
      })}
    </svg>
  );
};
