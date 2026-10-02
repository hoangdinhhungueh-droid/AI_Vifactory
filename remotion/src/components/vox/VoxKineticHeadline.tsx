import React from "react";
import { useCurrentFrame, useVideoConfig, interpolate, spring } from "remotion";

export interface VoxKineticHeadlineProps {
  headline?: string;
  highlightWord?: string;
  category?: string;
  subtext?: string;
  accentColor?: string;
}

export const VoxKineticHeadline: React.FC<VoxKineticHeadlineProps> = ({
  headline,
  highlightWord = "",
  category,
  subtext,
  accentColor = "#f59e0b",
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  if (!headline) return null;

  const words = headline.split(" ");

  // Category badge entrance
  const badgeSpring = spring({
    frame,
    fps,
    config: { damping: 14, stiffness: 100 },
  });

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        display: "flex",
        flexDirection: "column",
        justifyContent: "center",
        alignItems: "center",
        padding: "0 100px",
        zIndex: 26,
        pointerEvents: "none",
        textAlign: "center",
        fontFamily: "'Playfair Display', Georgia, serif",
      }}
    >
      {/* Category / Investigation Tag */}
      {category ? (
        <div
          style={{
            display: "inline-flex",
            alignItems: "center",
            gap: 8,
            padding: "6px 16px",
            backgroundColor: "rgba(245, 158, 11, 0.15)",
            border: `1.5px solid ${accentColor}`,
            borderRadius: 8,
            color: accentColor,
            fontSize: 14,
            fontWeight: 900,
            letterSpacing: 3,
            textTransform: "uppercase",
            marginBottom: 24,
            transform: `scale(${badgeSpring})`,
            opacity: badgeSpring,
            boxShadow: `0 0 20px ${accentColor}33`,
          }}
        >
          <span style={{ width: 8, height: 8, borderRadius: "50%", backgroundColor: accentColor }} />
          {category}
        </div>
      ) : null}

      {/* Main Kinetic Headline (Word-by-Word Impact Pop) */}
      <div
        style={{
          display: "flex",
          flexWrap: "wrap",
          justifyContent: "center",
          gap: "14px 20px",
          maxWidth: 1400,
        }}
      >
        {words.map((word, idx) => {
          const wordDelay = 4 + idx * 5;
          const wordSpring = spring({
            frame: Math.max(0, frame - wordDelay),
            fps,
            config: { damping: 12, stiffness: 130, mass: 0.5 },
          });

          const isHighlight =
            word.toUpperCase().includes(highlightWord.toUpperCase()) ||
            word.replace(/[^A-Za-z0-9]/g, "").toUpperCase() === highlightWord.toUpperCase();

          const scale = interpolate(wordSpring, [0, 1], [0.8, 1.0]);
          const translateY = interpolate(wordSpring, [0, 1], [30, 0]);

          return (
            <span
              key={idx}
              style={{
                display: "inline-block",
                fontSize: 68,
                fontWeight: 900,
                letterSpacing: -1,
                color: isHighlight ? "#000000" : "#ffffff",
                backgroundColor: isHighlight ? accentColor : "transparent",
                padding: isHighlight ? "0 18px" : "0",
                borderRadius: isHighlight ? 8 : 0,
                transform: `translateY(${translateY}px) scale(${scale})`,
                opacity: wordSpring,
                textShadow: isHighlight ? "none" : "0 4px 20px rgba(0,0,0,0.9)",
                boxShadow: isHighlight ? `0 8px 30px ${accentColor}66` : "none",
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
            marginTop: 28,
            color: "#94a3b8",
            fontSize: 22,
            fontWeight: 600,
            maxWidth: 900,
            fontFamily: "'Segoe UI', Roboto, sans-serif",
            letterSpacing: 0.5,
            opacity: interpolate(frame, [20, 35], [0, 1], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            }),
            transform: `translateY(${interpolate(frame, [20, 35], [15, 0], {
              extrapolateLeft: "clamp",
              extrapolateRight: "clamp",
            })}px)`,
          }}
        >
          {subtext}
        </div>
      )}
    </div>
  );
};
