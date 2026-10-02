import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { VoxBrassPin } from "./VoxBrassPin";
import { VoxWashiTape } from "./VoxWashiTape";

export interface VoxStampedLabelProps {
  text: string;
  subtext?: string;
  x?: number | string;
  y?: number | string;
  rotation?: number;
  dropFrame?: number;
  theme?: "ivory_typewriter" | "crimson_dymo" | "black_embossed" | "manila_stamp";
  hasPin?: boolean;
  hasTape?: boolean;
  fontSize?: number;
  style?: React.CSSProperties;
}

export const VoxStampedLabel: React.FC<VoxStampedLabelProps> = ({
  text,
  subtext,
  x = "50%",
  y = "85%",
  rotation = -1,
  dropFrame = 0,
  theme = "ivory_typewriter",
  hasPin = false,
  hasTape = false,
  fontSize = 24,
  style,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const relFrame = Math.max(0, frame - dropFrame);
  const labelSpring = spring({
    frame: relFrame,
    fps,
    config: { damping: 12, mass: 0.5, stiffness: 160 },
  });

  const scale = dropFrame > 0 ? interpolate(labelSpring, [0, 1], [0.85, 1.0]) : 1.0;
  const opacity = dropFrame > 0 ? interpolate(labelSpring, [0, 0.25, 1], [0, 0.9, 1.0]) : 1.0;

  // Theme styling
  let bg = "#FAF7EE";
  let textColor = "#0F172A";
  let borderColor = "rgba(100, 80, 50, 0.4)";
  let fontFamily = "'Courier Prime', 'Special Elite', 'Courier New', Courier, monospace";
  let letterSpacing = 3;

  if (theme === "crimson_dymo") {
    bg = "#DC2626";
    textColor = "#FFFFFF";
    borderColor = "#991B1B";
    fontFamily = "'Impact', 'Arial Black', sans-serif";
    letterSpacing = 2;
  } else if (theme === "black_embossed") {
    bg = "#0F172A";
    textColor = "#F8FAFC";
    borderColor = "#334155";
    fontFamily = "'Impact', 'Arial Black', sans-serif";
    letterSpacing = 2;
  } else if (theme === "manila_stamp") {
    bg = "#E3DAC9";
    textColor = "#451A03";
    borderColor = "#92400E";
    fontFamily = "'Courier Prime', 'Courier New', monospace";
    letterSpacing = 2.5;
  }

  return (
    <div
      style={{
        position: "absolute",
        left: x,
        top: y,
        transform: `translate(-50%, -50%) scale(${scale}) rotate(${rotation}deg)`,
        opacity,
        zIndex: 32,
        pointerEvents: "none",
        ...style,
      }}
    >
      <div
        style={{
          backgroundColor: bg,
          color: textColor,
          border: `1.5px solid ${borderColor}`,
          padding: "8px 22px",
          borderRadius: 3,
          boxShadow: "0 8px 20px rgba(0, 0, 0, 0.22), 0 2px 5px rgba(0, 0, 0, 0.12)",
          display: "flex",
          flexDirection: "column",
          alignItems: "center",
          justifyContent: "center",
          position: "relative",
        }}
      >
        <div
          style={{
            fontSize,
            fontWeight: 900,
            letterSpacing,
            textTransform: "uppercase",
            fontFamily,
            lineHeight: 1.15,
          }}
        >
          {text}
        </div>
        {subtext ? (
          <div
            style={{
              fontSize: Math.round(fontSize * 0.45),
              fontWeight: 700,
              letterSpacing: 1.5,
              opacity: 0.8,
              marginTop: 3,
              textTransform: "uppercase",
              fontFamily: "'Segoe UI', Roboto, sans-serif",
            }}
          >
            {subtext}
          </div>
        ) : null}

        {/* Optional Pin on Left/Center */}
        {hasPin ? (
          <VoxBrassPin
            x={14}
            y="50%"
            size={22}
            dropFrame={dropFrame + 6}
          />
        ) : null}

        {/* Optional Washi Tape across Top Edge */}
        {hasTape ? (
          <VoxWashiTape
            x="50%"
            y={-6}
            width={70}
            height={20}
            rotation={-2}
            dropFrame={dropFrame + 4}
          />
        ) : null}
      </div>
    </div>
  );
};
