import React from "react";
import {
  Easing,
  Img,
  interpolate,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { SPRING_PRESETS } from "./springPresets";
import { useStopMotion } from "./useStopMotion";

export type InteractingPropType =
  | "rubber_stamp"
  | "brass_caliper"
  | "magnifying_glass"
  | "forensic_highlighter"
  | "scissors_cutter"
  | "brass_binder_clip"
  | "dossier_envelope"
  | string;

export interface DynamicInteractingPropProps {
  id?: string;
  propType?: InteractingPropType;
  src?: string;
  x?: number;
  y?: number;
  width?: number;
  height?: number;
  rotation?: number;
  startFrame?: number;
  contactFrameOffset?: number;
  impactDamping?: number;
  ingressDirection?: "left_to_right" | "right_to_left" | "top_to_bottom" | "drop";
  ingressDurationSec?: number;
  dualPassShadow?: boolean;
}

export const DynamicInteractingProp: React.FC<DynamicInteractingPropProps> = ({
  id = "interacting_prop",
  propType = "rubber_stamp",
  src,
  x = 1100,
  y = 480,
  width = 240,
  height = 240,
  rotation = 15,
  startFrame = 4,
  contactFrameOffset = 12,
  impactDamping = 0.75,
  ingressDirection = "top_to_bottom",
  ingressDurationSec = 0.3,
  dualPassShadow = true,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // 12fps tactile micro-jitter for stop-motion realism
  const { dx: jitterX, dy: jitterY } = useStopMotion(12, 0.6, 88);

  const localFrame = Math.max(0, frame - startFrame);

  // Snappy ingress spring
  const springConfig =
    ingressDirection === "drop"
      ? SPRING_PRESETS.opuscarStampSlam
      : SPRING_PRESETS.opuscarSnappy;

  const ingressProgress = spring({
    frame: localFrame,
    fps,
    config: springConfig,
  });

  // Calculate high-speed ingress offset
  let offsetX = 0;
  let offsetY = 0;
  const offscreenDist = 700;

  switch (ingressDirection) {
    case "left_to_right":
      offsetX = interpolate(ingressProgress, [0, 1], [-offscreenDist, 0]);
      break;
    case "right_to_left":
      offsetX = interpolate(ingressProgress, [0, 1], [offscreenDist, 0]);
      break;
    case "top_to_bottom":
      offsetY = interpolate(ingressProgress, [0, 1], [-offscreenDist, 0]);
      break;
    case "drop":
    default:
      offsetY = interpolate(ingressProgress, [0, 1], [-500, 0]);
      break;
  }

  // Micro-bounce impact at contact frame
  const contactFrame = startFrame + contactFrameOffset;
  let impactScale = 1.0;
  if (frame >= contactFrame && frame <= contactFrame + 8) {
    const bounceFrame = frame - contactFrame;
    impactScale = 1.0 + Math.sin((bounceFrame / 8) * Math.PI) * (0.08 * impactDamping);
  }

  // Dual-pass shadow
  const shadowStyle = dualPassShadow
    ? "drop-shadow(0 2px 3px rgba(15, 23, 42, 0.45)) drop-shadow(0 14px 22px rgba(15, 23, 42, 0.28))"
    : "drop-shadow(0 8px 16px rgba(0,0,0,0.25))";

  const resolvedSrc = src
    ? src.startsWith("http") || src.startsWith("/") || src.startsWith("data:")
      ? src
      : staticFile(src)
    : undefined;

  return (
    <div
      id={id}
      style={{
        position: "absolute",
        left: x + offsetX + jitterX,
        top: y + offsetY + jitterY,
        width,
        height,
        transform: `rotate(${rotation}deg) scale(${impactScale})`,
        filter: shadowStyle,
        zIndex: 40,
        pointerEvents: "none",
        transformOrigin: "center center",
      }}
    >
      {resolvedSrc ? (
        <Img
          src={resolvedSrc}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "contain",
            display: "block",
          }}
        />
      ) : (
        /* Bespoke SVG Stylized Prop Fallback */
        <div style={{ width: "100%", height: "100%", position: "relative" }}>
          {propType === "rubber_stamp" && (
            <svg viewBox="0 0 100 100" width="100%" height="100%">
              {/* Wooden handle */}
              <ellipse cx="50" cy="20" rx="14" ry="10" fill="#7D4E2D" stroke="#3A1E0D" strokeWidth="2" />
              <path d="M42 20 C42 42, 34 52, 28 65 L72 65 C66 52, 58 42, 58 20 Z" fill="#8E5B37" stroke="#3A1E0D" strokeWidth="2" />
              {/* Brass collar */}
              <rect x="26" y="65" width="48" height="6" rx="1" fill="#D9A441" stroke="#8C6517" strokeWidth="1.5" />
              {/* Rubber base */}
              <rect x="22" y="71" width="56" height="12" rx="2" fill="#D62E1F" stroke="#1A1A1A" strokeWidth="2" />
            </svg>
          )}

          {propType === "magnifying_glass" && (
            <svg viewBox="0 0 100 100" width="100%" height="100%">
              <circle cx="42" cy="42" r="30" fill="rgba(244, 241, 234, 0.2)" stroke="#D9A441" strokeWidth="6" />
              <circle cx="42" cy="42" r="26" fill="rgba(255, 255, 255, 0.4)" stroke="rgba(255,255,255,0.7)" strokeWidth="1.5" />
              <line x1="64" y1="64" x2="88" y2="88" stroke="#3A1E0D" strokeWidth="8" strokeLinecap="round" />
              <line x1="64" y1="64" x2="70" y2="70" stroke="#D9A441" strokeWidth="9" />
            </svg>
          )}

          {propType === "brass_caliper" && (
            <svg viewBox="0 0 100 100" width="100%" height="100%">
              <rect x="20" y="44" width="65" height="10" rx="1" fill="#D9A441" stroke="#8C6517" strokeWidth="1.5" />
              {/* Caliper vernier jaw */}
              <path d="M20 30 L20 68 L28 54 L28 30 Z" fill="#D9A441" stroke="#8C6517" strokeWidth="1.5" />
              <path d="M48 30 L48 68 L54 54 L54 30 Z" fill="#B88A2E" stroke="#8C6517" strokeWidth="1.5" />
            </svg>
          )}

          {propType === "forensic_highlighter" && (
            <svg viewBox="0 0 100 100" width="100%" height="100%">
              <rect x="25" y="40" width="50" height="20" rx="3" fill="#FFE600" stroke="#1A1A1A" strokeWidth="2" />
              <polygon points="75,44 86,47 86,53 75,56" fill="#1A1A1A" />
              <polygon points="86,47 94,49 94,51 86,53" fill="#FFE600" />
            </svg>
          )}

          {propType === "scissors_cutter" && (
            <svg viewBox="0 0 100 100" width="100%" height="100%">
              <line x1="20" y1="20" x2="75" y2="75" stroke="#8C8C8C" strokeWidth="4" strokeLinecap="round" />
              <line x1="20" y1="75" x2="75" y2="20" stroke="#8C8C8C" strokeWidth="4" strokeLinecap="round" />
              <circle cx="24" cy="24" r="8" fill="none" stroke="#1A1A1A" strokeWidth="3" />
              <circle cx="24" cy="71" r="8" fill="none" stroke="#1A1A1A" strokeWidth="3" />
              <circle cx="47" cy="47" r="3" fill="#D9A441" />
            </svg>
          )}

          {!["rubber_stamp", "magnifying_glass", "brass_caliper", "forensic_highlighter", "scissors_cutter"].includes(propType) && (
            <div
              style={{
                width: "100%",
                height: "100%",
                backgroundColor: "#1A1A1A",
                color: "#F4F1EA",
                borderRadius: 4,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                fontFamily: "'IBM Plex Mono', monospace",
                fontWeight: 700,
                fontSize: 12,
                border: "2px solid #D9A441",
              }}
            >
              {propType.toUpperCase()}
            </div>
          )}
        </div>
      )}
    </div>
  );
};
