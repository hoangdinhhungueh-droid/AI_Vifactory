import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import {
  EAST_ASIA_ROUTE,
  buildRoutePolyline,
  pointAtProgress,
  Waypoint,
} from "../../geo/voxGeo";

export interface VoxInteractiveMapProps {
  title?: string;
  badge?: string;
  theme?: "vox_paper" | "noir_dossier" | "tactical_navy" | string;
  layout?: "full_bleed_focus" | "split_right" | "split_left" | "floating_card" | string;
  payload?: any;
  label?: string;
  drawDurationFrames?: number;
}

export const VoxInteractiveMap: React.FC<VoxInteractiveMapProps> = ({
  title,
  badge,
  theme = "tactical_navy",
  layout = "full_bleed_focus",
  payload,
  label,
  drawDurationFrames = 120,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const isFullBleed = layout === "full_bleed_focus" || layout === "fullscreen_dossier";
  const width = isFullBleed ? 1040 : 580;
  const height = isFullBleed ? 620 : 420;

  // Outer container scale spring
  const containerScale = spring({
    frame,
    fps,
    config: { damping: 14, mass: 0.6, stiffness: 140 },
  });

  const opacity = interpolate(frame, [0, 8], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const waypoints: Waypoint[] = payload?.waypoints || EAST_ASIA_ROUTE;
  const route = React.useMemo(
    () => buildRoutePolyline(waypoints, width, height, isFullBleed ? 80 : 50),
    [waypoints, width, height, isFullBleed]
  );

  // Path drawing progress (0 to 1 over drawDurationFrames)
  const drawProgress = interpolate(frame, [10, 10 + drawDurationFrames], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Current vessel position on the route
  const currentVessel = pointAtProgress(route, drawProgress);

  const displayTitle = title || label || "海上輸入航路 // 中国産タケノコ サプライチェーン";
  const displayBadge = badge || "検疫追跡テレメトリー";

  return (
    <div
      style={{
        width,
        height,
        backgroundColor: "rgba(7, 19, 31, 0.94)",
        border: "1.5px solid rgba(56, 189, 248, 0.45)",
        borderRadius: 14,
        padding: isFullBleed ? "20px 26px" : "14px 18px",
        boxShadow: "0 25px 60px rgba(0, 0, 0, 0.9), 0 0 35px rgba(56, 189, 248, 0.20)",
        zIndex: 30,
        fontFamily: "'Zen Kaku Gothic New', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
        fontFeatureSettings: '"palt" 1',
        opacity,
        transform: `scale(${containerScale})`,
        transformOrigin: "center center",
        pointerEvents: "none",
        color: "#ffffff",
        position: "relative",
        overflow: "hidden",
        display: "flex",
        flexDirection: "column",
      }}
    >
      {/* Blueprint Tactical Grid Lines */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundImage:
            "linear-gradient(to right, rgba(56, 189, 248, 0.08) 1px, transparent 1px), linear-gradient(to bottom, rgba(56, 189, 248, 0.08) 1px, transparent 1px)",
          backgroundSize: "40px 40px",
          pointerEvents: "none",
        }}
      />

      {/* Header HUD Bar */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          borderBottom: "1px solid rgba(56, 189, 248, 0.25)",
          paddingBottom: 8,
          marginBottom: 10,
          position: "relative",
          zIndex: 10,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ fontSize: 18 }}>🧭</span>
          <div>
            <div
              style={{
                color: "#38bdf8",
                fontSize: isFullBleed ? 15 : 12,
                fontWeight: 900,
                letterSpacing: 1.5,
                textTransform: "uppercase",
              }}
            >
              {displayTitle}
            </div>
            <div style={{ fontSize: 10.5, color: "rgba(255, 255, 255, 0.55)", letterSpacing: 0.5 }}>
              EAST CHINA SEA MARITIME LOGISTICS & BIOSECURITY CORRIDOR
            </div>
          </div>
        </div>

        <div
          style={{
            border: "1.5px solid rgba(56, 189, 248, 0.6)",
            color: "#38bdf8",
            fontSize: isFullBleed ? 12 : 10,
            fontWeight: 800,
            letterSpacing: 1,
            padding: "3px 10px",
            borderRadius: 6,
            backgroundColor: "rgba(56, 189, 248, 0.15)",
            textTransform: "uppercase",
          }}
        >
          📍 {displayBadge}
        </div>
      </div>

      {/* SVG Canvas Map */}
      <div style={{ flex: 1, position: "relative" }}>
        <svg
          width="100%"
          height="100%"
          viewBox={`0 0 ${width} ${height - (isFullBleed ? 80 : 60)}`}
          style={{ overflow: "visible" }}
        >
          <defs>
            <linearGradient id="routeGradient" x1="0%" y1="0%" x2="100%" y2="0%">
              <stop offset="0%" stopColor="#f59e0b" />
              <stop offset="50%" stopColor="#ef4444" />
              <stop offset="100%" stopColor="#38bdf8" />
            </linearGradient>
            <filter id="neonGlow" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="3" result="blur" />
              <feComposite in="SourceGraphic" in2="blur" operator="over" />
            </filter>
          </defs>

          {/* Ghost Route Track (Full Static Path Underneath) */}
          <path
            d={route.svgPathString}
            fill="none"
            stroke="rgba(255, 255, 255, 0.12)"
            strokeWidth={3}
            strokeDasharray="6,6"
          />

          {/* Animated Active Route Track */}
          <path
            d={route.svgPathString}
            fill="none"
            stroke="url(#routeGradient)"
            strokeWidth={4}
            strokeDasharray={route.totalLength}
            strokeDashoffset={route.totalLength * (1 - drawProgress)}
            strokeLinecap="round"
            filter="url(#neonGlow)"
          />

          {/* Port Nodes & Waypoint Beacons */}
          {waypoints.map((wp, idx) => {
            const pos = route.points[idx];
            if (!pos) return null;

            const isRevealed = frame >= wp.appearFrame;
            const isQuarantine = wp.kind === "quarantine";
            const nodeColor = isQuarantine ? "#ef4444" : wp.kind === "hub" ? "#f59e0b" : "#38bdf8";

            // Pulse wave ripple radius
            const rippleProgress = (Math.max(0, frame - wp.appearFrame) % 40) / 40;
            const rippleR = interpolate(rippleProgress, [0, 1], [6, 26]);
            const rippleOp = interpolate(rippleProgress, [0, 0.8, 1], [0.8, 0.3, 0]);

            return (
              <g key={wp.id} opacity={isRevealed ? 1 : 0.2}>
                {/* Radar Sonar Ripple */}
                {isRevealed && (
                  <circle
                    cx={pos[0]}
                    cy={pos[1]}
                    r={rippleR}
                    fill="none"
                    stroke={nodeColor}
                    strokeWidth={1.5}
                    opacity={rippleOp}
                  />
                )}

                {/* Node Center Dot */}
                <circle
                  cx={pos[0]}
                  cy={pos[1]}
                  r={isQuarantine ? 7 : 5}
                  fill={nodeColor}
                  stroke="#ffffff"
                  strokeWidth={2}
                  filter="url(#neonGlow)"
                />

                {/* Waypoint Label */}
                <text
                  x={pos[0] + 12}
                  y={pos[1] - (idx % 2 === 0 ? 12 : -18)}
                  fill="#ffffff"
                  fontSize={isFullBleed ? 12 : 10}
                  fontWeight={800}
                  letterSpacing={0.5}
                  style={{
                    textShadow: "0 2px 4px rgba(0,0,0,0.95), 0 0 8px rgba(0,0,0,0.8)",
                  }}
                >
                  {wp.labelJa}
                </text>
              </g>
            );
          })}

          {/* Moving Vessel Container Beacon */}
          {drawProgress > 0 && drawProgress < 1 && (
            <g
              transform={`translate(${currentVessel.pos[0]}, ${currentVessel.pos[1]}) rotate(${currentVessel.headingDeg})`}
            >
              <circle r={10} fill="rgba(239, 68, 68, 0.35)" />
              <polygon points="12,0 -8,-7 -4,0 -8,7" fill="#ef4444" stroke="#ffffff" strokeWidth={1.5} />
            </g>
          )}
        </svg>

        {/* Quarantine Final Alert Callout Tag (Appears at final stage) */}
        {drawProgress >= 0.85 && (
          <div
            style={{
              position: "absolute",
              right: 20,
              bottom: 15,
              backgroundColor: "rgba(45, 10, 15, 0.92)",
              border: "1.5px solid #ef4444",
              borderRadius: 8,
              padding: "8px 14px",
              boxShadow: "0 8px 25px rgba(239, 68, 68, 0.35)",
              display: "flex",
              flexDirection: "column",
              gap: 2,
            }}
          >
            <div style={{ color: "#ef4444", fontSize: 12, fontWeight: 900, letterSpacing: 1 }}>
              🚨 横浜検疫所にて輸入食品検査 摘発
            </div>
            <div style={{ color: "#ffffff", fontSize: 11, fontWeight: 700 }}>
              二酸化硫黄 0.72 g/kg (法定基準値の24倍) を検出
            </div>
          </div>
        )}
      </div>

      {/* Footer Source Reference */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          borderTop: "1px solid rgba(255, 255, 255, 0.1)",
          paddingTop: 8,
          marginTop: 6,
          fontSize: 10,
          color: "rgba(255, 255, 255, 0.65)",
          fontFamily: "'Courier New', Courier, monospace",
        }}
      >
        <span>📄 出典: 厚生労働省 横浜検疫所 食品衛生法違反事例速報</span>
        <span>MERCATOR WGS84 // GEO-RADAR 2.0</span>
      </div>
    </div>
  );
};
