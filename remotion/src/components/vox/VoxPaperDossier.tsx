import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

export interface VoxPaperDossierPayload {
  document_title?: string;
  agency?: string;
  case_number?: string;
  clauses?: string[];
  highlight_line_index?: number;
  redacted_terms?: string[];
  date?: string;
}

export interface VoxPaperDossierProps {
  title?: string;
  badge?: string;
  theme?: "vox_paper" | "noir_dossier" | string;
  layout?: "full_bleed_focus" | "split_right" | "split_left" | "fullscreen_dossier" | string;
  payload?: VoxPaperDossierPayload;
  label?: string;
}

export const VoxPaperDossier: React.FC<VoxPaperDossierProps> = ({
  title,
  badge,
  theme = "vox_paper",
  layout = "full_bleed_focus",
  payload,
  label,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Stop-motion physics (12fps feel on 30fps timeline)
  const steppedFrame = Math.floor(frame / 2.5) * 2.5;

  // Spring slide-in with subtle paper overshoot
  const entrance = spring({
    frame: steppedFrame,
    fps,
    config: { damping: 12, mass: 0.8, stiffness: 140 },
  });

  const opacity = interpolate(steppedFrame, [0, 6], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Animated yellow highlighter pen stroke (0% -> 100% across the targeted clause)
  const highlightProgress = interpolate(frame, [12, 38], [0, 100], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Black marker redaction progress
  const redactProgress = interpolate(frame, [24, 50], [0, 100], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Stamp slam bounce (violent impact + overshoot)
  const stampSlam = spring({
    frame: Math.max(0, frame - 16),
    fps,
    config: { damping: 9, mass: 0.4, stiffness: 220 },
  });

  const displayTitle = title || label || "OFFICIAL INVESTIGATION RECORD";
  const docTitle = payload?.document_title || "EXHIBIT A // EVIDENCE SUBMISSION";
  const agency = payload?.agency || "INDEPENDENT INVESTIGATION TASK FORCE";
  const caseNumber = payload?.case_number || "FORENSIC CASE FILE // EXHIBIT RECORD";
  const docDate = payload?.date || "OFFICIAL INQUIRY RECORD";
  const clauses = payload?.clauses && payload.clauses.length > 0
    ? payload.clauses
    : [
        "1. TRANSACTIONAL AUDIT CONFIRMED SYSTEMIC ANOMALIES IN STATUTORY FILINGS.",
        "2. CLAIMS TOTALING $10,482,910 WERE FRAUDULENTLY SUBMITTED TO ASSISTANCE PROGRAMS.",
        "3. REGULATORY COMPLIANCE OVERSIGHT REVEALED INCONSISTENT RECORD SEQUENCES.",
        "4. FORENSIC PAPER TRAIL DEMONSTRATES PERSISTENT PROTOCOL DEVIATIONS."
      ];
  const highlightIdx = typeof payload?.highlight_line_index === "number" ? payload.highlight_line_index : 1;
  const redactedTerms = payload?.redacted_terms || ["NOMINEE ACCOUNTS", "ZERO QUALIFYING"];
  const displayBadge = badge || "SUBPOENAED EVIDENCE";

  const isFullBleed = layout === "full_bleed_focus" || layout === "fullscreen_dossier";
  const width = isFullBleed ? 1040 : 580;
  const isNoir = theme === "noir_dossier";

  // Paper styling
  const paperBg = isNoir ? "#111827" : "#faf7ee";
  const textColor = isNoir ? "#f3f4f6" : "#1e293b";
  const subtleColor = isNoir ? "#9ca3af" : "#64748b";
  const borderColor = isNoir ? "#374151" : "#e2d9c2";
  const stampColor = isNoir ? "#ef4444" : "#b91c1c";

  return (
    <div
      style={{
        width,
        backgroundColor: paperBg,
        borderRadius: 4,
        padding: isFullBleed ? "32px 42px" : "24px 30px",
        boxShadow: "0 25px 60px rgba(0,0,0,0.65), 0 5px 15px rgba(0,0,0,0.35)",
        border: `1px solid ${borderColor}`,
        fontFamily: "'Courier Prime', 'Special Elite', 'Courier New', Courier, monospace",
        opacity,
        transform: `scale(${entrance}) rotate(-1deg)`,
        transformOrigin: "center center",
        position: "relative",
        overflow: "hidden",
      }}
    >
      {/* Scotch tape at top center */}
      <div
        style={{
          position: "absolute",
          top: -10,
          left: "50%",
          transform: "translateX(-50%) rotate(1.5deg)",
          width: 140,
          height: 32,
          backgroundColor: "rgba(255, 255, 255, 0.45)",
          backdropFilter: "blur(1px)",
          border: "1px solid rgba(255, 255, 255, 0.6)",
          boxShadow: "0 2px 4px rgba(0,0,0,0.12)",
          zIndex: 40,
        }}
      />

      {/* Fold watermark / paper fiber linear texture */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          background: isNoir
            ? "linear-gradient(135deg, rgba(255,255,255,0.03) 0%, rgba(0,0,0,0.2) 100%)"
            : "linear-gradient(135deg, rgba(255,255,255,0.7) 0%, rgba(235,225,200,0.3) 100%)",
          pointerEvents: "none",
          zIndex: 1,
        }}
      />

      {/* Document Header Bar */}
      <div
        style={{
          position: "relative",
          zIndex: 2,
          borderBottom: `2px solid ${isNoir ? "#374151" : "#1e293b"}`,
          paddingBottom: 12,
          marginBottom: 16,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "flex-start",
        }}
      >
        <div>
          <div
            style={{
              fontSize: isFullBleed ? 13 : 11,
              fontWeight: 700,
              letterSpacing: 2,
              color: subtleColor,
              textTransform: "uppercase",
            }}
          >
            {agency} // {caseNumber}
          </div>
          <div
            style={{
              fontSize: isFullBleed ? 22 : 17,
              fontWeight: 900,
              color: textColor,
              letterSpacing: 0.5,
              marginTop: 4,
            }}
          >
            {docTitle}
          </div>
        </div>

        <div style={{ textAlign: "right" }}>
          <div style={{ fontSize: 11, fontWeight: 700, color: subtleColor }}>
            DATE: {docDate}
          </div>
          <div
            style={{
              fontSize: 10,
              fontWeight: 800,
              color: "#f59e0b",
              backgroundColor: "rgba(245, 158, 11, 0.12)",
              padding: "2px 8px",
              borderRadius: 3,
              marginTop: 4,
              display: "inline-block",
            }}
          >
            DOCUMENTARY EXHIBIT
          </div>
        </div>
      </div>

      {/* Clauses / Evidentiary Text Body */}
      <div
        style={{
          position: "relative",
          zIndex: 2,
          display: "flex",
          flexDirection: "column",
          gap: isFullBleed ? 14 : 10,
        }}
      >
        {clauses.map((clause, idx) => {
          const isTargetHighlight = idx === highlightIdx;

          // Check for redaction terms in this line
          let renderedContent: React.ReactNode = clause;
          for (const term of redactedTerms) {
            if (typeof renderedContent === "string" && renderedContent.includes(term)) {
              const parts = renderedContent.split(term);
              renderedContent = (
                <>
                  {parts[0]}
                  <span
                    style={{
                      position: "relative",
                      display: "inline-block",
                      padding: "0 4px",
                      margin: "0 2px",
                      backgroundColor: "#050505",
                      color: "transparent",
                      borderRadius: 2,
                      userSelect: "none",
                      clipPath: `inset(0 ${100 - redactProgress}% 0 0)`,
                      transition: "clip-path 0.1s linear",
                    }}
                  >
                    {term}
                  </span>
                  {parts[1]}
                </>
              );
            }
          }

          return (
            <div
              key={idx}
              style={{
                position: "relative",
                fontSize: isFullBleed ? 16 : 13,
                lineHeight: 1.5,
                color: textColor,
                fontWeight: isTargetHighlight ? 700 : 500,
                padding: "4px 8px",
              }}
            >
              {/* Neon Yellow Highlighter Stroke Overlay */}
              {isTargetHighlight ? (
                <div
                  style={{
                    position: "absolute",
                    inset: 0,
                    backgroundColor: "#ffeb3b",
                    opacity: 0.82,
                    mixBlendMode: isNoir ? "screen" : "multiply",
                    borderRadius: 3,
                    transform: "skewX(-4deg)",
                    clipPath: `inset(0 ${100 - highlightProgress}% 0 0)`,
                    transition: "clip-path 0.05s linear",
                    zIndex: -1,
                  }}
                />
              ) : null}

              {renderedContent}
            </div>
          );
        })}
      </div>

      {/* Forensic Rubber Stamp Slam (Bottom Right) */}
      <div
        style={{
          position: "absolute",
          bottom: 24,
          right: 32,
          zIndex: 10,
          border: `3.5px dashed ${stampColor}`,
          borderRadius: 6,
          padding: isFullBleed ? "8px 20px" : "6px 14px",
          color: stampColor,
          fontSize: isFullBleed ? 24 : 17,
          fontWeight: 900,
          letterSpacing: 3,
          textTransform: "uppercase",
          fontFamily: "'Courier New', Courier, monospace",
          transform: `scale(${stampSlam}) rotate(-8deg)`,
          opacity: stampSlam > 0.05 ? 0.95 : 0,
          boxShadow: "inset 0 0 8px rgba(185, 28, 28, 0.2)",
          backgroundColor: isNoir ? "rgba(17, 24, 39, 0.85)" : "rgba(250, 247, 238, 0.85)",
        }}
      >
        {displayBadge}
      </div>
    </div>
  );
};
