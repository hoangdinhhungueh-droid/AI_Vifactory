import React from "react";
import { Audio, staticFile } from "remotion";
import { VoxPaperDossier } from "./VoxPaperDossier";
import { VoxEvidenceBoard } from "./VoxEvidenceBoard";
import { VoxBankCheck } from "./VoxBankCheck";
import { VoxTacticalMap } from "./VoxTacticalMap";
import { VoxKineticCounter } from "./VoxKineticCounter";
import { VoxCausalFlowchart } from "./VoxCausalFlowchart";
import { EvidenceProp3D } from "../EvidenceProp3D";

export interface VoxForensicOverlayData {
  type?: string;
  theme?: string;
  layout?: "full_bleed_focus" | "split_right" | "split_left" | "fullscreen_dossier" | "floating_card" | string;
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
  const sfxCue = ov.sfx_cue || (
    rawType.includes("doc") || rawType.includes("dossier") ? "marker_stroke" :
    rawType.includes("check") || rawType.includes("counter") ? "stamp_slam" :
    rawType.includes("board") ? "paper_slide" :
    rawType.includes("map") ? "sonar_ping" : undefined
  );

  const isFullBleed = layout === "full_bleed_focus" || layout === "fullscreen_dossier";

  // Determine component positioning based on layout
  let positionStyles: React.CSSProperties = {
    position: "absolute",
    zIndex: 28,
  };

  if (isFullBleed) {
    positionStyles = {
      ...positionStyles,
      top: "46%",
      left: "50%",
      transform: "translate(-50%, -50%)",
    };
  } else if (layout === "split_left") {
    positionStyles = {
      ...positionStyles,
      top: 60,
      left: 60,
    };
  } else if (layout === "split_right") {
    positionStyles = {
      ...positionStyles,
      top: 60,
      right: 60,
    };
  } else {
    // floating_card / default
    positionStyles = {
      ...positionStyles,
      top: 60,
      right: isLeft ? 60 : "auto",
      left: isLeft ? "auto" : 60,
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
      {/* Background Dimmer Backdrop when Full-Bleed Document is active (Zero blur per anti-dropframe standard) */}
      {isFullBleed ? (
        <div
          style={{
            position: "absolute",
            inset: 0,
            backgroundColor: "rgba(5, 9, 13, 0.78)",
            zIndex: 27,
            pointerEvents: "none",
          }}
        />
      ) : null}

      {/* Audio Micro-SFX cue */}
      {sfxCue && validSfx.includes(sfxCue) ? (
        <Audio
          src={staticFile(`sfx/${sfxCue}.mp3`)}
          volume={0.3}
        />
      ) : null}

      {/* Visual Component Render */}
      <div style={positionStyles}>
        {/* Paper Dossier / Official Document Highlight / Court Docket / Redacted Memo */}
        {rawType === "document_highlight" || rawType === "redacted_doc" || rawType === "paper_dossier" || rawType === "court_docket" || rawType === "redacted_memo" ? (
          <VoxPaperDossier
            title={ov.title}
            badge={ov.badge}
            theme={ov.theme || "vox_paper"}
            layout={layout}
            payload={ov.payload}
            label={ov.label}
          />
        ) : null}

        {/* Evidence Corkboard / Suspect Network / Corporate Org Chart */}
        {rawType === "evidence_board" || rawType === "suspect_network" || rawType === "corporate_org_chart" ? (
          <VoxEvidenceBoard
            title={ov.title}
            badge={ov.badge}
            theme={ov.theme || "vox_paper"}
            layout={layout}
            payload={ov.payload}
            label={ov.label}
          />
        ) : null}

        {/* Bank Check / Subsidy Disbursement Ledger */}
        {rawType === "bank_check" || rawType === "financial_ledger" ? (
          <VoxBankCheck
            title={ov.title}
            badge={ov.badge}
            theme={ov.theme || "vox_paper"}
            layout={layout}
            payload={ov.payload}
            label={ov.label}
          />
        ) : null}

        {/* Kinetic Counter Metric (Correctly wired to VoxKineticCounter) */}
        {rawType === "kinetic_counter" || rawType === "financial_chart" ? (
          <VoxKineticCounter
            title={ov.title}
            badge={ov.badge}
            theme={ov.theme || "tech_infographic"}
            layout={layout}
            payload={ov.payload}
            label={ov.label}
          />
        ) : null}

        {/* Tactical Paper Map */}
        {rawType === "tactical_map" || rawType === "radar_map" || rawType === "surveillance_crt" ? (
          <VoxTacticalMap
            title={ov.title}
            badge={ov.badge}
            theme={ov.theme || "vox_paper"}
            layout={layout}
            payload={ov.payload}
            label={ov.label}
          />
        ) : null}

        {/* Causal Flowchart / Money Trail Network */}
        {rawType === "causal_flowchart" || rawType === "money_trail_network" ? (
          <VoxCausalFlowchart
            title={ov.title}
            badge={ov.badge}
            theme={ov.theme || "vox_paper"}
            layout={layout}
            payload={ov.payload}
            label={ov.label}
          />
        ) : null}

        {/* 3D Procedural Evidence Prop (Vox Stop-Motion 12fps Evidence Specimen) */}
        {rawType.includes("3d") || rawType === "evidence_3d_prop" || rawType === "evidence_prop" ? (
          <div
            style={{
              width: isFullBleed ? 1160 : 700,
              height: isFullBleed ? 720 : 480,
              position: "relative",
            }}
          >
            <EvidenceProp3D
              title={ov.title || "CONFIDENTIAL EVIDENCE // EXHIBIT A"}
              subtitle={ov.label || ov.badge || "PROCEDURAL THREE.JS ARTIFACT"}
              theme={ov.theme || "noir_dossier"}
              layout={layout}
            />
          </div>
        ) : null}
      </div>
    </>
  );
};
