import React from "react";
import {
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
  Easing,
  Img,
  Video,
} from "remotion";
import { SPRING_PRESETS } from "./springPresets";
import { useStopMotion } from "./useStopMotion";
import {
  VoxBrassPin,
  VoxWashiTape,
  VoxConnectingYarn,
} from "./papercraft";
import { VoxParallaxLayer } from "./VoxParallaxLayer";
import { VoxDynamicChart, VoxDynamicChartProps } from "./VoxDynamicChart";
import { ProceduralMarkerSweep } from "../kinetics/ProceduralMarkerSweep";

export interface VoxBuildOnCutout {
  id: string;
  src?: string;
  label?: string;
  role?: string;
  xPct: number; // percentage of stage width (0 - 100)
  yPct: number; // percentage of stage height (0 - 100)
  widthPct?: number; // width in % of stage (delicate 14-18%)
  rotation?: number; // tilt degrees (-15 to 15)
  delaySec?: number; // entry delay in seconds (default ~ 3.5s)
  hasPin?: boolean;
  hasTape?: boolean;
  entranceType?: "slide_in_deal" | "delicate_tack" | "stamp_slam" | "drop";
  hasMarkerHighlight?: boolean;
  highlightText?: string;
}

export interface VoxBuildOnYarn {
  fromX: number; // %
  fromY: number; // %
  toX: number;   // %
  toY: number;   // %
  color?: string; // default crimson #dc2626
  delaySec?: number; // default ~ 5.0s
}

export interface VoxBuildOnStageProps {
  /** Scene Headline / Beat Title */
  headline?: string;
  subtitle?: string;

  /** Visual Theme Preset (from 9 Canonical Themes) */
  theme?:
    | "swiss-modern"
    | "punk-zine"
    | "soviet-constructivist"
    | "wpa-propaganda"
    | "american-retro"
    | "chinese-ink"
    | "atomic-age"
    | "70s-groovy"
    | "newsprint-editorial"
    | string;

  /** Layer 1 Environmental Background Image */
  backgroundSrc?: string;

  /** Primary Hero Subject Cutout */
  heroSrc?: string;
  heroLabel?: string;
  heroPosition?: { xPct: number; yPct: number; widthPct?: number };

  /** Supporting Cutouts (Documents, Polaroids, Evidence) */
  supportingCutouts?: VoxBuildOnCutout[];

  /** Red Yarn / Tactical Connecting Lines */
  yarns?: VoxBuildOnYarn[];

  /** Official Rubber Stamp */
  stampText?: string;
  stampColor?: string;

  /** Highlight Marker Underline */
  hasMarkerHighlight?: boolean;

  /** Duration of total clip in seconds (default 10s) */
  durationSec?: number;

  /** Visual Pacing Layout Mode to prevent repetitive slideshow fatigue */
  layoutVariant?:
    | "paper_collage"
    | "cinematic_doc"
    | "kinetic_headline"
    | "evidence_dossier"
    | string;

  /** Scene sequence index for deterministic camera direction variation */
  sceneIndex?: number;

  /** Explicit camera directive from Director Plan */
  cameraMovement?: string;

  /** Procedural SVG Data Chart (Vox Dynamic Engine) */
  chartProps?: VoxDynamicChartProps;
}

/**
 * VoxBuildOnStage: Adaptive Multi-Mode Vox Visual & Tactile Engine.
 *
 * Supports 4 distinct editorial visual modes to match authentic Vox documentary pacing:
 * 1. "paper_collage" (15-20%): Tactile paper build-on assembly with brass pins, washi tape, and authentic documentary pacing.
 * 2. "cinematic_doc" (40%): Smooth Ken Burns pan/zoom full-bleed documentary staging without repetitive slide-in or head-pins.
 * 3. "kinetic_headline" (20%): High-impact editorial typography focus with marker sweep.
 * 4. "evidence_dossier" (20%): Forensic document & quantitative data staging synchronized with overlay layers.
 */
