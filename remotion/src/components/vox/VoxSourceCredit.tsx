import React from "react";
import { Easing, interpolate, useCurrentFrame } from "remotion";
import { VoxSourceCreditProps } from "../../types";

export const VoxSourceCredit: React.FC<VoxSourceCreditProps> = ({
  source,
  verifiedDate,
  docketNumber,
  position = "bottom_left",
  theme = "noir",
}) => {
  const frame = useCurrentFrame();

  if (!source) {
    return null;
  }

  // Smooth entrance: subtle slide & fade in first 10 frames
  const slide = interpolate(frame, [0, 10], [-20, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });

  const opacity = interpolate(frame, [0, 8], [0, 0.95], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Positioning coordinates
  const posStyle: React.CSSProperties = {};
  if (position === "bottom_left") {
    posStyle.bottom = 32;
    posStyle.left = 40;
    posStyle.transform = `translateX(${slide}px)`;
  } else if (position === "bottom_right") {
    posStyle.bottom = 32;
    posStyle.right = 40;
    posStyle.transform = `translateX(${-slide}px)`;
  } else if (position === "top_left") {
    posStyle.top = 70;
    posStyle.left = 40;
    posStyle.transform = `translateX(${slide}px)`;
  } else {
    // top_right
    posStyle.top = 70;
    posStyle.right = 40;
    posStyle.transform = `translateX(${-slide}px)`;
  }

  const isPaper = theme === "paper";
  const bg = isPaper ? "rgba(250, 247, 238, 0.92)" : "rgba(10, 15, 24, 0.88)";
  const textColor = isPaper ? "#1e293b" : "#ffffff";
  const borderColor = isPaper ? "rgba(180, 83, 9, 0.4)" : "rgba(255, 255, 255, 0.12)";
  const accentColor = isPaper ? "#b45309" : "#f2a63b";
  const subtextColor = isPaper ? "#64748b" : "rgba(255, 255, 255, 0.6)";

  return (
    <div
      style={{
        position: "absolute",
        ...posStyle,
        zIndex: 35,
        backgroundColor: bg,
        border: `1px solid ${borderColor}`,
        borderLeft: `3.5px solid ${accentColor}`,
        borderRadius: 4,
        padding: "6px 14px",
        boxShadow: "0 8px 25px rgba(0, 0, 0, 0.65), 0 1px 3px rgba(0, 0, 0, 0.4)",
        display: "flex",
        flexDirection: "column",
        gap: 2,
        maxWidth: 440,
        pointerEvents: "none",
        opacity,
        fontFamily: "'Zen Kaku Gothic New', 'Segoe UI', Roboto, sans-serif",
        fontFeatureSettings: '"palt" 1',
      }}
    >
      {/* Meta Tag Line */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 6,
          fontSize: 10,
          fontWeight: 800,
          color: accentColor,
          letterSpacing: 1.2,
          textTransform: "uppercase",
          fontFamily: "'Courier New', Courier, monospace",
        }}
      >
        <span>📰</span>
        <span>出典 / SOURCE REFERENCE</span>
        {verifiedDate ? <span style={{ color: subtextColor }}>• {verifiedDate}</span> : null}
        {docketNumber ? <span style={{ color: subtextColor }}>• {docketNumber}</span> : null}
      </div>

      {/* Main Source Citation String */}
      <div
        style={{
          fontSize: 12,
          fontWeight: 700,
          lineHeight: 1.3,
          color: textColor,
          letterSpacing: 0.2,
        }}
      >
        {source}
      </div>
    </div>
  );
};
