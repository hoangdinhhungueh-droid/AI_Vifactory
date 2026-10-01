import React from "react";
import { interpolate, useCurrentFrame, useVideoConfig } from "remotion";

export interface ProceduralMarkerSweepProps {
  startFrame?: number;
  durationFrames?: number;
  color?: string; // e.g. "#ffe600", "#38bdf8", "#f59e0b"
  height?: number | string;
  width?: number | string;
  blendMode?: "multiply" | "screen" | "overlay" | "color-burn" | "normal";
  borderRadius?: number;
  slantDeg?: number; // nib tilt, e.g. -2 to -4 deg
  opacity?: number;
  children?: React.ReactNode;
  className?: string;
  style?: React.CSSProperties;
}

/**
 * ProceduralMarkerSweep - Signature Vox-style fluorescent highlighter sweep.
 * Sweeps smoothly from 0% to 100% width across target frames, simulating
 * a real chisel-tip marker drawing across archival document text.
 */
export const ProceduralMarkerSweep: React.FC<ProceduralMarkerSweepProps> = ({
  startFrame = 10,
  durationFrames = 12,
  color = "#ffe600",
  height = "1.25em",
  width = "100%",
  blendMode = "multiply",
  borderRadius = 3,
  slantDeg = -1.8,
  opacity = 0.55,
  children,
  className,
  style,
}) => {
  const frame = useCurrentFrame();

  const relFrame = Math.max(0, frame - startFrame);
  const sweepProgress = interpolate(
    relFrame,
    [0, Math.max(1, durationFrames)],
    [0, 100],
    {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    }
  );

  // Subtle organic jitter on the marker trail edge
  const jitter = Math.sin(frame * 1.5) * 1.5;

  return (
    <span
      className={className}
      style={{
        position: "relative",
        display: "inline-block",
        ...style,
      }}
    >
      {/* Background Marker Sweep Layer */}
      <span
        aria-hidden="true"
        style={{
          position: "absolute",
          left: -4,
          bottom: "8%",
          height,
          width: `${Math.min(100, sweepProgress)}%`,
          backgroundColor: color,
          borderRadius,
          transform: `skewX(${slantDeg}deg)`,
          transformOrigin: "left center",
          opacity: sweepProgress > 0 ? opacity : 0,
          mixBlendMode: blendMode,
          pointerEvents: "none",
          zIndex: 1,
          boxShadow:
            sweepProgress > 0
              ? `0 0 10px ${color}66, inset 0 1px 2px rgba(255,255,255,0.4)`
              : "none",
          transition: "none",
        }}
      >
        {/* Chisel-tip leading head glow */}
        {sweepProgress > 0 && sweepProgress < 100 && (
          <span
            style={{
              position: "absolute",
              right: -3,
              top: 0,
              bottom: 0,
              width: 8 + jitter,
              backgroundColor: color,
              borderRadius: "50%",
              filter: "blur(2px)",
              opacity: 0.8,
            }}
          />
        )}
      </span>

      {/* Foreground Text Layer */}
      <span
        style={{
          position: "relative",
          zIndex: 2,
        }}
      >
        {children}
      </span>
    </span>
  );
};