export const VoxBuildOnStage: React.FC<VoxBuildOnStageProps> = ({
  headline,
  subtitle,
  theme = "newsprint-editorial",
  backgroundSrc,
  heroSrc,
  heroLabel,
  heroPosition = { xPct: 50, yPct: 52, widthPct: 22 },
  supportingCutouts = [],
  yarns = [],
  stampText,
  stampColor = "#dc2626",
  hasMarkerHighlight = true,
  durationSec = 10,
  layoutVariant,
  sceneIndex = 0,
  cameraMovement,
  chartProps,
}) => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Resolve effective visual mode: reserve full tactile paper_collage for key beats or multi-cutout scenes
  const resolvedVariant =
    layoutVariant ||
    (supportingCutouts.length > 0 || yarns.length > 0 || Boolean(stampText)
      ? "paper_collage"
      : sceneIndex % 6 === 0
      ? "paper_collage"
      : sceneIndex % 5 === 2
      ? "kinetic_headline"
      : sceneIndex % 4 === 1
      ? "evidence_dossier"
      : "cinematic_doc");

  const isTactileCollage = resolvedVariant === "paper_collage";
  const isKineticHeadline = resolvedVariant === "kinetic_headline";
  const isEvidenceDossier = resolvedVariant === "evidence_dossier";
  const isCinematicDoc = resolvedVariant === "cinematic_doc";

  // Zero Jitter Mandate: Smooth cinematic stability without cheap 12fps screen shaking
  const jitterX = 0;
  const jitterY = 0;
  const jitterRot = 0;

  // Phase Timers in Frames (Adaptive to Beat Duration)
  const dSec = Math.max(1, durationSec || 10);
  const fTotal = Math.max(1, Math.round(fps * dSec));
  const speedRatio = dSec < 7.0 ? Math.max(0.2, dSec / 7.0) : 1.0;

  const fMid = Math.max(1, Math.round(fTotal * 0.65));
  const fEnd = Math.max(fMid + 1, fTotal);

  // Diverse Camera Choreography (Ken Burns push, pull, lateral drift)
  const camDir = sceneIndex % 4;
  const isPullOut =
    cameraMovement === "pull_out" || (!cameraMovement && camDir === 1 && !isTactileCollage);
  const cameraScale = interpolate(
    frame,
    [0, fMid, fEnd],
    isPullOut ? [1.065, 1.03, 1.0] : isTactileCollage ? [1.0, 1.015, 1.035] : [1.0, 1.03, 1.06],
    { extrapolateRight: "clamp" }
  );
  const cameraPanX = isTactileCollage
    ? 0
    : interpolate(
        frame,
        [0, fEnd],
        camDir === 2 ? [-14, 14] : camDir === 3 ? [14, -14] : [0, 0],
        { extrapolateRight: "clamp" }
      );

  // 1. BASE BACKDROP ENTRANCE
  const backdropSpring = spring({
    frame,
    fps,
    config: SPRING_PRESETS.paperSlide,
  });
  const backdropScale = isTactileCollage
    ? interpolate(backdropSpring, [0, 1], [0.96, 1.0])
    : 1.0;
  const backdropOpacity = isTactileCollage
    ? interpolate(backdropSpring, [0, 1], [0.2, 1])
    : interpolate(frame, [0, Math.min(10, fTotal)], [0.85, 1], { extrapolateRight: "clamp" });

  // 2. HERO SUBJECT CHOREOGRAPHY (Tactile slide only in paper_collage; grounded rise/fade in cinematic_doc)
  const heroDelayFrames = isTactileCollage ? Math.round(fps * 0.6 * speedRatio) : 0;
  const steppedHeroFrame = isTactileCollage ? Math.floor(frame / 2) * 2 : frame;
  const heroSpring = spring({
    frame: Math.max(0, steppedHeroFrame - heroDelayFrames),
    fps,
    config: isTactileCollage ? SPRING_PRESETS.paperSlide : SPRING_PRESETS.paperHeavy,
  });
  const heroTargetX = heroPosition.xPct;
  const isRight = heroTargetX > 50;
  const heroStartX = isTactileCollage
    ? isRight
      ? heroTargetX + 10
      : heroTargetX - 10
    : isRight
    ? heroTargetX + 2.5
    : heroTargetX - 2.5;
  const heroCurrentX = interpolate(heroSpring, [0, 1], [heroStartX, heroTargetX]);
  const heroRotation = isTactileCollage
    ? interpolate(heroSpring, [0, 0.8, 1], [isRight ? 2.5 : -2.5, isRight ? -0.8 : 0.8, 0])
    : 0;
  const heroDropShadow = interpolate(heroSpring, [0, 1], [4, 18]);
  const heroOpacity = interpolate(heroSpring, [0, 0.35, 1], [0, 1, 1]);

  // 3. EDITORIAL HEADLINE STAMP (2.5s - 4.0s)
  const headlineDelayFrames = Math.round(fps * 2.2 * speedRatio);
  const headlineSpring = spring({
    frame: Math.max(0, frame - headlineDelayFrames),
    fps,
    config: SPRING_PRESETS.stamp,
  });

  // 4. RUBBER STAMP SLAM (5.0s - 6.5s)
  const stampDelayFrames = Math.round(fps * 4.8 * speedRatio);
  const stampSpring = spring({
    frame: Math.max(0, frame - stampDelayFrames),
    fps,
    config: SPRING_PRESETS.stamp,
  });
  const stampScale = interpolate(stampSpring, [0, 1], [2.2, 1.0]);
  const stampOpacity = interpolate(stampSpring, [0, 0.2, 1], [0, 0.95, 0.9]);

  // Theme Styling Map
  const getThemeBackground = () => {
    switch (theme) {
      case "swiss-modern":
        return "#f8fafc";
      case "punk-zine":
        return "#18181b";
      case "soviet-constructivist":
        return "#fef3c7";
      case "wpa-propaganda":
        return "#f5efe6";
      case "chinese-ink":
        return "#fbf7ed";
      case "atomic-age":
        return "#ecfdf5";
      case "70s-groovy":
        return "#fef9c3";
      case "newsprint-editorial":
      default:
        return "#f4ece1"; // vintage warm archival paper
    }
  };

  return (
    <div
      style={{
        width: "100%",
        height: "100%",
        backgroundColor: getThemeBackground(), // Match theme background, zero dark studio border
        overflow: "hidden",
        position: "relative",
        display: "flex",
        alignItems: "center",
        justifyContent: "center",
      }}
    >
      {/* MASTER LIVING CAMERA RIG */}
      <div
        style={{
          width: "100%",
          height: "100%",
          perspective: 1400,
          transformStyle: "preserve-3d",
          transform: `scale(${cameraScale}) translate(${cameraPanX}px, 0px)`,
          transformOrigin: "center center",
          position: "relative",
        }}
      >
        {/* LAYER 0: BASE PAPER BACKDROP (PARALLAX BACKGROUND) */}
        <VoxParallaxLayer depth="background" cameraMovement={cameraMovement} durationInFrames={fTotal}>
          <div
            style={{
              position: "absolute",
              inset: 0,
              backgroundColor: getThemeBackground(),
              borderRadius: 0,
              boxShadow: "none",
              transform: `scale(${backdropScale})`,
              opacity: backdropOpacity,
              overflow: "hidden",
            }}
          >
            {backgroundSrc && (
              Boolean(/\.(mp4|webm)($|\?)/i.test(backgroundSrc)) ? (
                <Video
                  src={backgroundSrc}
                  style={{
                    position: "absolute",
                    inset: 0,
                    width: "100%",
                    height: "100%",
                    objectFit: "cover",
                    filter: "contrast(1.05) brightness(0.96)",
                  }}
                  muted
                  loop
                />
              ) : (
                <Img
                  src={backgroundSrc}
                  style={{
                    position: "absolute",
                    inset: 0,
                    width: "100%",
                    height: "100%",
                    objectFit: "cover",
                    filter: isTactileCollage
                      ? "contrast(0.9) brightness(1.08) grayscale(0.55)"
                      : "contrast(1.05) brightness(0.96)",
                    opacity: isTactileCollage ? 0.28 : 1.0,
                  }}
                />
              )
            )}

            {/* Paper Texture Overlay */}
            <div
              style={{
                position: "absolute",
                inset: 0,
                backgroundImage:
                  "radial-gradient(circle at 50% 50%, rgba(0,0,0,0.02) 1px, transparent 1px)",
                backgroundSize: "24px 24px",
                opacity: 0.65,
                pointerEvents: "none",
              }}
            />
          </div>
        </VoxParallaxLayer>

        {/* MIDGROUND LAYER 1: EDITORIAL HEADLINES & EVIDENCE DOSSIER */}
        <VoxParallaxLayer depth="midground" cameraMovement={cameraMovement} durationInFrames={fTotal}>
          {/* Archival Dossier Watermark (Rule 128 Generic Contract — only when subtitle is provided without headline) */}
          {subtitle && !headline && (
            <div
              style={{
                position: "absolute",
                top: "24px",
                left: "28px",
                fontFamily: "monospace",
                fontSize: "12px",
                fontWeight: 700,
                color: "rgba(0,0,0,0.25)",
                letterSpacing: "0.15em",
                textTransform: "uppercase",
              }}
            >
              {subtitle}
            </div>
          )}

          {/* EDITORIAL HEADLINE (Standard Top-Left for paper_collage & cinematic_doc) */}
          {headline && !isKineticHeadline && !isEvidenceDossier && (
            <div
              style={{
                position: "absolute",
                top: "7%",
                left: "6%",
                right: "6%",
                zIndex: 10,
                opacity: interpolate(headlineSpring, [0, 1], [0, 1]),
                transform: `translateY(${interpolate(headlineSpring, [0, 1], [-20, 0])}px)`,
                pointerEvents: "none",
              }}
            >
              {subtitle && (
                <div
                  style={{
                    fontSize: "13px",
                    fontWeight: 800,
                    color: "#dc2626",
                    letterSpacing: "0.2em",
                    marginBottom: "4px",
                    textTransform: "uppercase",
                    fontFamily: "monospace",
                  }}
                >
                  {subtitle}
                </div>
              )}
              <h1
                style={{
                  fontSize: headline.length > 36 ? "28px" : "38px",
                  fontWeight: 900,
                  color: isCinematicDoc ? "#fafaf9" : "#18181b",
                  backgroundColor: isCinematicDoc ? "rgba(15, 23, 42, 0.78)" : "transparent",
                  padding: isCinematicDoc ? "8px 16px" : "0",
                  borderRadius: isCinematicDoc ? "4px" : "0",
                  display: isCinematicDoc ? "inline-block" : "block",
                  lineHeight: 1.1,
                  letterSpacing: "-0.02em",
                  textTransform: "uppercase",
                  fontFamily: "Impact, Inter, sans-serif",
                  margin: 0,
                  maxWidth: "85%",
                  textShadow: isCinematicDoc
                    ? "0 2px 10px rgba(0,0,0,0.65)"
                    : "1px 1px 0 rgba(255,255,255,0.85)",
                }}
              >
                {headline}
              </h1>

              {/* Marker Underline Highlight */}
              {hasMarkerHighlight && (
                <div
                  style={{
                    height: "8px",
                    maxWidth: "420px",
                    backgroundColor: "#facc15",
                    marginTop: "6px",
                    borderRadius: "2px",
                    transformOrigin: "left center",
                    transform: `scaleX(${interpolate(
                      frame,
                      [headlineDelayFrames + 10, headlineDelayFrames + 25],
                      [0, 1],
                      { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                    )})`,
                    opacity: 0.85,
                    mixBlendMode: isCinematicDoc ? "normal" : "multiply",
                  }}
                />
              )}
            </div>
          )}

          {/* MODE 3: KINETIC HEADLINE STAGE (Sleek Cinematic Full-Screen Impact Typography) */}
          {isKineticHeadline && headline && (
            <div
              style={{
                position: "absolute",
                inset: 0,
                display: "flex",
                alignItems: "center",
                justifyContent: "center",
                zIndex: 28,
                pointerEvents: "none",
              }}
            >
              <div
                style={{
                  backgroundColor: "rgba(10, 15, 24, 0.78)",
                  backdropFilter: "blur(14px)",
                  borderLeft: "6px solid #dc2626",
                  borderRight: "6px solid #dc2626",
                  padding: "24px 44px",
                  maxWidth: "85%",
                  boxShadow: "0 20px 50px rgba(0,0,0,0.8)",
                  borderRadius: "8px",
                  transform: `scale(${interpolate(headlineSpring, [0, 1], [0.94, 1])})`,
                  opacity: interpolate(headlineSpring, [0, 1], [0, 1]),
                  textAlign: "center",
                }}
              >
                {subtitle && (
                  <div
                    style={{
                      fontSize: "14px",
                      fontWeight: 800,
                      color: "#f87171",
                      letterSpacing: "0.24em",
                      marginBottom: "8px",
                      textTransform: "uppercase",
                      fontFamily: "monospace",
                    }}
                  >
                    {subtitle}
                  </div>
                )}
                <h1
                  style={{
                    fontSize: headline.length <= 8 ? "86px" : headline.length > 36 ? "46px" : "60px",
                    fontWeight: 900,
                    color: "#f8fafc",
                    lineHeight: 1.04,
                    letterSpacing: headline.length <= 8 ? "0.04em" : "-0.02em",
                    textTransform: "uppercase",
                    fontFamily: "Impact, 'Zen Kaku Gothic New', Inter, sans-serif",
                    margin: 0,
                    textShadow: "0 0 30px rgba(220, 38, 38, 0.5), 0 4px 16px rgba(0,0,0,0.9)",
                  }}
                >
                  {headline}
                </h1>
                <div
                  style={{
                    height: "6px",
                    width: "50%",
                    margin: "12px auto 0 auto",
                    backgroundColor: "#ef4444",
                    borderRadius: "3px",
                    transformOrigin: "center center",
                    transform: `scaleX(${interpolate(
                      frame,
                      [headlineDelayFrames + 8, headlineDelayFrames + 24],
                      [0, 1],
                      { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
                    )})`,
                  }}
                />
              </div>
            </div>
          )}

          {/* MODE 4: EVIDENCE DOSSIER SPLIT-CARD STAGE (Sleek Dark Glassmorphism Evidence Badge) */}
          {isEvidenceDossier && (headline || heroLabel) && (
            <div
              style={{
                position: "absolute",
                top: "12%",
                left: heroSrc ? "6%" : "22%",
                width: heroSrc ? "42%" : "56%",
                backgroundColor: "rgba(10, 15, 24, 0.88)",
                backdropFilter: "blur(14px)",
                borderLeft: "5px solid #dc2626",
                border: "1px solid rgba(255, 255, 255, 0.12)",
                borderRadius: "8px",
                padding: "20px 24px",
                boxShadow: "0 18px 40px rgba(0,0,0,0.75)",
                zIndex: 28,
                opacity: interpolate(headlineSpring, [0, 1], [0, 1]),
                transform: `translateX(${interpolate(headlineSpring, [0, 1], [-28, 0])}px)`,
                pointerEvents: "none",
              }}
            >
              <div
                style={{
                  fontSize: "12px",
                  fontWeight: 800,
                  color: "#ef4444",
                  letterSpacing: "0.2em",
                  marginBottom: "8px",
                  textTransform: "uppercase",
                  fontFamily: "monospace",
                }}
              >
                {subtitle || "FORENSIC EVIDENCE DOSSIER"}
              </div>
              {headline && (
                <div
                  style={{
                    fontSize: "28px",
                    fontWeight: 900,
                    color: "#f8fafc",
                    lineHeight: 1.12,
                    textTransform: "uppercase",
                    fontFamily: "Impact, Inter, sans-serif",
                    marginBottom: "12px",
                  }}
                >
                  {headline}
                </div>
              )}
              {heroLabel && (
                <div
                  style={{
                    fontSize: "13px",
                    fontWeight: 700,
                    color: "#94a3b8",
                    fontFamily: "monospace",
                    borderTop: "1px dashed rgba(255, 255, 255, 0.2)",
                    paddingTop: "10px",
                  }}
                >
                  EXHIBIT // {heroLabel}
                </div>
              )}
              {stampText && (
                <div
                  style={{
                    display: "inline-block",
                    marginTop: "14px",
                    border: `2.5px solid ${stampColor}`,
                    padding: "4px 10px",
                    color: stampColor,
                    fontWeight: 900,
                    fontSize: "12px",
                    fontFamily: "monospace",
                    letterSpacing: "0.14em",
                    textTransform: "uppercase",
                  }}
                >
                  {stampText}
                </div>
              )}
            </div>
          )}
        </VoxParallaxLayer>

        {/* LAYER 1: HERO CUTOUT SUBJECT (PARALLAX FOREGROUND) */}
        {heroSrc && (isTactileCollage || isEvidenceDossier || isCinematicDoc || !backgroundSrc) && (
          <VoxParallaxLayer depth="foreground" cameraMovement={cameraMovement} durationInFrames={fTotal}>
            <div
              style={{
                position: "absolute",
                left: `${isEvidenceDossier ? Math.max(heroCurrentX, 68) : heroCurrentX}%`,
                top: `${heroPosition.yPct}%`,
                width: `${heroPosition.widthPct || 22}%`,
                transform: `translate(-50%, -50%) rotate(${heroRotation}deg)`,
                filter: `drop-shadow(0 ${heroDropShadow}px 24px rgba(0,0,0,0.35))`,
                opacity: heroOpacity,
                zIndex: 30,
              }}
            >
              <div style={{ position: "relative" }}>
                {Boolean(/\.(mp4|webm)($|\?)/i.test(heroSrc)) ? (
                  <Video
                    src={heroSrc}
                    style={{
                      width: "100%",
                      height: "auto",
                      display: "block",
                      filter: "contrast(1.08)",
                    }}
                    muted
                    loop
                  />
                ) : (
                  <Img
                    src={heroSrc}
                    style={{
                      width: "100%",
                      height: "auto",
                      display: "block",
                      filter: "contrast(1.08)",
                    }}
                  />
                )}

                {/* Tactile 3D Brass Pushpin anchoring Hero Cutout in paper_collage mode */}
                {isTactileCollage && (
                  <div
                    style={{
                      position: "absolute",
                      top: "-12px",
                      left: "50%",
                      transform: "translateX(-50%)",
                      zIndex: 35,
                    }}
                  >
                    <VoxBrassPin size={28} dropFrame={heroDelayFrames + 4} />
                  </div>
                )}
              </div>
            </div>
          </VoxParallaxLayer>
        )}

        {/* LAYER 1.5: PROCEDURAL SVG DYNAMIC CHART (Vox Dynamic Data Engine) */}
        {chartProps && (
          <VoxParallaxLayer depth="foreground" cameraMovement={cameraMovement} durationInFrames={fTotal}>
            <div
              style={{
                position: "absolute",
                top: "50%",
                left: "50%",
                transform: "translate(-50%, -50%)",
                zIndex: 32,
              }}
            >
              <VoxDynamicChart {...chartProps} />
            </div>
          </VoxParallaxLayer>
        )}

        {/* LAYER 2: SUPPORTING CUTOUTS & EVIDENCE (PARALLAX MIDGROUND) */}
        <VoxParallaxLayer depth="midground" cameraMovement={cameraMovement} durationInFrames={fTotal}>
          {(isTactileCollage || supportingCutouts.length > 0) && supportingCutouts.map((cutout, idx) => {
            const defaultCutSec = Math.min(dSec * 0.45, 0.4 + idx * 0.3) * (dSec < 7.0 ? speedRatio : 1.0);
            const cutDelayFrames = Math.round(
              fps * (cutout.delaySec !== undefined ? cutout.delaySec : defaultCutSec)
            );
            // Varied Entrance Choreography: slide_in_deal, delicate_tack, stamp_slam
            const entrance = cutout.entranceType || (idx % 2 === 0 ? "slide_in_deal" : "delicate_tack");
            const steppedCutFrame = isTactileCollage ? Math.floor(frame / 2) * 2 : frame;
            const cutSpring = spring({
              frame: Math.max(0, steppedCutFrame - cutDelayFrames),
              fps,
              config: entrance === "slide_in_deal"
                ? SPRING_PRESETS.paperSlide
                : entrance === "stamp_slam"
                ? SPRING_PRESETS.stamp
                : SPRING_PRESETS.paperHeavy,
            });

            let curX = cutout.xPct;
            let curY = cutout.yPct;
            let curRot = cutout.rotation || 0;
            let curScale = 1.0;

            if (entrance === "slide_in_deal") {
              const startX = cutout.xPct > 50 ? cutout.xPct + 14 : cutout.xPct - 14;
              curX = interpolate(cutSpring, [0, 1], [startX, cutout.xPct]);
              curY = cutout.yPct;
              curRot = interpolate(
                cutSpring,
                [0, 0.8, 1],
                [(cutout.rotation || 0) + (cutout.xPct > 50 ? 5 : -5), (cutout.rotation || 0) - (cutout.xPct > 50 ? 1 : -1), cutout.rotation || 0]
              );
            } else if (entrance === "stamp_slam") {
              curScale = interpolate(cutSpring, [0, 1], [1.7, 1.0]);
              curX = cutout.xPct;
              curY = cutout.yPct;
              curRot = cutout.rotation || 0;
            } else {
              // Delicate tack/drop: gentle 8% descent from above (not 25% drop)
              curX = cutout.xPct;
              curY = interpolate(cutSpring, [0, 1], [cutout.yPct - 8, cutout.yPct]);
              curRot = interpolate(cutSpring, [0, 1], [(cutout.rotation || 0) * 1.4, cutout.rotation || 0]);
            }

            return (
              <div
                key={cutout.id || idx}
                style={{
                  position: "absolute",
                  left: `${curX}%`,
                  top: `${curY}%`,
                  width: `${cutout.widthPct || 16}%`,
                  transform: `translate(-50%, -50%) scale(${curScale}) rotate(${curRot}deg)`,
                  opacity: interpolate(cutSpring, [0, 0.25, 1], [0, 1, 1]),
                  zIndex: 20 + idx,
                  filter: "drop-shadow(0 8px 16px rgba(0,0,0,0.22))",
                }}
              >
                {cutout.src ? (
                  <Img
                    src={cutout.src}
                    style={{ width: "100%", height: "auto", display: "block" }}
                  />
                ) : (
                  <div
                    style={{
                      padding: "10px 12px",
                      backgroundColor: "#ffffff",
                      border: "1.5px solid #e2e8f0",
                      borderRadius: "4px",
                      fontFamily: "monospace",
                      fontSize: "10px",
                      fontWeight: 700,
                      color: "#1e293b",
                    }}
                  >
                    <div style={{ color: "#dc2626", marginBottom: "3px" }}>
                      [EXHIBIT #{idx + 1}]
                    </div>
                    <div>{cutout.label || "FORENSIC RECORD"}</div>
                  </div>
                )}

                {/* Secondary Micro-Motion: Procedural Highlighter Sweep across evidence */}
                {cutout.hasMarkerHighlight && (
                  <div style={{ marginTop: 4, width: "100%", textAlign: "center" }}>
                    <ProceduralMarkerSweep
                      startFrame={cutDelayFrames + 12}
                      durationFrames={14}
                      color="#ffe600"
                      height="1.25em"
                      blendMode="multiply"
                    >
                      <span
                        style={{
                          fontFamily: "monospace",
                          fontSize: "10px",
                          fontWeight: 800,
                          color: "#0f172a",
                          backgroundColor: "rgba(255,255,255,0.75)",
                          padding: "1px 5px",
                          borderRadius: "2px",
                        }}
                      >
                        {cutout.highlightText || cutout.label || "VERIFIED"}
                      </span>
                    </ProceduralMarkerSweep>
                  </div>
                )}

                {cutout.hasPin && (
                  <div
                    style={{
                      position: "absolute",
                      top: "-12px",
                      left: "50%",
                      transform: "translateX(-50%)",
                      zIndex: 35,
                    }}
                  >
                    <VoxBrassPin size={26} dropFrame={cutDelayFrames + 4} />
                  </div>
                )}

                {cutout.hasTape && (
                  <div
                    style={{
                      position: "absolute",
                      top: "-14px",
                      left: "-12px",
                      zIndex: 35,
                    }}
                  >
                    <VoxWashiTape
                      width={85}
                      height={28}
                      rotation={22}
                      color="yellow"
                      dropFrame={cutDelayFrames + 3}
                    />
                  </div>
                )}
              </div>
            );
          })}

          {/* LAYER 3: RED CONNECTING YARN LINES (3D Catenary Woolen Yarn with Braided Fibers & Cast Shadow) */}
          {(isTactileCollage || yarns.length > 0) && yarns.map((yarn, yIdx) => {
            const defaultYarnSec = Math.min(dSec * 0.65, 0.9 + yIdx * 0.3) * (dSec < 7.0 ? speedRatio : 1.0);
            const yarnDelayFrames = Math.round(
              fps * (yarn.delaySec !== undefined ? yarn.delaySec : defaultYarnSec)
            );
            const yarnDurationFrames = Math.max(10, Math.round(fps * 0.7 * speedRatio));

            return (
              <VoxConnectingYarn
                key={`yarn-${yIdx}`}
                fromX={yarn.fromX}
                fromY={yarn.fromY}
                toX={yarn.toX}
                toY={yarn.toY}
                color={yarn.color || "#dc2626"}
                yarnThickness={4.5}
                drawStartFrame={yarnDelayFrames}
                drawDuration={yarnDurationFrames}
                showPins={true}
                pinSize={26}
              />
            );
          })}

          {/* LAYER 4: OFFICIAL RUBBER STAMP SLAM (Strictly tactile paper_collage mode) */}
          {isTactileCollage && stampText && (
            <div
              style={{
                position: "absolute",
                bottom: "10%",
                right: "8%",
                zIndex: 40,
                transform: `rotate(-14deg) scale(${stampScale})`,
                opacity: stampOpacity,
              }}
            >
              <div
                style={{
                  border: `4px solid ${stampColor}`,
                  borderRadius: "8px",
                  padding: "8px 18px",
                  color: stampColor,
                  fontWeight: 900,
                  fontSize: "18px",
                  fontFamily: "Impact, sans-serif",
                  letterSpacing: "0.12em",
                  textTransform: "uppercase",
                  boxShadow: `inset 0 0 0 1px ${stampColor}`,
                  backgroundColor: "rgba(255,255,255,0.2)",
                  backdropFilter: "blur(1px)",
                }}
              >
                {stampText}
              </div>
            </div>
          )}
        </VoxParallaxLayer>
      </div>
    </div>
  );
};
