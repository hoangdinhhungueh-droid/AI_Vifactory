import React from "react";
import { useCurrentFrame, useVideoConfig, interpolate, spring } from "remotion";
import { VoxWashiTape, VoxBrassPin } from "./papercraft";

export interface VoxKineticHeadlineProps {
  headline?: string;
  highlightWord?: string;
  category?: string;
  subtext?: string;
  accentColor?: string;
  theme?: "papercraft" | "dark";
}

export const VoxKineticHeadline: React.FC<VoxKineticHeadlineProps> = ({
  headline,
  highlightWord = "",
  category,
  subtext,
  accentColor = "#d97706",
  theme = "papercraft",
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  if (!headline) return null;

  const words = headline.split(" ");
  const isPaper = theme === "papercraft";

  // Category badge entrance
  const badgeSpring = spring({
    frame,
    fps,
    config: { damping: 14, stiffness: 100 },
  });

  const bannerSpring = spring({
    frame,
    fps,
    config: { damping: 13, mass: 0.65, stiffness: 120 },
  });

  // Precomputed rough deckle edge clip-path for paper banner
  const decklePolygon = `polygon(
    0% 2px, 3% 0px, 8% 3px, 15% 1px, 24% 4px, 35% 0px, 46% 3px, 58% 1px, 70% 3px, 82% 0px, 92% 2px, 100% 0px,
    99% 14%, 100% 28%, 98% 42%, 100% 58%, 99% 72%, 100% 86%, 99% 100%,
    97% 98%, 88% 100%, 78% 97%, 66% 100%, 54% 98%, 42% 100%, 30% 97%, 18% 100%, 8% 98%, 0% 100%,
    2% 86%, 0% 70%, 2% 54%, 1% 38%, 0% 20%
  )`;

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        padding: "0 80px",
        zIndex: 26,
        pointerEvents: "none",
        textAlign: "center",
        fontFamily: isPaper ? "'Impact', 'Arial Black', sans-serif" : "'Playfair Display', Georgia, serif",
      }}
    >
      {/* Category / Investigation Tag */}
      {category ? (
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 8,
            padding: "7px 20px",
            backgroundColor: isPaper ? "#FAF7EE" : "rgba(245, 158, 11, 0.15)",
            border: isPaper ? "2px solid #92400e" : `1.5px solid ${accentColor}`,
            borderRadius: 4,
            color: isPaper ? "#92400e" : accentColor,
            fontSize: 13,
            fontWeight: 900,
            letterSpacing: 2.5,
            textTransform: "uppercase",
            marginBottom: 24,
            transform: `scale(${badgeSpring}) rotate(${isPaper ? "-1deg" : "0deg"})`,
            opacity: badgeSpring,
            boxShadow: isPaper ? "0 4px 14px rgba(45, 30, 15, 0.20)" : `0 0 20px ${accentColor}33`,
            fontFamily: "'Courier Prime', 'Courier New', Courier, monospace",
          }}
        >
          <span style={{ width: 8, height: 8, borderRadius: "50%", backgroundColor: isPaper ? "#dc2626" : accentColor }} />
          {category}
        </div>
      ) : null}

      {/* Main Kinetic Headline Paper Banner */}
      <div
        style={{
          position: "relative",
          backgroundColor: isPaper ? "#FAF7EE" : "transparent",
          clipPath: isPaper ? decklePolygon : undefined,
          border: isPaper ? "1.5px solid rgba(160, 130, 90, 0.45)" : "none",
          boxShadow: isPaper ? "0 22px 55px rgba(45, 30, 15, 0.28), 0 4px 14px rgba(0, 0, 0, 0.12)" : "none",
          padding: isPaper ? "36px 56px 32px 56px" : "0",
          transform: `scale(${bannerSpring}) rotate(${isPaper ? "-0.8deg" : "0deg"})`,
          opacity: bannerSpring,
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          maxWidth: 1380,
        }}
      >
        {/* Authentic Physical Washi Tape Anchors & Brass Pin */}
        {isPaper ? (
          <>
            <VoxWashiTape x="6%" y="-14px" rotation={-24} corner="top_left" dropFrame={4} />
            <VoxWashiTape x="94%" y="-14px" rotation={22} corner="top_right" dropFrame={6} />
            <VoxBrassPin x="50%" y="-10px" size={26} dropFrame={8} />
          </>
        ) : null}

        {/* Paper texture fiber grain overlay */}
        {isPaper ? (
          <div
            style={{
              position: "absolute",
              inset: 0,
              backgroundImage: "radial-gradient(rgba(120, 80, 40, 0.06) 1px, transparent 1px)",
              backgroundSize: "20px 20px",
              pointerEvents: "none",
            }}
          />
        ) : null}

        {/* Word-by-Word Impact Pop */}
        <div
          style={{
            position: "relative",
            zIndex: 10,
            display: "flex",
            flexWrap: "wrap",
            justifyContent: "center",
            gap: "14px 20px",
            maxWidth: 1300,
          }}
        >
          {words.map((word, idx) => {
            const wordDelay = 6 + idx * 5;
            const wordSpring = spring({
              frame: Math.max(0, frame - wordDelay),
              fps,
              config: { damping: 12, stiffness: 130, mass: 0.5 },
            });

            const isHighlight =
              word.toUpperCase().includes(highlightWord.toUpperCase()) ||
              word.replace(/[^A-Za-z0-9가-힣]/g, "").toUpperCase() === highlightWord.toUpperCase();

            const scale = interpolate(wordSpring, [0, 1], [0.8, 1.0]);
            const translateY = interpolate(wordSpring, [0, 1], [28, 0]);

            const highlightBg = isPaper ? (accentColor === "#f59e0b" ? "#dc2626" : accentColor) : accentColor;
            const baseTextColor = isPaper ? "#0F172A" : "#ffffff";
            const highlightTextColor = "#ffffff";

            return (
              <span
                key={idx}
                style={{
                  display: "inline-block",
                  fontSize: 66,
                  fontWeight: 900,
                  letterSpacing: 1.5,
                  textTransform: "uppercase",
                  color: isHighlight ? highlightTextColor : baseTextColor,
                  backgroundColor: isHighlight ? highlightBg : "transparent",
                  padding: isHighlight ? "4px 22px" : "0",
                  borderRadius: isHighlight ? 4 : 0,
                  transform: `translateY(${translateY}px) scale(${scale})`,
                  opacity: wordSpring,
                  textShadow: isHighlight
                    ? "none"
                    : isPaper
                    ? "0 1px 3px rgba(45,30,15,0.18)"
                    : "0 4px 20px rgba(0,0,0,0.9)",
                  boxShadow: isHighlight ? `0 8px 24px rgba(45,30,15,0.30)` : "none",
                }}
              >
                {word}
              </span>
            );
          })}
        </div>

        {/* Subtext reveal */}
        {subtext && (
          <div
            style={{
              position: "relative",
              zIndex: 10,
              marginTop: 22,
              color: isPaper ? "#475569" : "#94a3b8",
              fontSize: 21,
              fontWeight: 700,
              maxWidth: 960,
              fontFamily: isPaper ? "'Courier Prime', 'Courier New', monospace" : "'Segoe UI', Roboto, sans-serif",
              letterSpacing: 1.2,
              opacity: interpolate(frame, [22, 38], [0, 1], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              }),
              transform: `translateY(${interpolate(frame, [22, 38], [15, 0], {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
              })}px)`,
            }}
          >
            {subtext}
          </div>
        )}
      </div>
    </div>
  );
};
