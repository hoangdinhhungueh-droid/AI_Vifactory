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

  // Extract props and numeric values dynamically (Rule 128 Anti-Semantic-Bias)
  const baselineVal = payload?.baseline_value ?? 1;
  const detectedVal = payload?.detected_value ?? payload?.actual_value ?? baselineVal;
  const rawMultiplier = payload?.multiplier ?? payload?.ratio ?? (detectedVal / Math.max(0.0001, baselineVal));
  const multiplier = Number(rawMultiplier.toFixed(1));
  const unit = payload?.unit ?? "";
  const paramName = payload?.parameter_name ?? payload?.chemical_name ?? "QUANTITATIVE AUDIT";
  const standardName = payload?.standard_name ?? "STATUTORY BASELINE";
  const detectedName = payload?.detected_name ?? "VERIFIED OBSERVATION";
  const sourceCitation = payload?.source_citation ?? "OFFICIAL VERIFICATION RECORD";

  // Two-Stage Reveal parameters (Secondary statutory standard comparison)
  const secondaryStandardName = payload?.secondary_standard_name;
  const secondaryBaselineVal = payload?.secondary_baseline_value;
  const secondaryMultiplier = payload?.secondary_multiplier ?? (
    secondaryBaselineVal ? Number((detectedVal / Math.max(0.0001, secondaryBaselineVal)).toFixed(1)) : null
  );
  const stageRevealFrame = payload?.stage_reveal_frame ?? 52;
  const hasStage2 = Boolean(secondaryStandardName && secondaryMultiplier && frame >= stageRevealFrame);

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

  const displayTitle = title || label || `QUANTITATIVE AUDIT // ${paramName}`;
  const displayBadge = hasStage2
    ? (badge || `${secondaryMultiplier}× EXCEEDANCE DETECTED`)
    : (badge || `${multiplier}× EXCEEDANCE`);

  // Numeric counter rolling for Stage 1 (0 to multiplier)
  const countProgress = interpolate(frame, [8, 38], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const currentNumericVal = baselineVal + (detectedVal - baselineVal) * countProgress;
  const currentMultiplierVal = 1 + (multiplier - 1) * countProgress;

  // Formatted counter string
  const formattedDetected = currentNumericVal >= 100
    ? Math.round(currentNumericVal).toLocaleString()
    : currentNumericVal.toFixed(1);
  const formattedMultiplier = currentMultiplierVal.toFixed(1);

  // Layout sizing
  const isFullBleed = layout === "full_bleed_focus" || layout === "fullscreen_dossier";
  const containerWidth = isFullBleed ? 980 : 560;

  // Dynamic Scale-Adaptive Layout Selector (Opus 5.5 Architecture)
  const chooseGrid = () => {
    if (payload?.grid_cols && payload?.grid_rows) {
      return { cols: payload.grid_cols, rows: payload.grid_rows };
    }
    if (multiplier <= 12) {
      const c = 4;
      return { cols: c, rows: Math.max(1, Math.ceil(multiplier / c)) };
    }
    if (multiplier <= 25) {
      return { cols: 5, rows: 5 };
    }
    if (multiplier <= 100) {
      const c = 10;
      return { cols: c, rows: Math.min(10, Math.max(1, Math.ceil(multiplier / c))) };
    }
    // High magnitude: comparative bar mode fallback
    return { cols: 5, rows: 5, useBars: true };
  };

  const gridConfig = chooseGrid();
  const cols = gridConfig.cols;
  const rows = gridConfig.rows;
  const totalCells = cols * rows;

  const fullCellsCount = Math.min(totalCells, Math.floor(multiplier));
  const remainder = Number((multiplier - Math.floor(multiplier)).toFixed(2));
  const hasPartialCell = remainder > 0.01 && fullCellsCount < totalCells;
  const partialCellIndex = fullCellsCount;

  // Staccato timing parameters for grid
  const gridStartFrame = 10;
  const framesPerCell = Math.max(0.6, 25 / Math.max(1, totalCells));

  return (
    <div
      style={{
        width: containerWidth,
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
              FORENSIC STATUTORY COMPLIANCE // QUANTITATIVE AUDIT REVEAL
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

      {/* Main Dual Counter Section: Baseline vs Detected */}
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
              BASELINE (1.0×)
            </span>
          </div>
        </div>

        {/* Multiplier Exceedance Badge */}
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
              AUDIT EXCEEDANCE
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
              +{((detectedVal / Math.max(0.0001, baselineVal) - 1) * 100).toFixed(0)}%
            </span>
          </div>
        </div>
      </div>

      {/* Grid Ratio Display or High-Magnitude Comparative View */}
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
          <span>1 CELL = 1.0× BASELINE ({baselineVal} {unit})</span>
          <span style={{ color: "#ef4444", fontWeight: 900 }}>
            {cols}×{rows} MATRIX: {fullCellsCount} FULL {hasPartialCell ? `+ ${remainder}×` : ""} ＝ {multiplier}× TOTAL
          </span>
        </div>

        {/* Dynamic Grid Matrix Container */}
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
            const isFullActive = idx < fullCellsCount;
            const isPartialActive = hasPartialCell && idx === partialCellIndex;
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

            // Partial fill animation
            const fillProgress = spring({
              frame: Math.max(0, frame - cellRevealFrame),
              fps,
              config: { mass: 0.6, stiffness: 180, damping: 18 },
            });
            const partialHeightPercent = isPartialActive
              ? Math.min(100, Math.max(0, fillProgress * remainder * 100))
              : 100;

            const shouldHighlight = isRevealed && (isFullActive || isPartialActive);

            return (
              <div
                key={idx}
                style={{
                  height: isFullBleed ? (cols > 6 ? 32 : 42) : (cols > 6 ? 24 : 30),
                  borderRadius: 5,
                  display: "flex",
                  flexDirection: "column",
                  justifyContent: "center",
                  alignItems: "center",
                  position: "relative",
                  overflow: "hidden",
                  transform: shouldHighlight ? `scale(${cellSpring})` : "scale(1.0)",
                  opacity: shouldHighlight ? cellOpacity : 0.15,
                  backgroundColor: !shouldHighlight
                    ? "rgba(30, 41, 59, 0.35)"
                    : isBaselineCell
                    ? st.cellBaselineBg
                    : isPartialActive
                    ? "rgba(30, 41, 59, 0.45)"
                    : st.cellActiveBg,
                  border: !shouldHighlight
                    ? "1px solid rgba(255, 255, 255, 0.08)"
                    : isBaselineCell
                    ? `2px solid ${st.cellBaselineBorder}`
                    : isPartialActive
                    ? "1.5px dashed rgba(245, 158, 11, 0.85)"
                    : `1.5px solid ${st.cellActiveBorder}`,
                  boxShadow: shouldHighlight
                    ? isBaselineCell
                      ? "0 0 10px rgba(245, 158, 11, 0.4)"
                      : isPartialActive
                      ? "0 0 10px rgba(245, 158, 11, 0.3)"
                      : "0 0 10px rgba(239, 68, 68, 0.55)"
                    : "none",
                }}
              >
                {/* Partial Fill Bar */}
                {isPartialActive && isRevealed && (
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
                    <span style={{ fontSize: isFullBleed ? 10 : 8, fontWeight: 900, color: "#f59e0b", letterSpacing: 0.5 }}>
                      BASE
                    </span>
                    <span style={{ fontSize: isFullBleed ? 9.5 : 7.5, color: "rgba(255, 255, 255, 0.8)", fontWeight: 700 }}>
                      1×
                    </span>
                  </>
                ) : isPartialActive ? (
                  <span
                    style={{
                      position: "relative",
                      zIndex: 2,
                      fontSize: isFullBleed ? 11 : 8.5,
                      fontWeight: 900,
                      color: isRevealed ? "#ffffff" : "rgba(255, 255, 255, 0.3)",
                      fontVariantNumeric: "tabular-nums",
                      textShadow: "0 1px 3px rgba(0,0,0,0.8)",
                    }}
                  >
                    +{remainder}×
                  </span>
                ) : (
                  <span
                    style={{
                      fontSize: isFullBleed ? (cols > 6 ? 10 : 12) : (cols > 6 ? 8 : 9.5),
                      fontWeight: 900,
                      color: shouldHighlight ? "#ffffff" : "rgba(255, 255, 255, 0.3)",
                      fontVariantNumeric: "tabular-nums",
                    }}
                  >
                    #{idx + 1}
                  </span>
                )}

                {/* Micro Alert Dot for Exceeded Cells */}
                {shouldHighlight && !isBaselineCell && !isPartialActive && (
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

      {/* Stage 2 Explosive Morph: Secondary Statutory Comparison (e.g. Domestic vs International) */}
      {hasStage2 && secondaryBaselineVal ? (
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
                STATUTORY COMPARISON // {secondaryStandardName} ({secondaryBaselineVal} {unit})
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
              {secondaryMultiplier}× OVER LIMIT
            </div>
          </div>

          {/* Comparative Ratio Bars */}
          <div style={{ display: "flex", flexDirection: "column", gap: 6 }}>
            {/* Bar 1: Secondary Statutory Limit */}
            <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 10.5 }}>
              <span style={{ width: 160, color: "#94a3b8", fontWeight: 700, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {secondaryStandardName}:
              </span>
              <div style={{ flex: 1, backgroundColor: "rgba(255,255,255,0.08)", height: 12, borderRadius: 3, overflow: "hidden" }}>
                <div
                  style={{
                    width: `${Math.max(1, (secondaryBaselineVal / Math.max(1, detectedVal)) * 100 * stage2BarProgress)}%`,
                    height: "100%",
                    backgroundColor: "#38bdf8",
                  }}
                />
              </div>
              <span style={{ width: 45, color: "#38bdf8", fontWeight: 800, textAlign: "right" }}>1.0×</span>
            </div>

            {/* Bar 2: Primary Standard Limit */}
            <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 10.5 }}>
              <span style={{ width: 160, color: "#94a3b8", fontWeight: 700, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {standardName}:
              </span>
              <div style={{ flex: 1, backgroundColor: "rgba(255,255,255,0.08)", height: 12, borderRadius: 3, overflow: "hidden" }}>
                <div
                  style={{
                    width: `${Math.max(1, (baselineVal / Math.max(1, detectedVal)) * 100 * stage2BarProgress)}%`,
                    height: "100%",
                    backgroundColor: "#f59e0b",
                  }}
                />
              </div>
              <span style={{ width: 45, color: "#f59e0b", fontWeight: 800, textAlign: "right" }}>
                {(baselineVal / Math.max(0.001, secondaryBaselineVal)).toFixed(1)}×
              </span>
            </div>

            {/* Bar 3: Detected Observation */}
            <div style={{ display: "flex", alignItems: "center", gap: 8, fontSize: 10.5 }}>
              <span style={{ width: 160, color: "#fca5a5", fontWeight: 900, overflow: "hidden", textOverflow: "ellipsis", whiteSpace: "nowrap" }}>
                {detectedName}:
              </span>
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
              <span style={{ width: 45, color: "#ef4444", fontWeight: 900, textAlign: "right" }}>
                {secondaryMultiplier}×
              </span>
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
