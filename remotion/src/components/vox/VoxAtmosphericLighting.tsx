import React from "react";
import { AbsoluteFill, interpolate, useCurrentFrame, useVideoConfig } from "remotion";

interface DustMote {
  x: number;
  y: number;
  size: number;
  speedX: number;
  speedY: number;
  opacity: number;
}

const GENERATE_MOTES = (count: number): DustMote[] => {
  const motes: DustMote[] = [];
  for (let i = 0; i < count; i++) {
    const seed = (i + 1) * 9301 + 49297;
    const rand1 = ((seed * 233) % 1000) / 1000;
    const rand2 = ((seed * 439) % 1000) / 1000;
    const rand3 = ((seed * 701) % 1000) / 1000;
    motes.push({
      x: rand1 * 1920,
      y: rand2 * 1080,
      size: 2 + rand3 * 3.5,
      speedX: (rand1 - 0.5) * 0.4,
      speedY: -0.2 - rand2 * 0.3,
      opacity: 0.25 + rand3 * 0.45,
    });
  }
  return motes;
};

const DUST_MOTES = GENERATE_MOTES(24);

export const VoxAtmosphericLighting: React.FC<{
  intensity?: number;
}> = ({ intensity = 1.0 }) => {
  const frame = useCurrentFrame();
  const { width, height } = useVideoConfig();
  const steppedFrame = Math.floor(frame / 2.5) * 2.5;

  const sweepTranslate = interpolate(
    steppedFrame,
    [0, 300],
    [-80, 80],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );

  const sweepOpacity = interpolate(
    Math.sin(steppedFrame * 0.03),
    [-1, 1],
    [0.08 * intensity, 0.16 * intensity]
  );

  return (
    <AbsoluteFill style={{ pointerEvents: "none", zIndex: 22, overflow: "hidden" }}>
      <div
        style={{
          position: "absolute",
          top: -200,
          left: -200,
          width: width + 400,
          height: height + 400,
          background: "linear-gradient(135deg, rgba(255, 235, 180, 0.12) 0%, rgba(255, 255, 255, 0.0) 50%, rgba(200, 225, 255, 0.08) 100%)",
          transform: `translateX(${sweepTranslate}px) rotate(-12deg)`,
          opacity: sweepOpacity,
          mixBlendMode: "screen",
        }}
      />
      {DUST_MOTES.map((mote, idx) => {
        const posX = (mote.x + steppedFrame * mote.speedX * 3.0 + 1920) % 1920;
        const posY = (mote.y + steppedFrame * mote.speedY * 3.0 + 1080) % 1080;
        const flicker = 0.85 + Math.sin(steppedFrame * 0.1 + idx) * 0.15;
        const finalOpacity = mote.opacity * flicker * intensity;

        return (
          <div
            key={idx}
            style={{
              position: "absolute",
              left: posX,
              top: posY,
              width: mote.size,
              height: mote.size,
              borderRadius: "50%",
              backgroundColor: "#fffaed",
              opacity: finalOpacity,
              boxShadow: `0 0 ${mote.size * 2}px rgba(255, 245, 220, 0.8)`,
            }}
          />
        );
      })}
    </AbsoluteFill>
  );
};
