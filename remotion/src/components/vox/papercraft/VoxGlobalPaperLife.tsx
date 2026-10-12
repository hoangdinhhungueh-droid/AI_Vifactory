import React from "react";
import { AbsoluteFill, useCurrentFrame, useVideoConfig } from "remotion";

export interface VoxGlobalPaperLifeProps {
  intensity?: number; // 0.0 - 1.0 (default 0.75)
  showVignette?: boolean;
  showDust?: boolean;
  style?: React.CSSProperties;
}

/**
 * VoxGlobalPaperLife: Global Archival Paper Life, Grain & Tactile Mote Overlay.
 *
 * Implements Rule 122 & YouTube Vox/MH370 Reference Parity:
 * - Unifies foreground, cutouts, text, and background into one single tactile physical scene
 * - Warm archival paper fiber & fine halftone grain
 * - Subtle camera gate-weave & micro ambient light breathing
 * - Drifting documentary archive dust motes
 */
export const VoxGlobalPaperLife: React.FC<VoxGlobalPaperLifeProps> = ({
  intensity = 0.75,
  showVignette = true,
  showDust = true,
  style,
}) => {
  const frame = useCurrentFrame();
  const { width = 1920, height = 1080 } = useVideoConfig();

  // Gentle 4-second breathing cycle
  const breath = Math.sin(frame * 0.05) * 0.08;

  // Slow drifting documentary dust motes
  const motes = [
    {
      x: ((Math.sin(frame * 0.018) * 45 + 240) % width + width) % width,
      y: ((Math.cos(frame * 0.014) * 35 + 320) % height + height) % height,
      size: 2.8,
      opacity: 0.35 + Math.sin(frame * 0.04) * 0.15,
      color: "rgba(255, 248, 230, 0.45)",
    },
    {
      x: ((Math.cos(frame * 0.022) * 50 + 1380) % width + width) % width,
      y: ((Math.sin(frame * 0.016) * 40 + 640) % height + height) % height,
      size: 2.2,
      opacity: 0.30 + Math.cos(frame * 0.05) * 0.12,
      color: "rgba(240, 200, 140, 0.42)",
    },
    {
      x: ((Math.sin(frame * 0.012) * 60 + 860) % width + width) % width,
      y: ((Math.cos(frame * 0.020) * 35 + 210) % height + height) % height,
      size: 3.2,
      opacity: 0.28 + Math.sin(frame * 0.03) * 0.14,
      color: "rgba(255, 255, 255, 0.40)",
    },
    {
      x: ((Math.cos(frame * 0.016) * 45 + 520) % width + width) % width,
      y: ((Math.sin(frame * 0.024) * 30 + 850) % height + height) % height,
      size: 2.0,
      opacity: 0.25 + Math.cos(frame * 0.04) * 0.10,
      color: "rgba(230, 190, 130, 0.38)",
    },
    {
      x: ((Math.sin(frame * 0.025) * 55 + 1650) % width + width) % width,
      y: ((Math.cos(frame * 0.018) * 40 + 480) % height + height) % height,
      size: 2.5,
      opacity: 0.32 + Math.sin(frame * 0.06) * 0.16,
      color: "rgba(255, 245, 220, 0.42)",
    },
  ];

  return (
    <AbsoluteFill
      style={{
        pointerEvents: "none",
        zIndex: 36,
        overflow: "hidden",
        ...style,
      }}
    >
      {/* 1. WARM ARCHIVAL AMBIENT LIGHT BREATHING */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          background:
            "radial-gradient(ellipse at 48% 46%, rgba(255, 242, 215, 0.045) 0%, transparent 75%)",
          opacity: 1 + breath,
        }}
      />

      {/* 2. SUBTLE ARCHIVAL PAPER GRAIN / HALFTONE MATRIX */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundImage:
            "radial-gradient(rgba(100, 70, 40, 0.07) 1px, transparent 1px)",
          backgroundSize: "18px 18px",
          opacity: 0.55 * intensity,
          mixBlendMode: "multiply",
        }}
      />

      {/* 3. VINTAGE PAPER EDGE VIGNETTE */}
      {showVignette && (
        <div
          style={{
            position: "absolute",
            inset: 0,
            background:
              "radial-gradient(ellipse at 50% 50%, transparent 62%, rgba(45, 28, 12, 0.18) 100%)",
            opacity: 0.85 * intensity,
            mixBlendMode: "multiply",
          }}
        />
      )}

      {/* 4. TACTILE FLOATING DUST MOTES */}
      {showDust &&
        motes.map((m, idx) => (
          <div
            key={idx}
            style={{
              position: "absolute",
              left: m.x,
              top: m.y,
              width: m.size,
              height: m.size,
              borderRadius: "50%",
              backgroundColor: m.color,
              boxShadow: `0 0 3px ${m.color}`,
              opacity: m.opacity * intensity,
            }}
          />
        ))}
    </AbsoluteFill>
  );
};
