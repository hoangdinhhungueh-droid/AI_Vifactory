import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { VoxBrassPin, VoxWashiTape } from "./papercraft";
import { PaperDrop } from "./PaperDrop";

export interface PaperStatCardProps {
  statValue: string;
  statLabel?: string;
  isLeft?: boolean;
  dropFrame?: number;
  top?: number;
}

/**
 * Tactile Torn-Paper Stat Card (Zero Digital HUD / Zero Emoji)
 * Replaces dark UI boxes and emojis with physical archival paper pinned to the board,
 * hand-drawn marker underline, and typewriter label.
 */
export const PaperStatCard: React.FC<PaperStatCardProps> = ({
  statValue,
  statLabel,
  isLeft = false,
  dropFrame = 12,
  top = 64,
}) => {
  const frame = useCurrentFrame();
  const relFrame = Math.max(0, frame - dropFrame);
  const markerProgress = interpolate(relFrame, [8, 22], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <PaperDrop
      dropFrame={dropFrame}
      baseRotation={isLeft ? 1.8 : -1.8}
      seed={19}
      style={{
        position: "absolute",
        top,
        left: isLeft ? "auto" : 76,
        right: isLeft ? 76 : "auto",
        zIndex: 30,
        pointerEvents: "none",
      }}
    >
      {/* Physical Washi Tape & Brass Pin */}
      <VoxWashiTape
        x="16%"
        y="-14px"
        rotation={-22}
        corner="top_left"
        dropFrame={dropFrame + 3}
      />
      <VoxBrassPin
        x="88%"
        y="-10px"
        size={24}
        dropFrame={dropFrame + 5}
      />

      <div
        style={{
          backgroundColor: "#FAF6EE",
          backgroundImage:
            "repeating-linear-gradient(0deg, transparent, transparent 23px, rgba(160, 130, 90, 0.14) 24px)",
          border: "2px solid rgba(135, 105, 70, 0.55)",
          borderRadius: 3,
          padding: "16px 28px 18px 28px",
          minWidth: 240,
          display: "flex",
          flexDirection: "column",
          gap: 6,
          fontFamily:
            "'Courier Prime', 'Special Elite', 'Courier New', Courier, monospace",
        }}
      >
        {/* Stamped Archival Header Strip (Zero Emoji) */}
        <div
          style={{
            display: "flex",
            alignItems: "center",
            justifyContent: "space-between",
            borderBottom: "1.5px dashed rgba(120, 90, 60, 0.4)",
            paddingBottom: 4,
            marginBottom: 2,
          }}
        >
          <span
            style={{
              fontSize: 10,
              fontWeight: 900,
              letterSpacing: 2.2,
              color: "#78350F",
              textTransform: "uppercase",
            }}
          >
            EVIDENCE METRIC // RECORD
          </span>
          <span
            style={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              backgroundColor: "#B91C1C",
              display: "inline-block",
            }}
          />
        </div>

        {/* Marker-Struck Quantitative Value */}
        <div style={{ position: "relative", display: "inline-block" }}>
          <div
            style={{
              color: "#991B1B",
              fontSize: 40,
              fontWeight: 900,
              letterSpacing: 1.2,
              lineHeight: 1.08,
            }}
          >
            {statValue}
          </div>
          {/* Hand-drawn felt-tip marker underline sweep */}
          <div
            style={{
              height: 5,
              width: `${(markerProgress * 100).toFixed(1)}%`,
              backgroundColor: "rgba(234, 179, 8, 0.65)",
              borderRadius: 3,
              marginTop: 2,
              transform: "rotate(-0.8deg)",
            }}
          />
        </div>

        {statLabel ? (
          <div
            style={{
              color: "#334155",
              fontSize: 13,
              fontWeight: 800,
              letterSpacing: 1.6,
              textTransform: "uppercase",
              marginTop: 2,
            }}
          >
            {statLabel}
          </div>
        ) : null}
      </div>
    </PaperDrop>
  );
};
