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
} from "./papercraft";
import { VoxParallaxLayer } from "./VoxParallaxLayer";

export interface VoxBuildOnCutout {
  id: string;
  src?: string;
  label?: string;
  role?: string;
  xPct: number; // percentage of stage width (0 - 100)
  yPct: number; // percentage of stage height (0 - 100)
  widthPct?: number; // width in % of stage
  rotation?: number; // tilt degrees (-15 to 15)
  delaySec?: number; // entry delay in seconds (default ~ 3.5s)
  hasPin?: boolean;
  hasTape?: boolean;
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
}

/**
 * VoxBuildOnStage: Adaptive Multi-Mode Vox Visual & Tactile Engine.
 *
 * Supports 4 distinct editorial visual modes to match authentic Vox documentary pacing:
 * 1. "paper_collage" (15-20%): Tactile paper build-on assembly with brass pins, washi tape, and 12fps stop-motion jitter.
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
  heroPosition = { xPct: 50, yPct: 52, widthPct: 36 },
  supportingCutouts = [],
  yarns = [],
  stampText,
  stampColor = "#dc2626",
  hasMarkerHighlight = true,
  durationSec = 10,
  layoutVariant,
  sceneIndex = 0,
  cameraMovement,
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

  // 12fps Quantized Stop-Motion Jitter (active in tactile collage mode, calm in cinematic_doc)
  const rawJitter = useStopMotion(12, isTactileCollage ? 1.1 : 0.15, 42 + sceneIndex);
  const jitterX = isTactileCollage ? rawJitter.dx : 0;
  const jitterY = isTactileCollage ? rawJitter.dy : 0;
  const jitterRot = isTactileCollage ? rawJitter.dRot : 0;

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
  const heroSpring = spring({
    frame: Math.max(0, frame - heroDelayFrames),
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
          transform: `scale(${cameraScale}) translate(${jitterX + cameraPanX}px, ${jitterY}px) rotate(${jitterRot}deg)`,
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
                    filter: "contrast(1.05) brightness(0.96)",
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

          {/* MODE 3: KINETIC HEADLINE STAGE (Giant Centered Typography Card) */}
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
                  backgroundColor: "rgba(244, 236, 225, 0.94)",
                  borderTop: "6px solid #dc2626",
                  borderBottom: "3px solid #18181b",
                  padding: "32px 48px",
                  maxWidth: "78%",
                  boxShadow: "0 24px 48px rgba(0,0,0,0.42)",
                  transform: `scale(${interpolate(headlineSpring, [0, 1], [0.92, 1])})`,
                  opacity: interpolate(headlineSpring, [0, 1], [0, 1]),
                  textAlign: "center",
                }}
              >
                {subtitle && (
                  <div
                    style={{
                      fontSize: "14px",
                      fontWeight: 800,
                      color: "#dc2626",
                      letterSpacing: "0.24em",
                      marginBottom: "10px",
                      textTransform: "uppercase",
                      fontFamily: "monospace",
                    }}
                  >
                    {subtitle}
                  </div>
                )}
                <h1
                  style={{
                    fontSize: headline.length <= 8 ? "82px" : headline.length > 36 ? "44px" : "56px",
                    fontWeight: 900,
                    color: "#18181b",
                    lineHeight: 1.04,
                    letterSpacing: headline.length <= 8 ? "0.04em" : "-0.02em",
                    textTransform: "uppercase",
                    fontFamily: "Impact, 'Zen Kaku Gothic New', Inter, sans-serif",
                    margin: 0,
                  }}
                >
                  {headline}
                </h1>
                <div
                  style={{
                    height: "10px",
                    width: "65%",
                    margin: "14px auto 0 auto",
                    backgroundColor: "#facc15",
                    transformOrigin: "left center",
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

          {/* MODE 4: EVIDENCE DOSSIER SPLIT-CARD STAGE (Left Manila Card + Right Exhibit Cutout) */}
          {isEvidenceDossier && (headline || heroLabel) && (
            <div
              style={{
                position: "absolute",
                top: "14%",
                left: heroSrc ? "6%" : "24%",
                width: heroSrc ? "44%" : "52%",
                backgroundColor: "#f5efe1",
                borderLeft: "6px solid #b91c1c",
                border: "1px solid rgba(24,24,27,0.22)",
                padding: "24px 28px",
                boxShadow: "0 18px 36px rgba(0,0,0,0.34)",
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
                  color: "#b91c1c",
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
                    color: "#18181b",
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
                    fontSize: "14px",
                    fontWeight: 700,
                    color: "#3f3f46",
                    fontFamily: "monospace",
                    borderTop: "1px dashed rgba(24,24,27,0.25)",
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
                width: `${heroPosition.widthPct || 38}%`,
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
                {/* White Paper Cutout Border Simulation (only in tactile paper_collage mode) */}
                {isTactileCollage && (
                  <div
                    style={{
                      position: "absolute",
                      inset: "-3px",
                      border: "2px solid rgba(255,255,255,0.9)",
                      pointerEvents: "none",
                      borderRadius: "4px",
                    }}
                  />
                )}
              </div>

              {/* Brass Pin on Hero Head (only in tactile paper_collage mode) */}
              {isTactileCollage && (
                <div
                  style={{
                    position: "absolute",
                    top: "-10px",
                    left: "50%",
                    transform: "translateX(-50%)",
                    zIndex: 35,
                  }}
                >
                  <VoxBrassPin size={18} />
                </div>
              )}

              {/* Corner Washi Tape (only in tactile paper_collage mode) */}
              {isTactileCollage && (
                <div
                  style={{
                    position: "absolute",
                    bottom: "-8px",
                    right: "-12px",
                    zIndex: 35,
                  }}
                >
                  <VoxWashiTape width={65} rotation={-12} color="translucent" />
                </div>
              )}
            </div>
          </VoxParallaxLayer>
        )}

        {/* LAYER 2: SUPPORTING CUTOUTS & EVIDENCE (PARALLAX MIDGROUND) */}
        <VoxParallaxLayer depth="midground" cameraMovement={cameraMovement} durationInFrames={fTotal}>
          {isTactileCollage && supportingCutouts.map((cutout, idx) => {
            const defaultCutSec = (3.5 + idx * 0.4) * speedRatio;
            const cutDelayFrames = Math.round(
              fps * (cutout.delaySec !== undefined ? cutout.delaySec : defaultCutSec)
            );
            const cutSpring = spring({
              frame: Math.max(0, frame - cutDelayFrames),
              fps,
              config: SPRING_PRESETS.paperHeavy,
            });
            const curY = interpolate(
              cutSpring,
              [0, 1],
              [cutout.yPct - 25, cutout.yPct]
            );
            const curRot = interpolate(
              cutSpring,
              [0, 1],
              [(cutout.rotation || 0) * 2, cutout.rotation || 0]
            );

            return (
              <div
                key={cutout.id || idx}
                style={{
                  position: "absolute",
                  left: `${cutout.xPct}%`,
                  top: `${curY}%`,
                  width: `${cutout.widthPct || 24}%`,
                  transform: `translate(-50%, -50%) rotate(${curRot}deg)`,
                  opacity: interpolate(cutSpring, [0, 0.2, 1], [0, 1, 1]),
                  zIndex: 20 + idx,
                  filter: "drop-shadow(0 12px 20px rgba(0,0,0,0.3))",
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
                      padding: "12px 14px",
                      backgroundColor: "#ffffff",
                      border: "2px solid #e2e8f0",
                      borderRadius: "6px",
                      fontFamily: "monospace",
                      fontSize: "11px",
                      fontWeight: 700,
                      color: "#1e293b",
                    }}
                  >
                    <div style={{ color: "#dc2626", marginBottom: "4px" }}>
                      [EXHIBIT #{idx + 1}]
                    </div>
                    <div>{cutout.label || "FORENSIC RECORD"}</div>
                  </div>
                )}

                {cutout.hasPin && (
                  <div
                    style={{
                      position: "absolute",
                      top: "-8px",
                      left: "50%",
                      transform: "translateX(-50%)",
                    }}
                  >
                    <VoxBrassPin size={16} />
                  </div>
                )}

                {cutout.hasTape && (
                  <div
                    style={{
                      position: "absolute",
                      top: "-10px",
                      left: "-8px",
                    }}
                  >
                    <VoxWashiTape width={50} rotation={22} color="yellow" />
                  </div>
                )}
              </div>
            );
          })}

          {/* LAYER 3: RED CONNECTING YARN LINES (Strictly tactile paper_collage mode) */}
          {isTactileCollage && yarns.map((yarn, yIdx) => {
            const defaultYarnSec = (4.8 + yIdx * 0.3) * speedRatio;
            const yarnDelayFrames = Math.round(
              fps * (yarn.delaySec !== undefined ? yarn.delaySec : defaultYarnSec)
            );
            const yarnDurationFrames = Math.max(6, Math.round(fps * 0.6 * speedRatio));
            const drawProgress = interpolate(
              frame,
              [yarnDelayFrames, yarnDelayFrames + yarnDurationFrames],
              [0, 1],
              {
                extrapolateLeft: "clamp",
                extrapolateRight: "clamp",
                easing: Easing.out(Easing.cubic),
              }
            );

            if (drawProgress <= 0) return null;

            return (
              <svg
                key={yIdx}
                style={{
                  position: "absolute",
                  inset: 0,
                  width: "100%",
                  height: "100%",
                  pointerEvents: "none",
                  zIndex: 25,
                }}
              >
                <line
                  x1={`${yarn.fromX}%`}
                  y1={`${yarn.fromY}%`}
                  x2={`${interpolate(
                    drawProgress,
                    [0, 1],
                    [yarn.fromX, yarn.toX]
                  )}%`}
                  y2={`${interpolate(
                    drawProgress,
                    [0, 1],
                    [yarn.fromY, yarn.toY]
                  )}%`}
                  stroke={yarn.color || "#dc2626"}
                  strokeWidth="3.5"
                  strokeDasharray="6 4"
                  strokeLinecap="round"
                />
              </svg>
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
