import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

export interface VoxTacticalMapPayload {
  target_name?: string;
  coordinates?: string;
  grid_type?: "radar" | "chokepoint" | "flight_path" | string;
  points_of_interest?: string[];
}

export interface VoxTacticalMapProps {
  title?: string;
  badge?: string;
  theme?: "noir_dossier" | "tech_infographic" | "surveillance_cctv" | string;
  layout?: "split_right" | "split_left" | "fullscreen_dossier" | "floating_card" | string;
  payload?: VoxTacticalMapPayload;
  label?: string;
}

export const VoxTacticalMap: React.FC<VoxTacticalMapProps> = ({
  title,
  badge,
  theme = "surveillance_cctv",
  layout = "split_right",
  payload,
  label,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const themeStyles = {
    noir_dossier: {
      bg: "rgba(12, 16, 26, 0.94)",
      border: "1.5px solid rgba(242, 166, 59, 0.55)",
      headerColor: "#ffd166",
      radarColor: "#f2a63b",
      targetColor: "#ef4444",
      textColor: "#cbd5e1",
      shadow: "0 15px 40px rgba(0,0,0,0.85), inset 0 0 20px rgba(242,166,59,0.12)",
    },
    tech_infographic: {
      bg: "rgba(7, 20, 34, 0.94)",
      border: "1.5px solid rgba(56, 189, 248, 0.55)",
      headerColor: "#38bdf8",
      radarColor: "#38bdf8",
      targetColor: "#ef4444",
      textColor: "#94a3b8",
      shadow: "0 15px 40px rgba(0,0,0,0.85), 0 0 25px rgba(56,189,248,0.2)",
    },
    surveillance_cctv: {
      bg: "rgba(4, 18, 12, 0.95)",
      border: "1.5px solid rgba(34, 197, 94, 0.55)",
      headerColor: "#22c55e",
      radarColor: "#22c55e",
      targetColor: "#ef4444",
      textColor: "#86efac",
      shadow: "0 15px 40px rgba(0,0,0,0.85), 0 0 25px rgba(34,197,94,0.2)",
    },
  };

  const st = themeStyles[theme as keyof typeof themeStyles] || themeStyles.surveillance_cctv;

  const scale = spring({
    frame,
    fps,
    config: { damping: 14, mass: 0.7, stiffness: 120 },
  });

  const opacity = interpolate(frame, [0, 8], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const sweepAngle = (frame * 4) % 360;
  const pingOpacity = Math.sin(frame * 0.25) > 0 ? 1 : 0.3;

  const displayTitle = title || label || "GEO-TACTICAL TELEMETRY // SECTOR GRID";
  const displayBadge = badge || "ACTIVE TELEMETRY";
  const targetName = payload?.target_name || "TACTICAL VECTOR // TARGET INTERCEPT";
  const coordinates = payload?.coordinates || "37.5665°N, 126.9780°E";
  const pois = payload?.points_of_interest || ["PRIMARY CATALYST", "LOGISTICAL CHOKE"];

  const isFullscreen = layout === "fullscreen_dossier";
  const width = isFullscreen ? 880 : 500;

  return (
    <div
      style={{
        width,
        backgroundColor: st.bg,
        border: st.border,
        borderRadius: 14,
        padding: "20px 24px",
        boxShadow: st.shadow,
        zIndex: 28,
        fontFamily: "'Courier New', Courier, monospace",
        opacity,
        transform: `scale(${scale})`,
        transformOrigin: "top center",
      }}
    >
      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          borderBottom: "1px solid rgba(255, 255, 255, 0.15)",
          paddingBottom: 8,
          marginBottom: 16,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: 16 }}>📡</span>
          <span
            style={{
              color: st.headerColor,
              fontSize: 13,
              fontWeight: 900,
              letterSpacing: 1.5,
              textTransform: "uppercase",
            }}
          >
            {displayTitle}
          </span>
        </div>

        <div
          style={{
            border: `1.5px solid ${st.radarColor}`,
            color: st.radarColor,
            fontSize: 11,
            fontWeight: 900,
            letterSpacing: 1.5,
            padding: "2px 8px",
            borderRadius: 4,
            backgroundColor: "rgba(0,0,0,0.4)",
          }}
        >
          {displayBadge}
        </div>
      </div>

      {/* Radar Container and Info Panel */}
      <div style={{ display: "flex", alignItems: "center", gap: 24 }}>
        {/* Animated Radar Sweep Vector Circle */}
        <div
          style={{
            position: "relative",
            width: 140,
            height: 140,
            borderRadius: "50%",
            border: `1.5px solid ${st.radarColor}`,
            overflow: "hidden",
            backgroundColor: "rgba(0,0,0,0.4)",
            flexShrink: 0,
          }}
        >
          <div style={{ position: "absolute", inset: 22, borderRadius: "50%", border: `1px dashed rgba(255,255,255,0.2)` }} />
          <div style={{ position: "absolute", inset: 44, borderRadius: "50%", border: `1px solid rgba(255,255,255,0.15)` }} />
          <div style={{ position: "absolute", top: "50%", left: 0, right: 0, height: 1, backgroundColor: "rgba(255,255,255,0.2)" }} />
          <div style={{ position: "absolute", left: "50%", top: 0, bottom: 0, width: 1, backgroundColor: "rgba(255,255,255,0.2)" }} />

          {/* Sweep Needle */}
          <div
            style={{
              position: "absolute",
              top: "50%",
              left: "50%",
              width: 70,
              height: 2,
              backgroundColor: st.radarColor,
              transformOrigin: "left center",
              transform: `rotate(${sweepAngle}deg)`,
              boxShadow: `0 0 10px ${st.radarColor}`,
            }}
          />

          {/* Threat Target Point */}
          <div
            style={{
              position: "absolute",
              top: 45,
              left: 80,
              width: 10,
              height: 10,
              borderRadius: "50%",
              backgroundColor: st.targetColor,
              opacity: pingOpacity,
              boxShadow: `0 0 12px ${st.targetColor}`,
            }}
          />
        </div>

        {/* Telemetry Information */}
        <div style={{ display: "flex", flexDirection: "column", gap: 6, fontSize: 12, color: st.textColor }}>
          <div>
            <span style={{ color: "rgba(255,255,255,0.4)" }}>TARGET: </span>
            <span style={{ fontWeight: 700, color: "#ffffff" }}>{targetName}</span>
          </div>
          <div>
            <span style={{ color: "rgba(255,255,255,0.4)" }}>COORDINATES: </span>
            <span style={{ color: st.radarColor, fontWeight: 700 }}>{coordinates}</span>
          </div>
          <div>
            <span style={{ color: "rgba(255,255,255,0.4)" }}>GRID TYPE: </span>
            <span>POLAR SECTOR SCAN</span>
          </div>
          {pois.length > 0 ? (
            <div style={{ marginTop: 4 }}>
              <span style={{ color: "rgba(255,255,255,0.4)", fontSize: 11 }}>POINTS OF INTEREST:</span>
              <div style={{ display: "flex", gap: 6, marginTop: 4 }}>
                {pois.map((poi, idx) => (
                  <span
                    key={idx}
                    style={{
                      fontSize: 10,
                      backgroundColor: "rgba(255,255,255,0.08)",
                      padding: "2px 6px",
                      borderRadius: 3,
                    }}
                  >
                    • {poi}
                  </span>
                ))}
              </div>
            </div>
          ) : null}
        </div>
      </div>
    </div>
  );
};
