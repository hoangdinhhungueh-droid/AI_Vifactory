import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

export interface VoxFlowchartNode {
  id: string;
  label: string;
  status?: "normal" | "breach" | "fatal" | string;
}

export interface VoxFlowchartEdge {
  from: string;
  to: string;
  label?: string;
}

export interface VoxCausalFlowchartPayload {
  nodes?: VoxFlowchartNode[];
  edges?: VoxFlowchartEdge[];
}

export interface VoxCausalFlowchartProps {
  title?: string;
  badge?: string;
  theme?: "noir_dossier" | "tech_infographic" | "surveillance_cctv" | string;
  layout?: "split_right" | "split_left" | "fullscreen_dossier" | "floating_card" | string;
  payload?: VoxCausalFlowchartPayload;
  label?: string;
}

export const VoxCausalFlowchart: React.FC<VoxCausalFlowchartProps> = ({
  title,
  badge,
  theme = "noir_dossier",
  layout = "fullscreen_dossier",
  payload,
  label,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const themeStyles = {
    noir_dossier: {
      bg: "rgba(12, 16, 26, 0.95)",
      border: "1.5px solid rgba(242, 166, 59, 0.55)",
      headerColor: "#ffd166",
      normalNodeBg: "rgba(30, 41, 59, 0.85)",
      normalNodeBorder: "rgba(242, 166, 59, 0.4)",
      breachNodeBg: "rgba(69, 26, 26, 0.85)",
      breachNodeBorder: "#ef4444",
      fatalNodeBg: "rgba(45, 10, 10, 0.95)",
      fatalNodeBorder: "#dc2626",
      arrowColor: "#f2a63b",
      textColor: "#ffffff",
      shadow: "0 15px 40px rgba(0,0,0,0.85), inset 0 0 20px rgba(242,166,59,0.12)",
    },
    tech_infographic: {
      bg: "rgba(7, 20, 34, 0.95)",
      border: "1.5px solid rgba(56, 189, 248, 0.55)",
      headerColor: "#38bdf8",
      normalNodeBg: "rgba(15, 32, 54, 0.85)",
      normalNodeBorder: "rgba(56, 189, 248, 0.4)",
      breachNodeBg: "rgba(69, 26, 26, 0.85)",
      breachNodeBorder: "#f87171",
      fatalNodeBg: "rgba(45, 10, 10, 0.95)",
      fatalNodeBorder: "#ef4444",
      arrowColor: "#38bdf8",
      textColor: "#ffffff",
      shadow: "0 15px 40px rgba(0,0,0,0.85), 0 0 25px rgba(56,189,248,0.2)",
    },
    surveillance_cctv: {
      bg: "rgba(4, 18, 12, 0.95)",
      border: "1.5px solid rgba(34, 197, 94, 0.55)",
      headerColor: "#22c55e",
      normalNodeBg: "rgba(10, 34, 20, 0.85)",
      normalNodeBorder: "rgba(34, 197, 94, 0.4)",
      breachNodeBg: "rgba(69, 26, 26, 0.85)",
      breachNodeBorder: "#ef4444",
      fatalNodeBg: "rgba(45, 10, 10, 0.95)",
      fatalNodeBorder: "#dc2626",
      arrowColor: "#22c55e",
      textColor: "#ffffff",
      shadow: "0 15px 40px rgba(0,0,0,0.85), 0 0 25px rgba(34,197,94,0.2)",
    },
  };

  const st = themeStyles[theme as keyof typeof themeStyles] || themeStyles.noir_dossier;

  const scale = spring({
    frame,
    fps,
    config: { damping: 14, mass: 0.7, stiffness: 120 },
  });

  const opacity = interpolate(frame, [0, 8], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const displayTitle = title || label || "CAUSAL TRANSMISSION // ASYMMETRIC CHOKE";
  const displayBadge = badge || "RESTRICTED";

  const nodes = payload?.nodes && payload.nodes.length > 0
    ? payload.nodes
    : [
        { id: "origin", label: "Consumer Deposit Stream", status: "normal" },
        { id: "intermediary", label: "Platform Escrow Vault", status: "breach" },
        { id: "offshore", label: "Non-Refund Capital Pool", status: "fatal" },
      ];

  const edges = payload?.edges && payload.edges.length > 0
    ? payload.edges
    : [
        { from: "origin", to: "intermediary", label: "Monthly Retainer" },
        { from: "intermediary", to: "offshore", label: "Arbitration Blockade" },
      ];

  const isFullscreen = layout === "fullscreen_dossier";
  const width = isFullscreen ? 960 : 540;

  return (
    <div
      style={{
        width,
        backgroundColor: st.bg,
        border: st.border,
        borderRadius: 14,
        padding: "20px 28px",
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
          marginBottom: 20,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: 16 }}>⛓️</span>
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
            border: "1.5px solid #ef4444",
            color: "#ef4444",
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

      {/* Nodes and Flow Arrows */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          justifyContent: "space-around",
          gap: 12,
          padding: "10px 0",
        }}
      >
        {nodes.map((node, nIdx) => {
          const nodeDelay = nIdx * 14;
          const nodeSpring = spring({
            frame: Math.max(0, frame - nodeDelay),
            fps,
            config: { damping: 12, mass: 0.5 },
          });

          const isBreach = node.status === "breach";
          const isFatal = node.status === "fatal";
          const nodeBg = isFatal ? st.fatalNodeBg : (isBreach ? st.breachNodeBg : st.normalNodeBg);
          const nodeBorder = isFatal ? st.fatalNodeBorder : (isBreach ? st.breachNodeBorder : st.normalNodeBorder);

          const edge = edges[nIdx];
          const edgeProgress = interpolate(frame, [nodeDelay + 10, nodeDelay + 24], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
          });

          return (
            <React.Fragment key={node.id}>
              {/* Node Card */}
              <div
                style={{
                  transform: `scale(${nodeSpring})`,
                  backgroundColor: nodeBg,
                  border: `1.5px solid ${nodeBorder}`,
                  borderRadius: 8,
                  padding: "12px 16px",
                  minWidth: 150,
                  maxWidth: 220,
                  textAlign: "center",
                  boxShadow: `0 6px 15px rgba(0,0,0,0.5)`,
                }}
              >
                <div style={{ fontSize: 10, color: "rgba(255,255,255,0.4)", marginBottom: 4, letterSpacing: 1 }}>
                  NODE {nIdx + 1} // {node.id.toUpperCase()}
                </div>
                <div style={{ fontSize: 13, fontWeight: 700, color: st.textColor, lineHeight: 1.3 }}>
                  {node.label}
                </div>
                {node.status && node.status !== "normal" ? (
                  <div
                    style={{
                      fontSize: 9,
                      fontWeight: 800,
                      marginTop: 6,
                      color: isFatal ? "#ef4444" : "#f87171",
                      letterSpacing: 1,
                    }}
                  >
                    [{node.status.toUpperCase()}]
                  </div>
                ) : null}
              </div>

              {/* Connecting Arrow */}
              {nIdx < nodes.length - 1 ? (
                <div
                  style={{
                    display: "flex",
                    flexDirection: "column",
                    alignItems: "center",
                    opacity: edgeProgress,
                    minWidth: 50,
                  }}
                >
                  <div style={{ fontSize: 9, color: st.arrowColor, marginBottom: 2, textAlign: "center", letterSpacing: 0.5 }}>
                    {edge?.label || "TRANSMIT"}
                  </div>
                  <div style={{ color: st.arrowColor, fontSize: 18, fontWeight: 900 }}>
                    ➔
                  </div>
                </div>
              ) : null}
            </React.Fragment>
          );
        })}
      </div>
    </div>
  );
};
