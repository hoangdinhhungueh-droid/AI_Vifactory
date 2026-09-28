import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { WordTimestamp } from "../../types";

export interface VoxKineticTypographyProps {
  words?: WordTimestamp[];
  highlightKeywords?: string[];
  accentColor?: string;
  position?: "center" | "lower_third" | "upper_center";
  disabled?: boolean;
}

// Default investigative shock keywords that trigger kinetic punch
const DEFAULT_KEYWORD_PATTERNS = [
  "VIOLATION",
  "FRAUD",
  "CRITICAL",
  "CRASH",
  "ILLEGAL",
  "EXCEED",
  "ALERT",
  "CORRUPT",
  "CONTRABAND",
  "基準値",
  "超過",
  "違法",
  "偽装",
  "虚偽",
  "危険",
  "毒物",
  "摘発",
  "劇物",
  "強制捜査",
  "위반",
  "사기",
  "불법",
  "초과",
  "기준치",
];

export const VoxKineticTypography: React.FC<VoxKineticTypographyProps> = ({
  words,
  highlightKeywords,
  accentColor = "#ffd166",
  position = "center",
  disabled = false,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  if (disabled || !words || !Array.isArray(words) || words.length === 0) {
    return null;
  }

  const currentMs = (frame / fps) * 1000;
  const targetKeywords = highlightKeywords && highlightKeywords.length > 0
    ? highlightKeywords
    : DEFAULT_KEYWORD_PATTERNS;

  // Find active keyword based on word timestamps
  const activeWordIndex = words.findIndex((w) => {
    if (!w || !w.word) return false;
    // Buffer end_ms slightly for readable impact hold
    const holdEndMs = w.end_ms + 200;
    if (currentMs < w.start_ms || currentMs > holdEndMs) {
      return false;
    }
    const cleanWord = w.word.trim();
    // Check keyword match
    return targetKeywords.some(
      (kw) => cleanWord.includes(kw) || kw.includes(cleanWord)
    );
  });

  if (activeWordIndex === -1) {
    return null;
  }

  const activeWord = words[activeWordIndex];
  const wordStartFrame = Math.round((activeWord.start_ms / 1000) * fps);
  const wordEndFrame = Math.round((activeWord.end_ms / 1000) * fps);
  const relFrame = Math.max(0, frame - wordStartFrame);
  const wordDurFrames = Math.max(1, wordEndFrame - wordStartFrame);

  // High-impact spring punch (rapid pop-in slam)
  const punchScale = spring({
    frame: relFrame,
    fps,
    config: { damping: 11, mass: 0.35, stiffness: 240 },
    from: 2.2,
    to: 1.0,
  });

  // Deterministic directional motion blur (peaks during entrance velocity)
  const motionBlurPx = interpolate(relFrame, [0, 2, 5], [12, 4, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Opacity fade in & exit fade out
  const fadeIn = interpolate(relFrame, [0, 2], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const fadeOut = interpolate(
    relFrame,
    [wordDurFrames + 1, wordDurFrames + 6],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );
  const opacity = Math.min(fadeIn, fadeOut);

  // Position alignment
  let topStyle: React.CSSProperties = {
    top: "44%",
    left: "50%",
    transform: `translate(-50%, -50%) scale(${punchScale})`,
  };

  if (position === "lower_third") {
    topStyle = {
      bottom: 140,
      left: "50%",
      transform: `translateX(-50%) scale(${punchScale})`,
    };
  } else if (position === "upper_center") {
    topStyle = {
      top: 180,
      left: "50%",
      transform: `translateX(-50%) scale(${punchScale})`,
    };
  }

  const isDanger = ["超過", "違法", "危険", "毒物", "摘発", "24倍", "VIOLATION", "FRAUD", "ILLEGAL"].some(
    (k) => activeWord.word.includes(k)
  );
  const finalColor = isDanger ? "#ef4444" : accentColor;
  const glowColor = isDanger ? "rgba(239, 68, 68, 0.85)" : "rgba(255, 209, 102, 0.85)";

  return (
    <div
      style={{
        position: "absolute",
        ...topStyle,
        zIndex: 38,
        display: "flex",
        flexDirection: "column",
        alignItems: "center",
        justifyContent: "center",
        pointerEvents: "none",
        opacity,
        filter: motionBlurPx > 0.1 ? `blur(${motionBlurPx.toFixed(1)}px)` : undefined,
        willChange: "transform, opacity, filter",
      }}
    >
      {/* Tactical Framing HUD Brackets */}
      <div
        style={{
          display: "flex",
          alignItems: "center",
          gap: 16,
          backgroundColor: "rgba(5, 9, 14, 0.82)",
          border: `2px solid ${finalColor}`,
          borderRadius: 12,
          padding: "12px 32px",
          boxShadow: `0 20px 60px rgba(0, 0, 0, 0.9), 0 0 35px ${glowColor}`,
        }}
      >
        <span
          style={{
            fontSize: 48,
            color: finalColor,
            fontWeight: 300,
            lineHeight: 1,
            userSelect: "none",
          }}
        >
          [
        </span>

        <span
          style={{
            fontFamily: "'Zen Kaku Gothic New', 'Hiragino Sans', 'Yu Gothic', sans-serif",
            fontFeatureSettings: '"palt" 1',
            fontSize: 74,
            fontWeight: 900,
            lineHeight: 1.1,
            color: finalColor,
            letterSpacing: 2,
            textShadow: `0 0 20px ${glowColor}, 0 4px 16px rgba(0,0,0,0.95)`,
            textTransform: "uppercase",
            textAlign: "center",
          }}
        >
          {activeWord.word}
        </span>

        <span
          style={{
            fontSize: 48,
            color: finalColor,
            fontWeight: 300,
            lineHeight: 1,
            userSelect: "none",
          }}
        >
          ]
        </span>
      </div>

      {/* Micro Telemetry Cue */}
      <div
        style={{
          marginTop: 6,
          fontSize: 12,
          fontWeight: 800,
          color: "rgba(255, 255, 255, 0.75)",
          letterSpacing: 2,
          textTransform: "uppercase",
          fontFamily: "'Courier New', Courier, monospace",
          textShadow: "0 2px 4px rgba(0,0,0,0.9)",
        }}
      >
        KEY PHRASE VERIFIED // {activeWord.start_ms}ms
      </div>
    </div>
  );
};
