import React from "react";
import { useCurrentFrame, useVideoConfig, interpolate, spring, Easing } from "remotion";

export interface VoxForensicPaperProps {
  title?: string;
  documentNumber?: string;
  date?: string;
  agency?: string;
  bodyText?: string;
  highlightedPhrase?: string;
  stampText?: string;
  stampColor?: string;
  width?: number;
  height?: number;
  layout?: string;
}

export const VoxForensicPaper: React.FC<VoxForensicPaperProps> = ({
  title = "TREASURY INTERNATIONAL CAPITAL (TIC) REPORT",
  documentNumber = "DOC-SEC-2026-X99",
  date = "JUNE 2026",
  agency = "DEPARTMENT OF THE TREASURY // OFFICE OF INTERNATIONAL AFFAIRS",
  bodyText = "Upon detailed forensic examination of cross-border securities transactions, foreign portfolio allocations shifted abruptly away from direct equity purchases into synthetic derivative hedges and dollar-clearing conduits.",
  highlightedPhrase = "shifted abruptly away from direct equity purchases",
  stampText = "RESTRICTED",
  stampColor = "#dc2626", // Crimson Red
  width = 680,
  height = 440,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Paper Entrance Spring (with subtle 3D perspective tilt)
  const enterSpring = spring({
    frame,
    fps,
    config: { damping: 15, stiffness: 85, mass: 0.9 },
  });

  // Highlighter sweep progress (starts at frame 15, completes at frame 38)
  const highlightProgress = interpolate(frame, [15, 38], [0, 100], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.2, 0.8, 0.2, 1),
  });

  // Stamp Slam Spring (slams down at frame 28 with heavy impact bounce)
  const stampSpring = spring({
    frame: Math.max(0, frame - 25),
    fps,
    config: { damping: 10, stiffness: 120, mass: 0.6 },
  });

  const stampScale = interpolate(stampSpring, [0, 1], [2.2, 1.0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const stampOpacity = interpolate(stampSpring, [0, 0.4, 1], [0, 0.8, 0.92], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        width,
        height,
        backgroundColor: "#f4ede2", // Aged parchment / legal bond color
        backgroundImage: "radial-gradient(#d6cbba 1px, transparent 1px)",
        backgroundSize: "20px 20px",
        borderRadius: 4,
        padding: "32px 36px",
        color: "#1e293b",
        fontFamily: "'Courier Prime', 'Special Elite', 'Courier New', monospace",
        boxShadow:
          "0 30px 60px rgba(0, 0, 0, 0.80), 0 10px 25px rgba(0, 0, 0, 0.50), inset 0 0 40px rgba(180, 150, 120, 0.35)",
        border: "1px solid #d4c5b0",
        transform: `scale(${enterSpring}) rotate(-1.2deg)`,
        opacity: enterSpring,
        zIndex: 28,
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* Top Header: Agency & Serial Code */}
      <div
        style={{
          borderBottom: "2px solid #0f172a",
          paddingBottom: 12,
          marginBottom: 16,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
        }}
      >
        <div>
          <div style={{ fontSize: 10, fontWeight: 900, letterSpacing: 2, color: "#475569" }}>
            {agency}
          </div>
          <div style={{ fontSize: 15, fontWeight: 900, letterSpacing: 1, color: "#0f172a", marginTop: 4 }}>
            {title}
          </div>
        </div>
        <div style={{ textAlign: "right", fontSize: 11, fontWeight: 700, color: "#64748b" }}>
          <div>{documentNumber}</div>
          <div>DATE: {date}</div>
        </div>
      </div>

      {/* Barcode line */}
      <div
        style={{
          height: 14,
          backgroundColor: "#0f172a",
          maskImage:
            "repeating-linear-gradient(90deg, #000 0, #000 2px, transparent 2px, transparent 4px, #000 4px, #000 8px, transparent 8px, transparent 11px)",
          WebkitMaskImage:
            "repeating-linear-gradient(90deg, #000 0, #000 2px, transparent 2px, transparent 4px, #000 4px, #000 8px, transparent 8px, transparent 11px)",
          marginBottom: 18,
          opacity: 0.75,
        }}
      />

      {/* Main Document Body with Highlighter Sweep */}
      <div
        style={{
          fontSize: 16,
          lineHeight: 1.65,
          color: "#1e293b",
          fontWeight: 600,
          position: "relative",
        }}
      >
        {bodyText.includes(highlightedPhrase) ? (
          <>
            {bodyText.split(highlightedPhrase)[0]}
            <span
              style={{
                position: "relative",
                display: "inline",
                fontWeight: 800,
                color: "#000000",
              }}
            >
              {/* The Yellow Highlighter Sweep Overlay */}
              <span
                style={{
                  position: "absolute",
                  left: -4,
                  right: -4,
                  top: -2,
                  bottom: -2,
                  backgroundColor: "rgba(250, 204, 21, 0.72)", // Neon Yellow Highlighter
                  borderRadius: 3,
                  clipPath: `inset(0 ${100 - highlightProgress}% 0 0)`,
                  zIndex: -1,
                  boxShadow: "0 0 10px rgba(250, 204, 21, 0.5)",
                }}
              />
              {highlightedPhrase}
            </span>
            {bodyText.split(highlightedPhrase)[1]}
          </>
        ) : (
          bodyText
        )}
      </div>

      {/* Redacted Bar Decorative Element */}
      <div style={{ marginTop: 20, display: "flex", gap: 12, alignItems: "center" }}>
        <span style={{ fontSize: 11, fontWeight: 700, color: "#64748b" }}>CUSTODY CLUSTER:</span>
        <div style={{ width: 140, height: 16, backgroundColor: "#0f172a", borderRadius: 2 }} />
        <span style={{ fontSize: 11, fontWeight: 700, color: "#64748b" }}>TRANSACTION ID:</span>
        <div style={{ width: 90, height: 16, backgroundColor: "#0f172a", borderRadius: 2 }} />
      </div>

      {/* Red Ink Rubber Stamp Slam */}
      <div
        style={{
          position: "absolute",
          right: 38,
          bottom: 30,
          border: `4px solid ${stampColor}`,
          borderRadius: 8,
          padding: "6px 20px",
          color: stampColor,
          fontFamily: "'Impact', 'Arial Black', sans-serif",
          fontSize: 32,
          fontWeight: 900,
          letterSpacing: 4,
          textTransform: "uppercase",
          transform: `rotate(-14deg) scale(${stampScale})`,
          opacity: stampOpacity,
          maskImage: "radial-gradient(circle, #000 60%, rgba(0,0,0,0.5) 100%)",
          WebkitMaskImage: "radial-gradient(circle, #000 60%, rgba(0,0,0,0.5) 100%)",
          boxShadow: `0 0 15px ${stampColor}44`,
          pointerEvents: "none",
        }}
      >
        {stampText}
      </div>

      {/* Bottom corner fold effect */}
      <div
        style={{
          position: "absolute",
          bottom: 0,
          right: 0,
          width: 0,
          height: 0,
          borderStyle: "solid",
          borderWidth: "0 0 28px 28px",
          borderColor: "transparent transparent #d4c5b0 transparent",
          boxShadow: "-4px -4px 6px rgba(0, 0, 0, 0.15)",
        }}
      />
    </div>
  );
};
