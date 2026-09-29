import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

export interface CapitalFlow {
  from: "TYO" | "LON" | "SEL" | "FRA" | "ZUR" | "HKG" | string;
  to: "NYC" | "WST" | string;
  fromLabel?: string;
  toLabel?: string;
  amount: number;
  amountDisplay?: string;
  delayFrames?: number;
}

export interface CapitalFlowMapProps {
  title?: string;
  badge?: string;
  flows?: CapitalFlow[];
  market?: "EN" | "JP" | "KR" | string;
  theme?: "wall_st_noir" | "tactical_audit" | string;
  layout?: "fullscreen_focus" | "split_right" | "floating_card" | string;
  label?: string;
}

// Normalized coordinate map for major financial epicenters (1920 x 1080 canvas)
const HUBS: Record<string, { x: number; y: number; name: string }> = {
  NYC: { x: 540, y: 390, name: "NEW YORK // WALL ST" },
  WST: { x: 540, y: 390, name: "NEW YORK // WALL ST" },
  LON: { x: 970, y: 320, name: "LONDON // CITY" },
  FRA: { x: 1040, y: 330, name: "FRANKFURT // ECB" },
  ZUR: { x: 1050, y: 350, name: "ZURICH // SIX" },
  TYO: { x: 1610, y: 430, name: "TOKYO // KABUTOCHO" },
  SEL: { x: 1530, y: 420, name: "SEOUL // YEOUIDO" },
  HKG: { x: 1470, y: 530, name: "HONG KONG // HKEX" },
};

