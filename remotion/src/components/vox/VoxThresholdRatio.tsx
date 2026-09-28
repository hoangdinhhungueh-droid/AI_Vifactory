import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { VoxThresholdRatioPayload } from "../../types";

export interface VoxThresholdRatioProps {
  title?: string;
  badge?: string;
  theme?: "crimson_alert" | "noir_dossier" | "tech_infographic" | string;
  layout?: "full_bleed_focus" | "split_right" | "split_left" | "floating_card" | string;
  payload?: VoxThresholdRatioPayload;
  label?: string;
}

export const VoxThresholdRatio: React.FC<VoxThresholdRatioProps> = ({
  title,
  badge,
  theme = "crimson_alert",
  layout = "full_bleed_focus",
  payload,
  label,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Color theme palette
  const themeStyles = {
    crimson_alert: {
      bg: "rgba(15, 10, 16, 0.95)",
      border: "1.5px solid rgba(239, 68, 68, 0.65)",
      headerColor: "#fca5a5",
      badgeBg: "rgba(220, 38, 38, 0.25)",
      badgeBorder: "#ef4444",
      badgeText: "#ef4444",
      cellActiveBg: "rgba(220, 38, 38, 0.90)",
      cellActiveBorder: "#ef4444",
      cellBaselineBg: "rgba(245, 158, 11, 0.35)",
      cellBaselineBorder: "#f59e0b",
      shadow: "0 20px 50px rgba(0, 0, 0, 0.9), 0 0 30px rgba(220, 38, 38, 0.22)",
    },
    noir_dossier: {
      bg: "rgba(12, 16, 26, 0.95)",
      border: "1.5px solid rgba(242, 166, 59, 0.60)",
      headerColor: "#ffd166",
      badgeBg: "rgba(242, 166, 59, 0.20)",
      badgeBorder: "#f2a63b",
      badgeText: "#ffd166",
      cellActiveBg: "rgba(242, 166, 59, 0.90)",
      cellActiveBorder: "#ffd166",
      cellBaselineBg: "rgba(56, 189, 248, 0.35)",
      cellBaselineBorder: "#38bdf8",
      shadow: "0 20px 50px rgba(0, 0, 0, 0.9), 0 0 30px rgba(242, 166, 59, 0.20)",
    },
    tech_infographic: {
      bg: "rgba(7, 20, 34, 0.95)",
      border: "1.5px solid rgba(56, 189, 248, 0.60)",
      headerColor: "#38bdf8",
      badgeBg: "rgba(56, 189, 248, 0.20)",
      badgeBorder: "#38bdf8",
      badgeText: "#38bdf8",
      cellActiveBg: "rgba(239, 68, 68, 0.90)",
      cellActiveBorder: "#f87171",
      cellBaselineBg: "rgba(56, 189, 248, 0.35)",
      cellBaselineBorder: "#38bdf8",
      shadow: "0 20px 50px rgba(0, 0, 0, 0.9), 0 0 30px rgba(56, 189, 248, 0.20)",
    },
  };

  const st = themeStyles[theme as keyof typeof themeStyles] || themeStyles.crimson_alert;

  // Outer container entrance spring animation
  const containerScale = spring({
    frame,
    fps,
    config: { damping: 14, mass: 0.7, stiffness: 120 },
  });

  const opacity = interpolate(frame, [0, 8], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Extract props and numeric values
  const baselineVal = payload?.baseline_value ?? 0.03;
  const detectedVal = payload?.detected_value ?? (payload as any)?.actual_value ?? 0.72;
  const multiplier = payload?.multiplier ?? (payload as any)?.ratio ?? Math.round(detectedVal / Math.max(0.001, baselineVal));
  const unit = payload?.unit ?? "g/kg";
  const chemicalName = payload?.chemical_name ?? "二酸化硫黄 (SULFUR DIOXIDE)";
  const standardName = payload?.standard_name ?? "法定基準値 (LEGAL LIMIT)";
  const detectedName = payload?.detected_name ?? "検出値 (DETECTED)";
  const cols = payload?.grid_cols ?? 6;
  const rows = payload?.grid_rows ?? 4;
  const totalCells = cols * rows; // default 24
  const sourceCitation = payload?.source_citation ?? "国家標準 GB 2760-2014 & 厚生労働省 検疫所検査";

  const displayTitle = title || label || `化学残留検査 // ${chemicalName}`;
  const displayBadge = badge || `基準値の${multiplier}倍を検出`;

  // Numeric counter rolling from baselineVal to detectedVal
  const countProgress = interpolate(frame, [8, 42], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const currentNumericVal = baselineVal + (detectedVal - baselineVal) * countProgress;
  const currentMultiplierVal = 1 + (multiplier - 1) * countProgress;

  // Formatted counter string
  const formattedDetected = currentNumericVal >= 100 ? Math.round(currentNumericVal).toLocaleString() : currentNumericVal.toFixed(2);
  const formattedMultiplier = currentMultiplierVal.toFixed(1);

  // Layout sizing
  const isFullBleed = layout === "full_bleed_focus" || layout === "fullscreen_dossier";
  const width = isFullBleed ? 980 : 540;

  // Staccato timing parameters
  const gridStartFrame = 10;
  const framesPerCell = 1.35; // staccato cadence

  return (
    <div
      style={{
        width,
        backgroundColor: st.bg,
        border: st.border,
        borderRadius: 14,
        padding: isFullBleed ? "24px 32px" : "18px 22px",
        boxShadow: st.shadow,
        zIndex: 30,
        fontFamily: "'Zen Kaku Gothic New', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
        fontFeatureSettings: '"palt" 1',
        opacity,
        transform: `scale(${containerScale})`,
        transformOrigin: "center center",
        pointerEvents: "none",
        color: "#ffffff",
      }}
    >
      {/* Header Bar */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          borderBottom: "1px solid rgba(255, 255, 255, 0.14)",
          paddingBottom: 10,
          marginBottom: 16,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ fontSize: 20 }}>⚠️</span>
          <div>
            <div
              style={{
                color: st.headerColor,
                fontSize: isFullBleed ? 15 : 13,
                fontWeight: 900,
                letterSpacing: 1.5,
                textTransform: "uppercase",
              }}
            >
              {displayTitle}
            </div>
            <div style={{ fontSize: 11, color: "rgba(255, 255, 255, 0.55)", letterSpacing: 0.5 }}>
              FORENSIC TOXICOLOGY & STATUTORY COMPLIANCE AUDIT
            </div>
          </div>
        </div>

        <div
          style={{
            border: `1.5px solid ${st.badgeBorder}`,
            color: st.badgeText,
            fontSize: isFullBleed ? 13 : 11,
            fontWeight: 900,
            letterSpacing: 1.2,
            padding: "4px 12px",
            borderRadius: 6,
            backgroundColor: st.badgeBg,
            textTransform: "uppercase",
            boxShadow: `0 0 12px ${st.badgeBorder}40`,
          }}
        >
          🚨 {displayBadge}
        </div>
      </div>

      {/* Main Dual Counter Section: Baseline vs Detected (with tabular-nums) */}
      <div
        style={{
          display: "grid",
          gridTemplateColumns: isFullBleed ? "1fr auto 1fr" : "1fr",
          alignItems: "center",
          gap: 16,
          backgroundColor: "rgba(0, 0, 0, 0.45)",
          borderRadius: 10,
          border: "1px solid rgba(255, 255, 255, 0.08)",
          padding: isFullBleed ? "16px 24px" : "12px 16px",
          marginBottom: 20,
        }}
      >
        {/* Baseline (1x legal threshold) */}
        <div>
          <div style={{ fontSize: 11, fontWeight: 700, color: "#94a3b8", letterSpacing: 1.2, textTransform: "uppercase", marginBottom: 4 }}>
            {standardName}
          </div>
          <div style={{ display: "flex", alignItems: "baseline", gap: 4 }}>
            <span
              style={{
                fontSize: isFullBleed ? 36 : 28,
                fontWeight: 900,
                color: "#f59e0b",
                fontVariantNumeric: "tabular-nums",
                fontFamily: "'Courier New', Courier, monospace",
                lineHeight: 1,
              }}
            >
              {baselineVal >= 100 ? Math.round(baselineVal).toLocaleString() : baselineVal.toFixed(2)}
            </span>
            <span style={{ fontSize: 14, color: "rgba(255, 255, 255, 0.7)", fontWeight: 700 }}>
              {unit}
            </span>
            <span
              style={{
                marginLeft: 8,
                fontSize: 11,
                fontWeight: 800,
                backgroundColor: "rgba(245, 158, 11, 0.2)",
                color: "#f59e0b",
                padding: "2px 6px",
                borderRadius: 4,
                border: "1px solid rgba(245, 158, 11, 0.5)",
              }}
            >
              基準 (1.0x)
            </span>
          </div>
        </div>

        {/* Multiplier Exceedance Arrow */}
        {isFullBleed && (
          <div style={{ textAlign: "center", padding: "0 12px" }}>
            <div
              style={{
                fontSize: 32,
                fontWeight: 900,
                color: "#ef4444",
                textShadow: "0 0 16px rgba(239, 68, 68, 0.8)",
                fontFamily: "'Segoe UI', Roboto, sans-serif",
                letterSpacing: -1,
                lineHeight: 1,
              }}
            >
              {formattedMultiplier}×
            </div>
            <div style={{ fontSize: 10, color: "rgba(239, 68, 68, 0.9)", fontWeight: 800, letterSpacing: 1, marginTop: 2 }}>
              OVER LIMIT
            </div>
          </div>
        )}

        {/* Detected Exceedance Value */}
        <div style={{ textAlign: isFullBleed ? "right" : "left" }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: "#f87171", letterSpacing: 1.2, textTransform: "uppercase", marginBottom: 4 }}>
            {detectedName}
          </div>
          <div style={{ display: "flex", alignItems: "baseline", gap: 4, justifyContent: isFullBleed ? "flex-end" : "flex-start" }}>
            <span
              style={{
                fontSize: isFullBleed ? 44 : 32,
                fontWeight: 900,
                color: "#ef4444",
                fontVariantNumeric: "tabular-nums",
                fontFamily: "'Courier New', Courier, monospace",
                lineHeight: 1,
                textShadow: "0 0 18px rgba(239, 68, 68, 0.65)",
              }}
            >
              {formattedDetected}
            </span>
            <span style={{ fontSize: 14, color: "rgba(255, 255, 255, 0.8)", fontWeight: 700 }}>
              {unit}
            </span>
            <span
              style={{
                marginLeft: 8,
                fontSize: 11,
                fontWeight: 800,
                backgroundColor: "rgba(220, 38, 38, 0.25)",
                color: "#fca5a5",
                padding: "2px 6px",
                borderRadius: 4,
                border: "1px solid rgba(239, 68, 68, 0.6)",
              }}
            >
              超過 (+{((detectedVal / Math.max(0.001, baselineVal) - 1) * 100).toFixed(0)}%)
            </span>
          </div>
        </div>
      </div>

      {/* The 6x4 Grid: Staccato Reveal Visualizing the 24x Multiplier */}
      <div style={{ marginBottom: 16 }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            fontSize: 11,
            color: "rgba(255, 255, 255, 0.65)",
            fontWeight: 700,
            marginBottom: 8,
            letterSpacing: 0.8,
          }}
        >
          <span>1セル = 法定基準値 1回分 ({baselineVal >= 100 ? Math.round(baselineVal).toLocaleString() : baselineVal.toFixed(2)} {unit})</span>
          <span style={{ color: "#ef4444", fontWeight: 900 }}>
            計 {totalCells} セル (合計 約{multiplier}倍の残留超過)
          </span>
        </div>

        {/* 6x4 Grid Container */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: `repeat(${cols}, 1fr)`,
            gap: isFullBleed ? 10 : 6,
            padding: isFullBleed ? 14 : 10,
            backgroundColor: "rgba(0, 0, 0, 0.5)",
            borderRadius: 10,
            border: "1px solid rgba(255, 255, 255, 0.1)",
            position: "relative",
          }}
        >
          {Array.from({ length: totalCells }).map((_, idx) => {
            const isBaselineCell = idx === 0;
            const cellRevealFrame = isBaselineCell ? 4 : gridStartFrame + Math.floor((idx - 1) * framesPerCell);
            const isRevealed = frame >= cellRevealFrame;

            // Staccato pop spring
            const cellSpring = spring({
              frame: Math.max(0, frame - cellRevealFrame),
              fps,
              config: { damping: 10, mass: 0.25, stiffness: 220 },
              from: 1.6,
              to: 1.0,
            });

            const cellOpacity = interpolate(
              frame,
              [cellRevealFrame - 1, cellRevealFrame + 1],
              [0.2, 1],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            );

            return (
              <div
                key={idx}
                style={{
                  height: isFullBleed ? 48 : 34,
                  borderRadius: 6,
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "center",
                  alignItems: "center",
                  position: "relative",
                  transform: isRevealed ? `scale(${cellSpring})` : "scale(1.0)",
                  opacity: isRevealed ? cellOpacity : 0.15,
                  backgroundColor: !isRevealed
                    ? "rgba(30, 41, 59, 0.35)"
                    : isBaselineCell
                    ? st.cellBaselineBg
                    : st.cellActiveBg,
                  border: !isRevealed
                    ? "1px solid rgba(255, 255, 255, 0.08)"
                    : isBaselineCell
                    ? `2px solid ${st.cellBaselineBorder}`
                    : `1.5px solid ${st.cellActiveBorder}`,
                  boxShadow: isRevealed
                    ? isBaselineCell
                    ? "0 0 10px rgba(245, 158, 11, 0.4)"
                    : "0 0 12px rgba(239, 68, 68, 0.6)"
                    : "none",
                  transition: "background-color 0.1s ease",
                }}
              >
                {/* Baseline Cell Indicator Badge */}
                {isBaselineCell ? (
                  <>
                    <span
                      style={{
                        fontSize: isFullBleed ? 12 : 9,
                        fontWeight: 900,
                        color: "#f59e0b",
                        letterSpacing: 0.5,
                      }}
                    >
                      基準値
                    </span>
                    <span style={{ fontSize: isFullBleed ? 10 : 8, color: "rgba(255, 255, 255, 0.8)", fontWeight: 700 }}>
                      1×
                    </span>
                  </>
                ) : (
                  <span
                    style={{
                      fontSize: isFullBleed ? 13 : 10,
                      fontWeight: 900,
                      color: isRevealed ? "#ffffff" : "rgba(255, 255, 255, 0.3)",
                      fontVariantNumeric: "tabular-nums",
                    }}
                  >
                    #{idx + 1}
                  </span>
                )}

                {/* Micro Alert Dot for Exceeded Cells */}
                {isRevealed && !isBaselineCell && (
                  <div
                    style={{
                      position: "absolute",
                      top: 4,
                      right: 4,
                      width: 5,
                      height: 5,
                      borderRadius: "50%",
                      backgroundColor: "#fca5a5",
                      boxShadow: "0 0 4px #ef4444",
                    }}
                  />
                )}
              </div>
            );
          })}
        </div>
      </div>

      {/* Journalistic Source Footnote Citation (Rule 130 Causal Integrity) */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          padding: "8px 14px",
          backgroundColor: "rgba(0, 0, 0, 0.35)",
          borderRadius: 6,
          border: "1px solid rgba(255, 255, 255, 0.08)",
          fontSize: isFullBleed ? 11 : 9.5,
          color: "rgba(255, 255, 255, 0.70)",
          fontFamily: "'Courier New', Courier, monospace",
          letterSpacing: 0.4,
        }}
      >
        <span style={{ fontSize: 13 }}>📄</span>
        <span style={{ fontWeight: 800, color: "#94a3b8" }}>出典 / EVIDENCE SOURCE:</span>
        <span style={{ color: "rgba(255, 255, 255, 0.85)" }}>{sourceCitation}</span>
      </div>
    </div>
  );
};
