import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

export interface PhysicalStampSlamProps {
  label?: string;
  subLabel?: string;
  theme?: "danger" | "warning" | "success" | "investigation" | "custom";
  color?: string;
  slamFrame?: number;
  rotation?: number; // e.g. -6 to 6 deg
  scaleMultiplier?: number;
  className?: string;
  style?: React.CSSProperties;
}

/**
 * PhysicalStampSlam - Heavy tactile archival stamp slam.
 * Simulates an ink stamp forcefully hitting a document table with
 * spring bounce, dynamic floor contact shadow, and ink distress.
 */
export const PhysicalStampSlam: React.FC<PhysicalStampSlamProps> = ({
  label = "CONFIDENTIAL",
  subLabel = "EVIDENCE FILE // ARCHIVE DEPT",
  theme = "danger",
  color,
  slamFrame = 15,
  rotation = -4.5,
  scaleMultiplier = 1.0,
  className,
  style,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const relFrame = frame - slamFrame;

  // Before slam, hide or hold in air
  if (relFrame < 0) {
    return null;
  }

  // Stamp bounce physics: rapid drop from high altitude with bounce back up then settle
  const springProgress = spring({
    frame: relFrame,
    fps,
    config: {
      damping: 10,
      mass: 0.45,
      stiffness: 150,
    },
    from: 2.4,
    to: 1.0,
  });

  const finalScale = springProgress * scaleMultiplier;

  // Impact micro-shake on the stamp itself for 4 frames post-impact
  const impactJitter =
    relFrame >= 0 && relFrame <= 4
      ? Math.sin(relFrame * Math.PI) * (4 - relFrame) * 1.5
      : 0;

  // Contact shadow under stamp: expands and darkens as stamp reaches surface
  const shadowOpacity = interpolate(relFrame, [0, 2], [0.2, 0.85], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const shadowScale = interpolate(relFrame, [0, 3], [0.6, 1.05], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Color scheme
  const themeColors = {
    danger: { text: "#dc2626", border: "#b91c1c", bg: "rgba(220, 38, 38, 0.08)" },
    warning: { text: "#d97706", border: "#b45309", bg: "rgba(217, 119, 6, 0.08)" },
    success: { text: "#059669", border: "#047857", bg: "rgba(5, 150, 105, 0.08)" },
    investigation: { text: "#f59e0b", border: "#d97706", bg: "rgba(245, 158, 11, 0.08)" },
    custom: { text: color || "#ef4444", border: color || "#ef4444", bg: `${color || "#ef4444"}15` },
  };

  const scheme = themeColors[theme] || themeColors.danger;

  return (
    <div
      className={className}
      style={{
        position: "relative",
        display: "inline-flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        transform: `rotate(${rotation}deg) scale(${finalScale}) translateY(${impactJitter}px)`,
        transformOrigin: "center center",
        pointerEvents: "none",
        zIndex: 22,
        ...style,
      }}
    >
      {/* Dynamic contact shadow */}
      <div
        aria-hidden="true"
        style={{
          position: "absolute",
          bottom: -12,
          width: "90%",
          height: 18,
          borderRadius: "50%",
          background: "radial-gradient(ellipse at center, rgba(0,0,0,0.65) 0%, rgba(0,0,0,0.2) 50%, transparent 80%)",
          transform: `scale(${shadowScale})`,
          opacity: shadowOpacity,
          zIndex: -1,
        }}
      />

      {/* Outer Distressed Border Box */}
      <div
        style={{
          border: `4px solid ${scheme.border}`,
          borderRadius: 8,
          padding: "8px 24px",
          backgroundColor: scheme.bg,
          backdropFilter: "blur(2px)",
          boxShadow: `0 0 0 2px ${scheme.border}44, 0 12px 30px rgba(0,0,0,0.5), inset 0 0 15px ${scheme.border}22`,
          textAlign: "center",
          textTransform: "uppercase",
        }}
      >
        {/* Main Stamp Text */}
        <div
          style={{
            fontFamily: "'Courier New', Courier, monospace, 'Impact'",
            fontWeight: 900,
            fontSize: 38,
            letterSpacing: 4,
            color: scheme.text,
            lineHeight: 1.1,
            textShadow: `0 0 1px ${scheme.text}, 1px 1px 0 rgba(0,0,0,0.4)`,
          }}
        >
          {label}
        </div>

        {/* Sub-label / Dep / File ID */}
        {subLabel && (
          <div
            style={{
              fontFamily: "'Courier New', Courier, monospace",
              fontWeight: 700,
              fontSize: 12,
              letterSpacing: 2,
              color: scheme.text,
              opacity: 0.85,
              marginTop: 4,
              borderTop: `1.5px dashed ${scheme.border}88`,
              paddingTop: 3,
            }}
          >
            {subLabel}
          </div>
        )}
      </div>
    </div>
  );
};
