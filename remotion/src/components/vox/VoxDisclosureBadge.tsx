import React from "react";
import { VoxDisclosureBadgeProps } from "../../types";

export const VoxDisclosureBadge: React.FC<VoxDisclosureBadgeProps> = ({
  text = "※イメージ映像・再現",
  subtext,
  position = "bottom_right",
  theme = "dark",
  isAiGenerated = true,
}) => {
  if (isAiGenerated === false) {
    return null;
  }

  // Positioning coordinates
  const posStyle: React.CSSProperties = {};
  if (position === "bottom_right") {
    posStyle.bottom = 26;
    posStyle.right = 36;
  } else if (position === "bottom_left") {
    posStyle.bottom = 26;
    posStyle.left = 36;
  } else if (position === "top_left") {
    posStyle.top = 70;
    posStyle.left = 36;
  } else {
    // top_right
    posStyle.top = 70;
    posStyle.right = 36;
  }

  const isGlass = theme === "glass";
  const bg = isGlass ? "rgba(255, 255, 255, 0.12)" : "rgba(5, 9, 14, 0.72)";
  const border = isGlass ? "1px solid rgba(255, 255, 255, 0.3)" : "1px solid rgba(255, 255, 255, 0.18)";

  return (
    <div
      style={{
        position: "absolute",
        ...posStyle,
        zIndex: 36,
        backgroundColor: bg,
        border,
        borderRadius: 4,
        padding: "4px 10px",
        boxShadow: "0 4px 14px rgba(0, 0, 0, 0.5)",
        display: "flex",
        alignItems: "center",
        gap: 6,
        pointerEvents: "none",
        fontFamily: "'Zen Kaku Gothic New', 'Hiragino Sans', 'Yu Gothic', sans-serif",
        fontFeatureSettings: '"palt" 1',
      }}
    >
      <span
        style={{
          fontSize: 12,
          fontWeight: 700,
          color: "rgba(255, 255, 255, 0.90)",
          letterSpacing: 0.6,
          textShadow: "0 1px 3px rgba(0, 0, 0, 0.9)",
          lineHeight: 1,
        }}
      >
        {text}
      </span>

      {subtext ? (
        <span
          style={{
            fontSize: 9.5,
            fontWeight: 800,
            color: "rgba(255, 255, 255, 0.55)",
            letterSpacing: 1,
            textTransform: "uppercase",
            fontFamily: "'Courier New', Courier, monospace",
            lineHeight: 1,
          }}
        >
          // {subtext}
        </span>
      ) : null}
    </div>
  );
};
