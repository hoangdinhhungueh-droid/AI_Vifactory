import React from "react";
import { Easing, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

export interface OdometerRollupProps {
  startValue?: number;
  endValue?: number;
  prefix?: string; // e.g. "$", "+$"
  suffix?: string; // e.g. "B", "M", "%", " Trillion"
  label?: string; // e.g. "RECORD FOREIGN CAPITAL INFLOW"
  subLabel?: string; // e.g. "TREASURY TIC DATASET // 2024-2025"
  startFrame?: number;
  durationFrames?: number;
  decimals?: number;
  color?: string;
  accentColor?: string;
  showBrackets?: boolean;
  className?: string;
  style?: React.CSSProperties;
}

/**
 * OdometerRollup - High-impact forensic numerical rollup.
 * Numbers dynamically roll up with exponential deceleration, framed
 * by archival data brackets and forensic category metadata.
 */
export const OdometerRollup: React.FC<OdometerRollupProps> = ({
  startValue = 0,
  endValue = 942,
  prefix = "$",
  suffix = "B",
  label = "RECORD FOREIGN INFLOW",
  subLabel = "TREASURY TIC DATASET // CUMULATIVE 12M",
  startFrame = 5,
  durationFrames = 28,
  decimals = 0,
  color = "#ffffff",
  accentColor = "#f59e0b",
  showBrackets = true,
  className,
  style,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const relFrame = Math.max(0, frame - startFrame);

  // Exponential deceleration rollup progress: 0 -> 1
  const progress = interpolate(
    relFrame,
    [0, Math.max(1, durationFrames)],
    [0, 1],
    {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.bezier(0.12, 0.9, 0.25, 1),
    }
  );

  const currentValue = startValue + (endValue - startValue) * progress;

  // Format number with commas and decimals
  const formattedNumber = currentValue.toLocaleString("en-US", {
    minimumFractionDigits: decimals,
    maximumFractionDigits: decimals,
  });

  // Entrance spring for container
  const popSpring = spring({
    frame: relFrame,
    fps,
    config: { damping: 12, stiffness: 120, mass: 0.6 },
  });

  // Brackets expand animation
  const bracketExpand = interpolate(relFrame, [0, 10], [0.6, 1.0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.ease,
  });

  if (frame < startFrame) {
    return null;
  }

  return (
    <div
      className={className}
      style={{
        display: "inline-flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        transform: `scale(${popSpring})`,
        pointerEvents: "none",
        fontFamily: "'Courier New', Courier, monospace, sans-serif",
        ...style,
      }}
    >
      {/* Category / Sub-label header */}
      {label && (
        <div
          style={{
            fontSize: 13,
            fontWeight: 800,
            letterSpacing: 3,
            color: accentColor,
            textTransform: "uppercase",
            marginBottom: 6,
            display: "flex",
            alignItems: "center",
            gap: 6,
          }}
        >
          <span
            style={{
              width: 6,
              height: 6,
              borderRadius: "50%",
              backgroundColor: accentColor,
              boxShadow: `0 0 8px ${accentColor}`,
            }}
          />
          {label}
        </div>
      )}

      {/* Main Counter Body */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 12,
          padding: "6px 16px",
          backgroundColor: "rgba(5, 9, 13, 0.85)",
          border: `1.5px solid ${accentColor}55`,
          borderRadius: 10,
          boxShadow: `0 12px 35px rgba(0,0,0,0.7), inset 0 0 15px ${accentColor}15`,
        }}
      >
        {/* Left Bracket */}
        {showBrackets && (
          <span
            style={{
              fontSize: 54,
              fontWeight: 300,
              color: accentColor,
              transform: `scaleY(${bracketExpand})`,
              lineHeight: 1,
            }}
          >
            [
          </span>
        )}

        {/* Counter Number */}
        <span
          style={{
            fontSize: 58,
            fontWeight: 900,
            letterSpacing: -1,
            color,
            textShadow: `0 0 20px ${accentColor}66, 0 4px 12px rgba(0,0,0,0.9)`,
            lineHeight: 1,
          }}
        >
          {prefix}
          {formattedNumber}
          {suffix}
        </span>

        {/* Right Bracket */}
        {showBrackets && (
          <span
            style={{
              fontSize: 54,
              fontWeight: 300,
              color: accentColor,
              transform: `scaleY(${bracketExpand})`,
              lineHeight: 1,
            }}
          >
            ]
          </span>
        )}
      </div>

      {/* Footer provenance / Dataset reference */}
      {subLabel && (
        <div
          style={{
            fontSize: 11,
            fontWeight: 600,
            letterSpacing: 1.5,
            color: "#94a3b8",
            marginTop: 6,
            textTransform: "uppercase",
            opacity: 0.8,
          }}
        >
          {subLabel}
        </div>
      )}
    </div>
  );
};
