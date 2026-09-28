import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";

export interface VoxDocumentHighlightPayload {
  document_title?: string;
  clauses?: string[];
  highlight_line_index?: number;
  redacted_terms?: string[];
}

export interface VoxDocumentHighlightProps {
  title?: string;
  badge?: string;
  theme?: "noir_dossier" | "tech_infographic" | "surveillance_cctv" | string;
  layout?: "split_right" | "split_left" | "fullscreen_dossier" | "floating_card" | string;
  payload?: VoxDocumentHighlightPayload;
  label?: string;
}

export const VoxDocumentHighlight: React.FC<VoxDocumentHighlightProps> = ({
  title,
  badge,
  theme = "noir_dossier",
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
      badgeBorder: "#ef4444",
      badgeColor: "#ef4444",
      highlightColor: "rgba(255, 230, 0, 0.42)",
      highlightBorder: "1px solid rgba(255, 230, 0, 0.75)",
      redactColor: "#05080f",
      textColor: "#cbd5e1",
      shadow: "0 15px 40px rgba(0,0,0,0.85), inset 0 0 20px rgba(242,166,59,0.12)",
    },
    tech_infographic: {
      bg: "rgba(7, 20, 34, 0.94)",
      border: "1.5px solid rgba(56, 189, 248, 0.55)",
      headerColor: "#38bdf8",
      badgeBorder: "#10b981",
      badgeColor: "#10b981",
      highlightColor: "rgba(56, 189, 248, 0.35)",
      highlightBorder: "1px solid rgba(56, 189, 248, 0.8)",
      redactColor: "#020b14",
      textColor: "#94a3b8",
      shadow: "0 15px 40px rgba(0,0,0,0.85), 0 0 25px rgba(56,189,248,0.2)",
    },
    surveillance_cctv: {
      bg: "rgba(4, 18, 12, 0.95)",
      border: "1.5px solid rgba(34, 197, 94, 0.55)",
      headerColor: "#22c55e",
      badgeBorder: "#ef4444",
      badgeColor: "#ef4444",
      highlightColor: "rgba(34, 197, 94, 0.38)",
      highlightBorder: "1px solid rgba(34, 197, 94, 0.8)",
      redactColor: "#020d06",
      textColor: "#86efac",
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

  const highlightProgress = interpolate(frame, [10, 36], [0, 100], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const redactProgress = interpolate(frame, [22, 48], [0, 100], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const badgeScale = spring({
    frame: Math.max(0, frame - 18),
    fps,
    config: { damping: 10, mass: 0.5, stiffness: 150 },
  });

  const displayTitle = title || label || "LEGAL CLAUSE // EXCLUSION AUDIT";
  const docTitle = payload?.document_title || "OFFICIAL MEMORANDUM // EXCLUSION PROVISION";
  const clauses = payload?.clauses && payload.clauses.length > 0
    ? payload.clauses
    : [
        "SECTION 4 // NON-REFUNDABLE CONTINGENCY",
        "ARTICLE 17 // EXCLUSION OF LIABILITY",
        "ARBITRATION PROTOCOL // FINAL BINDING VERDICT",
      ];
  const highlightIdx = typeof payload?.highlight_line_index === "number" ? payload.highlight_line_index : 1;
  const redactedTerms = payload?.redacted_terms || ["ARBITRATION PROTOCOL", "NON-REFUNDABLE"];
  const displayBadge = badge || "SUBPOENAED";

  const isFullscreen = layout === "fullscreen_dossier";
  const width = isFullscreen ? 880 : 520;

  return (
    <div
      style={{
        width,
        backgroundColor: st.bg,
        border: st.border,
        borderRadius: 14,
        padding: "20px 24px",
        boxShadow: st.shadow,
        zIndex: 28,
        fontFamily: "'Courier New', Courier, monospace",
        opacity,
        transform: `scale(${scale})`,
        transformOrigin: "top center",
      }}
    >
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          borderBottom: "1px solid rgba(255, 255, 255, 0.15)",
          paddingBottom: 8,
          marginBottom: 12,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ fontSize: 16 }}>📁</span>
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

        {displayBadge ? (
          <div
            style={{
              transform: `scale(${badgeScale})`,
              transformOrigin: "center center",
              border: `1.5px solid ${st.badgeBorder}`,
              color: st.badgeColor,
              fontSize: 11,
              fontWeight: 900,
              letterSpacing: 1.5,
              padding: "2px 8px",
              borderRadius: 4,
              backgroundColor: "rgba(0,0,0,0.4)",
              boxShadow: `0 0 10px ${st.badgeBorder}`,
            }}
          >
            {displayBadge}
          </div>
        ) : null}
      </div>

      <div
        style={{
          fontSize: 11,
          color: "rgba(255, 255, 255, 0.45)",
          letterSpacing: 1,
          marginBottom: 12,
          textTransform: "uppercase",
        }}
      >
        RECORD REF: {docTitle}
      </div>

      <div style={{ display: "flex", flexDirection: "column", gap: 10 }}>
        {clauses.map((clause, idx) => {
          const isHighlighted = idx === highlightIdx;
          const isRedacted = redactedTerms.some((term) =>
            clause.toLowerCase().includes(term.toLowerCase())
          );

          return (
            <div
              key={idx}
              style={{
                position: "relative",
                fontSize: 13,
                lineHeight: 1.6,
                color: isHighlighted ? "#ffffff" : st.textColor,
                padding: "4px 8px",
                borderRadius: 4,
                overflow: "hidden",
              }}
            >
              {isHighlighted ? (
                (() => {
                  const isLegalStatute = clause.includes("法") || clause.includes("基準") || clause.includes("GB") || clause.includes("ARTICLE") || clause.includes("SECTION");
                  const markerBg = isLegalStatute
                    ? "linear-gradient(90deg, rgba(249, 115, 22, 0.45) 0%, rgba(251, 146, 60, 0.52) 85%, rgba(249, 115, 22, 0.65) 100%)"
                    : "linear-gradient(90deg, rgba(232, 194, 41, 0.45) 0%, rgba(255, 230, 0, 0.55) 85%, rgba(232, 194, 41, 0.65) 100%)";
                  const markerBorder = isLegalStatute
                    ? "1px solid rgba(249, 115, 22, 0.85)"
                    : "1px solid rgba(232, 194, 41, 0.85)";
                  return (
                    <div
                      style={{
                        position: "absolute",
                        top: 1,
                        left: 0,
                        bottom: 1,
                        width: `${highlightProgress}%`,
                        background: markerBg,
                        border: markerBorder,
                        borderRadius: 3,
                        boxShadow: isLegalStatute
                          ? "0 0 10px rgba(249, 115, 22, 0.4)"
                          : "0 0 10px rgba(232, 194, 41, 0.4)",
                        zIndex: 0,
                      }}
                    />
                  );
                })()
              ) : null}

              <span style={{ position: "relative", zIndex: 1, fontWeight: isHighlighted ? 700 : 500 }}>
                {clause}
              </span>

              {isRedacted && idx !== highlightIdx ? (
                <div
                  style={{
                    position: "absolute",
                    top: 2,
                    left: 4,
                    bottom: 2,
                    width: `${redactProgress}%`,
                    backgroundColor: st.redactColor,
                    border: "1px solid rgba(255,255,255,0.08)",
                    borderRadius: 3,
                    zIndex: 2,
                  }}
                />
              ) : null}
            </div>
          );
        })}
      </div>
    </div>
  );
};
