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
      bg: "rgba(12, 8, 14, 0.96)",
      border: "1.5px solid rgba(239, 68, 68, 0.70)",
      headerColor: "#fca5a5",
      badgeBg: "rgba(220, 38, 38, 0.28)",
      badgeBorder: "#ef4444",
      badgeText: "#ef4444",
      cellActiveBg: "rgba(220, 38, 38, 0.90)",
      cellActiveBorder: "#ef4444",
      cellBaselineBg: "rgba(245, 158, 11, 0.35)",
      cellBaselineBorder: "#f59e0b",
      shadow: "0 22px 60px rgba(0, 0, 0, 0.95), 0 0 35px rgba(220, 38, 38, 0.25)",
    },
    noir_dossier: {
      bg: "rgba(10, 14, 24, 0.96)",
      border: "1.5px solid rgba(242, 166, 59, 0.65)",
      headerColor: "#ffd166",
      badgeBg: "rgba(242, 166, 59, 0.22)",
      badgeBorder: "#f2a63b",
      badgeText: "#ffd166",
      cellActiveBg: "rgba(242, 166, 59, 0.90)",
      cellActiveBorder: "#ffd166",
      cellBaselineBg: "rgba(56, 189, 248, 0.35)",
      cellBaselineBorder: "#38bdf8",
      shadow: "0 22px 60px rgba(0, 0, 0, 0.95), 0 0 35px rgba(242, 166, 59, 0.22)",
    },
    tech_infographic: {
      bg: "rgba(6, 18, 32, 0.96)",
      border: "1.5px solid rgba(56, 189, 248, 0.65)",
      headerColor: "#38bdf8",
      badgeBg: "rgba(56, 189, 248, 0.22)",
      badgeBorder: "#38bdf8",
      badgeText: "#38bdf8",
      cellActiveBg: "rgba(239, 68, 68, 0.90)",
      cellActiveBorder: "#f87171",
      cellBaselineBg: "rgba(56, 189, 248, 0.35)",
      cellBaselineBorder: "#38bdf8",
      shadow: "0 22px 60px rgba(0, 0, 0, 0.95), 0 0 35px rgba(56, 189, 248, 0.22)",
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
  const baselineVal = payload?.baseline_value ?? 200;
  const detectedVal = payload?.detected_value ?? payload?.actual_value ?? 4860;
  const rawMultiplier = payload?.multiplier ?? payload?.ratio ?? (detectedVal / Math.max(1, baselineVal));
  const multiplier = Number(rawMultiplier.toFixed(1)); // 24.3
  const unit = payload?.unit ?? "mg/kg";
  const chemicalName = payload?.chemical_name ?? "二酸化硫黄 (SO₂ 残留)";
  const standardName = payload?.standard_name ?? "中国国家標準 GB 2760 (200 mg/kg)";
  const detectedName = payload?.detected_name ?? "検疫実測値 (4,860 mg/kg)";
  const cols = payload?.grid_cols ?? 5;
  const rows = payload?.grid_rows ?? 5;
  const totalCells = cols * rows; // 5x5 = 25 cells
  const sourceCitation = payload?.source_citation ?? "厚生労働省 検疫所検査記録 / 国家標準 GB 2760-2014";

  // Two-Stage Reveal parameters (Japan Food Sanitation Act Comparison)
  const secondaryStandardName = payload?.secondary_standard_name ?? "日本 食品衛生法 使用基準 (30 mg/kg)";
  const secondaryBaselineVal = payload?.secondary_baseline_value ?? 30;
  const secondaryMultiplier = payload?.secondary_multiplier ?? Number((detectedVal / secondaryBaselineVal).toFixed(1)); // 162.0
  const stageRevealFrame = payload?.stage_reveal_frame ?? 52;
  const hasStage2 = frame >= stageRevealFrame;

  // Stage 2 spring pop
  const stage2Spring = spring({
    frame: Math.max(0, frame - stageRevealFrame),
    fps,
    config: { damping: 12, mass: 0.65, stiffness: 160 },
  });

  const stage2BarProgress = interpolate(
    frame,
    [stageRevealFrame + 4, stageRevealFrame + 32],
    [0, 1],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const displayTitle = title || label || `化学残留検査 // ${chemicalName}`;
  const displayBadge = hasStage2
    ? `日本法定基準の ${secondaryMultiplier}倍 超過`
    : (badge || `中国国家基準の ${multiplier}倍 超過`);

  // Numeric counter rolling for Stage 1 (0 to 24.3)
  const countProgress = interpolate(frame, [8, 38], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const currentNumericVal = baselineVal + (detectedVal - baselineVal) * countProgress;
  const currentMultiplierVal = 1 + (multiplier - 1) * countProgress;

  // Formatted counter string
  const formattedDetected = currentNumericVal >= 100 ? Math.round(currentNumericVal).toLocaleString() : currentNumericVal.toFixed(1);
  const formattedMultiplier = currentMultiplierVal.toFixed(1);

  // Layout sizing
  const isFullBleed = layout === "full_bleed_focus" || layout === "fullscreen_dossier";
  const width = isFullBleed ? 980 : 560;

  // Staccato timing parameters for 5x5 grid
  const gridStartFrame = 10;
  const framesPerCell = 1.25;

  return (
    <div
      style={{
        width,
        backgroundColor: st.bg,
        border: st.border,
        borderRadius: 14,
        padding: isFullBleed ? "22px 30px" : "16px 20px",
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
          marginBottom: 14,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
          <span style={{ fontSize: 22 }}>⚠️</span>
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
              FORENSIC STATUTORY COMPLIANCE // TWO-STAGE EXCEEDANCE REVEAL
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
            boxShadow: `0 0 14px ${st.badgeBorder}50`,
            transition: "all 0.3s ease",
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
          backgroundColor: "rgba(0, 0, 0, 0.50)",
          borderRadius: 10,
          border: "1px solid rgba(255, 255, 255, 0.08)",
          padding: isFullBleed ? "14px 22px" : "10px 14px",
          marginBottom: 16,
        }}
      >
        {/* Baseline (1x legal threshold) */}
        <div>
          <div style={{ fontSize: 11, fontWeight: 700, color: "#94a3b8", letterSpacing: 1.2, textTransform: "uppercase", marginBottom: 3 }}>
            {standardName}
          </div>
          <div style={{ display: "flex", alignItems: "baseline", gap: 4 }}>
            <span
              style={{
                fontSize: isFullBleed ? 34 : 26,
                fontWeight: 900,
                color: "#f59e0b",
                fontVariantNumeric: "tabular-nums",
                fontFamily: "'Courier New', Courier, monospace",
                lineHeight: 1,
              }}
            >
              {baselineVal >= 100 ? Math.round(baselineVal).toLocaleString() : baselineVal.toFixed(1)}
            </span>
            <span style={{ fontSize: 13, color: "rgba(255, 255, 255, 0.7)", fontWeight: 700 }}>
              {unit}
            </span>
            <span
              style={{
                marginLeft: 6,
                fontSize: 10.5,
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
          <div style={{ textAlign: "center", padding: "0 10px" }}>
            <div
              style={{
                fontSize: 30,
                fontWeight: 900,
                color: "#ef4444",
                textShadow: "0 0 16px rgba(239, 68, 68, 0.85)",
                fontFamily: "'Segoe UI', Roboto, sans-serif",
                letterSpacing: -1,
                lineHeight: 1,
              }}
            >
              {formattedMultiplier}×
            </div>
            <div style={{ fontSize: 9.5, color: "rgba(239, 68, 68, 0.95)", fontWeight: 800, letterSpacing: 1, marginTop: 2 }}>
              GB 2760 超過
            </div>
          </div>
        )}

        {/* Detected Exceedance Value */}
        <div style={{ textAlign: isFullBleed ? "right" : "left" }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: "#f87171", letterSpacing: 1.2, textTransform: "uppercase", marginBottom: 3 }}>
            {detectedName}
          </div>
          <div style={{ display: "flex", alignItems: "baseline", gap: 4, justifyContent: isFullBleed ? "flex-end" : "flex-start" }}>
            <span
              style={{
                fontSize: isFullBleed ? 40 : 30,
                fontWeight: 900,
                color: "#ef4444",
                fontVariantNumeric: "tabular-nums",
                fontFamily: "'Courier New', Courier, monospace",
                lineHeight: 1,
                textShadow: "0 0 18px rgba(239, 68, 68, 0.70)",
              }}
            >
              {formattedDetected}
            </span>
            <span style={{ fontSize: 13, color: "rgba(255, 255, 255, 0.8)", fontWeight: 700 }}>
              {unit}
            </span>
            <span
              style={{
                marginLeft: 6,
                fontSize: 10.5,
                fontWeight: 800,
                backgroundColor: "rgba(220, 38, 38, 0.25)",
                color: "#fca5a5",
                padding: "2px 6px",
                borderRadius: 4,
                border: "1px solid rgba(239, 68, 68, 0.6)",
              }}
            >
              超過 (+{((detectedVal / Math.max(1, baselineVal) - 1) * 100).toFixed(0)}%)
            </span>
          </div>
        </div>
      </div>

      {/* The 5x5 Grid: 24 Full Cells + Cell #25 Filled 30% from Bottom (Visualizing 24.3x) */}
      <div style={{ marginBottom: 14 }}>
        <div
          style={{
            display: "flex",
            justifyContent: "space-between",
            alignItems: "center",
            fontSize: 10.5,
            color: "rgba(255, 255, 255, 0.65)",
            fontWeight: 700,
            marginBottom: 6,
            letterSpacing: 0.8,
          }}
        >
          <span>1セル = 中国基準上限 1回分 ({baselineVal} {unit})</span>
          <span style={{ color: "#ef4444", fontWeight: 900 }}>
            5×5 グリッド: 24全満 + 25セル目 30% 残留 ＝ 計 {multiplier}倍
          </span>
        </div>

        {/* 5x5 Grid Container */}
        <div
          style={{
            display: "grid",
            gridTemplateColumns: `repeat(${cols}, 1fr)`,
            gap: isFullBleed ? 8 : 5,
            padding: isFullBleed ? 12 : 8,
            backgroundColor: "rgba(0, 0, 0, 0.55)",
            borderRadius: 10,
            border: "1px solid rgba(255, 255, 255, 0.1)",
            position: "relative",
          }}
        >
          {Array.from({ length: totalCells }).map((_, idx) => {
            const isBaselineCell = idx === 0;
            const isLastCell = idx === 24; // Cell #25 for the partial .3 fill
            const cellRevealFrame = isBaselineCell ? 4 : gridStartFrame + Math.floor((idx - 1) * framesPerCell);
            const isRevealed = frame >= cellRevealFrame;

            // Staccato pop spring
            const cellSpring = spring({
              frame: Math.max(0, frame - cellRevealFrame),
              fps,
              config: { damping: 10, mass: 0.25, stiffness: 220 },
              from: 1.5,
              to: 1.0,
            });

            const cellOpacity = interpolate(
              frame,
              [cellRevealFrame - 1, cellRevealFrame + 1],
              [0.2, 1],
              { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
            );

            // Cell 25 partial fill from bottom: partial = 0.3 (Opus 5.5 masterclass)
            const partial = 0.30;
            const fillProgress = spring({
              frame: Math.max(0, frame - cellRevealFrame),
              fps,
              config: { mass: 0.6, stiffness: 180, damping: 18 },
            });
            const partialHeightPercent = isLastCell
              ? Math.min(100, Math.max(0, fillProgress * partial * 100))
              : 100;

            return (
              <div
                key={idx}
                style={{
                  height: isFullBleed ? 42 : 30,
                  borderRadius: 5,
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "center",
                  alignItems: "center",
                  position: "relative",
                  overflow: "hidden",
                  transform: isRevealed ? `scale(${cellSpring})` : "scale(1.0)",
                  opacity: isRevealed ? cellOpacity : 0.15,
                  backgroundColor: !isRevealed
                    ? "rgba(30, 41, 59, 0.35)"
                    : isBaselineCell
                    ? st.cellBaselineBg
                    : isLastCell
                    ? "rgba(30, 41, 59, 0.45)"
                    : st.cellActiveBg,
                  border: !isRevealed
                    ? "1px solid rgba(255, 255, 255, 0.08)"
                    : isBaselineCell
                    ? `2px solid ${st.cellBaselineBorder}`
                    : isLastCell
                    ? "1.5px dashed rgba(245, 158, 11, 0.85)"
                    : `1.5px solid ${st.cellActiveBorder}`,
                  boxShadow: isRevealed
                    ? isBaselineCell
                      ? "0 0 10px rgba(245, 158, 11, 0.4)"
                      : isLastCell
                      ? "0 0 10px rgba(245, 158, 11, 0.3)"
                      : "0 0 10px rgba(239, 68, 68, 0.55)"
                    : "none",
                }}
              >
                {/* Cell 25 Bottom Fill Bar (+0.3x) */}
                {isLastCell && isRevealed && (
                  <div
                    style={{
                      position: "absolute",
                      bottom: 0,
                      left: 0,
                      right: 0,
                      height: `${partialHeightPercent}%`,
                      backgroundColor: "rgba(245, 158, 11, 0.85)",
                      boxShadow: "0 0 10px rgba(245, 158, 11, 0.7)",
                      zIndex: 1,
                    }}
                  />
                )}

                {/* Baseline Cell Indicator Badge */}
                {isBaselineCell ? (
                  <>
                    <span style={{ fontSize: isFullBleed ? 11 : 8.5, fontWeight: 900, color: "#f59e0b", letterSpacing: 0.5 }}>
                      基準値
                    </span>
                    <span style={{ fontSize: isFullBleed ? 9.5 : 7.5, color: "rgba(255, 255, 255, 0.8)", fontWeight: 700 }}>
                      1×
                    </span>
                  </>
                ) : isLastCell ? (
                  <span
                    style={{
                      position: "relative",
                      zIndex: 2,
                      fontSize: isFullBleed ? 11.5 : 9,
                      fontWeight: 900,
                      color: isRevealed ? "#ffffff" : "rgba(255, 255, 255, 0.3)",
                      fontVariantNumeric: "tabular-nums",
                      textShadow: "0 1px 3px rgba(0,0,0,0.8)",
                    }}
                  >
                    +0.3×
                  </span>
                ) : (
                  <span
                    style={{
                      fontSize: isFullBleed ? 12 : 9.5,
                      fontWeight: 900,
                      color: isRevealed ? "#ffffff" : "rgba(255, 255, 255, 0.3)",
                      fontVariantNumeric: "tabular-nums",
                    }}
                  >
                    #{idx + 1}
                  </span>
                )}

                {/* Micro Alert Dot for Exceeded Cells */}
                {isRevealed && !isBaselineCell && !isLastCell && (
                  <div
                    style={{
                      position: "absolute",
                      top: 3,
                      right: 3,
                      width: 4,
                      height: 4,
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

      {/* Stage 2 Explosive Morph: Japan Food Sanitation Act (162x Over Limit) */}
      {hasStage2 ? (
        <div
          style={{
            transform: `scale(${stage2Spring})`,
            transformOrigin: "center top",
            backgroundColor: "rgba(30, 8, 12, 0.90)",
            border: "1.5px solid #ef4444",
            borderRadius: 10,
            padding: "12px 18px",
            marginBottom: 14,
            boxShadow: "0 0 25px rgba(239, 68, 68, 0.40)",
          }}
        >
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", marginBottom: 8 }}>
            <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
              <span style={{ fontSize: 16 }}>⚡</span>
              <span style={{ fontSize: 12, fontWeight: 900, color: "#fca5a5", letterSpacing: 1.2 }}>
                日本国内基準との対比 // 食品衛生法 使用基準 (0.030 g/kg ＝ 30 mg/kg)
              </span>
            </div>
            <div
              style={{
                fontSize: 16,
                fontWeight: 900,
                color: "#ef4444",
                fontFamily: "'Courier New', Courier, monospace",
                textShadow: "0 0 12px rgba(239, 68, 68, 0.8)",
              }}
            >
              162.0× OVER LIMIT
            </div>
          </div>

          {/* Comparative Ratio Bars: Japan Standard (30mg) vs China GB (200mg) vs Kobe Quarantine (4,860mg) */}
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {/* Bar 1: Japan Statutory Limit */}
            <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 10.5 }}>
              <span style={{ width: 140, color: "#94a3b8", fontWeight: 700 }}>日本法定上限 (30 mg/kg):</span>
              <div style={{ flex: 1, backgroundColor: "rgba(255,255,255,0.08)", height: 12, borderRadius: 3, overflow: "hidden" }}>
                <div style={{ width: `${Math.max(1, (30 / 4860) * 100 * stage2BarProgress)}%`, height: "100%", backgroundColor: "#38bdf8" }} />
              </div>
              <span style={{ width: 45, color: "#38bdf8", fontWeight: 800, textAlign: "right" }}>1.0×</span>
            </div>

            {/* Bar 2: China GB 2760 Limit */}
            <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 10.5 }}>
              <span style={{ width: 140, color: "#94a3b8", fontWeight: 700 }}>中国国家標準 (200 mg/kg):</span>
              <div style={{ flex: 1, backgroundColor: "rgba(255,255,255,0.08)", height: 12, borderRadius: 3, overflow: "hidden" }}>
                <div style={{ width: `${Math.max(1, (200 / 4860) * 100 * stage2BarProgress)}%`, height: "100%", backgroundColor: "#f59e0b" }} />
              </div>
              <span style={{ width: 45, color: "#f59e0b", fontWeight: 800, textAlign: "right" }}>6.7×</span>
            </div>

            {/* Bar 3: Detected Kobe Quarantine */}
            <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 10.5 }}>
              <span style={{ width: 140, color: "#fca5a5", fontWeight: 900 }}>検疫実測値 (4,860 mg/kg):</span>
              <div style={{ flex: 1, backgroundColor: "rgba(255,255,255,0.08)", height: 14, borderRadius: 3, overflow: "hidden" }}>
                <div
                  style={{
                    width: `${stage2BarProgress * 100}%`,
                    height: "100%",
                    background: "linear-gradient(90deg, #ef4444 0%, #dc2626 70%, #ff4d4d 100%)",
                    boxShadow: "0 0 14px rgba(239, 68, 68, 0.8)",
                  }}
                />
              </div>
              <span style={{ width: 45, color: "#ef4444", fontWeight: 900, textAlign: "right" }}>162.0×</span>
            </div>
          </div>
        </div>
      ) : null}

      {/* Journalistic Source Footnote Citation (Rule 130 Causal Integrity) */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 8,
          padding: "7px 12px",
          backgroundColor: "rgba(0, 0, 0, 0.40)",
          borderRadius: 6,
          border: "1px solid rgba(255, 255, 255, 0.08)",
          fontSize: isFullBleed ? 10.5 : 9,
          color: "rgba(255, 255, 255, 0.70)",
          fontFamily: "'Courier New', Courier, monospace",
          letterSpacing: 0.4,
        }}
      >
        <span style={{ fontSize: 12 }}>📄</span>
        <span style={{ fontWeight: 800, color: "#94a3b8" }}>EVIDENCE SOURCE:</span>
        <span style={{ color: "rgba(255, 255, 255, 0.90)" }}>{sourceCitation}</span>
      </div>
    </div>
  );
};

