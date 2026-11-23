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

export type ContactResidueType =
  | "red_ink_stain"
  | "yellow_glow"
  | "paper_tear"
  | "needle_hole"
  | "embossed_crease"
  | string;

export type HostAnchorArea =
  | "top_right_corner"
  | "left_margin"
  | "document_face"
  | "paragraph_body"
  | "bottom_seal_zone"
  | string;

export interface TactileHostCardProps {
  id?: string;
  src?: string;
  title?: string;
  subtitle?: string;
  width?: number;
  height?: number;
  x?: number;
  y?: number;
  rotation?: number;
  startFrame?: number;
  ingressDirection?: "left_to_right" | "right_to_left" | "top_to_bottom" | "bottom_to_top" | "drop";
  ingressDurationSec?: number;
  activeContactResidue?: ContactResidueType;
  residueTriggerFrame?: number;
  residueAnchorArea?: HostAnchorArea;
  children?: React.ReactNode;
}

/**
 * Calculates normalized coordinates within the host card for the designated anchor zone.
 */
function getAnchorZoneCoordinates(area?: HostAnchorArea): { xPct: number; yPct: number } {
  switch (area) {
    case "top_right_corner":
      return { xPct: 84, yPct: 16 };
    case "left_margin":
      return { xPct: 14, yPct: 48 };
    case "paragraph_body":
      return { xPct: 50, yPct: 45 };
    case "bottom_seal_zone":
      return { xPct: 78, yPct: 82 };
    case "document_face":
    default:
      return { xPct: 52, yPct: 50 };
  }
}

