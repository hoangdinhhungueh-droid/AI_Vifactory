import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig, Easing, Img, staticFile } from "remotion";

export interface NetworkNode {
  id: string;
  label: string;
  subtext?: string;
  image_src?: string; // Cutout image path
  x_pct: number; // 0 - 100% of canvas width
  y_pct: number; // 0 - 100% of canvas height
  enter_frame: number; // Frame when node appears
  theme?: "danger" | "warning" | "cyan" | "gold" | "neutral";
  badge?: string;
  role?: string;
}

export interface NetworkEdge {
  from: string; // Source node id
  to: string;   // Target node id
  label?: string; // e.g. "+$942B CAPITAL FLOW"
  start_frame: number; // Frame when arrow begins drawing
  duration_frames?: number; // Duration of draw animation (default 18)
  color?: string; // Arrow line & glow color
  curve_offset?: number; // Perpendicular curve offset (-80 to +80)
  style?: "solid" | "dashed";
  pulse?: boolean; // Traveling flow pulses along line
}

export interface VoxConnectedNetworkProps {
  title?: string;
  badge?: string;
  layout?: "full_bleed_focus" | "split_right" | "split_left" | string;
  nodes?: NetworkNode[];
  edges?: NetworkEdge[];
}

export const VoxConnectedNetwork: React.FC<VoxConnectedNetworkProps> = ({
  title = "INSTITUTIONAL CAPITAL TRANSMISSION // FORENSIC NETWORK",
  badge = "CAUSAL VECTOR AUDIT",
  layout = "full_bleed_focus",
  nodes = [],
  edges = [],
}) => {
  const frame = useCurrentFrame();
  const { fps, width: canvasW = 1920, height: canvasH = 1080 } = useVideoConfig();

  // Master container entrance with tactile spring
  const containerSpring = spring({
    frame,
    fps,
    config: { damping: 14, mass: 0.6, stiffness: 120 },
  });

  const isFullBleed = layout === "full_bleed_focus" || layout === "fullscreen_dossier";
  const boardW = isFullBleed ? 1560 : 1000;
  const boardH = isFullBleed ? 860 : 620;

  // Auto-layout normalization: provides organic positions if x_pct/y_pct are not passed
  const totalNodes = Math.max(1, nodes.length);
  const normalizedNodes = nodes.map((n, idx) => {
    const x_pct = n.x_pct !== undefined ? n.x_pct : Math.round(20 + (idx / Math.max(1, totalNodes - 1)) * 60);
    const y_pct = n.y_pct !== undefined ? n.y_pct : (idx % 2 === 0 ? 32 : 68);
    const enter_frame = n.enter_frame !== undefined ? n.enter_frame : 10 + idx * 15;
    return { ...n, x_pct, y_pct, enter_frame };
  });

  const normalizedEdges = edges.map((e, idx) => {
    const start_frame = e.start_frame !== undefined ? e.start_frame : 25 + idx * 20;
    const duration_frames = e.duration_frames || 20;
    return { ...e, start_frame, duration_frames };
  });

  // Node lookup map
  const nodeMap = new Map<string, NetworkNode>();
  normalizedNodes.forEach((n) => nodeMap.set(n.id, n));

  const themeColors = {
    danger: { border: "#ef4444", glow: "rgba(239, 68, 68, 0.4)", badgeBg: "#451a1a", text: "#fca5a5" },
    warning: { border: "#f59e0b", glow: "rgba(245, 158, 11, 0.4)", badgeBg: "#452e10", text: "#fde68a" },
    cyan: { border: "#38bdf8", glow: "rgba(56, 189, 248, 0.4)", badgeBg: "#0c3247", text: "#bae6fd" },
    gold: { border: "#eab308", glow: "rgba(234, 179, 8, 0.4)", badgeBg: "#422e08", text: "#fef08a" },
    neutral: { border: "#94a3b8", glow: "rgba(148, 163, 184, 0.3)", badgeBg: "#1e293b", text: "#e2e8f0" },
  };

  return (
    <div
      style={{
        width: boardW,
        height: boardH,
        position: "relative",
        transform: `scale(${containerSpring})`,
        transformOrigin: "center center",
        backgroundColor: "rgba(10, 14, 23, 0.94)",
        backgroundImage: `
          radial-gradient(rgba(242, 166, 59, 0.08) 1.5px, transparent 1.5px),
          linear-gradient(to right, rgba(255, 255, 255, 0.03) 1px, transparent 1px),
          linear-gradient(to bottom, rgba(255, 255, 255, 0.03) 1px, transparent 1px)
        `,
        backgroundSize: "28px 28px, 140px 140px, 140px 140px",
        borderRadius: 16,
        border: "2px solid rgba(242, 166, 59, 0.55)",
        boxShadow: "0 25px 70px rgba(0, 0, 0, 0.85), inset 0 0 35px rgba(242, 166, 59, 0.12)",
        padding: "24px 32px",
        overflow: "hidden",
        fontFamily: "'Courier Prime', 'Special Elite', 'Courier New', monospace",
        color: "#ffffff",
      }}
    >
      {/* Top Telemetry Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          borderBottom: "1.5px solid rgba(255, 255, 255, 0.15)",
          paddingBottom: 12,
          marginBottom: 16,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div
            style={{
              width: 10,
              height: 10,
              borderRadius: "50%",
              backgroundColor: "#f59e0b",
              boxShadow: "0 0 10px #f59e0b",
            }}
          />
          <span
            style={{
              color: "#fbbf24",
              fontSize: 14,
              fontWeight: 900,
              letterSpacing: 2,
              textTransform: "uppercase",
            }}
          >
            {title}
          </span>
        </div>

        <div
          style={{
            border: "1.5px solid #ef4444",
            color: "#f87171",
            backgroundColor: "rgba(69, 26, 26, 0.6)",
            fontSize: 11,
            fontWeight: 900,
            letterSpacing: 1.5,
            padding: "3px 12px",
            borderRadius: 4,
          }}
        >
          {badge}
        </div>
      </div>

      {/* SVG Canvas for Dynamic Vector Arrows & Connecting Paths */}
      <svg
        width={boardW}
        height={boardH}
        viewBox={`0 0 ${boardW} ${boardH}`}
        style={{ position: "absolute", top: 0, left: 0, pointerEvents: "none", zIndex: 12 }}
      >
        <defs>
          <filter id="vectorGlow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="3.5" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>

        {normalizedEdges.map((edge, idx) => {
          const srcNode = nodeMap.get(edge.from);
          const tgtNode = nodeMap.get(edge.to);
          if (!srcNode || !tgtNode) return null;

          // Convert percentage coords to SVG pixel coords relative to board
          const x1 = (srcNode.x_pct / 100) * boardW;
          const y1 = (srcNode.y_pct / 100) * boardH;
          const x2 = (tgtNode.x_pct / 100) * boardW;
          const y2 = (tgtNode.y_pct / 100) * boardH;

          const startF = edge.start_frame;
          const durF = edge.duration_frames || 18;

          // Drawing progress (0 to 1) with snappy bezier easing
          const drawProgress = interpolate(frame, [startF, startF + durF], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.bezier(0.16, 1, 0.3, 1),
          });

          if (drawProgress <= 0.01) return null;

          // Calculate curved control point
          const midX = (x1 + x2) / 2;
          const midY = (y1 + y2) / 2;
          const dx = x2 - x1;
          const dy = y2 - y1;
          const dist = Math.hypot(dx, dy);

          // Normal vector for curve bulge
          const curveBulge = edge.curve_offset !== undefined ? edge.curve_offset : -35;
          const nx = -dy / (dist || 1);
          const ny = dx / (dist || 1);
          const cx = midX + nx * curveBulge;
          const cy = midY + ny * curveBulge;

          const pathD = `M ${x1} ${y1} Q ${cx} ${cy} ${x2} ${y2}`;
          const approxLen = dist * 1.15;
          const dashOffset = approxLen * (1 - drawProgress);
          const strokeColor = edge.color || "#f59e0b";

          // Arrowhead tangent angle at target (t = 1)
          // Derivative of quadratic bezier at t=1: 2*(P2 - P1)
          const tangentX = x2 - cx;
          const tangentY = y2 - cy;
          const angleDeg = (Math.atan2(tangentY, tangentX) * 180) / Math.PI;

          // Arrowhead scale overshoot
          const headScale = spring({
            frame: Math.max(0, frame - (startF + durF - 4)),
            fps,
            config: { damping: 10, mass: 0.4, stiffness: 180 },
          });

          // Label pop-in spring
          const labelSpring = spring({
            frame: Math.max(0, frame - (startF + Math.round(durF * 0.5))),
            fps,
            config: { damping: 12, mass: 0.5, stiffness: 160 },
          });

          // Flowing particle traveling position (after arrow is fully drawn)
          const isDrawn = drawProgress >= 0.99;
          const pulseT = ((frame - (startF + durF)) * 0.04) % 1;
          // Quadratic Bezier interpolation for pulse point: B(t) = (1-t)^2 P0 + 2(1-t)t P1 + t^2 P2
          const ptX = (1 - pulseT) * (1 - pulseT) * x1 + 2 * (1 - pulseT) * pulseT * cx + pulseT * pulseT * x2;
          const ptY = (1 - pulseT) * (1 - pulseT) * y1 + 2 * (1 - pulseT) * pulseT * cy + pulseT * pulseT * y2;

          return (
            <g key={`edge-${edge.from}-${edge.to}-${idx}`}>
              {/* Ghost background track */}
              <path
                d={pathD}
                fill="none"
                stroke="rgba(255, 255, 255, 0.08)"
                strokeWidth={2.5}
                strokeDasharray="6 6"
              />

              {/* Main animated glowing vector arrow */}
              <path
                d={pathD}
                fill="none"
                stroke={strokeColor}
                strokeWidth={3.5}
                strokeDasharray={approxLen}
                strokeDashoffset={dashOffset}
                filter="url(#vectorGlow)"
              />

              {/* Arrowhead polygon landing on target */}
              {drawProgress >= 0.85 ? (
                <polygon
                  points="0,-7 14,0 0,7"
                  fill={strokeColor}
                  transform={`translate(${x2}, ${y2}) rotate(${angleDeg}) scale(${headScale})`}
                  style={{ transformOrigin: "0 0" }}
                />
              ) : null}

              {/* Traveling pulse dot for continuous flow */}
              {isDrawn && edge.pulse !== false ? (
                <circle cx={ptX} cy={ptY} r={5} fill="#ffffff" filter="url(#vectorGlow)" />
              ) : null}

              {/* Floating label pill along arrow curve */}
              {edge.label && labelSpring > 0.05 ? (
                <g transform={`translate(${cx}, ${cy - 12}) scale(${labelSpring})`}>
                  <rect
                    x={-((edge.label.length * 7.5 + 24) / 2)}
                    y={-14}
                    width={edge.label.length * 7.5 + 24}
                    height={28}
                    rx={6}
                    fill="rgba(15, 23, 42, 0.96)"
                    stroke={strokeColor}
                    strokeWidth={1.5}
                  />
                  <text
                    x={0}
                    y={4}
                    textAnchor="middle"
                    fill={strokeColor}
                    fontSize={11}
                    fontWeight={900}
                    letterSpacing={1.2}
                    fontFamily="'Courier New', monospace"
                  >
                    {edge.label}
                  </text>
                </g>
              ) : null}
            </g>
          );
        })}
      </svg>

      {/* Interactive Network Nodes (Photos/Cutouts + Badges + Spring Physics) */}
      {normalizedNodes.map((node, nIdx) => {
        const nodeSpring = spring({
          frame: Math.max(0, frame - node.enter_frame),
          fps,
          config: { damping: 11, mass: 0.55, stiffness: 140 },
        });

        if (nodeSpring <= 0.01) return null;

        const th = themeColors[node.theme || "warning"];
        const nodeLeft = `${node.x_pct}%`;
        const nodeTop = `${node.y_pct}%`;

        return (
          <div
            key={node.id}
            style={{
              position: "absolute",
              left: nodeLeft,
              top: nodeTop,
              transform: `translate(-50%, -50%) scale(${nodeSpring})`,
              zIndex: 20,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: 8,
              minWidth: 160,
              maxWidth: 240,
            }}
          >
            {/* Cutout Image or Icon Avatar */}
            <div
              style={{
                width: 84,
                height: 84,
                borderRadius: 12,
                backgroundColor: th.badgeBg,
                border: `2.5px solid ${th.border}`,
                boxShadow: `0 10px 25px rgba(0,0,0,0.8), 0 0 16px ${th.glow}`,
                display: "flex",
                justifyContent: "center",
                alignItems: "center",
                overflow: "hidden",
                position: "relative",
              }}
            >
              {node.image_src ? (
                <Img
                  src={staticFile(node.image_src)}
                  style={{
                    width: "100%",
                    height: "100%",
                    objectFit: "contain",
                    filter: "drop-shadow(0 2px 4px rgba(0,0,0,0.6))",
                  }}
                />
              ) : (
                <div style={{ fontSize: 32, fontWeight: 900, color: th.border }}>
                  {nIdx + 1}
                </div>
              )}
            </div>

            {/* Node Info Dossier Card */}
            <div
              style={{
                backgroundColor: "rgba(15, 23, 42, 0.95)",
                border: `1.5px solid ${th.border}`,
                borderRadius: 8,
                padding: "8px 14px",
                textAlign: "center",
                boxShadow: "0 8px 20px rgba(0,0,0,0.7)",
                backdropFilter: "blur(8px)",
              }}
            >
              {node.badge ? (
                <div
                  style={{
                    fontSize: 9,
                    fontWeight: 900,
                    color: th.border,
                    letterSpacing: 1.2,
                    marginBottom: 2,
                    textTransform: "uppercase",
                  }}
                >
                  {node.badge}
                </div>
              ) : null}

              <div
                style={{
                  fontSize: 13,
                  fontWeight: 800,
                  color: "#ffffff",
                  lineHeight: 1.2,
                  letterSpacing: 0.5,
                }}
              >
                {node.label}
              </div>

              {node.subtext ? (
                <div
                  style={{
                    fontSize: 10,
                    color: th.text,
                    marginTop: 3,
                    fontWeight: 600,
                  }}
                >
                  {node.subtext}
                </div>
              ) : null}
            </div>
          </div>
        );
      })}
    </div>
  );
};
