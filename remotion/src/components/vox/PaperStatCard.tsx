import React from "react";
import { interpolate, useCurrentFrame } from "remotion";
import { VoxBrassPin, VoxWashiTape } from "./papercraft";
import { PaperDrop } from "./PaperDrop";

export interface PaperStatCardProps {
  statValue: string;
  statLabel?: string;
  sourceTag?: string;
  isLeft?: boolean;
  dropFrame?: number;
  top?: number;
}

/**
 * Tactile Torn-Paper Stat Card (Zero Digital HUD / Zero Emoji)
 * Adheres to Swiss Extreme Scale Contrast (Opuscar swiss-motion box):
 * - Giant stat numbers (hero character, 30-35% mass)
 * - Precision IBM Plex Mono source tag on 6x12 chip
 * - Physical archival paper pinned to the board with hand-drawn marker underline
 */
export const PaperStatCard: React.FC<PaperStatCardProps> = ({
  statValue,
  statLabel,
  sourceTag,
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
      baseRotation={isLeft ? -1.8 : 1.8}
      seed={19}
      style={{
        position: "absolute",
        top,
        left: isLeft ? 76 : "auto",
        right: isLeft ? "auto" : 76,
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
          minWidth: 260,
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

        {/* Marker-Struck Quantitative Value (Swiss Extreme Scale Contrast) */}
        <div style={{ position: "relative", display: "inline-block" }}>
          <div
            style={{
              color: "#B91C1C",
              fontSize: 54,
              fontWeight: 900,
              letterSpacing: 1.5,
              lineHeight: 1.0,
              fontFamily: "'Franklin Gothic Heavy', 'Arial Black', Impact, sans-serif",
            }}
          >
            {statValue}
          </div>
          {/* Hand-drawn felt-tip marker underline sweep */}
          <div
            style={{
              height: 6,
              width: `${(markerProgress * 100).toFixed(1)}%`,
              backgroundColor: "rgba(234, 179, 8, 0.75)",
              borderRadius: 3,
              marginTop: 3,
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
              marginTop: 3,
            }}
          >
            {statLabel}
          </div>
        ) : null}

        {/* Precision IBM Plex Mono source tag on 6x12 chip */}
        <div
          style={{
            fontFamily: "'IBM Plex Mono', 'Courier Prime', Courier, monospace",
            fontSize: 9,
            fontWeight: 700,
            letterSpacing: 1.4,
            color: "#475569",
            backgroundColor: "#E2E8F0",
            padding: "2px 8px",
            borderRadius: 2,
            alignSelf: "flex-start",
            marginTop: 6,
            border: "1px solid #CBD5E1",
            textTransform: "uppercase",
          }}
        >
          {sourceTag || "SOURCE: VERIFIED FORENSIC DOSSIER"}
        </div>
      </div>
    </PaperDrop>
  );
};