export const TactileHostCard: React.FC<TactileHostCardProps> = ({
  id = "host_card",
  src,
  title,
  subtitle,
  width = 800,
  height = 560,
  x = 560,
  y = 260,
  rotation = -1.2,
  startFrame = 0,
  ingressDirection = "right_to_left",
  ingressDurationSec = 0.3,
  activeContactResidue,
  residueTriggerFrame = 12,
  residueAnchorArea = "bottom_seal_zone",
  children,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Subtle 12fps paper tactile micro-jitter
  const { dx: jitterX, dy: jitterY } = useStopMotion(12, 0.5, 42);

  const localFrame = Math.max(0, frame - startFrame);
  const ingressFrames = Math.max(6, Math.min(12, Math.round(ingressDurationSec * fps)));

  // Snappy stop-motion ingress physics (mass: 0.35, stiffness: 290, damping: 15)
  const ingressProgress = spring({
    frame: localFrame,
    fps,
    config: SPRING_PRESETS.opuscarSnappy,
  });

  // Calculate entry offset based on direction
  let offsetX = 0;
  let offsetY = 0;
  const offscreenDist = 900;

  switch (ingressDirection) {
    case "left_to_right":
      offsetX = interpolate(ingressProgress, [0, 1], [-offscreenDist, 0]);
      break;
    case "top_to_bottom":
      offsetY = interpolate(ingressProgress, [0, 1], [-offscreenDist, 0]);
      break;
    case "bottom_to_top":
      offsetY = interpolate(ingressProgress, [0, 1], [offscreenDist, 0]);
      break;
    case "drop":
      offsetY = interpolate(ingressProgress, [0, 1], [-400, 0]);
      break;
    case "right_to_left":
    default:
      offsetX = interpolate(ingressProgress, [0, 1], [offscreenDist, 0]);
      break;
  }

  // Dual-Pass Contact Shadow formula (Rule 140 / Deep Research Dossier)
  const dualPassShadow =
    "drop-shadow(0 2px 3px rgba(15, 23, 42, 0.45)) drop-shadow(0 12px 20px rgba(15, 23, 42, 0.22))";

  // Contact residue animation
  const isResidueActive = activeContactResidue && frame >= residueTriggerFrame;
  const residueFrameOffset = Math.max(0, frame - residueTriggerFrame);
  const residueOpacity = isResidueActive
    ? interpolate(residueFrameOffset, [0, 4], [0, 1], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      })
    : 0;

  const anchorPos = getAnchorZoneCoordinates(residueAnchorArea);

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
        transform: `rotate(${rotation}deg)`,
        filter: dualPassShadow,
        zIndex: 20,
        pointerEvents: "none",
        transformOrigin: "center center",
      }}
    >
      {/* Real Card Body */}
      <div
        style={{
          position: "relative",
          width: "100%",
          height: "100%",
          backgroundColor: "#F4F1EA",
          borderRadius: 3,
          overflow: "hidden",
          border: "1px solid rgba(58, 53, 42, 0.25)",
          boxShadow: "inset 0 0 0 1px rgba(255, 255, 255, 0.6)",
        }}
      >
        {/* Archival Cream Paper Grain Background */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            opacity: 0.12,
            backgroundImage:
              "radial-gradient(circle at 50% 50%, rgba(26,26,26,0.3) 1px, transparent 1px)",
            backgroundSize: "8px 8px",
            pointerEvents: "none",
          }}
        />

        {/* Optional Host Image (Clean cutout or full document) */}
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
          <div
            style={{
              padding: "24px 32px",
              height: "100%",
              boxSizing: "border-box",
              display: "flex",
              flexDirection: "column",
              justifyContent: "space-between",
            }}
          >
            <div>
              <div
                style={{
                  fontFamily: "'IBM Plex Mono', monospace",
                  fontSize: 13,
                  fontWeight: 700,
                  letterSpacing: 2,
                  color: "#D62E1F",
                  textTransform: "uppercase",
                  marginBottom: 8,
                }}
              >
                {subtitle || "OFFICIAL REGULATORY EVIDENCE"}
              </div>
              <div
                style={{
                  fontFamily: "'Syne', 'Public Sans', sans-serif",
                  fontSize: 26,
                  fontWeight: 800,
                  color: "#1A1A1A",
                  lineHeight: 1.15,
                  maxWidth: "85%",
                }}
              >
                {title || "EXHIBIT AUDIT DOSSIER"}
              </div>
            </div>

            {/* Document Decorative Grid / Lines */}
            <div style={{ opacity: 0.35, marginTop: 16 }}>
              <div
                style={{
                  height: 3,
                  backgroundColor: "#1A1A1A",
                  marginBottom: 8,
                  width: "100%",
                }}
              />
              <div
                style={{
                  height: 1,
                  backgroundColor: "#1A1A1A",
                  marginBottom: 6,
                  width: "92%",
                }}
              />
              <div
                style={{
                  height: 1,
                  backgroundColor: "#1A1A1A",
                  marginBottom: 6,
                  width: "88%",
                }}
              />
              <div
                style={{
                  height: 1,
                  backgroundColor: "#1A1A1A",
                  width: "74%",
                }}
              />
            </div>
          </div>
        )}

        {/* Children components overlay */}
        {children}

        {/* Tactile Contact Residue Rendering */}
        {isResidueActive && (
          <div
            style={{
              position: "absolute",
              left: `${anchorPos.xPct}%`,
              top: `${anchorPos.yPct}%`,
              transform: "translate(-50%, -50%)",
              opacity: residueOpacity,
              pointerEvents: "none",
              zIndex: 35,
            }}
          >
            {activeContactResidue === "red_ink_stain" && (
              <div
                style={{
                  width: 140,
                  height: 140,
                  borderRadius: "50%",
                  border: "4px solid #D62E1F",
                  display: "flex",
                  alignItems: "center",
                  justifyContent: "center",
                  color: "#D62E1F",
                  fontFamily: "'IBM Plex Mono', monospace",
                  fontWeight: 900,
                  fontSize: 16,
                  letterSpacing: 2,
                  transform: "rotate(-14deg)",
                  boxShadow: "0 0 12px rgba(214, 46, 31, 0.4)",
                  backgroundColor: "rgba(214, 46, 31, 0.08)",
                }}
              >
                SEALED
              </div>
            )}

            {activeContactResidue === "yellow_glow" && (
              <div
                style={{
                  width: 260,
                  height: 28,
                  backgroundColor: "#FFE600",
                  opacity: 0.65,
                  mixBlendMode: "multiply",
                  borderRadius: 2,
                  boxShadow: "0 0 16px rgba(255, 230, 0, 0.7)",
                  transform: "rotate(-0.8deg)",
                }}
              />
            )}

            {activeContactResidue === "paper_tear" && (
              <div
                style={{
                  width: 180,
                  height: 4,
                  backgroundColor: "#1A1A1A",
                  opacity: 0.8,
                  boxShadow: "0 2px 4px rgba(0,0,0,0.5)",
                  transform: "rotate(24deg)",
                }}
              />
            )}

            {activeContactResidue === "needle_hole" && (
              <div
                style={{
                  width: 10,
                  height: 10,
                  borderRadius: "50%",
                  backgroundColor: "#1A1A1A",
                  boxShadow: "inset 0 1px 2px rgba(0,0,0,0.8), 0 0 0 2px rgba(217, 164, 65, 0.6)",
                }}
              />
            )}

            {activeContactResidue === "embossed_crease" && (
              <div
                style={{
                  width: 160,
                  height: 2,
                  backgroundColor: "rgba(0,0,0,0.22)",
                  boxShadow: "0 1px 0 rgba(255,255,255,0.7)",
                  transform: "rotate(45deg)",
                }}
              />
            )}
          </div>
        )}
      </div>
    </div>
  );
};
