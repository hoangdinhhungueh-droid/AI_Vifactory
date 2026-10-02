import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { VoxBrassPin } from "./VoxBrassPin";
import { VoxWashiTape } from "./VoxWashiTape";

export interface VoxTornPaperProps {
  children?: React.ReactNode;
  width?: number | string;
  height?: number | string;
  x?: number | string;
  y?: number | string;
  rotation?: number;
  color?: "ivory" | "cream" | "crimson" | "blueprint_dark" | "manila";
  dropFrame?: number;
  hasTapeTopLeft?: boolean;
  hasTapeTopRight?: boolean;
  hasPinTopRight?: boolean;
  hasPinCenter?: boolean;
  roughness?: "subtle" | "medium" | "heavy";
  style?: React.CSSProperties;
}

export const VoxTornPaper: React.FC<VoxTornPaperProps> = ({
  children,
  width = 680,
  height = 420,
  x = "50%",
  y = "50%",
  rotation = -1.5,
  color = "ivory",
  dropFrame = 0,
  hasTapeTopLeft = false,
  hasTapeTopRight = false,
  hasPinTopRight = false,
  hasPinCenter = false,
  roughness = "medium",
  style,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const relFrame = Math.max(0, frame - dropFrame);
  const paperSpring = spring({
    frame: relFrame,
    fps,
    config: { damping: 13, mass: 0.6, stiffness: 120 },
  });

  const translateY = dropFrame > 0 ? interpolate(paperSpring, [0, 1], [-45, 0]) : 0;
  const scale = dropFrame > 0 ? interpolate(paperSpring, [0, 1], [0.92, 1.0]) : 1.0;
  const opacity = dropFrame > 0 ? interpolate(paperSpring, [0, 0.3, 1], [0, 0.85, 1.0]) : 1.0;

  // Paper color themes
  let paperBg = "#FAF7EE";
  let paperText = "#1A1A1A";
  let paperBorder = "1px solid rgba(180, 160, 130, 0.35)";
  let shadowColor = "rgba(45, 30, 15, 0.22)";

  if (color === "cream") {
    paperBg = "#F4EDE1";
    paperText = "#1F2937";
    paperBorder = "1px solid rgba(160, 140, 110, 0.4)";
    shadowColor = "rgba(40, 25, 10, 0.25)";
  } else if (color === "crimson") {
    paperBg = "#DC2626"; // vibrant archival crimson like intro_sec_10.jpg
    paperText = "#FFFFFF";
    paperBorder = "1px solid rgba(153, 27, 27, 0.5)";
    shadowColor = "rgba(120, 20, 20, 0.35)";
  } else if (color === "blueprint_dark") {
    paperBg = "#1E293B";
    paperText = "#F8FAFC";
    paperBorder = "1px solid rgba(56, 189, 248, 0.3)";
    shadowColor = "rgba(0, 0, 0, 0.55)";
  } else if (color === "manila") {
    paperBg = "#E8DFCE";
    paperText = "#292524";
    paperBorder = "1px solid rgba(168, 148, 120, 0.45)";
    shadowColor = "rgba(60, 45, 25, 0.28)";
  }

  // Precomputed rough deckle edge clip-path
  // Generates jagged, non-uniform torn paper contour
  const clipPathRough = `polygon(
    0% 2px, 3% 0px, 8% 3px, 14% 1px, 22% 4px, 30% 0px, 38% 3px, 46% 1px, 55% 4px, 63% 0px, 72% 3px, 81% 1px, 90% 4px, 97% 1px, 100% 3px,
    99% 10%, 100% 20%, 98% 32%, 100% 44%, 99% 56%, 100% 68%, 98% 80%, 100% 92%, 99% 100%,
    96% 99%, 88% 100%, 79% 98%, 70% 100%, 61% 98%, 52% 100%, 43% 97%, 34% 100%, 25% 98%, 16% 100%, 8% 97%, 0% 100%,
    2% 90%, 0% 78%, 3% 66%, 1% 52%, 2% 38%, 0% 24%, 2% 12%
  )`;

  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y,
        width,
        height,
        transform: `translate(-50%, -50%) translateY(${translateY.toFixed(1)}px) scale(${scale.toFixed(3)}) rotate(${rotation}deg)`,
        transformOrigin: "center center",
        opacity,
        zIndex: 20,
        pointerEvents: "none",
        ...style,
      }}
    >
      {/* Outer Paper Drop Shadow Container */}
      <div
        style={{
          width: "100%",
          height: "100%",
          position: "relative",
          filter: `drop-shadow(0 14px 28px ${shadowColor}) drop-shadow(0 3px 8px rgba(0, 0, 0, 0.12))`,
        }}
      >
        {/* Torn Paper Body with Jagged Deckle Edges */}
        <div
          style={{
            width: "100%",
            height: "100%",
            backgroundColor: paperBg,
            color: paperText,
            clipPath: roughness === "subtle" ? undefined : clipPathRough,
            borderRadius: roughness === "subtle" ? 4 : undefined,
            border: paperBorder,
            padding: "20px 24px",
            boxSizing: "border-box",
            overflow: "hidden",
            position: "relative",
          }}
        >
          {/* Subtle Paper Fiber Grain */}
          <div
            style={{
              position: "absolute",
              inset: 0,
              backgroundImage: "radial-gradient(rgba(0, 0, 0, 0.05) 1px, transparent 1px)",
              backgroundSize: "16px 16px",
              pointerEvents: "none",
            }}
          />

          {/* Children Content (Text, Records, Graphs) */}
          <div style={{ position: "relative", zIndex: 10, width: "100%", height: "100%" }}>
            {children}
          </div>
        </div>
      </div>

      {/* Optional Washi Tape Top-Left */}
      {hasTapeTopLeft ? (
        <VoxWashiTape
          x="12%"
          y="4%"
          rotation={-28}
          corner="top_left"
          dropFrame={dropFrame + 6}
        />
      ) : null}

      {/* Optional Washi Tape Top-Right */}
      {hasTapeTopRight ? (
        <VoxWashiTape
          x="88%"
          y="4%"
          rotation={26}
          corner="top_right"
          dropFrame={dropFrame + 8}
        />
      ) : null}

      {/* Optional Brass Pushpin Top-Right */}
      {hasPinTopRight ? (
        <VoxBrassPin
          x="92%"
          y="8%"
          size={26}
          dropFrame={dropFrame + 10}
        />
      ) : null}

      {/* Optional Brass Pushpin Center */}
      {hasPinCenter ? (
        <VoxBrassPin
          x="50%"
          y="12%"
          size={28}
          dropFrame={dropFrame + 12}
        />
      ) : null}
    </div>
  );
};
