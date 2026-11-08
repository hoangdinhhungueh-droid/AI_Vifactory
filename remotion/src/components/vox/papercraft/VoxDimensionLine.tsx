import React from "react";
import { Audio, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { SPRING_PRESETS } from "../springPresets";

export interface VoxDimensionLineProps {
  startX?: number; // % of frame width (e.g. 30)
  endX?: number;   // % of frame width (e.g. 70)
  y?: number;      // % of frame height (e.g. 52)
  label?: string;  // Metric string (e.g. "0.0% // MISSING BASELINE")
  color?: string;  // Dimension line color (default crimson #DC2626 or ink #1A1A1A)
  startFrame?: number;
  rotation?: number;
  style?: React.CSSProperties;
}

/**
 * VoxDimensionLine — Architectural & Forensic Caliper Dimension Line Ride.
 * Enforces Opuscar Vox Engine specifications:
 * - Dimension line rides with arrowhead taps
 * - Precision IBM Plex Mono source chip
 * - Mechanical spring dynamics (opuscarDimensionLine)
 * - Tactile counter tick audio on arrowhead tap
 */
export const VoxDimensionLine: React.FC<VoxDimensionLineProps> = ({
  startX = 32,
  endX = 68,
  y = 48,
  label = "0.0% // UNVERIFIED BASELINE",
  color = "#DC2626",
  startFrame = 12,
  rotation = 0,
  style,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const relFrame = Math.max(0, frame - startFrame);

  // Dimension ride spring: snappy deployment with mechanical settle
  const rideProgress = spring({
    frame: relFrame,
    fps,
    config: SPRING_PRESETS.opuscarDimensionLine,
  });

  // Arrowhead tap overshoot and settle
  const tapSpring = spring({
    frame: Math.max(0, relFrame - 8),
    fps,
    config: { damping: 14, mass: 0.3, stiffness: 350 },
  });

  if (frame < startFrame) {
    return null;
  }

  const currentSpan = interpolate(rideProgress, [0, 1], [0, endX - startX]);
  const leftX = startX;
  const rightX = startX + currentSpan;
  const isTapLanded = relFrame >= 8;

  return (
    <div
      style={{
        position: "absolute",
        left: 0,
        top: 0,
        width: "100%",
        height: "100%",
        pointerEvents: "none",
        zIndex: 35,
        transform: `rotate(${rotation}deg)`,
        ...style,
      }}
    >
      {/* Audio SFX on arrowhead tap */}
      {relFrame >= 8 && relFrame <= 28 && (
        <Audio src={staticFile("sfx/counter_tick.mp3")} volume={0.35} />
      )}

      {/* SVG Dimension Line & Arrowheads */}
      <svg
        style={{
          position: "absolute",
          inset: 0,
          width: "100%",
          height: "100%",
          overflow: "visible",
        }}
      >
        <defs>
          <marker
            id="dim-arrow-left"
            viewBox="0 0 10 10"
            refX="2"
            refY="5"
            markerWidth="6"
            markerHeight="6"
            orient="auto"
          >
            <path d="M 10 0 L 0 5 L 10 10 z" fill={color} />
          </marker>
          <marker
            id="dim-arrow-right"
            viewBox="0 0 10 10"
            refX="8"
            refY="5"
            markerWidth="6"
            markerHeight="6"
            orient="auto"
          >
            <path d="M 0 0 L 10 5 L 0 10 z" fill={color} />
          </marker>
        </defs>

        {/* Left extension witness line */}
        <line
          x1={`${leftX}%`}
          y1={`${y - 3.5}%`}
          x2={`${leftX}%`}
          y2={`${y + 3.5}%`}
          stroke={color}
          strokeWidth="2.5"
          strokeDasharray="4 2"
          opacity={0.85}
        />

        {/* Right extension witness line */}
        {isTapLanded && (
          <line
            x1={`${rightX}%`}
            y1={`${y - 3.5}%`}
            x2={`${rightX}%`}
            y2={`${y + 3.5}%`}
            stroke={color}
            strokeWidth="2.5"
            strokeDasharray="4 2"
            opacity={0.85}
          />
        )}

        {/* Main dimension line with arrowheads */}
        <line
          x1={`${leftX}%`}
          y1={`${y}%`}
          x2={`${rightX}%`}
          y2={`${y}%`}
          stroke={color}
          strokeWidth="2.5"
          markerStart="url(#dim-arrow-left)"
          markerEnd={isTapLanded ? "url(#dim-arrow-right)" : undefined}
        />
      </svg>

      {/* Precision IBM Plex Mono Metric Chip on 6x12 Chip */}
      {isTapLanded && (
        <div
          style={{
            position: "absolute",
            left: `${leftX + currentSpan / 2}%`,
            top: `${y}%`,
            transform: `translate(-50%, -140%) scale(${interpolate(tapSpring, [0, 1], [0.8, 1.0])})`,
            backgroundColor: "#FAF6EE",
            border: `1.5px solid ${color}`,
            borderRadius: 2,
            padding: "3px 10px",
            boxShadow: "0 2px 8px rgba(0,0,0,0.25)",
            display: "flex",
            alignItems: "center",
            gap: 6,
          }}
        >
          <span
            style={{
              fontFamily: "'IBM Plex Mono', 'Courier Prime', Courier, monospace",
              fontSize: 12,
              fontWeight: 800,
              letterSpacing: 1.5,
              color: color,
              textTransform: "uppercase",
            }}
          >
            {label}
          </span>
        </div>
      )}
    </div>
  );
};
