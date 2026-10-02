import React from "react";
import { Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";
import { VoxBrassPin, VoxWashiTape, VoxConnectingYarn } from "./papercraft";

export interface VoxEvidenceBoardPayload {
  suspect_name?: string;
  role?: string;
  photo_url?: string;
  charges?: string[];
  connected_entities?: string[];
  evidence_tag?: string;
}

export interface VoxEvidenceBoardProps {
  title?: string;
  badge?: string;
  theme?: "vox_paper" | "noir_dossier" | string;
  layout?: "full_bleed_focus" | "split_right" | "split_left" | string;
  payload?: VoxEvidenceBoardPayload;
  label?: string;
}

export const VoxEvidenceBoard: React.FC<VoxEvidenceBoardProps> = ({
  title,
  badge,
  theme = "vox_paper",
  layout = "full_bleed_focus",
  payload,
  label,
}) => {
  const frame = useCurrentFrame();
  const { fps, width: canvasW = 1920, height: canvasH = 1080 } = useVideoConfig();

  // 12fps stop-motion stepping
  const steppedFrame = Math.floor(frame / 2.5) * 2.5;

  const boardDrop = spring({
    frame: steppedFrame,
    fps,
    config: { damping: 13, mass: 0.65, stiffness: 120 },
  });

  const polaroidDrop = spring({
    frame: Math.max(0, steppedFrame - 6),
    fps,
    config: { damping: 11, mass: 0.55, stiffness: 140 },
  });

  const pinPop = spring({
    frame: Math.max(0, steppedFrame - 12),
    fps,
    config: { damping: 9, mass: 0.35, stiffness: 220 },
  });

  const tagSlam = spring({
    frame: Math.max(0, frame - 18),
    fps,
    config: { damping: 8, mass: 0.45, stiffness: 180 },
  });

  const displayTitle = title || label || "INVESTIGATION DOSSIER // EVIDENCE NETWORK";
  const suspectName = payload?.suspect_name || "PRIMARY SUBJECT // PERSON OF INTEREST";
  const role = payload?.role || "OPERATIONAL EXECUTIVE / TARGET ENTITY";
  const charges = payload?.charges || [
    "REGULATORY NON-COMPLIANCE AUDIT",
    "INTERNAL CONTROL VIOLATION",
    "FALSIFICATION OF STATUTORY RECORDS"
  ];
  const connected = payload?.connected_entities || [
    "REGULATORY OVERSIGHT COMMISSION",
    "CORPORATE EXECUTIVE COMMITTEE",
    "TECHNICAL AUDIT LOGS"
  ];
  const displayBadge = badge || "CRIMINAL INDICTMENT";
  const evidenceTag = payload?.evidence_tag || "EVIDENCE ITEM #42";

  const isFullBleed = layout === "full_bleed_focus" || layout === "fullscreen_dossier";
  const width = isFullBleed ? 1120 : 660;

  // Deckle edge ragged polygon for board
  const decklePolygon = `polygon(
    0% 3px, 3% 0px, 8% 4px, 15% 1px, 24% 4px, 33% 0px, 42% 3px, 51% 1px, 60% 4px, 70% 0px, 80% 3px, 90% 1px, 98% 3px, 100% 0px,
    99% 12%, 100% 25%, 98% 38%, 100% 50%, 99% 64%, 100% 76%, 98% 88%, 100% 100%,
    96% 99%, 86% 100%, 75% 98%, 65% 100%, 54% 97%, 42% 100%, 30% 98%, 18% 100%, 8% 97%, 0% 100%,
    2% 88%, 0% 74%, 3% 60%, 1% 45%, 2% 30%, 0% 15%
  )`;

  return (
    <div
      style={{
        width,
        position: "relative",
        transform: `scale(${boardDrop}) rotate(-0.5deg)`,
        transformOrigin: "center center",
        pointerEvents: "none",
        zIndex: 26,
        filter: "drop-shadow(0 20px 45px rgba(45, 30, 15, 0.28)) drop-shadow(0 4px 10px rgba(0, 0, 0, 0.15))",
      }}
    >
      {/* 4 Corner Washi Tape Anchors (Authentic Documentary Feel per intro_sec_08.jpg) */}
      <VoxWashiTape x="4%" y="2%" corner="top_left" dropFrame={8} />
      <VoxWashiTape x="96%" y="2%" corner="top_right" dropFrame={10} />
      <VoxWashiTape x="4%" y="98%" corner="bottom_left" dropFrame={12} />
      <VoxWashiTape x="96%" y="98%" corner="bottom_right" dropFrame={14} />

      {/* Main Tactile Aged Manila / Blueprint Board */}
      <div
        style={{
          width: "100%",
          backgroundColor: "#FAF7EE", // Aged archival paper surface
          backgroundImage: `
            radial-gradient(rgba(120, 80, 40, 0.08) 1.5px, transparent 1.5px),
            linear-gradient(to right, rgba(0, 0, 0, 0.04) 1px, transparent 1px),
            linear-gradient(to bottom, rgba(0, 0, 0, 0.04) 1px, transparent 1px)
          `,
          backgroundSize: "24px 24px, 120px 120px, 120px 120px",
          border: "1.5px solid rgba(160, 130, 90, 0.4)",
          clipPath: decklePolygon,
          padding: isFullBleed ? "32px 42px" : "22px 28px",
          fontFamily: "'Courier Prime', 'Special Elite', 'Courier New', Courier, monospace",
          color: "#0F172A",
          boxSizing: "border-box",
        }}
      >
        {/* Header bar */}
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            borderBottom: "1.5px solid #1E293B",
            paddingBottom: 10,
            marginBottom: 20,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            {/* 3D Brass Pin on Header */}
            <div style={{ position: "relative", width: 24, height: 24 }}>
              <VoxBrassPin x={12} y={12} size={22} dropFrame={4} />
            </div>
            <div
              style={{
                color: "#92400E",
                fontSize: isFullBleed ? 16 : 13,
                fontWeight: 900,
                letterSpacing: 2,
                textTransform: "uppercase",
              }}
            >
              {displayTitle}
            </div>
          </div>

          {/* Stamped Red Seal Badge */}
          <div
            style={{
              backgroundColor: "#DC2626",
              color: "#FFFFFF",
              fontWeight: 900,
              fontSize: 11,
              letterSpacing: 1.5,
              padding: "4px 14px",
              borderRadius: 3,
              boxShadow: "0 4px 10px rgba(220, 38, 38, 0.35)",
              transform: `scale(${tagSlam}) rotate(-2deg)`,
              fontFamily: "'Impact', 'Arial Black', sans-serif",
              textTransform: "uppercase",
            }}
          >
            {displayBadge}
          </div>
        </div>

        {/* Main Board Content: Polaroid on Left, Connections & Charges on Right */}
        <div
          style={{
            display: "flex",
            gap: isFullBleed ? 36 : 22,
            alignItems: "flex-start",
          }}
        >
          {/* Polaroid Card with Brass Pin and Tape */}
          <div
            style={{
              width: isFullBleed ? 290 : 210,
              backgroundColor: "#FFFFFF",
              padding: "12px 12px 28px 12px",
              boxShadow: "0 14px 28px rgba(0, 0, 0, 0.25), 0 2px 6px rgba(0, 0, 0, 0.15)",
              transform: `rotate(-2.5deg) scale(${polaroidDrop})`,
              position: "relative",
              flexShrink: 0,
              border: "1px solid #E2E8F0",
            }}
          >
            {/* 3D Brass Pin at Top Center of Polaroid */}
            <div style={{ position: "absolute", top: 4, left: "50%", zIndex: 40 }}>
              <VoxBrassPin x={0} y={0} size={24} dropFrame={14} />
            </div>

            {/* Photo area */}
            <div
              style={{
                width: "100%",
                height: isFullBleed ? 220 : 160,
                backgroundColor: "#F1F5F9",
                display: "flex",
                flexDirection: "column",
                alignItems: "center",
                justifyContent: "center",
                border: "1px solid #CBD5E1",
                position: "relative",
                overflow: "hidden",
                marginTop: 8,
              }}
            >
              {payload?.photo_url ? (
                <Img
                  src={payload.photo_url.startsWith("http") ? payload.photo_url : staticFile(payload.photo_url)}
                  style={{
                    width: "100%",
                    height: "100%",
                    objectFit: "cover",
                    objectPosition: "top center",
                    filter: "contrast(1.15) brightness(0.96)",
                  }}
                />
              ) : (
                <span style={{ fontSize: 48, opacity: 0.85 }}>👤</span>
              )}

              {/* Tag at bottom of photo */}
              <div
                style={{
                  position: "absolute",
                  bottom: 0,
                  width: "100%",
                  backgroundColor: "rgba(15, 23, 42, 0.85)",
                  color: "#FEF08A",
                  fontSize: 10,
                  fontWeight: 900,
                  textAlign: "center",
                  padding: "3px 0",
                  letterSpacing: 1,
                  fontFamily: "'Courier New', Courier, monospace",
                }}
              >
                {evidenceTag}
              </div>
            </div>

            {/* Polaroid handwritten label text */}
            <div
              style={{
                marginTop: 10,
                textAlign: "center",
                color: "#0F172A",
                fontWeight: 900,
                fontSize: 12,
                letterSpacing: 0.5,
                textTransform: "uppercase",
              }}
            >
              {suspectName}
            </div>
          </div>

          {/* Right Side: Network Connections & Statutory Charges */}
          <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 16 }}>
            {/* Suspect Role & Status */}
            <div
              style={{
                backgroundColor: "#F4EDE1",
                borderLeft: "4px solid #B45309",
                padding: "10px 14px",
                borderRadius: 2,
              }}
            >
              <div style={{ color: "#78350F", fontSize: 10, fontWeight: 800, letterSpacing: 1 }}>
                IDENTIFIED ROLE & OPERATION:
              </div>
              <div style={{ color: "#0F172A", fontSize: isFullBleed ? 15 : 13, fontWeight: 900, marginTop: 2 }}>
                {role}
              </div>
            </div>

            {/* Red Connecting Yarn / Conspiracy Vectors */}
            <div>
              <div
                style={{
                  color: "#DC2626",
                  fontSize: 11,
                  fontWeight: 900,
                  letterSpacing: 1.5,
                  display: "flex",
                  alignItems: "center",
                  gap: 6,
                }}
              >
                <span>🧵</span>
                <span>CONSPIRACY VECTOR CONNECTIONS:</span>
              </div>
              <div
                style={{
                  display: "flex",
                  flexWrap: "wrap",
                  gap: 8,
                  marginTop: 8,
                }}
              >
                {connected.map((ent, i) => (
                  <div
                    key={i}
                    style={{
                      backgroundColor: "#FEF2F2",
                      border: "1.5px solid #DC2626",
                      color: "#991B1B",
                      fontSize: 11,
                      fontWeight: 900,
                      padding: "4px 10px",
                      borderRadius: 3,
                      boxShadow: "0 2px 5px rgba(220, 38, 38, 0.15)",
                    }}
                  >
                    🔗 {ent}
                  </div>
                ))}
              </div>
            </div>

            {/* Key Indictment Charges */}
            <div>
              <div style={{ color: "#475569", fontSize: 11, fontWeight: 800, letterSpacing: 1 }}>
                STATUTORY VIOLATIONS CHARGED:
              </div>
              <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 6 }}>
                {charges.map((ch, i) => (
                  <div
                    key={i}
                    style={{
                      color: "#1E293B",
                      fontSize: isFullBleed ? 12 : 11,
                      fontWeight: 700,
                      backgroundColor: "rgba(0, 0, 0, 0.04)",
                      borderLeft: "3px solid #64748B",
                      padding: "4px 10px",
                      borderRadius: 2,
                    }}
                  >
                    ⚖️ {ch}
                  </div>
                ))}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
