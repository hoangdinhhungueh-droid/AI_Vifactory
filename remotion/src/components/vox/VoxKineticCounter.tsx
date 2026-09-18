import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

export interface VoxKineticCounterPayload {
  start_value?: number;
  end_value?: number;
  unit?: string;
  prefix?: string;
  suffix?: string;
  trend?: "up" | "down" | "danger" | string;
  chart_type?: "line" | "candles" | "bars" | string;
}

export interface VoxKineticCounterProps {
  title?: string;
  badge?: string;
  theme?: "noir_dossier" | "tech_infographic" | "surveillance_cctv" | string;
  layout?: "split_right" | "split_left" | "fullscreen_dossier" | "floating_card" | string;
  payload?: VoxKineticCounterPayload;
  label?: string;
}

export const VoxKineticCounter: React.FC<VoxKineticCounterProps> = ({
  title,
  badge,
  theme = "tech_infographic",
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
      metricColor: "#f2a63b",
      trendUpColor: "#10b981",
      trendDownColor: "#ef4444",
      chartStroke: "#f2a63b",
      shadow: "0 15px 40px rgba(0,0,0,0.85), inset 0 0 20px rgba(242,166,59,0.12)",
    },
    tech_infographic: {
      bg: "rgba(7, 20, 34, 0.94)",
      border: "1.5px solid rgba(56, 189, 248, 0.55)",
      headerColor: "#38bdf8",
      metricColor: "#38bdf8",
      trendUpColor: "#10b981",
      trendDownColor: "#f87171",
      chartStroke: "#38bdf8",
      shadow: "0 15px 40px rgba(0,0,0,0.85), 0 0 25px rgba(56,189,248,0.2)",
    },
    surveillance_cctv: {
      bg: "rgba(4, 18, 12, 0.95)",
      border: "1.5px solid rgba(34, 197, 94, 0.55)",
      headerColor: "#22c55e",
      metricColor: "#86efac",
      trendUpColor: "#22c55e",
      trendDownColor: "#ef4444",
      chartStroke: "#22c55e",
      shadow: "0 15px 40px rgba(0,0,0,0.85), 0 0 25px rgba(34,197,94,0.2)",
    },
  };

  const st = themeStyles[theme as keyof typeof themeStyles] || themeStyles.tech_infographic;

  const scale = spring({
    frame,
    fps,
    config: { damping: 14, mass: 0.7, stiffness: 120 },
  });

  const opacity = interpolate(frame, [0, 8], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const startVal = typeof payload?.start_value === "number" ? payload.start_value : 0;
  const rawEnd = payload?.end_value;
  const endVal = typeof rawEnd === "number" ? rawEnd : (typeof rawEnd === "string" ? parseFloat(rawEnd) || 0 : 0);
  const prefix = payload?.prefix ?? "$";
  const suffix = payload?.suffix ?? "";
  const unit = payload?.unit ?? "M";
  const trend = payload?.trend ?? "down";
  const displayTitle = title || label || "EVIDENTIARY VALUE // METRIC";
  const displayBadge = badge || (trend === "down" ? "COLLAPSE" : "SURGE");

  // Numeric count-up interpolation
  const countProgress = interpolate(frame, [5, 45], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const currentVal = startVal + (endVal - startVal) * countProgress;
  const formattedVal = Math.abs(currentVal) >= 100
    ? currentVal.toFixed(0)
    : currentVal.toFixed(1);

  // SVG Line Chart Drawing animation
  const pathProgress = interpolate(frame, [10, 50], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const isFullscreen = layout === "fullscreen_dossier";
  const width = isFullscreen ? 880 : 520;

  // Generate dynamic sparkline points based on trend
  const sparkPoints = trend === "down"
    ? "10,20 60,30 120,25 180,45 240,40 300,75 360,90 420,110"
    : "10,110 60,95 120,90 180,70 240,65 300,40 360,30 420,15";

  return (
    <div
      style={{
        width,
        backgroundColor: st.bg,
        border: st.border,
        borderRadius: 14,
        padding: "20px 24px",
        boxShadow: st.shadow,
        backdropFilter: "blur(14px)",
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
          <span style={{ fontSize: 16 }}>📊</span>
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
            border: `1.5px solid ${trend === "down" ? st.trendDownColor : st.trendUpColor}`,
            color: trend === "down" ? st.trendDownColor : st.trendUpColor,
            fontSize: 11,
            fontWeight: 900,
            letterSpacing: 1.5,
            padding: "2px 8px",
            borderRadius: 4,
            backgroundColor: "rgba(0,0,0,0.4)",
          }}
        >
          {trend === "down" ? "▼" : "▲"} {displayBadge}
        </div>
      </div>

      {/* Main Metric Value */}
      <div style={{ display: "flex", alignItems: "baseline", gap: 6, marginBottom: 12 }}>
        <span
          style={{
            fontSize: 46,
            fontWeight: 900,
            color: st.metricColor,
            fontFamily: "'Segoe UI', Roboto, sans-serif",
            letterSpacing: -1,
            lineHeight: 1,
          }}
        >
          {prefix}{formattedVal}{unit}
        </span>
        <span style={{ fontSize: 18, color: "rgba(255,255,255,0.6)", fontWeight: 700 }}>
          {suffix}
        </span>
      </div>

      {/* Sparkline Chart */}
      <div
        style={{
          position: "relative",
          width: "100%",
          height: 120,
          backgroundColor: "rgba(0,0,0,0.3)",
          borderRadius: 8,
          border: "1px solid rgba(255,255,255,0.08)",
          overflow: "hidden",
          padding: "8px 12px",
        }}
      >
        <svg viewBox="0 0 440 120" style={{ width: "100%", height: "100%" }}>
          {/* Horizontal grid lines */}
          <line x1="0" y1="30" x2="440" y2="30" stroke="rgba(255,255,255,0.08)" strokeDasharray="4 4" />
          <line x1="0" y1="60" x2="440" y2="60" stroke="rgba(255,255,255,0.08)" strokeDasharray="4 4" />
          <line x1="0" y1="90" x2="440" y2="90" stroke="rgba(255,255,255,0.08)" strokeDasharray="4 4" />

          {/* Animated Polyline */}
          <polyline
            fill="none"
            stroke={st.chartStroke}
            strokeWidth="3.5"
            strokeLinecap="round"
            strokeLinejoin="round"
            points={sparkPoints}
            strokeDasharray="500"
            strokeDashoffset={500 * (1 - pathProgress)}
          />
        </svg>
      </div>
    </div>
  );
};