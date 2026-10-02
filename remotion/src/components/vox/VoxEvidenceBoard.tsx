import React from "react";
import { Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";

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
  const { fps } = useVideoConfig();

  // 12fps stop-motion stepping
  const steppedFrame = Math.floor(frame / 2.5) * 2.5;

  const polaroidDrop = spring({
    frame: steppedFrame,
    fps,
    config: { damping: 11, mass: 0.7, stiffness: 160 },
  });

  const pinPop = spring({
    frame: Math.max(0, steppedFrame - 8),
    fps,
    config: { damping: 9, mass: 0.3, stiffness: 240 },
  });

  const stringDraw = interpolate(frame, [10, 32], [0, 100], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const tagSlam = spring({
    frame: Math.max(0, frame - 20),
    fps,
    config: { damping: 8, mass: 0.5, stiffness: 180 },
  });

  const displayTitle = title || label || "INVESTIGATION DOSSIER // SUBJECT NETWORK";
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
  const width = isFullBleed ? 1040 : 600;

  return (
    <div
      style={{
        width,
        backgroundColor: "rgba(28, 22, 18, 0.95)", // Corkboard / dark investigative surface
        backgroundImage: "radial-gradient(#3a2e24 15%, transparent 16%)",
        backgroundSize: "16px 16px",
        borderRadius: 8,
        border: "3px solid #78350f",
        padding: isFullBleed ? "32px 38px" : "22px 26px",
        boxShadow: "0 25px 60px rgba(0,0,0,0.85), inset 0 0 40px rgba(0,0,0,0.6)",
        fontFamily: "'Courier Prime', 'Special Elite', 'Courier New', Courier, monospace",
        position: "relative",
        overflow: "hidden",
        transform: `scale(${polaroidDrop})`,
        transformOrigin: "center center",
      }}
    >
      {/* Header bar */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          borderBottom: "2px solid #b45309",
          paddingBottom: 10,
          marginBottom: 20,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ fontSize: 20 }}>📌</span>
          <div
            style={{
              color: "#fbbf24",
              fontSize: isFullBleed ? 18 : 14,
              fontWeight: 900,
              letterSpacing: 2,
              textTransform: "uppercase",
            }}
          >
            {displayTitle}
          </div>
        </div>
        <div
          style={{
            backgroundColor: "#ef4444",
            color: "#ffffff",
            fontWeight: 900,
            fontSize: 12,
            letterSpacing: 1.5,
            padding: "4px 12px",
            borderRadius: 4,
            transform: `scale(${tagSlam}) rotate(3deg)`,
          }}
        >
          {displayBadge}
        </div>
      </div>

      {/* Main Board Content: Polaroid on Left, Connections & Charges on Right */}
      <div
        style={{
          display: "flex",
          gap: isFullBleed ? 34 : 20,
          alignItems: "flex-start",
        }}
      >
        {/* Polaroid Card */}
        <div
          style={{
            width: isFullBleed ? 280 : 200,
            backgroundColor: "#ffffff",
            padding: "12px 12px 24px 12px",
            boxShadow: "0 15px 30px rgba(0,0,0,0.65), 0 2px 6px rgba(0,0,0,0.3)",
            transform: `rotate(-3deg) scale(${polaroidDrop})`,
            position: "relative",
            flexShrink: 0,
          }}
        >
          {/* Pushpin at top */}
          <div
            style={{
              position: "absolute",
              top: -10,
              left: "50%",
              transform: `translateX(-50%) scale(${pinPop})`,
              width: 22,
              height: 22,
              borderRadius: "50%",
              backgroundColor: "#ef4444",
              boxShadow: "0 4px 8px rgba(0,0,0,0.6), inset 0 -2px 4px rgba(0,0,0,0.4)",
              zIndex: 30,
              border: "2px solid #ffffff",
            }}
          />

          {/* Photo area */}
          <div
            style={{
              width: "100%",
              height: isFullBleed ? 220 : 160,
              backgroundColor: "#1e293b",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              justifyContent: "center",
              border: "1px solid #cbd5e1",
              position: "relative",
              overflow: "hidden",
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
                }}
              />
            ) : (
              <span style={{ fontSize: 48, opacity: 0.85 }}>👤</span>
            )}
            <div
              style={{
                position: "absolute",
                bottom: 0,
                width: "100%",
                backgroundColor: "rgba(0,0,0,0.75)",
                color: "#f87171",
                fontSize: 11,
                fontWeight: 900,
                textAlign: "center",
                padding: "3px 0",
                letterSpacing: 1,
              }}
            >
              {evidenceTag}
            </div>
          </div>

          {/* Polaroid label text */}
          <div
            style={{
              marginTop: 10,
              textAlign: "center",
              color: "#0f172a",
              fontWeight: 800,
              fontSize: 13,
              letterSpacing: 0.5,
            }}
          >
            {suspectName}
          </div>
          <div
            style={{
              textAlign: "center",
              color: "#64748b",
              fontSize: 10,
              fontWeight: 600,
              marginTop: 2,
            }}
          >
            {evidenceTag}
          </div>
        </div>

        {/* Right Side: Network Connections & Criminal Counts */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 16 }}>
          {/* Suspect Role & Status */}
          <div
            style={{
              backgroundColor: "rgba(0,0,0,0.4)",
              borderLeft: "4px solid #f59e0b",
              padding: "10px 14px",
            }}
          >
            <div style={{ color: "#94a3b8", fontSize: 11, fontWeight: 700, letterSpacing: 1 }}>
              IDENTIFIED ROLE & OPERATION:
            </div>
            <div style={{ color: "#f1f5f9", fontSize: isFullBleed ? 16 : 14, fontWeight: 800, marginTop: 2 }}>
              {role}
            </div>
          </div>

          {/* Red Connecting String to Target Entities */}
          <div>
            <div style={{ color: "#ef4444", fontSize: 12, fontWeight: 900, letterSpacing: 1.5, display: "flex", alignItems: "center", gap: 6 }}>
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
                    backgroundColor: "rgba(239, 68, 68, 0.15)",
                    border: "1.5px solid #ef4444",
                    color: "#fecaca",
                    fontSize: 12,
                    fontWeight: 800,
                    padding: "4px 10px",
                    borderRadius: 4,
                    clipPath: `inset(0 ${100 - stringDraw}% 0 0)`,
                  }}
                >
                  🔗 {ent}
                </div>
              ))}
            </div>
          </div>

          {/* Key Indictment Charges */}
          <div>
            <div style={{ color: "#e2e8f0", fontSize: 12, fontWeight: 800, letterSpacing: 1 }}>
              STATUTORY VIOLATIONS CHARGED:
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 6, marginTop: 6 }}>
              {charges.map((ch, i) => (
                <div
                  key={i}
                  style={{
                    color: "#cbd5e1",
                    fontSize: isFullBleed ? 13 : 11,
                    fontWeight: 600,
                    backgroundColor: "rgba(255,255,255,0.04)",
                    padding: "4px 8px",
                    borderRadius: 3,
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
  );
};
