import React, { useEffect, useState } from "react";
import {
  AbsoluteFill,
  Audio,
  Composition,
  Easing,
  Img,
  Sequence,
  continueRender,
  delayRender,
  interpolate,
  registerRoot,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import { DataStoryTest } from "./DataStoryTest";
import { FullStory } from "./FullStory";

const INK = "#05090d";
const LIGHT = "#ffffff";

const BEAT_STYLE = {
  rise: { accent: "#f2a63b", dir: "up" },
  peak: { accent: "#ffd166", dir: "flat" },
  collapse: { accent: "#c81e3a", dir: "down" },
  aftermath: { accent: "#8fa3b0", dir: "flat" },
};

const ZONE_STYLE = {
  top_left: { justifyContent: "flex-start", alignItems: "flex-start", textAlign: "left" },
  top_right: { justifyContent: "flex-start", alignItems: "flex-end", textAlign: "right" },
  bottom_left: { justifyContent: "flex-end", alignItems: "flex-start", textAlign: "left" },
  bottom_right: { justifyContent: "flex-end", alignItems: "flex-end", textAlign: "right" },
};

const POINTS = {
  up: "0,120 80,96 160,64 240,40 320,8",
  down: "0,8 80,40 160,72 240,100 320,132",
  flat: "0,70 80,66 160,72 240,68 320,70",
};

const SUB_RESERVE = 0.22;

const outline = (px, color) => {
  const dirs = [[-1, -1], [1, -1], [-1, 1], [1, 1], [0, -1], [0, 1], [-1, 0], [1, 0]];
  const parts = dirs.map((d) => `${d[0] * px}px ${d[1] * px}px 0 ${color}`);
  parts.push(`0 ${px * 2}px ${px * 3}px rgba(0,0,0,0.55)`);
  return parts.join(", ");
};

const TrendIcon = ({ accent, dir, k, progress }) => {
  const pts = POINTS[dir] ? POINTS[dir] : POINTS.flat;
  return (
    <svg width={320 * k} height={140 * k} viewBox="0 0 320 140">
      <polyline
        points={pts}
        fill="none"
        stroke={INK}
        strokeWidth={16}
        strokeLinecap="round"
        strokeDasharray={520}
        strokeDashoffset={520 * (1 - progress)}
        opacity={0.55}
      />
      <polyline
        points={pts}
        fill="none"
        stroke={accent}
        strokeWidth={10}
        strokeLinecap="round"
        strokeDasharray={520}
        strokeDashoffset={520 * (1 - progress)}
      />
    </svg>
  );
};

export const SceneCard = (props) => {
  const bgFile = props.bgFile;
  const statValue = props.statValue;
  const statLabel = props.statLabel;
  const storyBeat = props.storyBeat;
  const hasChartInBg = props.hasChartInBg;
  const safeZone = props.safeZone ? props.safeZone : "top_left";
  const accentOverride = props.accentOverride;

  const frame = useCurrentFrame();
  const cfg = useVideoConfig();
  const width = cfg.width;
  const height = cfg.height;
  const durationInFrames = cfg.durationInFrames;
  const fps = cfg.fps;
  const k = width / 1536;

  const beat = BEAT_STYLE[storyBeat] ? BEAT_STYLE[storyBeat] : BEAT_STYLE.rise;
  const accent = accentOverride ? accentOverride : beat.accent;
  const zone = ZONE_STYLE[safeZone] ? ZONE_STYLE[safeZone] : ZONE_STYLE.top_left;
  const isBottom = safeZone.indexOf("bottom") === 0;

  const zoom = interpolate(frame, [0, durationInFrames], [1, 1.06], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const appear = interpolate(frame, [0, Math.round(fps * 0.6)], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const drawP = interpolate(frame, [Math.round(fps * 0.3), Math.round(fps * 1.7)], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ backgroundColor: INK }}>
      <AbsoluteFill>
        <Img
          src={staticFile(bgFile)}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            transform: `scale(${zoom})`,
          }}
        />
      </AbsoluteFill>
      <AbsoluteFill
        style={{
          display: "flex",
          flexDirection: "column",
          padding: 64 * k,
          paddingBottom: isBottom ? height * SUB_RESERVE : 64 * k,
          justifyContent: zone.justifyContent,
          alignItems: zone.alignItems,
          opacity: appear,
          transform: `translateY(${(1 - appear) * 24 * k}px)`,
        }}
      >
        {hasChartInBg ? null : (
          <TrendIcon accent={accent} dir={beat.dir} k={k} progress={drawP} />
        )}
        <div
          style={{
            fontFamily: "Arial, Helvetica, sans-serif",
            fontWeight: 900,
            fontSize: 150 * k,
            lineHeight: 1,
            color: accent,
            textAlign: zone.textAlign,
            textShadow: outline(Math.max(2, 4 * k), INK),
          }}
        >
          {statValue}
        </div>
        <div
          style={{
            fontFamily: "Arial, Helvetica, sans-serif",
            fontWeight: 700,
            fontSize: 40 * k,
            marginTop: 14 * k,
            letterSpacing: 2 * k,
            color: LIGHT,
            maxWidth: width * 0.55,
            textAlign: zone.textAlign,
            textShadow: outline(Math.max(1, 3 * k), INK),
          }}
        >
          {statLabel}
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

// ---------------------------------------------------------------------------
// TwoLayerEpisode -- generic, episode-agnostic 2-layer (Background +
// Foreground/Overlay) composition for the new video architecture (Skill AI
// Rule 50-52). Not hardcoded to any single episode: driven entirely by the
// `scenes` prop, which is built by scripts/build_remotion_props.py from
// brain_input.json + the images pulled by scripts/pull_approved_images.py.
//
// Contract per scene:
//   background            : staticFile()-relative path OR absolute https URL
//                            (required). Hard-cut only -- never fades.
//   foreground            : same path rules, optional. Fades in at the start
//                            of the scene and fades out at the end (Rule 50).
//   durationInFrames      : integer frames this scene occupies.
//   foregroundFadeFrames  : frames used for the foreground fade in/out.
//   caption               : optional text drawn in the reserved safe zone.
//   safeZone              : "top" | "bottom" | "none" -- which edge is kept
//                            clear for number/text cards (matches the
//                            SUB_RESERVE pattern used by SceneCard above).
// ---------------------------------------------------------------------------

const resolveSrc = (src) => {
  if (!src) return null;
  if (/^https?:\/\//i.test(src)) return src;
  return staticFile(src);
};

const SAFE_ZONE_STYLE = {
  top: { justifyContent: "flex-start" },
  bottom: { justifyContent: "flex-end" },
  none: { justifyContent: "center" },
};

// Rule 59 v2 (04/08/2026 ~13:52) -- REPLACES the 6-cell grid below (user
// flagged the grid version as too small, and sent a reference image with a
// red box marking the target size/position). Measured from that reference
// (red box vs full 16:9 frame, pixel ratio of the attached screenshot):
// Foreground occupies ~82% of frame HEIGHT, grounded at the bottom (~2%
// bottom margin), placed flush against one side (left or right, chosen by
// `foregroundPosition`) with a ~6.5% side margin, inside a width band of
// ~27% of frame width (actual rendered width follows the image's own aspect
// ratio via objectFit:contain, never exceeding this band).
// Rule 63: unified with wide-pose height (image 2) per user request 05/08/2026 -- narrow/standard pose (image 1) no longer uses a taller scale than wide pose, for visual balance + easier future tuning (single height constant to adjust instead of two).
const FOREGROUND_HEIGHT_PCT = 0.78;
const FOREGROUND_BOTTOM_MARGIN_PCT = 0.02;
const FOREGROUND_SIDE_MARGIN_PCT = 0.065;
const FOREGROUND_WIDTH_BAND_PCT = 0.27;
// Rule 61: wide/outstretched-arm poses (e.g. pointing) are allowed a wider
// horizontal band so height/torso proportion is not sacrificed to the normal
// narrow band. Detected automatically from the cutout's own trimmed aspect
// ratio (width/height) -- no manual per-scene classification needed.
const FOREGROUND_WIDE_POSE_ASPECT_THRESHOLD = 0.75;
const FOREGROUND_WIDE_WIDTH_BAND_PCT = 0.55;
const FOREGROUND_WIDE_HEIGHT_PCT = 0.78;
// Rule 62: wide poses hug the frame edge more tightly than the
// standard 6.5% side margin (user marked a red box closer to the
// edge on a reference screenshot for the pointing/outstretched pose).
// Mirrors symmetrically for position === "right" via the existing
// left/right calc below.
const FOREGROUND_WIDE_SIDE_MARGIN_PCT = 0.02;
// Rule 90: 3-Zone Frame Template for 16:9 (Background + Foreground + Subtitle Safe Zone).
// 16:9-specific -- FG height 72% (vs 78% for 9:16), top at 28%, bottom at 0%.
// Subtitle Safe Zone: bottom 10%, full width, z-index 2 overlay on BG + FG.
const FOREGROUND_HEIGHT_PCT_16_9 = 0.82;
const FOREGROUND_BOTTOM_MARGIN_PCT_16_9 = 0.0;
const FOREGROUND_SIDE_MARGIN_PCT_16_9_NARROW = 0.03;
const FOREGROUND_WIDTH_BAND_PCT_16_9_NARROW = 0.36;
const FOREGROUND_SIDE_MARGIN_PCT_16_9_WIDE = 0.02;
const FOREGROUND_WIDTH_BAND_PCT_16_9_WIDE = 0.55;
const SUBTITLE_ZONE_HEIGHT_PCT_16_9 = 0.18;

const computeForegroundCell = (width, height, position, aspect) => {
  const cellHeight = height * 0.82;
  const cellWidth = cellHeight * (aspect || (768 / 1376));
  const top = height - cellHeight;
  const left = position === "right" ? width - cellWidth - 50 : 50;
  return { left, top, width: cellWidth, height: cellHeight };
};

const useForegroundAspect = (src) => {
  const [aspect, setAspect] = useState(null);
  useEffect(() => {
    if (!src) return;
    const handle = delayRender("measure-foreground-aspect:" + src);
    const img = new window.Image();
    img.onload = () => {
      if (img.naturalWidth && img.naturalHeight) {
        setAspect(img.naturalWidth / img.naturalHeight);
      }
      continueRender(handle);
    };
    img.onerror = () => {
      continueRender(handle);
    };
    img.src = resolveSrc(src);
  }, [src]);
  return aspect;
};

// Foreground/overlay layer: slides in from outside the frame edge (same side
// as its target corner) + fades in together over `fadeFrames`, once per
// entrance (Rule 59 point 4). Fades out at scene end WITHOUT a reverse slide
// (slide is entrance-only). When `position` is "left"/"right" it is placed in
// its side-anchored box (Rule 59 v2, ~82% height); otherwise it falls back to
// the legacy full-frame centered/contain behavior for backward compatibility.
const ForegroundLayer = ({ src, position, fadeFrames, durationInFrames, width, height }) => {
  const frame = useCurrentFrame();
  const aspect = useForegroundAspect(src);
  const fadeIn = interpolate(frame, [0, fadeFrames], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const fadeOut = interpolate(
    frame,
    [Math.max(0, durationInFrames - fadeFrames), durationInFrames],
    [1, 0],
    { extrapolateLeft: "clamp", extrapolateRight: "clamp" }
  );
  const opacity = Math.min(fadeIn, fadeOut);
  const hasGrid = position === "left" || position === "right";

  if (!hasGrid) {
    return (
      <AbsoluteFill style={{ opacity }}>
        <Img src={resolveSrc(src)} style={{ width: "100%", height: "100%", objectFit: "contain" }} />
      </AbsoluteFill>
    );
  }

  const cell = computeForegroundCell(width, height, position, aspect);
  const slideIn = interpolate(frame, [0, fadeFrames], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const offscreenX = position === "left" ? -(cell.left + cell.width) : width - cell.left;
  const translateX = offscreenX * (1 - slideIn);

  return (
    <div
      style={{
        position: "absolute",
        left: cell.left,
        top: cell.top,
        width: cell.width,
        height: cell.height,
        opacity,
        transform: `translateX(${translateX}px)`,
        filter: "drop-shadow(0 20px 35px rgba(0,0,0,0.65)) drop-shadow(0 4px 10px rgba(0,0,0,0.4))",
        zIndex: 15,
        pointerEvents: "none",
      }}
    >
      {/* Grounded radial-gradient contact floor shadow under character feet */}
      <div
        style={{
          position: "absolute",
          bottom: -10,
          left: "15%",
          width: "70%",
          height: 24,
          borderRadius: "50%",
          background: "radial-gradient(ellipse at center, rgba(0, 0, 0, 0.75) 0%, rgba(0, 0, 0, 0.35) 45%, rgba(0, 0, 0, 0) 70%)",
          filter: "blur(6px)",
          transform: "scaleY(0.4)",
          pointerEvents: "none",
          zIndex: -1,
        }}
      />
      <Img
        src={resolveSrc(src)}
        style={{
          width: "100%",
          height: "100%",
          objectFit: "contain",
          objectPosition: "bottom",
        }}
      />
    </div>
  );
};

// Rule 90: Subtitle Safe Zone overlay for 16:9 -- semi-transparent gradient
// at bottom 10% of frame for subtitle legibility. z-index 2 (above BG + FG).
const SubtitleZoneOverlay = ({ height, position }) => {
  const zoneHeight = height * SUBTITLE_ZONE_HEIGHT_PCT_16_9;
  // Rule 90 Logic 1: subtitle zone mirrors FG position
  // FG left -> overlay right half | FG right -> overlay left half
  const isLeft = position === "left";
  const isRight = position === "right";
  const overlayLeft = isLeft ? "50%" : 0;
  const overlayWidth = isLeft || isRight ? "50%" : "100%";
  return (
    <div
      style={{
        position: "absolute",
        left: overlayLeft,
        bottom: 0,
        width: overlayWidth,
        height: zoneHeight,
        background: "linear-gradient(to bottom, rgba(5,9,13,0) 0%, rgba(5,9,13,0.6) 30%, rgba(5,9,13,0.85) 100%)",
        zIndex: 2,
        pointerEvents: "none",
      }}
    />
  );
};

// === FORENSIC MOTION GRAPHICS TOOLKIT (Rule 122 & Rule 128) ===

const RedactedDocumentOverlay = ({ label, isLeft }: { label?: string; isLeft?: boolean }) => {
  const frame = useCurrentFrame();
  const red1 = interpolate(frame, [5, 25], [0, 100], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const red2 = interpolate(frame, [15, 38], [0, 100], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const red3 = interpolate(frame, [25, 50], [0, 100], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <div
      style={{
        position: "absolute",
        top: 60,
        left: isLeft ? "auto" : 80,
        right: isLeft ? 80 : "auto",
        width: 440,
        backgroundColor: "rgba(10, 15, 25, 0.90)",
        border: "1.5px solid rgba(242, 166, 59, 0.45)",
        borderRadius: 12,
        padding: "16px 20px",
        boxShadow: "0 10px 30px rgba(0,0,0,0.85), inset 0 0 15px rgba(242,166,59,0.1)",
        backdropFilter: "blur(10px)",
        zIndex: 28,
        fontFamily: "'Courier New', Courier, monospace",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid rgba(242, 166, 59, 0.3)", paddingBottom: 6, marginBottom: 10 }}>
        <span style={{ color: "#ffd166", fontSize: 12, fontWeight: 900, letterSpacing: 1.5 }}>
          📁 {label || "CLASSIFIED // EVIDENCE DOSSIER"}
        </span>
        <span style={{ color: "#ef4444", fontSize: 11, fontWeight: 800, border: "1px solid #ef4444", padding: "1px 6px", borderRadius: 4 }}>
          CONFIDENTIAL
        </span>
      </div>
      <div style={{ fontSize: 13, color: "#94a3b8", lineHeight: 1.8, position: "relative" }}>
        <div style={{ position: "relative", marginBottom: 6 }}>
          <span>SUBJECT: OPERATION ATLAS LOGISTICS COMPLIANCE</span>
          <div style={{ position: "absolute", inset: 0, width: `${red1}%`, backgroundColor: "#05090d", borderRadius: 3 }} />
        </div>
        <div style={{ position: "relative", marginBottom: 6 }}>
          <span>SECTION 14.2: LIABILITY CONCEALMENT & CLAUSE 9A</span>
          <div style={{ position: "absolute", inset: 0, width: `${red2}%`, backgroundColor: "#05090d", borderRadius: 3 }} />
        </div>
        <div style={{ position: "relative" }}>
          <span>AUTHORIZATION: NON-DISCLOSURE ENFORCED</span>
          <div style={{ position: "absolute", inset: 0, width: `${red3}%`, backgroundColor: "#05090d", borderRadius: 3 }} />
        </div>
      </div>
    </div>
  );
};

const DynamicRadarMapOverlay = ({ label, isLeft }: { label?: string; isLeft?: boolean }) => {
  const frame = useCurrentFrame();
  const sweepAngle = (frame * 4) % 360;
  const pingOpacity = Math.sin(frame * 0.25) > 0 ? 1 : 0.25;

  return (
    <div
      style={{
        position: "absolute",
        top: 60,
        left: isLeft ? "auto" : 80,
        right: isLeft ? 80 : "auto",
        width: 320,
        height: 200,
        backgroundColor: "rgba(5, 12, 18, 0.88)",
        border: "1.5px solid rgba(16, 185, 129, 0.5)",
        borderRadius: 12,
        padding: 14,
        boxShadow: "0 10px 30px rgba(0,0,0,0.85), 0 0 15px rgba(16,185,129,0.2)",
        backdropFilter: "blur(10px)",
        zIndex: 28,
        display: "flex",
        flexDirection: "column",
        justifyContent: "space-between",
        fontFamily: "'Courier New', Courier, monospace",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid rgba(16, 185, 129, 0.3)", paddingBottom: 6 }}>
        <span style={{ color: "#10b981", fontSize: 12, fontWeight: 900, letterSpacing: 1.5 }}>
          📡 {label || "ATC RADAR // VECTOR TRACK"}
        </span>
        <span style={{ color: "#10b981", fontSize: 11, fontWeight: 700 }}>LIVE 30Hz</span>
      </div>

      <div style={{ display: "flex", alignItems: "center", gap: 16 }}>
        <div style={{ position: "relative", width: 110, height: 110, borderRadius: "50%", border: "1px solid rgba(16, 185, 129, 0.4)", overflow: "hidden" }}>
          <div style={{ position: "absolute", inset: 18, borderRadius: "50%", border: "1px dashed rgba(16, 185, 129, 0.3)" }} />
          <div style={{ position: "absolute", inset: 36, borderRadius: "50%", border: "1px solid rgba(16, 185, 129, 0.2)" }} />
          <div style={{ position: "absolute", top: "50%", left: 0, right: 0, height: 1, backgroundColor: "rgba(16, 185, 129, 0.3)" }} />
          <div style={{ position: "absolute", left: "50%", top: 0, bottom: 0, width: 1, backgroundColor: "rgba(16, 185, 129, 0.3)" }} />
          <div
            style={{
              position: "absolute",
              top: "50%",
              left: "50%",
              width: 55,
              height: 2,
              backgroundColor: "#10b981",
              transformOrigin: "left center",
              transform: `rotate(${sweepAngle}deg)`,
              boxShadow: "0 0 8px #10b981",
            }}
          />
          <div
            style={{
              position: "absolute",
              top: 35,
              left: 65,
              width: 8,
              height: 8,
              borderRadius: "50%",
              backgroundColor: "#ef4444",
              opacity: pingOpacity,
              boxShadow: "0 0 10px #ef4444",
            }}
          />
        </div>

        <div style={{ color: "#cbd5e1", fontSize: 11, lineHeight: 1.6 }}>
          <div>CALLSIGN: <span style={{ color: "#38bdf8" }}>AMZ-21</span></div>
          <div>ALTITUDE: <span style={{ color: "#f87171" }}>3,200 -&gt; 0 FT</span></div>
          <div>V/S: <span style={{ color: "#f87171" }}>-4,800 FPM</span></div>
          <div>SECTOR: 25.79°N, 80.28°W</div>
        </div>
      </div>
    </div>
  );
};

const KineticChartOverlay = ({ label, isLeft }: { label?: string; isLeft?: boolean }) => {
  const frame = useCurrentFrame();
  const drawProgress = interpolate(frame, [0, 45], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const val = interpolate(frame, [5, 40], [0, -42.8], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });

  return (
    <div
      style={{
        position: "absolute",
        top: 60,
        left: isLeft ? "auto" : 80,
        right: isLeft ? 80 : "auto",
        width: 360,
        backgroundColor: "rgba(15, 23, 42, 0.92)",
        border: "1.5px solid rgba(239, 68, 68, 0.5)",
        borderRadius: 12,
        padding: "14px 18px",
        boxShadow: "0 12px 35px rgba(0,0,0,0.85), 0 0 15px rgba(239,68,68,0.25)",
        backdropFilter: "blur(10px)",
        zIndex: 28,
        fontFamily: "'Segoe UI', Roboto, sans-serif",
      }}
    >
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", borderBottom: "1px solid rgba(239, 68, 68, 0.3)", paddingBottom: 6, marginBottom: 8 }}>
        <span style={{ color: "#f87171", fontSize: 12, fontWeight: 900, letterSpacing: 1.5, textTransform: "uppercase" }}>
          📉 {label || "MARKET TRAJECTORY // LOSS"}
        </span>
        <span style={{ color: "#f87171", fontSize: 13, fontWeight: 900 }}>
          {val.toFixed(1)}B USD
        </span>
      </div>
      <svg width="320" height="70" viewBox="0 0 320 70">
        <defs>
          <linearGradient id="gradLoss" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="rgba(239, 68, 68, 0.3)" />
            <stop offset="100%" stopColor="rgba(239, 68, 68, 0)" />
          </linearGradient>
        </defs>
        <path
          d="M 0,15 Q 80,10 160,35 T 320,60"
          fill="none"
          stroke="#ef4444"
          strokeWidth="3"
          strokeDasharray="350"
          strokeDashoffset={350 * (1 - drawProgress)}
        />
        <circle cx={drawProgress * 320} cy={15 + drawProgress * 45} r="4" fill="#ffd166" />
      </svg>
    </div>
  );
};

const SurveillanceGridOverlay = ({ label }: { label?: string }) => {
  const frame = useCurrentFrame();
  const isRecBlink = frame % 30 < 15;
  const timeSec = Math.floor(frame / 30);

  return (
    <AbsoluteFill style={{ pointerEvents: "none", zIndex: 26 }}>
      <div style={{ position: "absolute", top: 40, left: 40, width: 30, height: 30, borderTop: "2px solid rgba(255,255,255,0.4)", borderLeft: "2px solid rgba(255,255,255,0.4)" }} />
      <div style={{ position: "absolute", top: 40, right: 40, width: 30, height: 30, borderTop: "2px solid rgba(255,255,255,0.4)", borderRight: "2px solid rgba(255,255,255,0.4)" }} />
      <div style={{ position: "absolute", bottom: 40, left: 40, width: 30, height: 30, borderBottom: "2px solid rgba(255,255,255,0.4)", borderLeft: "2px solid rgba(255,255,255,0.4)" }} />
      <div style={{ position: "absolute", bottom: 40, right: 40, width: 30, height: 30, borderBottom: "2px solid rgba(255,255,255,0.4)", borderRight: "2px solid rgba(255,255,255,0.4)" }} />

      <div style={{ position: "absolute", top: 46, left: 80, display: "flex", alignItems: "center", gap: 8, fontFamily: "'Courier New', monospace" }}>
        <div style={{ width: 12, height: 12, borderRadius: "50%", backgroundColor: "#ef4444", opacity: isRecBlink ? 1 : 0.2, boxShadow: isRecBlink ? "0 0 10px #ef4444" : "none" }} />
        <span style={{ color: "#ef4444", fontSize: 14, fontWeight: 900, letterSpacing: 2 }}>REC</span>
        <span style={{ color: "rgba(255,255,255,0.7)", fontSize: 13, marginLeft: 12 }}>
          {label || "CAM-04 // SEC_ZONE"}
        </span>
      </div>

      <div style={{ position: "absolute", top: 46, right: 80, color: "rgba(255,255,255,0.7)", fontFamily: "'Courier New', monospace", fontSize: 13 }}>
        00:00:{timeSec < 10 ? `0${timeSec}` : timeSec}:{(frame % 30) < 10 ? `0${frame % 30}` : frame % 30}
      </div>
    </AbsoluteFill>
  );
};

const ForensicStampBadge = ({ badge, isLeft }: { badge: string; isLeft?: boolean }) => {
  const frame = useCurrentFrame();
  const cfg = useVideoConfig();
  // Dynamic Stamp Slam physics: rapid scale drop from 2.4 down to 1.0 with damping spring
  const scale = spring({
    frame: Math.max(0, frame - 4),
    fps: cfg.fps || 30,
    config: { damping: 9, mass: 0.35, stiffness: 150 },
    from: 2.4,
    to: 1.0,
  });
  const opacity = interpolate(frame, [3, 7], [0, 1], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const bUp = (badge || "").toUpperCase();
  const isAlert = ["VIOLATION", "FRAUD", "PRICE_FRAUD", "VOID", "CRITICAL", "ILLEGAL"].some((k) => bUp.includes(k));
  const isAuth = ["CONFIDENTIAL", "CLASSIFIED", "SEALED", "EVIDENCE", "RESTRICTED"].some((k) => bUp.includes(k));

  const mainColor = isAlert ? "#ef4444" : isAuth ? "#f59e0b" : "#10b981";
  const borderColor = isAlert ? "rgba(239, 68, 68, 0.85)" : isAuth ? "rgba(245, 158, 11, 0.85)" : "rgba(16, 185, 129, 0.85)";
  const bg = isAlert ? "rgba(45, 10, 15, 0.92)" : isAuth ? "rgba(40, 25, 10, 0.92)" : "rgba(10, 35, 20, 0.92)";
  const icon = isAlert ? "🚨" : isAuth ? "📁" : "⚖️";

  return (
    <div
      style={{
        position: "absolute",
        top: 55,
        left: isLeft ? "auto" : 70,
        right: isLeft ? 70 : "auto",
        transform: `scale(${scale}) rotate(-8deg)`,
        opacity,
        zIndex: 32,
        border: `3px double ${borderColor}`,
        borderRadius: 8,
        padding: "8px 20px",
        backgroundColor: bg,
        boxShadow: `0 10px 30px rgba(0,0,0,0.85), 0 0 20px ${mainColor}40`,
        fontFamily: "'Courier New', Courier, monospace",
        textTransform: "uppercase",
        display: "flex",
        alignItems: "center",
        gap: 10,
        pointerEvents: "none",
      }}
    >
      <span style={{ fontSize: 20 }}>{icon}</span>
      <span style={{ color: mainColor, fontSize: 18, fontWeight: 900, letterSpacing: 2 }}>{badge}</span>
    </div>
  );
};

export const TwoLayerScene = (props) => {
  const background = props.background;
  const showBackground = props.showBackground === false ? false : true;
  const showForeground = props.showForeground === false ? false : true;
  const foreground = props.foreground;
  const foregroundPosition = props.foregroundPosition;
  const caption = props.caption || "";
  const safeZone = props.safeZone ? props.safeZone : "none";
  const fadeFrames = props.foregroundFadeFrames ? props.foregroundFadeFrames : 15;
  const statValue = props.statValue;
  const statLabel = props.statLabel;
  const forensicOverlay = props.forensicOverlay;
  const stampBadge = props.stampBadge;

  const cfg = useVideoConfig();
  const durationInFrames = cfg.durationInFrames || 180;
  const width = cfg.width || 1920;
  const height = cfg.height || 1080;
  const frame = useCurrentFrame();

  const isLeft = foregroundPosition === "left";
  const isRight = foregroundPosition === "right";
  const subtitles = props.subtitles || props.words || null;

  // Subtitle Smart Chunking & Pacing-Aware Karaoke Word Timing (Sync with TTS & Timeframe)
  const fullCaption = props.caption || props.narration || "";
  const hasExactSubtitles = Boolean(subtitles && Array.isArray(subtitles) && subtitles.length > 0);

  const words = hasExactSubtitles
    ? (subtitles as any[]).map((w) => w.word)
    : fullCaption.split(" ").filter(Boolean);
  const totalWords = Math.max(1, words.length);

  let activeGlobalWordIdx = -1;

  if (hasExactSubtitles && subtitles && subtitles.length > 0) {
    const currentMs = (frame / (cfg.fps || 30)) * 1000;
    activeGlobalWordIdx = (subtitles as any[]).findIndex(
      (item) => currentMs >= item.start_ms && currentMs < item.end_ms
    );
    if (activeGlobalWordIdx === -1) {
      const lastWord = subtitles[subtitles.length - 1];
      if (currentMs >= lastWord.end_ms) {
        activeGlobalWordIdx = subtitles.length - 1;
      } else {
        activeGlobalWordIdx = (subtitles as any[]).findIndex((item) => currentMs < item.start_ms);
        if (activeGlobalWordIdx > 0) {
          activeGlobalWordIdx -= 1;
        } else if (activeGlobalWordIdx === -1) {
          activeGlobalWordIdx = 0;
        }
      }
    }
  } else {
    // Fallback: speech-acoustic weight heuristic
    const weights = words.map((w) => {
      let weight = Math.max(3, w.length);
      if (/[.,!?;:—]/.test(w)) {
        weight += 9; // pause weighting for comma, period, dash
      }
      return weight;
    });
    const totalWeight = weights.reduce((a, b) => a + b, 0);

    let cum = 0;
    const wordEndFrames = weights.map((w) => {
      cum += w;
      return Math.min(durationInFrames, Math.round((cum / totalWeight) * durationInFrames));
    });

    activeGlobalWordIdx = wordEndFrames.findIndex((endF) => frame < endF);
    if (activeGlobalWordIdx === -1) {
      activeGlobalWordIdx = totalWords - 1;
    }
  }

  // Page chunking locked directly to active word index (prevents premature page flips)
  const CHUNK_SIZE = 10;
  const chunkIndex = Math.floor(Math.max(0, activeGlobalWordIdx) / CHUNK_SIZE);
  const chunkStartWord = chunkIndex * CHUNK_SIZE;
  const visibleWords = words.slice(chunkStartWord, chunkStartWord + CHUNK_SIZE);

  // Animated pop-in for Stat Card
  const statSpring = interpolate(frame, [0, 15], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ backgroundColor: showBackground ? INK : "transparent" }}>
      {showBackground && background ? (
        <AbsoluteFill>
          <Img
            src={resolveSrc(background)}
            style={{ width: "100%", height: "100%", objectFit: "cover" }}
          />
        </AbsoluteFill>
      ) : null}

      {showForeground && foreground ? (
        <ForegroundLayer
          src={foreground}
          position={foregroundPosition}
          fadeFrames={fadeFrames}
          durationInFrames={durationInFrames}
          width={width}
          height={height}
        />
      ) : null}

      {/* Top Safe-Zone Animated Stat / Financial Alert Card */}
      {statValue ? (
        <div
          style={{
            position: "absolute",
            top: 50,
            left: isLeft ? "auto" : 70,
            right: isLeft ? 70 : "auto",
            zIndex: 30,
            backgroundColor: "rgba(12, 18, 28, 0.92)",
            border: "2px solid #f2a63b",
            borderRadius: 16,
            padding: "16px 28px",
            boxShadow: "0 12px 35px rgba(0,0,0,0.75), 0 0 20px rgba(242, 166, 59, 0.25)",
            transform: `scale(${statSpring})`,
            opacity: statSpring,
            display: "flex",
            flexDirection: "column",
            gap: 4,
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 10 }}>
            <span style={{ fontSize: 24 }}>⚠️</span>
            <div
              style={{
                color: "#ffd166",
                fontSize: 38,
                fontWeight: 900,
                fontFamily: "'Segoe UI', Roboto, Arial, sans-serif",
                letterSpacing: 1,
                textShadow: "0 2px 8px rgba(0,0,0,0.9)",
              }}
            >
              {statValue}
            </div>
          </div>
          {statLabel ? (
            <div
              style={{
                color: "#94a3b8",
                fontSize: 16,
                fontWeight: 700,
                letterSpacing: 1.5,
                textTransform: "uppercase",
                fontFamily: "'Segoe UI', Roboto, Arial, sans-serif",
              }}
            >
              {statLabel}
            </div>
          ) : null}
        </div>
      ) : null}

      {/* Forensic Motion Graphics Evidentiary Overlays (Rule 122 & Rule 128) */}
      {(() => {
        const rawOv = forensicOverlay;
        const ovType = typeof rawOv === "string" ? rawOv : rawOv?.type;
        const ovLabel = typeof rawOv === "object" ? rawOv?.label : undefined;
        return (
          <>
            {ovType === "redacted_doc" ? (
              <RedactedDocumentOverlay label={ovLabel} isLeft={isLeft} />
            ) : null}
            {ovType === "radar_map" ? (
              <DynamicRadarMapOverlay label={ovLabel} isLeft={isLeft} />
            ) : null}
            {ovType === "financial_chart" ? (
              <KineticChartOverlay label={ovLabel} isLeft={isLeft} />
            ) : null}
            {ovType === "surveillance_crt" ? (
              <SurveillanceGridOverlay label={ovLabel} />
            ) : null}
          </>
        );
      })()}

      {/* Forensic Stamp Slam Badge (Rule 122 Acting & Evidence Props) */}
      {stampBadge ? (
        <ForensicStampBadge badge={String(stampBadge)} isLeft={isLeft} />
      ) : null}

      {/* Modern High-Retention Subtitle Dialogue Container (Exact Layout of User Reference Image 1) */}
      {words.length > 0 ? (
        <div
          style={{
            position: "absolute",
            bottom: 30,
            left: isLeft ? 520 : 60,
            right: isRight ? 520 : 60,
            minHeight: 145,
            zIndex: 25,
            background: "linear-gradient(180deg, rgba(15, 23, 42, 0.82) 0%, rgba(5, 9, 14, 0.88) 100%)",
            border: "2px solid rgba(242, 166, 59, 0.40)",
            borderRadius: 18,
            padding: "16px 28px",
            boxShadow: "0 15px 40px rgba(0,0,0,0.75), inset 0 1px 0 rgba(255,255,255,0.15)",
            backdropFilter: "blur(12px)",
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
          }}
        >
          {/* Header Speaker / Subject Tag */}
          <div
            style={{
              color: "#f2a63b",
              fontSize: 18,
              fontWeight: 800,
              letterSpacing: 1.5,
              textTransform: "uppercase",
              marginBottom: 8,
              display: "flex",
              alignItems: "center",
              gap: 8,
              fontFamily: "'Segoe UI', Roboto, Arial, sans-serif",
            }}
          >
            <span>📜</span>
            <span>{props.speakerTag ? String(props.speakerTag).toUpperCase() : (props.actTitle ? String(props.actTitle).toUpperCase() : "CASE INVESTIGATION")}</span>
          </div>

          {/* Karaoke Word-Highlight Subtitle Line */}
          <div
            style={{
              fontFamily: "'Segoe UI', Roboto, -apple-system, sans-serif",
              fontSize: 30,
              lineHeight: 1.45,
              color: "#FFFFFF",
              textAlign: "left",
            }}
          >
            {visibleWords.map((w, wIdx) => {
              const currentGlobalIdx = chunkStartWord + wIdx;
              const isPast = currentGlobalIdx < activeGlobalWordIdx;
              const isActive = currentGlobalIdx === activeGlobalWordIdx;
              
              if (isActive) {
                return (
                  <span
                    key={wIdx}
                    style={{
                      color: "#ffd166",
                      fontWeight: 900,
                      textShadow: "0 0 14px rgba(255, 209, 102, 0.9), 0 2px 4px rgba(0,0,0,0.9)",
                      marginRight: 8,
                      display: "inline-block",
                      transform: "scale(1.05)",
                      transition: "transform 0.1s ease",
                    }}
                  >
                    {w}
                  </span>
                );
              }
              if (isPast) {
                return (
                  <span
                    key={wIdx}
                    style={{
                      color: "#FFFFFF",
                      fontWeight: 700,
                      textShadow: "0 2px 4px rgba(0,0,0,0.8)",
                      marginRight: 8,
                      display: "inline-block",
                    }}
                  >
                    {w}
                  </span>
                );
              }
              return (
                <span
                  key={wIdx}
                  style={{
                    color: "rgba(255, 255, 255, 0.45)",
                    fontWeight: 600,
                    marginRight: 8,
                    display: "inline-block",
                  }}
                >
                  {w}
                </span>
              );
            })}
          </div>
        </div>
      ) : null}
    </AbsoluteFill>
  );
};

// Background cross-fade track (Rule 59 refinement ~11:39): groups
// consecutive scenes sharing the same background into segments, then fades
// the NEW segment in over the previous one only when the image actually
// changes. While a single background is displayed it stays 100% static (no
// opacity/zoom animation) -- only the transition itself fades.
const BACKGROUND_TRANSITION_FRAMES = 15;

const buildBackgroundSegments = (scenes, fadeFrames) => {
  const raw = [];
  let cursor = 0;
  scenes.forEach((s) => {
    const dur = Math.max(1, Math.round(s.durationInFrames ? s.durationInFrames : 1));
    const src = s.background || null;
    const last = raw[raw.length - 1];
    if (last && last.src === src) {
      last.end += dur;
    } else {
      raw.push({ src, start: cursor, end: cursor + dur });
    }
    cursor += dur;
  });
  return raw.map((seg, i) => {
    const next = raw[i + 1];
    const fadeIn = i === 0 ? 0 : Math.min(fadeFrames, seg.end - seg.start);
    const fadeOutExtend = next ? Math.min(fadeFrames, next.end - next.start) : 0;
    return {
      src: seg.src,
      from: seg.start,
      durationInFrames: seg.end - seg.start + fadeOutExtend,
      fadeInFrames: fadeIn,
    };
  });
};

const BackgroundSegment = ({ src, fadeInFrames, durationInFrames }) => {
  const frame = useCurrentFrame();
  const dur = durationInFrames || 300;
  const opacity =
    fadeInFrames > 0
      ? interpolate(frame, [0, fadeInFrames], [0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        })
      : 1;
  // Subtle Ken Burns slow zoom (1.0 -> 1.06) (Rule 95 & YouTube 2026 motion specs)
  const scale = interpolate(frame, [0, dur], [1.0, 1.06], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <AbsoluteFill style={{ opacity, overflow: "hidden" }}>
      {src ? (
        <Img
          src={resolveSrc(src)}
          style={{
            width: "100%",
            height: "100%",
            objectFit: "cover",
            transform: `scale(${scale})`,
            filter: "brightness(1.08) contrast(1.02)",
          }}
        />
      ) : null}
    </AbsoluteFill>
  );
};

// Rule 52.3 (12/08/2026 audit) -- Foreground/"core" track must behave like a
// continuous layer analogous to buildBackgroundSegments, not one fade cycle
// per Director-Plan scene:
//   - Every new Background segment should start with a Foreground already
//     on screen (no bg-only frames) whenever at least one scene inside that
//     background segment has a foreground assigned.
//   - A scene with no foreground of its own inherits ("holds") the previous
//     scene's foreground for as long as they remain inside the SAME
//     background segment, so the fade-in/out cycle only plays once per
//     continuous appearance instead of re-triggering on every scene cut.
//   - A held foreground can never bleed into a new background segment --
//     "1 core chi nen nam tren 1 background" -- so segments are always cut
//     at background-segment boundaries even if the next scene reuses the
//     same foreground path.
// This does NOT fabricate a placeholder image (Rule 70): if a whole
// background segment has zero scenes with a foreground assigned, no
// foreground segment is emitted for it and auditForegroundCoverage below
// will flag the gap for the Director Plan / content layer to fix upstream.
const computeBackgroundSegmentIds = (scenes) => {
  const ids = [];
  let curId = -1;
  let lastSrc;
  scenes.forEach((s, i) => {
    const src = s.background || null;
    if (i === 0 || src !== lastSrc) {
      curId += 1;
    }
    ids.push(curId);
    lastSrc = src;
  });
  return ids;
};

const buildForegroundSegments = (scenes, defaultFadeFrames) => {
  const bgIds = computeBackgroundSegmentIds(scenes);
  const raw = [];
  let cursor = 0;
  scenes.forEach((s, i) => {
    const dur = Math.max(1, Math.round(s.durationInFrames ? s.durationInFrames : 1));
    const bgId = bgIds[i];
    const explicitFg = s.foreground || null;
    const last = raw[raw.length - 1];
    const heldFg = last && last.bgId === bgId ? last.src : null;
    const effectiveFg = explicitFg || heldFg;
    if (last && last.bgId === bgId && last.src === effectiveFg) {
      last.end += dur;
    } else {
      raw.push({
        src: effectiveFg,
        bgId,
        start: cursor,
        end: cursor + dur,
        fadeFrames: s.foregroundFadeFrames ? s.foregroundFadeFrames : defaultFadeFrames,
        position: s.foregroundPosition,
      });
    }
    cursor += dur;
  });
  return raw.filter((seg) => seg.src);
};

// Audit helper (console-only, Rule 27/70/74): logs background segments that
// end up with zero or more-than-two foreground segments so the gap/overload
// is visible during render instead of silently under- or over-populating
// core frames.
const _auditedForegroundCoverageKeys = new Set();
const auditForegroundCoverage = (scenes, foregroundSegments) => {
  // Render runs this component body once per output frame -- dedupe by
  // scene shape so this only actually logs once per distinct episode.
  const dedupeKey = JSON.stringify(scenes.map((s) => [s.background, s.foreground, s.durationInFrames]));
  if (_auditedForegroundCoverageKeys.has(dedupeKey)) return;
  _auditedForegroundCoverageKeys.add(dedupeKey);
  const bgIds = computeBackgroundSegmentIds(scenes);
  const maxBgId = bgIds.length ? bgIds[bgIds.length - 1] : -1;
  for (let bgId = 0; bgId <= maxBgId; bgId += 1) {
    const count = foregroundSegments.filter((seg) => seg.bgId === bgId).length;
    if (count === 0) {
      console.warn(
        "[Rule 52.3 audit] background segment " + bgId + " has NO foreground/core -- every background should show a core (Rule 74)."
      );
    } else if (count > 2) {
      console.warn(
        "[Rule 52.3 audit] background segment " + bgId + " has " + count + " distinct foregrounds -- rule caps this at 2 cores per background."
      );
    }
  }
};


const ACT_DEFAULT_TITLES = [
  "ACT I // THE HOOK & EXPOSURE",
  "ACT II // THE ARCHITECTURE OF POWER",
  "ACT III // THE HIDDEN MECHANISM",
  "ACT IV // THE CRACK IN THE ILLUSION",
  "ACT V // THE AFTERMATH & RECKONING",
];

const TopProgressBar = ({ scenes, currentFrame, totalFrames }) => {
  const safeTotal = Math.max(1, totalFrames || 1);
  const safeFrame = Math.max(0, currentFrame);

  let cursor = 0;
  let currentSceneIdx = 0;
  for (let i = 0; i < scenes.length; i++) {
    const dur = Math.max(1, Math.round(scenes[i].durationInFrames || 1));
    if (safeFrame >= cursor && safeFrame < cursor + dur) {
      currentSceneIdx = i;
      break;
    }
    cursor += dur;
  }

  const totalScenes = Math.max(1, scenes.length);
  const sceneProgress = currentSceneIdx / totalScenes;
  let activeActIdx = 0;
  if (sceneProgress < 0.15) activeActIdx = 0;
  else if (sceneProgress < 0.40) activeActIdx = 1;
  else if (sceneProgress < 0.65) activeActIdx = 2;
  else if (sceneProgress < 0.85) activeActIdx = 3;
  else activeActIdx = 4;

  const currentScene = scenes[currentSceneIdx] || {};
  const currentAct = currentScene.actTitle || ACT_DEFAULT_TITLES[activeActIdx];
  const actBoundaries = [0.15, 0.40, 0.65, 0.85, 1.0];

  return (
    <div style={{ position: "absolute", top: 0, left: 0, width: "100%", zIndex: 40, pointerEvents: "none" }}>
      {/* 5-segment Progress Bar Tracks */}
      <div
        style={{
          width: "100%",
          display: "flex",
          gap: 4,
          padding: "0 2px",
          backgroundColor: "rgba(0, 0, 0, 0.6)",
          boxSizing: "border-box",
        }}
      >
        {actBoundaries.map((pctEnd, idx) => {
          const pctStart = idx === 0 ? 0 : actBoundaries[idx - 1];
          const startFrame = pctStart * safeTotal;
          const endFrame = pctEnd * safeTotal;
          const segDuration = Math.max(1, endFrame - startFrame);

          let segFill = 0;
          if (safeFrame >= endFrame) {
            segFill = 1;
          } else if (safeFrame <= startFrame) {
            segFill = 0;
          } else {
            segFill = (safeFrame - startFrame) / segDuration;
          }

          const isActActive = idx === activeActIdx;

          return (
            <div
              key={idx}
              style={{
                flex: pctEnd - pctStart,
                height: 6,
                backgroundColor: "rgba(255, 255, 255, 0.14)",
                borderRadius: 2,
                overflow: "hidden",
                boxShadow: isActActive ? "0 0 6px rgba(242, 166, 59, 0.35)" : "none",
              }}
            >
              <div
                style={{
                  width: `${Math.min(100, Math.max(0, segFill * 100))}%`,
                  height: "100%",
                  background: isActActive
                    ? "linear-gradient(90deg, #f2a63b 0%, #ffd166 100%)"
                    : "linear-gradient(90deg, rgba(242, 166, 59, 0.8) 0%, rgba(255, 209, 102, 0.8) 100%)",
                  boxShadow: isActActive ? "0 0 10px #ffd166" : "none",
                }}
              />
            </div>
          );
        })}
      </div>
      {/* Active Act Badge */}
      <div
        style={{
          position: "absolute",
          top: 18,
          left: 50,
          display: "flex",
          alignItems: "center",
          gap: 10,
          padding: "7px 18px",
          backgroundColor: "rgba(10, 15, 24, 0.88)",
          border: "1.5px solid rgba(242, 166, 59, 0.45)",
          borderRadius: 8,
          backdropFilter: "blur(10px)",
          boxShadow: "0 6px 20px rgba(0,0,0,0.6)",
        }}
      >
        <div
          style={{
            width: 8,
            height: 8,
            borderRadius: "50%",
            backgroundColor: "#f2a63b",
            boxShadow: "0 0 8px #f2a63b",
          }}
        />
        <span
          style={{
            color: "#ffd166",
            fontSize: 13,
            fontWeight: 800,
            letterSpacing: 1.5,
            fontFamily: "'Segoe UI', Roboto, sans-serif",
            textTransform: "uppercase",
          }}
        >
          {currentAct}
        </span>
      </div>
    </div>
  );
};

const CinematicVignette = () => (
  <div
    style={{
      position: "absolute",
      top: 0,
      left: 0,
      width: "100%",
      height: "100%",
      boxShadow: "inset 0 0 130px rgba(0, 0, 0, 0.70)",
      zIndex: 10,
      pointerEvents: "none",
    }}
  />
);

const CinematicOverlay = () => (
  <AbsoluteFill style={{ zIndex: 20, pointerEvents: "none" }}>
    {/* Subtle film grain via SVG fractal noise */}
    <svg style={{ position: "absolute", width: "100%", height: "100%", opacity: 0.045, mixBlendMode: "overlay" }}>
      <filter id="cinematicGrain">
        <feTurbulence type="fractalNoise" baseFrequency="0.75" numOctaves={3} stitchTiles="stitch" />
        <feColorMatrix type="matrix" values="0 0 0 0 1  0 0 0 0 1  0 0 0 0 1  0 0 0 1 0" />
      </filter>
      <rect width="100%" height="100%" filter="url(#cinematicGrain)" />
    </svg>
    {/* Cinematic soft-light tone grading */}
    <div
      style={{
        position: "absolute",
        width: "100%",
        height: "100%",
        background: "linear-gradient(135deg, rgba(20, 28, 45, 0.08) 0%, rgba(45, 25, 15, 0.06) 100%)",
        mixBlendMode: "soft-light",
      }}
    />
  </AbsoluteFill>
);

// === CINEMATIC CAMERA SYSTEM (Rule 122 & Rule 128) ===

export const computeCameraTransform = (
  cameraMovement: string | undefined,
  tensionLevel: string | undefined,
  sceneRelFrame: number,
  sceneDurationInFrames: number
): string => {
  const dur = Math.max(1, sceneDurationInFrames);
  const f = Math.max(0, Math.min(sceneRelFrame, dur));
  const mov = cameraMovement || "slow_push_in";

  if (mov === "snap_zoom") {
    // Sharp punch-in within first 8 frames (0.27s), then subtle hold creep
    const scale = interpolate(f, [0, 8, dur], [1.0, 1.20, 1.23], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.bezier(0.16, 1, 0.3, 1),
    });
    return `scale(${scale})`;
  }

  if (mov === "slow_push_in") {
    const maxScale = tensionLevel === "high" ? 1.14 : 1.08;
    const scale = interpolate(f, [0, dur], [1.0, maxScale], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    return `scale(${scale})`;
  }

  if (mov === "slow_pull_out") {
    const scale = interpolate(f, [0, dur], [1.12, 1.0], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    return `scale(${scale})`;
  }

  if (mov === "cinematic_pan") {
    // Subtle horizontal pan (-35px to +35px) with 1.06 base scale to prevent edge bleed
    const panX = interpolate(f, [0, dur], [-35, 35], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    return `scale(1.06) translateX(${panX}px)`;
  }

  if (mov === "macro_tilt") {
    // Vertical tilt (-22px to +22px) with 1.06 base scale
    const tiltY = interpolate(f, [0, dur], [-22, 22], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    return `scale(1.06) translateY(${tiltY}px)`;
  }

  if (mov === "handheld_shake") {
    // High-tension procedural camera jitter with base scale 1.05
    const intensity = tensionLevel === "high" ? 5.5 : 3.0;
    const shakeX = Math.sin(f * 0.45) * intensity + Math.cos(f * 0.8) * (intensity * 0.5);
    const shakeY = Math.cos(f * 0.35) * (intensity * 0.8) + Math.sin(f * 0.7) * (intensity * 0.4);
    const scale = interpolate(f, [0, dur], [1.04, 1.07], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    return `scale(${scale}) translate(${shakeX.toFixed(2)}px, ${shakeY.toFixed(2)}px)`;
  }

  // Fallback subtle Ken Burns slow zoom
  const scale = interpolate(f, [0, dur], [1.0, 1.06], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return `scale(${scale})`;
};

export const getCurrentSceneInfo = (scenes: any[], globalFrame: number) => {
  let acc = 0;
  for (let i = 0; i < scenes.length; i++) {
    const s = scenes[i];
    const dur = Math.max(1, Math.round(s.durationInFrames ? s.durationInFrames : 1));
    if (globalFrame >= acc && globalFrame < acc + dur) {
      return {
        scene: s,
        index: i,
        relFrame: globalFrame - acc,
        durationInFrames: dur,
      };
    }
    acc += dur;
  }
  if (scenes.length > 0) {
    const last = scenes[scenes.length - 1];
    const dur = Math.max(1, Math.round(last.durationInFrames ? last.durationInFrames : 1));
    return {
      scene: last,
      index: scenes.length - 1,
      relFrame: Math.max(0, globalFrame - Math.max(0, acc - dur)),
      durationInFrames: dur,
    };
  }
  return null;
};

export const TwoLayerEpisode = (props) => {
  const scenes = props.scenes ? props.scenes : [];
  const backgroundFadeFrames = props.backgroundFadeFrames
    ? props.backgroundFadeFrames
    : BACKGROUND_TRANSITION_FRAMES;
  const backgroundSegments = buildBackgroundSegments(scenes, backgroundFadeFrames);
  const foregroundSegments = buildForegroundSegments(scenes, 15);
  if (typeof console !== "undefined" && console.warn) {
    auditForegroundCoverage(scenes, foregroundSegments);
  }
  const cfg = useVideoConfig();
  const width = cfg.width;
  const height = cfg.height;
  const currentFrame = useCurrentFrame();

  const currentSceneInfo = getCurrentSceneInfo(scenes, currentFrame);
  const cameraTransform = currentSceneInfo
    ? computeCameraTransform(
        currentSceneInfo.scene.cameraMovement || (currentSceneInfo.scene.camera ? currentSceneInfo.scene.camera.movement : undefined),
        currentSceneInfo.scene.tensionLevel || (currentSceneInfo.scene.camera ? currentSceneInfo.scene.camera.tension_level : undefined),
        currentSceneInfo.relFrame,
        currentSceneInfo.durationInFrames
      )
    : "scale(1.0)";

  let cursor = 0;
  const items = scenes.map((s, i) => {
    const from = cursor;
    const dur = Math.max(1, Math.round(s.durationInFrames ? s.durationInFrames : 1));
    cursor += dur;
    return (
      <Sequence key={i} from={from} durationInFrames={dur} name={`scene-${i + 1}`}>
        <TwoLayerScene
          background={s.background}
          showBackground={false}
          showForeground={false}
          foreground={s.foreground}
          foregroundPosition={s.foregroundPosition}
          foregroundFadeFrames={s.foregroundFadeFrames}
          caption={s.caption}
          narration={s.narration}
          safeZone={s.safeZone}
          statValue={s.statValue}
          statLabel={s.statLabel}
          speakerTag={s.speakerTag}
          subtitles={s.subtitles || s.words}
          cameraMovement={s.cameraMovement || (s.camera ? s.camera.movement : undefined)}
          tensionLevel={s.tensionLevel || (s.camera ? s.camera.tension_level : undefined)}
          bgClusterId={s.bgClusterId || s.bg_cluster_id}
          forensicOverlay={s.forensicOverlay || s.forensic_overlay}
          stampBadge={s.stampBadge || s.stamp_badge}
        />
      </Sequence>
    );
  });

  const audioMaster = props.audioMaster ? props.audioMaster : null;
  const bgmFile = props.bgmFile ? props.bgmFile : null;
  const bgmVolume = props.bgmVolume !== undefined ? props.bgmVolume : 0.15;

  return (
    <AbsoluteFill style={{ backgroundColor: INK }}>
      {audioMaster ? (
        <Audio src={resolveSrc(audioMaster)} volume={1.0} />
      ) : null}
      {bgmFile ? (
        <Audio src={resolveSrc(bgmFile)} volume={bgmVolume} />
      ) : null}

      {/* Dynamic Cinematic Camera Container (Rule 122 & Rule 128) */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          transform: cameraTransform,
          transformOrigin: "center center",
          willChange: "transform",
        }}
      >
        {backgroundSegments.map((seg, i) => (
          <Sequence
            key={`bgseg-${i}`}
            from={seg.from}
            durationInFrames={seg.durationInFrames}
            name={`bg-segment-${i + 1}`}
          >
            <BackgroundSegment
              src={seg.src}
              fadeInFrames={seg.fadeInFrames}
              durationInFrames={seg.durationInFrames}
            />
          </Sequence>
        ))}
        {foregroundSegments.map((seg, i) => (
          <Sequence
            key={`fgseg-${i}`}
            from={seg.start}
            durationInFrames={seg.end - seg.start}
            name={`fg-segment-${i + 1}`}
          >
            <ForegroundLayer
              src={seg.src}
              position={seg.position}
              fadeFrames={seg.fadeFrames}
              durationInFrames={seg.end - seg.start}
              width={width}
              height={height}
            />
          </Sequence>
        ))}
      </div>

      {/* Subtitles, Stat Cards, and Fixed UI Overlays */}
      {items}
      <CinematicVignette />
      <CinematicOverlay />
      <TopProgressBar scenes={scenes} currentFrame={currentFrame} totalFrames={totalSceneFrames(scenes)} />
    </AbsoluteFill>
  );
};

const totalSceneFrames = (scenes) =>
  (scenes || []).reduce((sum, s) => sum + Math.max(1, Math.round(s.durationInFrames ? s.durationInFrames : 1)), 0);

const RemotionRoot = () => {
  return (
    <>
      <Composition
        id="SceneCard"
        component={SceneCard}
        durationInFrames={150}
        fps={30}
        width={1536}
        height={864}
        defaultProps={{
          bgFile: "bg_rise.jpg",
          statValue: "$619B",
          statLabel: "TOTAL DEBT AT FILING",
          storyBeat: "collapse",
          hasChartInBg: false,
          safeZone: "top_left",
          accentOverride: null,
        }}
        calculateMetadata={({ props }: { props: any }) => {
          return {
            durationInFrames: props.durationInFrames ? props.durationInFrames : 150,
            width: props.width ? props.width : 1536,
            height: props.height ? props.height : 864,
          };
        }}
      />
      <Composition
        id="DataStoryTest"
        component={DataStoryTest}
        durationInFrames={600}
        fps={30}
        width={1536}
        height={864}
        defaultProps={{}}
      />
      <Composition
        id="FullStory"
        component={FullStory}
        durationInFrames={14101}
        fps={30}
        width={1536}
        height={864}
        defaultProps={{}}
      />
      {/* Generic pipeline-wide composition for the new 2-layer architecture.
          Not tied to any one episode -- all content comes from `scenes`,
          built by scripts/build_remotion_props.py. Render with:
            npx remotion render src/index.tsx TwoLayerEpisode out.mp4 \
              --props=/var/vf/episodes/<id>/remotion_props.json */}
      <Composition
        id="TwoLayerEpisode"
        component={TwoLayerEpisode}
        durationInFrames={300}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{ scenes: [] }}
        calculateMetadata={({ props }: { props: any }) => {
          const fps = props.fps ? props.fps : 30;
          const width = props.width ? props.width : 1920;
          const height = props.height ? props.height : 1080;
          const total = totalSceneFrames(props.scenes);
          return {
            durationInFrames: total > 0 ? total : 300,
            fps,
            width,
            height,
          };
        }}
      />
    </>
  );
};

registerRoot(RemotionRoot);
