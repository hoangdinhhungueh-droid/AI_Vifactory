import React from "react";
import { AbsoluteFill, Img, interpolate, staticFile, useCurrentFrame, useVideoConfig } from "remotion";

export type PaperBackdropTheme = "parchment" | "blueprint" | "manila" | "vintage_map";

export interface VoxPaperBackdropProps {
  theme?: PaperBackdropTheme;
  bgImage?: string | null;
  showVignette?: boolean;
  showFoldCrease?: boolean;
  showGrid?: boolean;
  opacity?: number;
  zoomScale?: number;
  style?: React.CSSProperties;
  children?: React.ReactNode;
}

export const VoxPaperBackdrop: React.FC<VoxPaperBackdropProps> = ({
  theme = "parchment",
  bgImage,
  showVignette = true,
  showFoldCrease = true,
  showGrid = true,
  opacity = 1.0,
  zoomScale = 1.03,
  style,
  children,
}) => {
  const frame = useCurrentFrame();
  const { width = 1920, height = 1080, durationInFrames = 300 } = useVideoConfig();

  // Subtle living camera drift on the paper texture (0-3%)
  const scale = interpolate(frame, [0, durationInFrames], [1.0, zoomScale], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const panX = interpolate(frame, [0, durationInFrames], [0, -8], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Base colors by theme
  let baseColor = "#F5F2EB"; // warm off-white aged ivory
  let gridLineColor = "rgba(120, 80, 40, 0.05)";
  let dotColor = "rgba(120, 80, 40, 0.08)";
  let vignetteColor = "rgba(40, 25, 10, 0.35)";

  if (theme === "blueprint") {
    baseColor = "#1e293b"; // tactical dark navy blueprint
    gridLineColor = "rgba(56, 189, 248, 0.08)";
    dotColor = "rgba(255, 255, 255, 0.06)";
    vignetteColor = "rgba(2, 6, 23, 0.65)";
  } else if (theme === "manila") {
    baseColor = "#E3DAC9"; // warm manila craft folder
    gridLineColor = "rgba(100, 70, 30, 0.06)";
    dotColor = "rgba(100, 70, 30, 0.09)";
    vignetteColor = "rgba(50, 30, 15, 0.40)";
  } else if (theme === "vintage_map") {
    baseColor = "#ECE6D5"; // antique navigational chart
    gridLineColor = "rgba(80, 60, 40, 0.07)";
    dotColor = "rgba(80, 60, 40, 0.10)";
    vignetteColor = "rgba(45, 30, 15, 0.38)";
  }

  const resolveSrc = (src: string) => {
    if (/^https?:\/\//i.test(src)) return src;
    return staticFile(src);
  };

  return (
    <AbsoluteFill
      style={{
        backgroundColor: baseColor,
        overflow: "hidden",
        opacity,
        ...style,
      }}
    >
      {/* Container with gentle slow documentary camera drift */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          transform: `translate(${panX.toFixed(1)}px, 0) scale(${scale.toFixed(4)})`,
          transformOrigin: "center center",
        }}
      >
        {/* Background Image layer (if provided, blended with paper rather than dark void) */}
        {bgImage ? (
          <AbsoluteFill>
            <Img
              src={resolveSrc(bgImage)}
              style={{
                width: "100%",
                height: "100%",
                objectFit: "cover",
                filter: theme === "blueprint" 
                  ? "brightness(0.65) contrast(1.15) saturate(0.5) hue-rotate(180deg)"
                  : "brightness(0.92) saturate(0.7) sepia(0.25) contrast(1.05)",
                opacity: 0.88,
              }}
            />
            {/* Paper wash overlay */}
            <div
              style={{
                position: "absolute",
                inset: 0,
                backgroundColor: baseColor,
                opacity: 0.35,
                mixBlendMode: "multiply",
              }}
            />
          </AbsoluteFill>
        ) : null}

        {/* Paper Grid Matrix */}
        {showGrid ? (
          <div
            style={{
              position: "absolute",
              inset: 0,
              backgroundImage: `
                linear-gradient(to right, ${gridLineColor} 1px, transparent 1px),
                linear-gradient(to bottom, ${gridLineColor} 1px, transparent 1px)
              `,
              backgroundSize: "60px 60px",
              pointerEvents: "none",
            }}
          />
        ) : null}

        {/* Fine Halftone Dot Texture */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            backgroundImage: `radial-gradient(${dotColor} 1.2px, transparent 1.2px)`,
            backgroundSize: "24px 24px",
            pointerEvents: "none",
          }}
        />

        {/* Blueprint Radar / Circle Graphics (Blueprint Theme only) */}
        {theme === "blueprint" ? (
          <svg
            width="100%"
            height="100%"
            style={{ position: "absolute", inset: 0, pointerEvents: "none", opacity: 0.25 }}
          >
            <circle cx="50%" cy="50%" r="350" fill="none" stroke="#38bdf8" strokeWidth="1" strokeDasharray="6,4" />
            <circle cx="50%" cy="50%" r="520" fill="none" stroke="#38bdf8" strokeWidth="1" strokeDasharray="10,6" />
            <line x1="50%" y1="10%" x2="50%" y2="90%" stroke="#38bdf8" strokeWidth="1" strokeDasharray="4,4" />
            <line x1="10%" y1="50%" x2="90%" y2="50%" stroke="#38bdf8" strokeWidth="1" strokeDasharray="4,4" />
          </svg>
        ) : null}

        {/* Fold Creases / Cardboard Seams */}
        {showFoldCrease && theme !== "blueprint" ? (
          <>
            {/* Vertical Center Fold */}
            <div
              style={{
                position: "absolute",
                top: 0,
                bottom: 0,
                left: "49.8%",
                width: "0.4%",
                background: "linear-gradient(to right, rgba(0,0,0,0.06), rgba(255,255,255,0.12), rgba(0,0,0,0.04))",
                pointerEvents: "none",
              }}
            />
            {/* Horizontal Upper Fold */}
            <div
              style={{
                position: "absolute",
                left: 0,
                right: 0,
                top: "33%",
                height: "2px",
                background: "linear-gradient(to bottom, rgba(0,0,0,0.04), rgba(255,255,255,0.08))",
                pointerEvents: "none",
              }}
            />
          </>
        ) : null}

        {/* Soft Vignette Edge Shadow */}
        {showVignette ? (
          <div
            style={{
              position: "absolute",
              inset: 0,
              background: `radial-gradient(ellipse at 50% 50%, transparent 55%, ${vignetteColor} 100%)`,
              pointerEvents: "none",
            }}
          />
        ) : null}
      </div>

      {children}
    </AbsoluteFill>
  );
};
