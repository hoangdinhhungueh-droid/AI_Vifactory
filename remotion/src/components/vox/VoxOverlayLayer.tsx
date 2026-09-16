import React from "react";
import { Audio, staticFile } from "remotion";
import { VoxDocumentHighlight } from "./VoxDocumentHighlight";
import { VoxKineticCounter } from "./VoxKineticCounter";
import { VoxCausalFlowchart } from "./VoxCausalFlowchart";
import { VoxTacticalMap } from "./VoxTacticalMap";

export interface VoxForensicOverlayData {
  type?: string;
  theme?: string;
  layout?: "split_right" | "split_left" | "fullscreen_dossier" | "floating_card" | string;
  title?: string;
  badge?: string;
  sfx_cue?: string;
  label?: string;
  payload?: any;
}

export interface VoxOverlayLayerProps {
  forensicOverlay?: VoxForensicOverlayData | string | null;
  isLeft?: boolean;
}

export const VoxOverlayLayer: React.FC<VoxOverlayLayerProps> = ({
  forensicOverlay,
  isLeft,
}) => {
  if (!forensicOverlay) {
    return null;
  }

  // Normalize string to structured object
  const ov: VoxForensicOverlayData = typeof forensicOverlay === "string"
    ? { type: forensicOverlay, label: forensicOverlay }
    : forensicOverlay;

  const rawType = ov.type || "";
  const layout = ov.layout || (isLeft ? "split_right" : "split_left");
  const sfxCue = ov.sfx_cue;

  // Determine component positioning based on layout
  let positionStyles: React.CSSProperties = {
    position: "absolute",
    zIndex: 28,
  };

  if (layout === "fullscreen_dossier") {
    positionStyles = {
      ...positionStyles,
      top: 70,
      left: "50%",
      transform: "translateX(-50%)",
    };
  } else if (layout === "split_left") {
    positionStyles = {
      ...positionStyles,
      top: 60,
      left: 70,
    };
  } else if (layout === "split_right") {
    positionStyles = {
      ...positionStyles,
      top: 60,
      right: 70,
    };
  } else {
    // floating_card / default
    positionStyles = {
      ...positionStyles,
      top: 60,
      right: isLeft ? 70 : "auto",
      left: isLeft ? "auto" : 70,
    };
  }

  // Valid SFX cues matching public/sfx/*.mp3
  const validSfx = [
    "marker_stroke",
    "stamp_slam",
    "paper_slide",
    "counter_tick",
    "sonar_ping",
    "node_pop",
  ];

  return (
    <>
      {/* Audio Micro-SFX cue */}
      {sfxCue && validSfx.includes(sfxCue) ? (
        <Audio
          src={staticFile(`sfx/${sfxCue}.mp3`)}
          volume={0.25}
        />
      ) : null}

      {/* Visual Component */}
      <div style={positionStyles}>
        {rawType === "document_highlight" || rawType === "redacted_doc" ? (
          <VoxDocumentHighlight
            title={ov.title}
            badge={ov.badge}
            theme={ov.theme}
            layout={ov.layout}
            payload={ov.payload}
            label={ov.label}
          />
        ) : null}

        {rawType === "kinetic_counter" || rawType === "financial_chart" ? (
          <VoxKineticCounter
            title={ov.title}
            badge={ov.badge}
            theme={ov.theme}
            layout={ov.layout}
            payload={ov.payload}
            label={ov.label}
          />
        ) : null}

        {rawType === "causal_flowchart" ? (
          <VoxCausalFlowchart
            title={ov.title}
            badge={ov.badge}
            theme={ov.theme}
            layout={ov.layout}
            payload={ov.payload}
            label={ov.label}
          />
        ) : null}

        {rawType === "tactical_map" || rawType === "radar_map" || rawType === "surveillance_crt" ? (
          <VoxTacticalMap
            title={ov.title}
            badge={ov.badge}
            theme={ov.theme}
            layout={ov.layout}
            payload={ov.payload}
            label={ov.label}
          />
        ) : null}
      </div>
    </>
  );
};