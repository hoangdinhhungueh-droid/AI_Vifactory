import React from "react";
import {
  Easing,
  interpolate,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { useStopMotion } from "./useStopMotion";

export interface OrganicRedYarnProps {
  id?: string;
  fromX: number;
  fromY: number;
  toX: number;
  toY: number;
  label?: string;
  color?: string;
  sagMultiplier?: number;
  startFrame?: number;
  drawDurationFrames?: number;
  showAnchorPins?: boolean;
  width?: number;
  height?: number;
}

export const OrganicRedYarn: React.FC<OrganicRedYarnProps> = ({
  id = "organic_red_yarn",
  fromX,
  fromY,
  toX,
  toY,
  label,
  color = "#D62E1F",
  sagMultiplier = 1.0,
  startFrame = 8,
  drawDurationFrames = 14,
  showAnchorPins = true,
  width,
  height,
}) => {
  const frame = useCurrentFrame();
  const { fps, width: viewW, height: viewH } = useVideoConfig();
  const canvasW = width ?? viewW;
  const canvasH = height ?? viewH;

  // Subtle stop-motion yarn vibration (12fps on twos)
  const { dx: jitterX, dy: jitterY } = useStopMotion(12, 0.5, 33);

  // Progressive drawing of the yarn
  const drawProgress = interpolate(
    frame,
    [startFrame, startFrame + drawDurationFrames],
    [0, 1],
    {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.bezier(0.16, 1, 0.3, 1),
    }
  );

  if (drawProgress < 0.01) {
    return null;
  }

  // Calculate Catenary curve natural gravitational sag
  const distance = Math.hypot(toX - fromX, toY - fromY);
  const baseSag = Math.min(85, distance * 0.14) * sagMultiplier;

  // Dampening vibration after draw completion
  const postDrawFrames = Math.max(0, frame - (startFrame + drawDurationFrames));
  const vibration =
    postDrawFrames < 16
      ? Math.sin((postDrawFrames / 4) * Math.PI) * (4 * Math.exp(-postDrawFrames / 5))
      : 0;

  const midX = (fromX + toX) / 2;
  const midY = (fromY + toY) / 2 + baseSag + vibration;

  // Interpolate current end point during draw
  const currentEndX = interpolate(drawProgress, [0, 1], [fromX, toX]);
  const currentEndY = interpolate(drawProgress, [0, 1], [fromY, toY]);
  const currentMidY = interpolate(drawProgress, [0, 1], [fromY, midY]);

  const pathD = `M ${fromX} ${fromY} Q ${midX} ${currentMidY} ${currentEndX} ${currentEndY}`;

  return (
    <div
      id={id}
      style={{
        position: "absolute",
        top: 0,
        left: 0,
        width: canvasW,
        height: canvasH,
        pointerEvents: "none",
        zIndex: 28,
      }}
    >
      <svg
        width={canvasW}
        height={canvasH}
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          overflow: "visible",
        }}
      >
        <defs>
          <filter id={`yarn-shadow-${id}`} x="-20%" y="-20%" width="140%" height="140%">
            <feDropShadow dx="0" dy="3" stdDeviation="3" floodColor="rgba(15, 23, 42, 0.45)" />
            <feDropShadow dx="0" dy="10" stdDeviation="10" floodColor="rgba(15, 23, 42, 0.22)" />
          </filter>
        </defs>

        {/* Ambient shadow yarn line */}
        <path
          d={pathD}
          fill="none"
          stroke="rgba(26, 26, 26, 0.35)"
          strokeWidth="5"
          strokeLinecap="round"
          transform="translate(0, 4)"
        />

        {/* Outer fibrous core */}
        <path
          d={pathD}
          fill="none"
          stroke="rgba(182, 46, 31, 0.75)"
          strokeWidth="3.5"
          strokeLinecap="round"
          filter={`url(#yarn-shadow-${id})`}
        />

        {/* Vivid center yarn filament */}
        <path
          d={pathD}
          fill="none"
          stroke={color}
          strokeWidth="2.2"
          strokeLinecap="round"
        />

        {/* Micro-fiber highlight thread */}
        <path
          d={pathD}
          fill="none"
          stroke="rgba(255, 255, 255, 0.35)"
          strokeWidth="1.0"
          strokeDasharray="4 6"
          strokeLinecap="round"
        />

        {/* Brass Anchor Pins */}
        {showAnchorPins && (
          <>
            {/* Start Anchor Pin */}
            <g transform={`translate(${fromX}, ${fromY})`}>
              <circle cx="0" cy="0" r="7" fill="#D9A441" stroke="#8C6517" strokeWidth="1.5" />
              <circle cx="-1.5" cy="-1.5" r="2.5" fill="rgba(255,255,255,0.7)" />
              <circle cx="0" cy="0" r="3" fill="#3A2807" />
            </g>

            {/* End Anchor Pin (appears when yarn reaches end) */}
            {drawProgress >= 0.95 && (
              <g transform={`translate(${toX}, ${toY})`}>
                <circle cx="0" cy="0" r="7" fill="#D9A441" stroke="#8C6517" strokeWidth="1.5" />
                <circle cx="-1.5" cy="-1.5" r="2.5" fill="rgba(255,255,255,0.7)" />
                <circle cx="0" cy="0" r="3" fill="#3A2807" />
              </g>
            )}
          </>
        )}
      </svg>

      {/* Floating forensic label tag attached at the catenary crest */}
      {label && drawProgress >= 0.8 && (
        <div
          style={{
            position: "absolute",
            left: midX + jitterX,
            top: midY + 12 + jitterY,
            transform: "translate(-50%, 0)",
            backgroundColor: "#F4F1EA",
            color: "#1A1A1A",
            border: "1px solid rgba(214, 46, 31, 0.5)",
            padding: "2px 8px",
            borderRadius: 2,
            fontFamily: "'IBM Plex Mono', monospace",
            fontSize: 11,
            fontWeight: 800,
            letterSpacing: 1,
            boxShadow: "0 2px 6px rgba(0,0,0,0.25)",
            whiteSpace: "nowrap",
          }}
        >
          {label}
        </div>
      )}
    </div>
  );
};
