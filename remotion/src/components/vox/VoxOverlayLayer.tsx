import React from "react";
import { Audio, staticFile } from "remotion";
import { VoxPaperDossier } from "./VoxPaperDossier";
import { VoxEvidenceBoard } from "./VoxEvidenceBoard";
import { VoxBankCheck } from "./VoxBankCheck";
import { VoxTacticalMap } from "./VoxTacticalMap";
import { VoxKineticCounter } from "./VoxKineticCounter";
import { VoxCausalFlowchart } from "./VoxCausalFlowchart";
import { VoxThresholdRatio } from "./VoxThresholdRatio";
import { VoxInteractiveMap } from "./VoxInteractiveMap";
import { CapitalFlowMap } from "./CapitalFlowMap";
import { VoxDynamicChart } from "./VoxDynamicChart";
import { VoxForensicPaper } from "./VoxForensicPaper";
import { VoxKineticHeadline } from "./VoxKineticHeadline";
import { VoxConnectedNetwork } from "./VoxConnectedNetwork";
import { VoxCompositeStage } from "./VoxCompositeStage";
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
  hasForeground?: boolean;
  statValue?: string;
  statLabel?: string;
  durationInFrames?: number;
}

export const VoxOverlayLayer: React.FC<VoxOverlayLayerProps> = ({
  forensicOverlay,
  isLeft,
  hasForeground,
  statValue,
  statLabel,
  durationInFrames,
}) => {
  if (!forensicOverlay) {
    return null;
  }

  // Normalize string to structured object
  const ov: VoxForensicOverlayData = typeof forensicOverlay === "string"
    ? { type: forensicOverlay, label: forensicOverlay }
    : forensicOverlay;

  const rawType = ov.type || "";
  const isCharacterPresent = Boolean(hasForeground);
  const isHeadline = rawType === "kinetic_headline" || rawType === "cold_hook_headline";

  const effectiveLayout =
    isCharacterPresent && !isHeadline
      ? isLeft
        ? "split_right"
        : "split_left"
      : ov.layout || (isLeft ? "split_right" : "split_left");

  const layout = effectiveLayout;
  const sfxCue = ov.sfx_cue || (
    rawType.includes("doc") || rawType.includes("dossier") ? "marker_stroke" :
    rawType.includes("check") || rawType.includes("counter") || rawType.includes("threshold") || rawType.includes("ratio") ? "stamp_slam" :
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
      top: "50%",
      left: "50%",
      transform: "translate(-50%, -50%)",
      width: "100%",
      height: "100%",
      display: "flex",
      justifyContent: "center",
      alignItems: "center",
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
      {/* Background Dimmer Backdrop with warm paper vignette (Rule 118: Zero digital void) */}
      {isFullBleed ? (
        <div
          style={{
            position: "absolute",
            inset: 0,
            background: "radial-gradient(ellipse at center, rgba(35, 25, 15, 0.52) 0%, rgba(20, 15, 10, 0.80) 100%)",
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
            title={ov.title || statLabel}
            badge={ov.badge || "EVIDENTIARY METRIC"}
            theme={ov.theme || "noir_dossier"}
            layout={layout}
            payload={{
              ...ov.payload,
              ...(ov.payload?.end_value === undefined && statValue ? { amount: statValue } : {}),
            }}
            label={ov.label || statValue}
          />
        ) : null}

        {/* Threshold Ratio Visualization (24x Staccato 6x4 Grid & Statutory Limit) */}
        {rawType === "threshold_ratio" || rawType === "grid_ratio" || rawType === "ratio_grid" ? (
          <VoxThresholdRatio
            title={ov.title}
            badge={ov.badge}
            theme={ov.theme || "crimson_alert"}
            layout={layout}
            payload={ov.payload}
            label={ov.label}
          />
        ) : null}

        {/* Tactical Paper Map & Interactive Maritime Corridor (Vox Engine 2.0) */}
        {rawType === "tactical_map" || rawType === "radar_map" || rawType === "interactive_map" || rawType === "maritime_route" || rawType === "surveillance_crt" ? (
          <VoxInteractiveMap
            title={ov.title}
            badge={ov.badge}
            theme={ov.theme || "tactical_navy"}
            layout={layout}
            payload={ov.payload}
            label={ov.label}
          />
        ) : null}

        {/* Global Capital Flow Vectors / Treasury Flow Map (Vox Engine 3.0) */}
        {rawType === "capital_flow_map" || rawType === "capital_vectors" || rawType === "global_flow" ? (
          <CapitalFlowMap
            title={ov.title}
            badge={ov.badge}
            flows={ov.payload?.flows}
            market={ov.payload?.market}
            layout={layout}
          />
        ) : null}

        {/* Causal Flowchart / Connected Vector Network */}
        {rawType === "causal_flowchart" || rawType === "money_trail_network" || rawType === "connected_network" || rawType === "causal_network" || rawType === "vox_network" ? (
          ov.payload?.nodes && ov.payload?.edges ? (
            <VoxConnectedNetwork
              title={ov.title}
              badge={ov.badge}
              layout={layout}
              nodes={ov.payload.nodes}
              edges={ov.payload.edges}
            />
          ) : (
            <VoxCausalFlowchart
              title={ov.title}
              badge={ov.badge}
              theme={ov.theme || "vox_paper"}
              layout={layout}
              payload={ov.payload}
              label={ov.label}
            />
          )
        ) : null}

        {/* Multi-Motion Composite Paper Collage Stage (Vox Multi-Motion Engine) */}
        {rawType === "composite_stage" || rawType === "paper_collage_assembly" || rawType === "vox_composite" ? (
          <VoxCompositeStage
            title={ov.title}
            badge={ov.badge}
            layout={layout}
            {...(ov.payload || {})}
          />
        ) : null}

        {/* Dynamic Vector Financial Chart / Candlestick Line Draw (Vox Engine 4.0) */}
        {rawType === "dynamic_chart" || rawType === "vector_chart" || rawType === "line_chart" || rawType === "bar_chart" ? (
          <VoxDynamicChart
            title={ov.title || statLabel}
            badge={ov.badge || "MARKET FORENSIC DATA"}
            chartType={ov.payload?.chart_type || (rawType === "bar_chart" ? "bar" : "line")}
            data={ov.payload?.data}
            startValue={ov.payload?.start_value}
            endValue={ov.payload?.end_value !== undefined ? ov.payload?.end_value : (statValue ? parseFloat(String(statValue).replace(/[^0-9.-]/g, "")) : undefined)}
            unit={ov.payload?.unit || "B"}
            prefix={ov.payload?.prefix || "$"}
            color={ov.payload?.color}
            trend={ov.payload?.trend}
            layout={layout}
          />
        ) : null}

        {/* Archival Forensic Paper with Yellow Highlighter Sweep & Stamp (Vox Engine 4.0) */}
        {rawType === "forensic_paper" || rawType === "highlighter_doc" || rawType === "archival_paper" ? (
          <VoxForensicPaper
            title={ov.title}
            documentNumber={ov.payload?.doc_number}
            date={ov.payload?.date}
            agency={ov.payload?.agency}
            bodyText={ov.payload?.body_text || ov.label}
            highlightedPhrase={ov.payload?.highlighted_phrase}
            stampText={ov.payload?.stamp_text || ov.badge || "RESTRICTED"}
            stampColor={ov.payload?.stamp_color}
            layout={layout}
          />
        ) : null}

        {/* Kinetic Headline Word-by-Word Impact Typography (Vox Engine 4.0) */}
        {rawType === "kinetic_headline" || rawType === "cold_hook_headline" || rawType === "impact_headline" ? (
          <div style={{ width: 1400, height: 600, position: "relative" }}>
            <VoxKineticHeadline
              headline={ov.title || ov.label}
              highlightWord={ov.payload?.highlight_word}
              category={ov.badge || "FORENSIC INVESTIGATION"}
              subtext={ov.payload?.subtext}
              accentColor={ov.payload?.accent_color}
            />
          </div>
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
