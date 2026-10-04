import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { SPRING_PRESETS } from "../vox/springPresets";

export interface ForensicMetricItem {
  label: string;
  value: string | number;
  prefix?: string;
  suffix?: string;
  highlight?: boolean;
  change?: string; // e.g. "+312%", "CRITICAL"
}

export interface KineticForensicCardProps {
  caseId?: string;
  category?: string;
  title: string;
  subtitle?: string;
  metrics?: ForensicMetricItem[];
  stampText?: string; // e.g. "EVIDENCE #01", "CONFIDENTIAL", "SUBPOENAED"
  startFrame?: number;
  durationFrames?: number;
  theme?: "forensic_dark" | "archival_paper" | "cyber_terminal" | "amber_alert";
  showGrid?: boolean;
  width?: number | string;
  style?: React.CSSProperties;
  className?: string;
}

/**
 * KineticForensicCard - Declarative HyperFrames-inspired motion graphic card.
 * High-impact forensic dossier component powered by Remotion physics springs.
 * Renders investigative proof cards, metric breakdowns, and evidence badges
 * with zero headless-Chromium OOM overhead on VPS infrastructure.
 */
export const KineticForensicCard: React.FC<KineticForensicCardProps> = ({
  caseId = "DOSSIER // REF-2026-X09",
  category = "FORENSIC FINANCIAL AUDIT",
  title,
  subtitle,
  metrics = [],
  stampText,
  startFrame = 5,
  durationFrames = 60,
  theme = "forensic_dark",
  showGrid = true,
  width = 680,
  style,
  className,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const relFrame = Math.max(0, frame - startFrame);

  // Theme palettes
  const themeStyles = {
    forensic_dark: {
      bg: "rgba(10, 15, 26, 0.92)",
      border: "1px solid rgba(56, 189, 248, 0.35)",
      textPrimary: "#f8fafc",
      textSecondary: "#94a3b8",
      accent: "#38bdf8",
      grid: "radial-gradient(rgba(56, 189, 248, 0.15) 1px, transparent 1px)",
      stampBg: "rgba(239, 68, 68, 0.15)",
      stampBorder: "#ef4444",
      stampText: "#f87171",
      glow: "0 20px 45px -10px rgba(15, 23, 42, 0.8), 0 0 25px rgba(56, 189, 248, 0.15)",
    },
    archival_paper: {
      bg: "rgba(247, 243, 233, 0.96)",
      border: "1px solid rgba(120, 113, 108, 0.4)",
      textPrimary: "#1c1917",
      textSecondary: "#57534e",
      accent: "#b45309",
      grid: "linear-gradient(rgba(120, 113, 108, 0.08) 1px, transparent 1px)",
      stampBg: "rgba(185, 28, 28, 0.12)",
      stampBorder: "#b91c1c",
      stampText: "#991b1b",
      glow: "0 15px 35px -5px rgba(0, 0, 0, 0.3)",
    },
    cyber_terminal: {
      bg: "rgba(4, 18, 12, 0.94)",
      border: "1px solid rgba(34, 197, 94, 0.4)",
      textPrimary: "#f0fdf4",
      textSecondary: "#86efac",
      accent: "#22c55e",
      grid: "radial-gradient(rgba(34, 197, 94, 0.2) 1px, transparent 1px)",
      stampBg: "rgba(34, 197, 94, 0.15)",
      stampBorder: "#22c55e",
      stampText: "#4ade80",
      glow: "0 0 30px rgba(34, 197, 94, 0.25)",
    },
    amber_alert: {
      bg: "rgba(24, 15, 5, 0.95)",
      border: "1px solid rgba(245, 158, 11, 0.5)",
      textPrimary: "#fffbeb",
      textSecondary: "#fde68a",
      accent: "#f59e0b",
      grid: "radial-gradient(rgba(245, 158, 11, 0.2) 1px, transparent 1px)",
      stampBg: "rgba(245, 158, 11, 0.2)",
      stampBorder: "#f59e0b",
      stampText: "#fbbf24",
      glow: "0 0 35px rgba(245, 158, 11, 0.2)",
    },
  }[theme];

  // 1. Entrance Physics: Heavy paper dossier slide with inertia
  const enterSpring = spring({
    frame: relFrame,
    fps,
    config: SPRING_PRESETS.paperSlide,
  });

  const cardTranslateY = interpolate(enterSpring, [0, 1], [48, 0]);
  const cardScale = interpolate(enterSpring, [0, 1], [0.94, 1.0]);
  const cardOpacity = interpolate(relFrame, [0, 8], [0, 1], {
    extrapolateRight: "clamp",
  });

  // 2. Header Snap Physics
  const headerSnap = spring({
    frame: Math.max(0, relFrame - 4),
    fps,
    config: SPRING_PRESETS.labelSnap,
  });
  const headerOpacity = interpolate(headerSnap, [0, 1], [0, 1]);

  // 3. Stamp Slam Physics
  const stampSpring = spring({
    frame: Math.max(0, relFrame - 16),
    fps,
    config: SPRING_PRESETS.stamp,
  });
  const stampScale = interpolate(stampSpring, [0, 1], [2.8, 1.0]);
  const stampOpacity = interpolate(stampSpring, [0, 0.3, 1], [0, 0.9, 1]);

  // Subtle live scanline / breathing jitter
  const scanlineY = (frame * 2.5) % 360;

  return (
    <div
      className={className}
      style={{
        width,
        backgroundColor: themeStyles.bg,
        border: themeStyles.border,
        borderRadius: 8,
        boxShadow: themeStyles.glow,
        padding: "24px 28px",
        fontFamily: "'JetBrains Mono', 'Fira Code', 'Courier New', monospace",
        color: themeStyles.textPrimary,
        position: "relative",
        overflow: "hidden",
        backdropFilter: "blur(12px)",
        transform: `translateY(${cardTranslateY}px) scale(${cardScale})`,
        opacity: cardOpacity,
        ...style,
      }}
    >
      {/* Background Micro-Grid */}
      {showGrid && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            backgroundImage: themeStyles.grid,
            backgroundSize: "16px 16px",
            opacity: 0.45,
            pointerEvents: "none",
          }}
        />
      )}

      {/* Subtle Scanline Bar */}
      <div
        style={{
          position: "absolute",
          top: scanlineY,
          left: 0,
          right: 0,
          height: 1,
          background: `linear-gradient(90deg, transparent, ${themeStyles.accent}, transparent)`,
          opacity: 0.35,
          pointerEvents: "none",
        }}
      />

      {/* Reticle Corner Marks */}
      <div
        style={{
          position: "absolute",
          top: 6,
          left: 6,
          width: 8,
          height: 8,
          borderTop: `2px solid ${themeStyles.accent}`,
          borderLeft: `2px solid ${themeStyles.accent}`,
          opacity: 0.7,
        }}
      />
      <div
        style={{
          position: "absolute",
          top: 6,
          right: 6,
          width: 8,
          height: 8,
          borderTop: `2px solid ${themeStyles.accent}`,
          borderRight: `2px solid ${themeStyles.accent}`,
          opacity: 0.7,
        }}
      />
      <div
        style={{
          position: "absolute",
          bottom: 6,
          left: 6,
          width: 8,
          height: 8,
          borderBottom: `2px solid ${themeStyles.accent}`,
          borderLeft: `2px solid ${themeStyles.accent}`,
          opacity: 0.7,
        }}
      />
      <div
        style={{
          position: "absolute",
          bottom: 6,
          right: 6,
          width: 8,
          height: 8,
          borderBottom: `2px solid ${themeStyles.accent}`,
          borderRight: `2px solid ${themeStyles.accent}`,
          opacity: 0.7,
        }}
      />

      {/* Header Bar */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          borderBottom: `1px solid rgba(148, 163, 184, 0.2)`,
          paddingBottom: 10,
          marginBottom: 16,
          opacity: headerOpacity,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span
            style={{
              width: 8,
              height: 8,
              borderRadius: "50%",
              backgroundColor: themeStyles.accent,
              boxShadow: `0 0 8px ${themeStyles.accent}`,
              display: "inline-block",
            }}
          />
          <span
            style={{
              fontSize: 11,
              letterSpacing: "0.15em",
              textTransform: "uppercase",
              color: themeStyles.accent,
              fontWeight: 700,
            }}
          >
            {category}
          </span>
        </div>
        <span
          style={{
            fontSize: 10,
            letterSpacing: "0.12em",
            color: themeStyles.textSecondary,
            opacity: 0.8,
          }}
        >
          {caseId}
        </span>
      </div>

      {/* Main Title & Subtitle */}
      <div style={{ position: "relative", zIndex: 1, marginBottom: metrics.length > 0 ? 18 : 0 }}>
        <h3
          style={{
            margin: 0,
            fontSize: 22,
            lineHeight: 1.25,
            fontWeight: 800,
            letterSpacing: "-0.01em",
            color: themeStyles.textPrimary,
            textShadow: "0 2px 8px rgba(0,0,0,0.5)",
          }}
        >
          {title}
        </h3>
        {subtitle && (
          <p
            style={{
              margin: "6px 0 0 0",
              fontSize: 13,
              lineHeight: 1.4,
              color: themeStyles.textSecondary,
              letterSpacing: "0.02em",
            }}
          >
            {subtitle}
          </p>
        )}
      </div>

      {/* Metrics Grid */}
      {metrics.length > 0 && (
        <div
          style={{
            display: "grid",
            gridTemplateColumns: `repeat(${Math.min(metrics.length, 3)}, 1fr)`,
            gap: 12,
            marginTop: 14,
            position: "relative",
            zIndex: 1,
          }}
        >
          {metrics.map((metric, idx) => {
            const itemSpring = spring({
              frame: Math.max(0, relFrame - 8 - idx * 4),
              fps,
              config: SPRING_PRESETS.chartPop,
            });
            const itemScale = interpolate(itemSpring, [0, 1], [0.85, 1.0]);
            const itemOpacity = interpolate(itemSpring, [0, 1], [0, 1]);

            return (
              <div
                key={idx}
                style={{
                  backgroundColor: "rgba(0, 0, 0, 0.25)",
                  border: metric.highlight
                    ? `1px solid ${themeStyles.accent}`
                    : "1px solid rgba(148, 163, 184, 0.15)",
                  borderRadius: 6,
                  padding: "10px 12px",
                  transform: `scale(${itemScale})`,
                  opacity: itemOpacity,
                  boxShadow: metric.highlight ? `0 0 14px rgba(56, 189, 248, 0.15)` : undefined,
                }}
              >
                <div
                  style={{
                    fontSize: 10,
                    textTransform: "uppercase",
                    letterSpacing: "0.1em",
                    color: themeStyles.textSecondary,
                    marginBottom: 4,
                  }}
                >
                  {metric.label}
                </div>
                <div
                  style={{
                    fontSize: 18,
                    fontWeight: 700,
                    color: metric.highlight ? themeStyles.accent : themeStyles.textPrimary,
                    display: "flex",
                    alignItems: "baseline",
                    gap: 2,
                  }}
                >
                  {metric.prefix && <span style={{ fontSize: 13 }}>{metric.prefix}</span>}
                  <span>{metric.value}</span>
                  {metric.suffix && (
                    <span style={{ fontSize: 12, opacity: 0.85, marginLeft: 2 }}>{metric.suffix}</span>
                  )}
                </div>
                {metric.change && (
                  <div
                    style={{
                      fontSize: 10,
                      fontWeight: 600,
                      color: metric.change.startsWith("+")
                        ? "#10b981"
                        : metric.change.startsWith("-")
                        ? "#ef4444"
                        : themeStyles.accent,
                      marginTop: 2,
                    }}
                  >
                    {metric.change}
                  </div>
                )}
              </div>
            );
          })}
        </div>
      )}

      {/* Stamp Slam Overlay */}
      {stampText && relFrame >= 16 && (
        <div
          style={{
            position: "absolute",
            bottom: 18,
            right: 22,
            border: `3px double ${themeStyles.stampBorder}`,
            backgroundColor: themeStyles.stampBg,
            color: themeStyles.stampText,
            padding: "4px 14px",
            fontSize: 13,
            fontWeight: 900,
            letterSpacing: "0.2em",
            textTransform: "uppercase",
            transform: `scale(${stampScale}) rotate(-9deg)`,
            opacity: stampOpacity,
            borderRadius: 4,
            boxShadow: `0 0 15px ${themeStyles.stampBg}`,
            pointerEvents: "none",
            zIndex: 10,
          }}
        >
          {stampText}
        </div>
      )}
    </div>
  );
};
