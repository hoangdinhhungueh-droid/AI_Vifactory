import React from "react";
import { useCurrentFrame, useVideoConfig, interpolate, spring, Easing } from "remotion";

export interface DataPoint {
  label: string;
  value: number;
}

export interface VoxDynamicChartProps {
  title?: string;
  badge?: string;
  chartType?: "line" | "bar" | "candlestick";
  data?: DataPoint[];
  startValue?: number;
  endValue?: number;
  unit?: string;
  prefix?: string;
  color?: string;
  trend?: "up" | "down" | "volatile";
  highlightIndex?: number;
  width?: number;
  height?: number;
  layout?: string;
}

export const VoxDynamicChart: React.FC<VoxDynamicChartProps> = ({
  title = "MARKET CAPITAL INFLOW DYNAMICS",
  badge = "FED / TREASURY TIC DATA",
  chartType = "line",
  data,
  startValue = 188,
  endValue = 942,
  unit = "B",
  prefix = "$",
  color = "#f59e0b", // Vox Amber
  trend = "up",
  width = 720,
  height = 420,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Generate fallback data points if not provided
  const points: DataPoint[] = data || [
    { label: "Q1", value: startValue },
    { label: "Q2", value: Math.round(startValue + (endValue - startValue) * 0.35) },
    { label: "Q3", value: Math.round(startValue + (endValue - startValue) * 0.65) },
    { label: "PEAK", value: endValue },
  ];

  const values = points.map((p) => p.value);
  const minVal = Math.min(...values) * 0.85;
  const maxVal = Math.max(...values) * 1.15;
  const range = maxVal - minVal || 1;

  // Chart Entrance Spring
  const enterProgress = spring({
    frame,
    fps,
    config: { damping: 14, stiffness: 90, mass: 0.8 },
  });

  // Line Draw Progress (0 to 1 over first 35 frames)
  const drawProgress = interpolate(frame, [8, 42], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });

  // Calculate coordinates for SVG
  const paddingX = 60;
  const paddingY = 50;
  const chartW = width - paddingX * 2;
  const chartH = height - paddingY * 2 - 40;

  const coords = points.map((p, idx) => {
    const x = paddingX + (idx / (points.length - 1)) * chartW;
    const y = paddingY + 30 + chartH - ((p.value - minVal) / range) * chartH;
    return { x, y, ...p };
  });

  // SVG Path Construction
  const pathData = coords.reduce((acc, pt, i) => {
    return i === 0 ? `M ${pt.x},${pt.y}` : `${acc} L ${pt.x},${pt.y}`;
  }, "");

  // Area Path Construction (for gradient fill under curve)
  const areaPath = coords.length > 0
    ? `${pathData} L ${coords[coords.length - 1].x},${paddingY + 30 + chartH} L ${coords[0].x},${paddingY + 30 + chartH} Z`
    : "";

  // Dynamic animated counter
  const currentValue = Math.round(
    startValue + (endValue - startValue) * drawProgress
  );

  return (
    <div
      style={{
        width,
        height,
        backgroundColor: "rgba(10, 15, 24, 0.94)",
        border: "1.5px solid rgba(245, 158, 11, 0.35)",
        borderRadius: 16,
        padding: "24px 28px",
        boxShadow: "0 20px 50px rgba(0, 0, 0, 0.85), 0 0 30px rgba(245, 158, 11, 0.15)",
        backdropFilter: "blur(12px)",
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        fontFamily: "'Segoe UI', Roboto, 'Helvetica Neue', sans-serif",
        transform: `scale(${enterProgress})`,
        opacity: enterProgress,
        zIndex: 28,
        position: "relative",
      }}
    >
      {/* Header bar */}
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
        <div>
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              gap: 6,
              padding: "4px 10px",
              backgroundColor: "rgba(245, 158, 11, 0.15)",
              border: "1px solid rgba(245, 158, 11, 0.4)",
              borderRadius: 6,
              color: color,
              fontSize: 12,
              fontWeight: 800,
              letterSpacing: 1.5,
              textTransform: "uppercase",
              marginBottom: 6,
            }}
          >
            <span style={{ width: 6, height: 6, borderRadius: "50%", backgroundColor: color }} />
            {badge}
          </div>
          <div style={{ color: "#f8fafc", fontSize: 18, fontWeight: 800, letterSpacing: 0.5 }}>
            {title}
          </div>
        </div>

        {/* Big Kinetic Number */}
        <div style={{ textAlign: "right" }}>
          <div
            style={{
              color: color,
              fontSize: 34,
              fontWeight: 900,
              fontFamily: "'JetBrains Mono', 'Fira Code', monospace",
              textShadow: `0 0 16px ${color}66`,
            }}
          >
            {prefix}{currentValue.toLocaleString()}{unit}
          </div>
          <div style={{ color: "#94a3b8", fontSize: 12, fontWeight: 600 }}>
            {trend === "up" ? "▲ EXPONENTIAL SURGE" : "▼ LIQUIDITY CONTRACTION"}
          </div>
        </div>
      </div>

      {/* SVG Canvas for Chart */}
      <div style={{ flex: 1, position: "relative", marginTop: 10 }}>
        <svg width="100%" height="100%" viewBox={`0 0 ${width} ${height - 110}`} style={{ overflow: "visible" }}>
          <defs>
            <linearGradient id="chartGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor={color} stopOpacity={0.35} />
              <stop offset="100%" stopColor={color} stopOpacity={0.0} />
            </linearGradient>
            <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="4" result="blur" />
              <feMerge>
                <feMergeNode in="blur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* Grid lines */}
          {[0, 0.33, 0.66, 1].map((ratio, i) => {
            const y = paddingY + 30 + chartH * ratio;
            return (
              <line
                key={i}
                x1={paddingX}
                y1={y}
                x2={paddingX + chartW}
                y2={y}
                stroke="rgba(255, 255, 255, 0.08)"
                strokeDasharray="4 4"
                strokeWidth={1}
              />
            );
          })}

          {/* Area fill */}
          {chartType === "line" && (
            <path
              d={areaPath}
              fill="url(#chartGradient)"
              opacity={drawProgress}
            />
          )}

          {/* Line Chart Path */}
          {chartType === "line" && (
            <path
              d={pathData}
              fill="none"
              stroke={color}
              strokeWidth={3.5}
              strokeLinecap="round"
              strokeLinejoin="round"
              filter="url(#glow)"
              strokeDasharray={1000}
              strokeDashoffset={1000 * (1 - drawProgress)}
            />
          )}

          {/* Bar Chart Representation */}
          {chartType === "bar" &&
            coords.map((pt, idx) => {
              const barH = ((pt.value - minVal) / range) * chartH * drawProgress;
              const barW = chartW / (coords.length * 2);
              const barX = pt.x - barW / 2;
              const barY = paddingY + 30 + chartH - barH;
              return (
                <rect
                  key={idx}
                  x={barX}
                  y={barY}
                  width={barW}
                  height={barH}
                  rx={4}
                  fill={idx === coords.length - 1 ? color : "rgba(255, 255, 255, 0.25)"}
                  filter="url(#glow)"
                />
              );
            })}

          {/* Data Points on Line */}
          {chartType === "line" &&
            coords.map((pt, idx) => {
              const ptProgress = interpolate(
                frame,
                [15 + idx * 8, 25 + idx * 8],
                [0, 1],
                { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
              );
              return (
                <g key={idx} opacity={ptProgress} transform={`translate(0, ${(1 - ptProgress) * 10})`}>
                  <circle
                    cx={pt.x}
                    cy={pt.y}
                    r={6}
                    fill="#0f172a"
                    stroke={color}
                    strokeWidth={3}
                  />
                  <text
                    x={pt.x}
                    y={pt.y - 12}
                    textAnchor="middle"
                    fill="#f8fafc"
                    fontSize={13}
                    fontWeight={800}
                    fontFamily="'JetBrains Mono', monospace"
                  >
                    {prefix}{pt.value}{unit}
                  </text>
                  <text
                    x={pt.x}
                    y={paddingY + 30 + chartH + 20}
                    textAnchor="middle"
                    fill="#94a3b8"
                    fontSize={12}
                    fontWeight={700}
                  >
                    {pt.label}
                  </text>
                </g>
              );
            })}
        </svg>
      </div>

      {/* Footer ticker / forensic caption */}
      <div
        style={{
          borderTop: "1px solid rgba(255, 255, 255, 0.08)",
          paddingTop: 10,
          display: "flex",
          justifyContent: "space-between",
          color: "#64748b",
          fontSize: 11,
          fontWeight: 600,
          letterSpacing: 0.8,
        }}
      >
        <span>STATUS: ANOMALY VERIFIED</span>
        <span>FLOW VELOCITY: ACCELERATING</span>
      </div>
    </div>
  );
};