export const CapitalFlowMap: React.FC<CapitalFlowMapProps> = ({
  title = "GLOBAL CAPITAL VECTORS // TREASURY & EQUITY INFLOW",
  badge = "FED FLOW AUDIT",
  flows = [
    { from: "TYO", to: "NYC", amount: 426, amountDisplay: "$426B", delayFrames: 0 },
    { from: "LON", to: "NYC", amount: 314, amountDisplay: "$314B", delayFrames: 15 },
    { from: "SEL", to: "NYC", amount: 202, amountDisplay: "$202B", delayFrames: 30 },
  ],
  market = "EN",
  theme = "wall_st_noir",
  layout = "fullscreen_focus",
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const isFullBleed = layout === "fullscreen_focus";
  const width = isFullBleed ? 1160 : 720;
  const height = isFullBleed ? 680 : 460;

  const containerSpring = spring({
    frame,
    fps,
    config: { damping: 14, mass: 0.7, stiffness: 130 },
  });

  const opacity = interpolate(frame, [0, 8], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <div
      style={{
        position: "absolute",
        top: isFullBleed ? "8%" : "12%",
        left: isFullBleed ? "20%" : "30%",
        width,
        height,
        opacity,
        transform: `scale(${containerSpring})`,
        transformOrigin: "center center",
        backgroundColor: "rgba(10, 15, 26, 0.95)",
        border: "1.5px solid rgba(56, 189, 248, 0.45)",
        borderRadius: 8,
        padding: "20px 24px",
        boxShadow: "0 20px 50px rgba(0,0,0,0.85), inset 0 0 25px rgba(56, 189, 248, 0.08)",
        backdropFilter: "blur(12px)",
        color: "#e2e8f0",
        fontFamily: "'Inter', -apple-system, sans-serif",
        zIndex: 10,
      }}
    >
      {/* Header Bar */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          borderBottom: "1px solid rgba(255,255,255,0.12)",
          paddingBottom: 10,
          marginBottom: 14,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <div
            style={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              backgroundColor: "#38bdf8",
              boxShadow: "0 0 8px #38bdf8",
            }}
          />
          <span style={{ fontSize: 13, fontWeight: 800, letterSpacing: 1.5, color: "#38bdf8" }}>
            {title}
          </span>
        </div>
        <div
          style={{
            fontSize: 11,
            fontWeight: 800,
            letterSpacing: 1,
            color: "#fbbf24",
            border: "1px solid rgba(251, 191, 36, 0.6)",
            padding: "2px 8px",
            borderRadius: 4,
            backgroundColor: "rgba(251, 191, 36, 0.12)",
          }}
        >
          {badge}
        </div>
      </div>

      {/* SVG Canvas for Flow Arcs */}
      <svg
        width={width - 48}
        height={height - 90}
        viewBox="400 200 1300 500"
        style={{ overflow: "visible" }}
      >
        <defs>
          <linearGradient id="flowGradient" x1="0%" y1="0%" x2="100%" y2="0%">
            <stop offset="0%" stopColor="#38bdf8" stopOpacity="0.3" />
            <stop offset="50%" stopColor="#fbbf24" stopOpacity="0.8" />
            <stop offset="100%" stopColor="#f59e0b" stopOpacity="1" />
          </linearGradient>
          <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="4" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>

        {/* Global Grid Lines */}
        <line x1="450" y1="400" x2="1650" y2="400" stroke="rgba(255,255,255,0.06)" strokeDasharray="4 6" />
        <line x1="970" y1="220" x2="970" y2="650" stroke="rgba(255,255,255,0.06)" strokeDasharray="4 6" />
        <line x1="540" y1="220" x2="540" y2="650" stroke="rgba(255,255,255,0.06)" strokeDasharray="4 6" />

        {/* Render Each Flow Arc */}
        {flows.map((flow, idx) => {
          const start = HUBS[flow.from] || HUBS.LON;
          const end = HUBS[flow.to] || HUBS.NYC;
          const delay = flow.delayFrames || idx * 12;

          const progress = interpolate(frame, [delay, delay + 45], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });

          // Quadratic Bézier curve
          const midX = (start.x + end.x) / 2;
          const midY = Math.min(start.y, end.y) - 120;
          const pathD = `M ${start.x} ${start.y} Q ${midX} ${midY} ${end.x} ${end.y}`;

          // Approximate length for dash array
          const pathLen = Math.hypot(end.x - start.x, end.y - start.y) * 1.25;
          const dashOffset = pathLen * (1 - progress);

          return (
            <g key={idx}>
              {/* Ghost base arc */}
              <path
                d={pathD}
                fill="none"
                stroke="rgba(255,255,255,0.08)"
                strokeWidth={2}
                strokeDasharray="6 6"
              />
              {/* Dynamic animated flow vector */}
              <path
                d={pathD}
                fill="none"
                stroke="url(#flowGradient)"
                strokeWidth={3.5}
                strokeDasharray={pathLen}
                strokeDashoffset={dashOffset}
                filter="url(#glow)"
              />

              {/* Origin Marker */}
              <circle cx={start.x} cy={start.y} r={6} fill="#38bdf8" />
              <text
                x={start.x}
                y={start.y + 22}
                fill="#94a3b8"
                fontSize={12}
                fontWeight={700}
                textAnchor="middle"
              >
                {start.name}
              </text>

              {/* Destination Callout Badge (Swells when flow reaches NY) */}
              {progress > 0.6 ? (
                <g>
                  <circle cx={end.x} cy={end.y} r={8} fill="#f59e0b" filter="url(#glow)" />
                  <rect
                    x={end.x - 70}
                    y={end.y - 45 - idx * 30}
                    width={140}
                    height={26}
                    rx={4}
                    fill="rgba(245, 158, 11, 0.9)"
                  />
                  <text
                    x={end.x}
                    y={end.y - 28 - idx * 30}
                    fill="#0f172a"
                    fontSize={13}
                    fontWeight={900}
                    textAnchor="middle"
                  >
                    {flow.amountDisplay || `$${flow.amount}B`} INFLOW
                  </text>
                </g>
              ) : null}
            </g>
          );
        })}
      </svg>
    </div>
  );
};
