import React from "react";
import { Img, interpolate, spring, staticFile, useCurrentFrame, useVideoConfig } from "remotion";

export interface VoxStickerCutoutProps {
  src: string;
  xPct?: number; // % of canvas width
  yPct?: number; // % of canvas height
  width?: number | string;
  height?: number | string;
  rotation?: number;
  dropFrame?: number;
  stickerBorderWidth?: number; // default 3px
  stickerBorderColor?: string; // default #ffffff
  shadowIntensity?: "subtle" | "medium" | "heavy";
  label?: string;
  role?: string;
  isHero?: boolean;
  style?: React.CSSProperties;
}

export const VoxStickerCutout: React.FC<VoxStickerCutoutProps> = ({
  src,
  xPct = 70,
  yPct = 50,
  width = 540,
  height = 780,
  rotation = 0,
  dropFrame = 0,
  stickerBorderWidth = 3,
  stickerBorderColor = "#ffffff",
  shadowIntensity = "medium",
  label,
  role,
  isHero = false,
  style,
}) => {
  const frame = useCurrentFrame();
  const { fps, durationInFrames = 180 } = useVideoConfig();

  const relFrame = Math.max(0, frame - dropFrame);
  const dropSpring = spring({
    frame: relFrame,
    fps,
    config: { damping: 13, mass: 0.65, stiffness: 130 },
  });

  const translateY = dropFrame > 0 ? interpolate(dropSpring, [0, 1], [-40, 0]) : 0;
  const initialScale = dropFrame > 0 ? interpolate(dropSpring, [0, 1], [0.94, 1.0]) : 1.0;
  const opacity = dropFrame > 0 ? interpolate(dropSpring, [0, 0.25, 1], [0, 0.85, 1.0]) : 1.0;

  // Prompt 3/4 Micro-Idle Breathing (2-4px max, 0.5-1 deg rotation max, permanently locked in place)
  const afterDropRel = Math.max(0, relFrame - 16);
  const microSwayY = Math.sin(afterDropRel * 0.04) * 2;
  const microRot = Math.sin(afterDropRel * 0.03) * 0.4;
  const microScale = 1.0 + Math.sin(afterDropRel * 0.025) * 0.008;

  const currentTranslateY = translateY + microSwayY;
  const currentRotation = rotation + (dropFrame > 0 ? (1 - dropSpring) * 3 : 0) + microRot;
  const currentScale = initialScale * microScale;

  const resolveSrc = (path: string) => {
    if (/^https?:\/\//i.test(path)) return path;
    return staticFile(path);
  };

  // Optimized VOX Paper Sticker Filter: crisp pre-baked white stroke + single-pass soft directional paper shadow
  const shadowAlpha = shadowIntensity === "heavy" ? 0.60 : shadowIntensity === "subtle" ? 0.25 : 0.40;
  const stickerFilter = `drop-shadow(0 14px 22px rgba(0, 0, 0, ${shadowAlpha}))`;

  return (
    <div
      style={{
        position: "absolute",
        left: `${xPct}%`,
        top: `${yPct}%`,
        width,
        height,
        transform: `translate(-50%, -50%) translateY(${currentTranslateY.toFixed(1)}px) scale(${currentScale.toFixed(3)}) rotate(${currentRotation.toFixed(2)}deg)`,
        transformOrigin: "center bottom",
        opacity,
        zIndex: isHero ? 25 : 22,
        pointerEvents: "none",
        ...style,
      }}
    >
      {/* Contact Oval Shadow under feet/base */}
      <div
        style={{
          position: "absolute",
          bottom: 10,
          left: "20%",
          width: "60%",
          height: 22,
          borderRadius: "50%",
          background: "radial-gradient(ellipse at center, rgba(0,0,0,0.55) 0%, rgba(0,0,0,0) 70%)",
          transform: "scaleY(0.4)",
          pointerEvents: "none",
          zIndex: -1,
        }}
      />

      {/* Main Die-Cut Image */}
      <Img
        src={resolveSrc(src)}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "contain",
          objectPosition: "bottom center",
          filter: stickerFilter,
        }}
      />

      {/* Optional Subject Name / Role Label Tag */}
      {(label || role) ? (
        <div
          style={{
            position: "absolute",
            bottom: -8,
            left: "50%",
            transform: "translateX(-50%)",
            backgroundColor: "#FAF7EE",
            border: "1.5px solid #1E293B",
            borderRadius: 4,
            padding: "4px 14px",
            boxShadow: "0 4px 12px rgba(0, 0, 0, 0.35)",
            textAlign: "center",
            whiteSpace: "nowrap",
            zIndex: 30,
          }}
        >
          {label ? (
            <div
              style={{
                color: "#0F172A",
                fontSize: 12,
                fontWeight: 900,
                letterSpacing: 1.2,
                textTransform: "uppercase",
                fontFamily: "'Courier New', Courier, monospace",
              }}
            >
              {label}
            </div>
          ) : null}
          {role ? (
            <div
              style={{
                color: "#64748B",
                fontSize: 10,
                fontWeight: 700,
                letterSpacing: 1,
                textTransform: "uppercase",
                fontFamily: "'Segoe UI', sans-serif",
                marginTop: 1,
              }}
            >
              {role}
            </div>
          ) : null}
        </div>
      ) : null}
    </div>
  );
};
