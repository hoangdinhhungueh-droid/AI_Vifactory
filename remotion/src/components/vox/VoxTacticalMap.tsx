import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

export interface VoxTacticalMapPayload {
  target_name?: string;
  coordinates?: string;
  grid_type?: "radar" | "chokepoint" | "flight_path" | string;
  points_of_interest?: string[];
  map_region?: string;
}

export interface VoxTacticalMapProps {
  title?: string;
  badge?: string;
  theme?: "vox_paper" | "noir_dossier" | "tech_infographic" | "surveillance_cctv" | string;
  layout?: "full_bleed_focus" | "split_right" | "split_left" | "fullscreen_dossier" | string;
  payload?: VoxTacticalMapPayload;
  label?: string;
}

export const VoxTacticalMap: React.FC<VoxTacticalMapProps> = ({
  title,
  badge,
  theme = "vox_paper",
  layout = "full_bleed_focus",
  payload,
  label,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Stop motion 12fps stepping
  const steppedFrame = Math.floor(frame / 2.5) * 2.5;

  const mapDrop = spring({
    frame: steppedFrame,
    fps,
    config: { damping: 12, mass: 0.8, stiffness: 140 },
  });

  const pinDrop = spring({
    frame: Math.max(0, steppedFrame - 10),
    fps,
    config: { damping: 8, mass: 0.4, stiffness: 220 },
  });

  const routeDraw = interpolate(frame, [8, 36], [0, 100], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const displayTitle = title || label || "GEO-TACTICAL TELEMETRY // SECTOR GRID";
  const displayBadge = badge || "LOCATIONAL EVIDENCE";
  const targetName = payload?.target_name || "TARGET OPERATION SECTOR";
  const coordinates = payload?.coordinates || "COORDINATES // INCIDENT GRID";
  const mapRegion = payload?.map_region || "REGIONAL INVESTIGATION SECTOR";
  const pois = payload?.points_of_interest || ["PRIMARY LOCATION", "INTERMEDIARY FACILITY", "REGULATORY CHOKEPOINT"];

  const isFullBleed = layout === "full_bleed_focus" || layout === "fullscreen_dossier";
  const width = isFullBleed ? 1040 : 600;
  const isPaper = theme === "vox_paper";

  return (
    <div
      style={{
        width,
        backgroundColor: isPaper ? "#fdfbf7" : "rgba(12, 16, 26, 0.94)",
        borderRadius: 6,
        border: isPaper ? "2px solid #d97706" : "1.5px solid rgba(242, 166, 59, 0.55)",
        padding: isFullBleed ? "28px 36px" : "20px 24px",
        boxShadow: "0 25px 60px rgba(0,0,0,0.75), 0 4px 12px rgba(0,0,0,0.3)",
        fontFamily: "'Courier Prime', 'Special Elite', 'Courier New', Courier, monospace",
        position: "relative",
        overflow: "hidden",
        transform: `scale(${mapDrop}) rotate(-0.5deg)`,
        transformOrigin: "center center",
      }}
    >
      {/* Scotch tape on top corners */}
      <div
        style={{
          position: "absolute",
          top: -8,
          left: 40,
          width: 80,
          height: 24,
          backgroundColor: "rgba(255, 255, 255, 0.5)",
          backdropFilter: "blur(1px)",
          transform: "rotate(-15deg)",
          zIndex: 20,
        }}
      />
      <div
        style={{
          position: "absolute",
          top: -8,
          right: 40,
          width: 80,
          height: 24,
          backgroundColor: "rgba(255, 255, 255, 0.5)",
          backdropFilter: "blur(1px)",
          transform: "rotate(15deg)",
          zIndex: 20,
        }}
      />

      {/* Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          borderBottom: `2px solid ${isPaper ? "#d97706" : "#f59e0b"}`,
          paddingBottom: 8,
          marginBottom: 16,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: 18 }}>🗺️</span>
          <span
            style={{
              color: isPaper ? "#92400e" : "#ffd166",
              fontSize: isFullBleed ? 15 : 12,
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
            backgroundColor: "#b45309",
            color: "#ffffff",
            fontSize: 11,
            fontWeight: 900,
            letterSpacing: 1.5,
            padding: "3px 10px",
            borderRadius: 4,
          }}
        >
          {displayBadge}
        </div>
      </div>

      {/* Map Layout: Left side Stylized Grid Map, Right side Facility Details */}
      <div style={{ display: "flex", gap: 24, alignItems: "center" }}>
        {/* Paper Map Canvas Simulation */}
        <div
          style={{
            width: isFullBleed ? 440 : 260,
            height: isFullBleed ? 240 : 180,
            backgroundColor: isPaper ? "#f5efe1" : "#0f172a",
            border: "1.5px solid #cbd5e1",
            borderRadius: 4,
            position: "relative",
            overflow: "hidden",
            flexShrink: 0,
            boxShadow: "inset 0 2px 8px rgba(0,0,0,0.15)",
          }}
        >
          {/* Topographical grid lines */}
          <div
            style={{
              position: "absolute",
              inset: 0,
              backgroundImage: "linear-gradient(#e2d9c2 1px, transparent 1px), linear-gradient(90deg, #e2d9c2 1px, transparent 1px)",
              backgroundSize: "30px 30px",
              opacity: 0.6,
            }}
          />

          {/* Animated Route Line connecting points */}
          <svg
            style={{
              position: "absolute",
              inset: 0,
              width: "100%",
              height: "100%",
            }}
          >
            <path
              d="M 40 180 Q 120 80 240 120 T 380 60"
              fill="none"
              stroke="#dc2626"
              strokeWidth="3.5"
              strokeDasharray="6 4"
              strokeDashoffset={100 - routeDraw}
            />
            {/* POI dots */}
            <circle cx="40" cy="180" r="5" fill="#1e293b" />
            <circle cx="240" cy="120" r="5" fill="#1e293b" />
          </svg>

          {/* Target Red Pin with Bounce */}
          <div
            style={{
              position: "absolute",
              top: isFullBleed ? 38 : 28,
              left: isFullBleed ? 360 : 200,
              transform: `scale(${pinDrop})`,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              zIndex: 10,
            }}
          >
            <div
              style={{
                width: 20,
                height: 20,
                borderRadius: "50%",
                backgroundColor: "#dc2626",
                boxShadow: "0 0 10px #dc2626",
                border: "2px solid #ffffff",
              }}
            />
            <div style={{ width: 3, height: 16, backgroundColor: "#dc2626" }} />
          </div>

          {/* Target Highlight Circle (Yellow Highlighter Pen ring) */}
          <div
            style={{
              position: "absolute",
              top: isFullBleed ? 40 : 30,
              left: isFullBleed ? 345 : 185,
              width: 50,
              height: 50,
              borderRadius: "50%",
              border: "4px solid #facc15",
              backgroundColor: "rgba(250, 204, 21, 0.25)",
              mixBlendMode: "multiply",
              pointerEvents: "none",
            }}
          />

          {/* Region Label Watermark */}
          <div
            style={{
              position: "absolute",
              bottom: 8,
              left: 10,
              fontSize: 10,
              fontWeight: 800,
              color: "#64748b",
              letterSpacing: 1,
            }}
          >
            SECTOR: {mapRegion}
          </div>
        </div>

        {/* Right side Location Breakdown */}
        <div style={{ flex: 1, display: "flex", flexDirection: "column", gap: 10 }}>
          <div>
            <div style={{ color: "#b45309", fontSize: 11, fontWeight: 800, letterSpacing: 1 }}>
              LOCATIONAL TARGET:
            </div>
            <div
              style={{
                color: isPaper ? "#0f172a" : "#ffffff",
                fontSize: isFullBleed ? 17 : 14,
                fontWeight: 900,
                marginTop: 2,
              }}
            >
              📍 {targetName}
            </div>
          </div>

          <div>
            <div style={{ color: "#64748b", fontSize: 10, fontWeight: 700 }}>
              COORDINATES / JURISDICTION:
            </div>
            <div
              style={{
                color: isPaper ? "#334155" : "#93c5fd",
                fontSize: 12,
                fontWeight: 700,
                marginTop: 2,
              }}
            >
              {coordinates}
            </div>
          </div>

          <div>
            <div style={{ color: "#64748b", fontSize: 10, fontWeight: 800, marginTop: 4 }}>
              CONNECTED SURVEILLANCE POINTS:
            </div>
            <div style={{ display: "flex", flexDirection: "column", gap: 4, marginTop: 4 }}>
              {pois.map((poi, idx) => (
                <div
                  key={idx}
                  style={{
                    fontSize: 11,
                    color: isPaper ? "#1e293b" : "#e2e8f0",
                    fontWeight: 700,
                    backgroundColor: isPaper ? "rgba(0,0,0,0.04)" : "rgba(255,255,255,0.06)",
                    padding: "3px 8px",
                    borderRadius: 3,
                    borderLeft: "3px solid #dc2626",
                  }}
                >
                  • {poi}
                </div>
              ))}
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
