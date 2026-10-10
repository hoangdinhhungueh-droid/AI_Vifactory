import React, { useEffect, useState } from "react";
import {
  AbsoluteFill,
  Audio,
  Composition,
  Easing,
  Img,
  Sequence,
  Video,
  continueRender,
  delayRender,
  interpolate,
  registerRoot,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";
import {
  VoxOverlayLayer,
  VoxAtmosphericLighting,
  VoxParallaxLayer,
  VoxKineticTypography,
  VoxSourceCredit,
  VoxDisclosureBadge,
  VoxConnectingVectors,
  useStopMotion,
  PaperStatCard,
  PushThroughTransitionOverlay,
  VoxBuildOnStage,
  VoxPaperBackdrop,
} from "./components/vox";
import { VoxKineticHeadline } from "./components/vox/VoxKineticHeadline";
import {
  ProceduralMotionFollower,
  ProceduralMarkerSweep,
  PhysicalStampSlam,
  OdometerRollup,
  evaluateMotionPath,
} from "./components/kinetics";
import { WordTimestamp } from "./types";

const INK = "#05090d";
const LIGHT = "#ffffff";

export const resolveSrc = (src?: string | null): string | null => {
  if (!src) return null;
  const trimmed = typeof src === "string" ? src.trim() : "";
  if (!trimmed) return null;
  if (/^(https?:\/\/|data:|blob:)/i.test(trimmed)) {
    return trimmed;
  }
  if (
    typeof window !== "undefined" &&
    (window as any).remotion_staticBase &&
    trimmed.startsWith((window as any).remotion_staticBase)
  ) {
    return trimmed;
  }
  if (trimmed.startsWith("/public/")) {
    return trimmed;
  }
  const clean = trimmed.replace(/^\/?public\//i, "").replace(/^\/+/, "");
  if (!clean) return null;
  try {
    return staticFile(clean);
  } catch (_e) {
    return trimmed.startsWith("/") ? trimmed : `/${clean}`;
  }
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
// Optimized VOX Paper Sticker Filter (Pillar 2 & Rule 120 Anti-OOM/CPU Acceleration):
// White sticker border is pre-baked into PNG alpha channel via Python PIL (optimize_props_assets).
// Single-pass directional paper drop-shadow replaces 10 stacked CPU Gaussian blur convolutions.
const STICKER_BORDER_FILTER =
  "drop-shadow(0 12px 18px rgba(45, 30, 15, 0.38)) brightness(1.06) contrast(1.16) saturate(1.08)";
const STICKER_CONTAINER_FILTER = undefined;

const ForegroundLayer = ({
  src,
  position,
  fadeFrames,
  durationInFrames,
  width,
  height,
  cadence = "cutout",
  motionPath,
}: any) => {
  const frame = useCurrentFrame();
  const { qFrame, dx: smDx, dy: smDy, dRot: smDRot } = useStopMotion(
    12,
    1.15,
    position === "right" ? 23 : 11
  );
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

  // If explicit vector motion path is provided (Parametric Trajectory Spline)
  if (motionPath && Array.isArray(motionPath) && motionPath.length > 0) {
    const { xPct, yPct, scale, rotDeg, opacity: pathOpacity, zDepth } = evaluateMotionPath(motionPath, qFrame, 30);
    const targetW = Math.round(width * 0.42 * zDepth);
    const targetH = Math.round(height * 0.78 * zDepth);
    const finalOpacity = Math.min(opacity, pathOpacity);

    // Documentary Split Rule: Clamp character to side column to guarantee zero collision with center/opposite evidence
    const clampedXPct = position === "right" ? Math.max(68, xPct) : position === "left" ? Math.min(32, xPct) : xPct;

    return (
      <div
        style={{
          position: "absolute",
          left: `${clampedXPct}%`,
          top: `${yPct}%`,
          width: targetW,
          height: targetH,
          opacity: finalOpacity,
          transform: `translate(calc(-50% + ${smDx.toFixed(1)}px), calc(-50% + ${smDy.toFixed(1)}px)) scale(${scale.toFixed(3)}) rotate(${(rotDeg + smDRot).toFixed(2)}deg)`,
          filter: STICKER_CONTAINER_FILTER,
          zIndex: Math.round(15 * zDepth),
          pointerEvents: "none",
        }}
      >
        <div
          style={{
            position: "absolute",
            bottom: -10,
            left: "15%",
            width: "70%",
            height: 24,
            borderRadius: "50%",
            background: "radial-gradient(ellipse at center, rgba(45, 30, 15, 0.55) 0%, rgba(45, 30, 15, 0.25) 45%, rgba(0, 0, 0, 0) 70%)",
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
            filter: STICKER_BORDER_FILTER,
          }}
        />
      </div>
    );
  }

  // Fallback to organic paper placement with 12fps stop-motion micro-life (No dead freeze)
  const hasGrid = position === "left" || position === "right";

  if (!hasGrid) {
    const pushScale = interpolate(qFrame, [0, durationInFrames || 180], [1.0, 1.04], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    return (
      <AbsoluteFill style={{ opacity, transform: `scale(${pushScale})`, transformOrigin: "center center" }}>
        <Img src={resolveSrc(src)} style={{ width: "100%", height: "100%", objectFit: "contain", filter: STICKER_BORDER_FILTER }} />
      </AbsoluteFill>
    );
  }

  const cell = computeForegroundCell(width, height, position, aspect);

  // Stage 3: Tactile organic paper placement drop (frames 15-35, calibrated to duration)
  const dropStart = Math.min(24, Math.max(0, Math.round((durationInFrames || 180) * 0.12)));
  const relDrop = Math.max(0, frame - dropStart);
  const dropProgress = interpolate(relDrop, [0, 14], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });
  const initialTranslateY = (1 - dropProgress) * -42;
  const initialRotateDeg = (1 - dropProgress) * (position === "right" ? -3.2 : 3.2);

  // 12fps Stepped Stop-Motion micro-life after landing (Vox tactile collage aesthetic)
  const landedWeight = relDrop > 14 ? 1 : 0;
  const liveSwayX = smDx * landedWeight;
  const liveSwayY = smDy * landedWeight;
  const liveRot = smDRot * landedWeight;
  const liveScale = 1.0 + Math.sin(qFrame * 0.03) * 0.008 * landedWeight;

  const translateY = initialTranslateY + liveSwayY;
  const rotateDeg = initialRotateDeg + liveRot;
  const scale = (1.12 - 0.12 * dropProgress) * liveScale;

  const dropOpacity = frame < dropStart ? 0 : interpolate(relDrop, [0, 5], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const finalOpacity = Math.min(opacity, dropOpacity);

  return (
    <div
      style={{
        position: "absolute",
        left: cell.left + liveSwayX,
        top: cell.top,
        width: cell.width,
        height: cell.height,
        opacity: finalOpacity,
        transform: `translateY(${translateY.toFixed(1)}px) rotate(${rotateDeg.toFixed(2)}deg) scale(${scale.toFixed(3)})`,
        filter: STICKER_CONTAINER_FILTER,
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
          background: "radial-gradient(ellipse at center, rgba(45, 30, 15, 0.55) 0%, rgba(45, 30, 15, 0.25) 45%, rgba(0, 0, 0, 0) 70%)",
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
          filter: STICKER_BORDER_FILTER,
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

// === VOX-STYLE EXPLANATORY MOTION ENGINE (Rule 122 & Rule 128) ===
// Components modularized into src/components/vox/ (VoxOverlayLayer, VoxDocumentHighlight, VoxKineticCounter, VoxCausalFlowchart, VoxTacticalMap)

const ForensicStampBadge = ({
  badge,
  isLeft,
  hasStatCard,
  durationInFrames = 180,
  slamFrame,
}: {
  badge: string;
  isLeft?: boolean;
  hasStatCard?: boolean;
  durationInFrames?: number;
  slamFrame?: number;
}) => {
  const frame = useCurrentFrame();
  const cfg = useVideoConfig();
  const dur = Math.max(1, durationInFrames || cfg.durationInFrames || 180);
  const targetSlam = slamFrame !== undefined
    ? slamFrame
    : Math.min(180, Math.max(25, Math.round(dur * 0.65)));

  const relSlam = frame - targetSlam;
  if (relSlam < 0) return null;

  // Dynamic Stamp Slam physics: rapid scale drop from 2.4 down to 0.96 with bounce to 1.0
  const scale = spring({
    frame: relSlam,
    fps: cfg.fps || 30,
    config: { damping: 9, mass: 0.35, stiffness: 160 },
    from: 2.4,
    to: 1.0,
  });
  const opacity = interpolate(relSlam, [0, 2], [0.3, 0.92], { extrapolateLeft: "clamp", extrapolateRight: "clamp" });
  const bUp = (badge || "").toUpperCase();
  const isAlert = ["基準値超過", "EXCEEDED", "超過", "VOID", "CRITICAL", "ALERT", "漏洩", "違反", "BREACH"].some((k) => bUp.includes(k));
  const isAuth = ["未回答", "記録なし", "確認できず", "EVIDENCE", "RESTRICTED", "AUDIT", "CONFIDENTIAL", "不明", "極秘"].some((k) => bUp.includes(k));

  const inkColor = isAlert ? "#991b1b" : isAuth ? "#92400e" : "#1e3a8a";
  const paperBg = "rgba(250, 246, 236, 0.92)";

  return (
    <div
      style={{
        position: "absolute",
        top: hasStatCard ? 195 : 70,
        left: isLeft ? "auto" : 78,
        right: isLeft ? 78 : "auto",
        transform: `scale(${scale}) rotate(-7.5deg)`,
        opacity,
        zIndex: 32,
        border: `4px double ${inkColor}`,
        borderRadius: 3,
        padding: "6px 18px",
        backgroundColor: paperBg,
        boxShadow: "0 6px 16px rgba(35, 22, 10, 0.35)",
        fontFamily: "'Courier Prime', 'Special Elite', 'Courier New', Courier, monospace",
        textTransform: "uppercase",
        display: "flex",
        alignItems: "center",
        gap: 8,
        pointerEvents: "none",
      }}
    >
      <span style={{ color: inkColor, fontSize: 13, fontWeight: 900, letterSpacing: 1.5 }}>[STAMP]</span>
      <span style={{ color: inkColor, fontSize: 18, fontWeight: 900, letterSpacing: 2.2 }}>{badge}</span>
    </div>
  );
};


// Rule 136 (Zero-Asset-Leak & Pure Beat Header Mandate)
const cleanSpeakerTag = (rawTag: any, actTitle: any): string => {
  const str = rawTag ? String(rawTag).trim() : "";
  if (
    !str ||
    str.includes(".png") ||
    str.includes(".jpg") ||
    str.startsWith("fg_") ||
    str.startsWith("bg_") ||
    str.startsWith("ARCHIVE")
  ) {
    if (actTitle && !String(actTitle).includes(".png")) {
      return String(actTitle).toUpperCase();
    }
    return "BEAT 1: CASE INVESTIGATION";
  }
  return str.toUpperCase();
};

export const TwoLayerScene = (props) => {
  const background = props.background;
  const showBackground = props.showBackground === false ? false : true;
  const showForeground = props.showForeground === false ? false : true;
  const showOverlay = props.showOverlay === false ? false : true;
  const showSupportingCutouts =
    props.showSupportingCutouts !== undefined
      ? Boolean(props.showSupportingCutouts)
      : showForeground;
  const foreground = props.foreground;
  const foregroundPosition = props.foregroundPosition;
  const caption = props.caption || "";
  const safeZone = props.safeZone ? props.safeZone : "none";
  const fadeFrames = props.foregroundFadeFrames ? props.foregroundFadeFrames : 15;
  const statValue = props.statValue;
  const statLabel = props.statLabel;
  const forensicOverlay = props.forensicOverlay;
  const stampBadge = props.stampBadge;
  const sourceCredit = props.sourceCredit || props.source_credit;
  const disclosureBadge = props.disclosureBadge;
  const actTitle = props.actTitle;
  const connection = props.connection;
  const connections = props.connections;
  const radiatingConnections = props.radiatingConnections || props.radiating_connections;
  const supportingCutouts = props.supportingCutouts || props.supporting_cutouts;
  const editorialHeadline = props.editorialHeadline || props.editorial_headline;

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

  // Transition out / Entrance flicker (Tactile Stop-Motion Cut)
  const transitionOut = props.transition_out || props.transitionOut;
  let entranceOpacity = 1;
  if (transitionOut === "stop_motion_flicker_cut") {
    entranceOpacity = interpolate(
      frame,
      [0, 1, 2, 3, 4],
      [0, 1, 0.3, 1, 1],
      { extrapolateRight: "clamp", extrapolateLeft: "clamp" }
    );
  } else if (transitionOut === "crossfade_short") {
    entranceOpacity = interpolate(frame, [0, 6], [0, 1], {
      extrapolateRight: "clamp",
      extrapolateLeft: "clamp",
    });
  }

  // Floating Minimalist Subtitle: Intelligent Auto-Dodge Calculation
  const hasForeground = Boolean(foreground);
  const fgPos = foregroundPosition || "left";
  const hasFgLeft = hasForeground && fgPos === "left";
  const hasFgRight = hasForeground && fgPos === "right";

  const rawOverlay = forensicOverlay;
  const overlayObj = typeof rawOverlay === "object" ? rawOverlay : null;
  const ovLayout = overlayObj?.layout;
  const ovType = overlayObj?.type;
  const isFullBleedOverlay =
    ovLayout === "full_bleed_focus" ||
    ovLayout === "fullscreen_dossier" ||
    (ovType === "threshold_ratio" && (!ovLayout || ovLayout === "full_bleed_focus"));
  const isOverlayRight = ovLayout === "split_right" || (!ovLayout && hasFgLeft);
  const isOverlayLeft = ovLayout === "split_left" || (!ovLayout && hasFgRight);

  let subtitleContainerStyle: React.CSSProperties = {
    position: "absolute",
    zIndex: 25,
    pointerEvents: "none",
    display: "flex",
    flexDirection: "column",
  };

  let subtitleTextAlign: "left" | "center" | "right" = "center";
  let subtitleFontSize = (isLeft || isRight) ? 26 : 28;

  if (isFullBleedOverlay) {
    // Under full-bleed evidence (e.g. VoxThresholdRatio 6x4 grid), stay in bottom band
    subtitleContainerStyle = {
      ...subtitleContainerStyle,
      bottom: 22,
      left: "14%",
      right: "14%",
      maxWidth: "72%",
      alignItems: "center",
    };
    subtitleTextAlign = "center";
    subtitleFontSize = 24;
  } else if ((hasFgLeft && isOverlayRight) || (hasFgRight && isOverlayLeft)) {
    // Both sides occupied -> Grounded narrow center
    subtitleContainerStyle = {
      ...subtitleContainerStyle,
      bottom: 20,
      left: "22%",
      right: "22%",
      maxWidth: "56%",
      alignItems: "center",
    };
    subtitleTextAlign = "center";
    subtitleFontSize = 23;
  } else if (hasFgLeft || isOverlayLeft) {
    // Left side occupied -> Auto-dodge to Right side
    subtitleContainerStyle = {
      ...subtitleContainerStyle,
      bottom: 34,
      left: "50%",
      right: 70,
      maxWidth: "46%",
      alignItems: "flex-start",
    };
    subtitleTextAlign = "left";
    subtitleFontSize = 26;
  } else if (hasFgRight || isOverlayRight) {
    // Right side occupied -> Auto-dodge to Left side
    subtitleContainerStyle = {
      ...subtitleContainerStyle,
      bottom: 34,
      left: 70,
      right: "50%",
      maxWidth: "46%",
      alignItems: "flex-start",
    };
    subtitleTextAlign = "left";
    subtitleFontSize = 26;
  } else {
    // Clean screen -> Lower center floating
    subtitleContainerStyle = {
      ...subtitleContainerStyle,
      bottom: 42,
      left: "16%",
      right: "16%",
      maxWidth: "68%",
      alignItems: "center",
    };
    subtitleTextAlign = "center";
    subtitleFontSize = 28;
  }

  const rawSpeakerTag = cleanSpeakerTag(props.speakerTag, props.actTitle);
  const showSpeakerTag = Boolean(rawSpeakerTag && rawSpeakerTag !== "BEAT 1: CASE INVESTIGATION");

    return (
    <AbsoluteFill style={{ backgroundColor: "transparent", opacity: entranceOpacity }}>
      {showBackground ? (
        <BackgroundSegment
          src={background}
          paperTheme={props.papercraft_theme || props.paperTheme || "parchment"}
          fadeInFrames={0}
          durationInFrames={durationInFrames}
          hasForeground={Boolean(foreground || forensicOverlay || statValue)}
        />
      ) : null}

      {showForeground && foreground ? (
        <ForegroundLayer
          src={foreground}
          position={foregroundPosition}
          fadeFrames={fadeFrames}
          durationInFrames={durationInFrames}
          width={width}
          height={height}
          cadence={props.cadence}
        />
      ) : null}

      {/* Top Safe-Zone Tactile Paper Stat Card (Zero Emoji / Zero Digital HUD) */}
      {showOverlay && statValue ? (
        <PaperStatCard
          statValue={String(statValue)}
          statLabel={statLabel ? String(statLabel) : undefined}
          isLeft={isLeft}
          dropFrame={10}
          top={54}
        />
      ) : null}

      {/* Vox-Style Explanatory Motion Engine (Rule 122 & Rule 128) */}
      {showOverlay ? (
        <VoxOverlayLayer forensicOverlay={forensicOverlay} isLeft={isLeft} />
      ) : null}

      {/* Forensic Stamp Slam Badge (Rule 122 Acting & Evidence Props) */}
      {showOverlay && stampBadge ? (
        <ForensicStampBadge
          badge={String(stampBadge)}
          isLeft={isLeft}
          hasStatCard={Boolean(statValue)}
          durationInFrames={durationInFrames}
        />
      ) : null}

      {/* Vox Kinetic Typography (Word-Level Whisper Keywords Burst) */}
      {showOverlay && hasExactSubtitles ? (
        <VoxKineticTypography words={subtitles as WordTimestamp[]} />
      ) : null}

      {/* Journalistic Source Credit Bar (Rule 130 Causal Integrity) */}
      {sourceCredit ? (
        typeof sourceCredit === "string" ? (
          <VoxSourceCredit
            source={sourceCredit}
            position={hasFgLeft ? "bottom_right" : "bottom_left"}
            styleType={props.creditStyle || props.credit_style || "full"}
          />
        ) : (
          <VoxSourceCredit 
            {...sourceCredit} 
            styleType={(sourceCredit as any).styleType || props.creditStyle || props.credit_style || "full"}
          />
        )
      ) : null}

      {/* Statutory Visual Disclosure Badge (AI Recreation / Reenactment) */}
      {Boolean(disclosureBadge && disclosureBadge !== false) ? (
        <VoxDisclosureBadge
          text={typeof disclosureBadge === "string" ? disclosureBadge : "※イメージ映像・再現"}
          position={sourceCredit ? "top_right" : "bottom_right"}
          isAiGenerated={Boolean(foreground || background)}
        />
      ) : null}

      {/* Vox Curved Bezier Connecting Vectors & Red Yarn Strings (Rule 122 & Vox Explainer Motion) */}
      {showOverlay && (connection || connections || radiatingConnections) ? (
        <VoxConnectingVectors
          connections={[
            ...(connection ? [connection] : []),
            ...(Array.isArray(connections) ? connections : []),
            ...(Array.isArray(radiatingConnections) ? radiatingConnections : []),
          ]}
          width={width}
          height={height}
        />
      ) : null}

      {/* Supporting Cutouts & Micro-Evidence Pins (Staggered Spring Physics & Tactile Tape Labels) */}
      {showSupportingCutouts && supportingCutouts && Array.isArray(supportingCutouts) ? (
        supportingCutouts.map((cutout: any, cIdx: number) => {
          const delay = cutout.dropFrame || cutout.delayFrames || (cIdx * 8 + 6);
          const cutoutSpring = spring({
            frame: Math.max(0, frame - delay),
            fps: cfg.fps || 30,
            config: { damping: 14, stiffness: 120, mass: 0.8 },
          });
          const targetRot = cutout.rotation ?? ((cIdx % 2 === 0 ? -3.5 : 3.5) * (cIdx + 1));
          const rot = Number(interpolate(cutoutSpring, [0, 1], [targetRot - 10, targetRot]));
          const scale = Number(interpolate(cutoutSpring, [0, 1], [1.14, 1]));
          const opacity = Number(interpolate(cutoutSpring, [0, 0.3, 1], [0, 0.85, 1]));
          const left = cutout.xPct ?? (isLeft ? 65 + cIdx * 12 : 20 + cIdx * 12);
          const top = cutout.yPct ?? (40 + cIdx * 15);
          return (
            <div
              key={`supp-cutout-${cIdx}`}
              style={{
                position: "absolute",
                left: `${left}%`,
                top: `${top}%`,
                transform: `translate(-50%, -50%) scale(${scale}) rotate(${rot.toFixed(2)}deg)`,
                opacity,
                zIndex: 22,
                pointerEvents: "none",
                filter: "drop-shadow(0 10px 18px rgba(35, 22, 10, 0.45))",
              }}
            >
              {cutout.src ? (
                <Img
                  src={resolveSrc(cutout.src)}
                  style={{
                    maxWidth: cutout.width || 340,
                    maxHeight: cutout.height || 340,
                    objectFit: "contain",
                    border: cutout.border === false ? undefined : "4px solid #FAF6EE",
                    borderRadius: 2,
                  }}
                />
              ) : null}
              {cutout.label ? (
                <div
                  style={{
                    marginTop: 5,
                    backgroundColor: "#FAF6EC",
                    color: "#7F1D1D",
                    fontSize: 12,
                    fontWeight: 900,
                    fontFamily: "'Courier Prime', 'Courier New', monospace",
                    padding: "4px 10px",
                    borderRadius: 2,
                    textAlign: "center",
                    letterSpacing: 1.2,
                    textTransform: "uppercase",
                    border: "1.5px solid rgba(185, 28, 28, 0.55)",
                    boxShadow: "0 3px 8px rgba(35, 22, 10, 0.28)",
                  }}
                >
                  {cutout.label}
                </div>
              ) : null}
            </div>
          );
        })
      ) : null}

      {/* Kinetic Headline & Editorial Stamped Typography (Rule 444 & Vox Architecture) */}
      {showOverlay &&
      (editorialHeadline || (props.sceneIndex === 0 && (props.headline || props.statValue)) || props.motionDirective === "kinetic_headline") &&
      (editorialHeadline || props.headline || props.statValue) ? (
        <VoxKineticHeadline
          headline={
            typeof editorialHeadline === "object"
              ? editorialHeadline.text
              : (editorialHeadline || props.headline || (props.statValue ? String(props.statValue) : undefined))
          }
          highlightWord={props.highlightWord || (typeof editorialHeadline === "object" ? editorialHeadline.highlightWord : "")}
          category={props.category || props.actTitle}
          subtext={props.subtext || props.statLabel || (typeof editorialHeadline === "object" ? editorialHeadline.subtext : undefined)}
          accentColor={props.accentColor || (typeof editorialHeadline === "object" ? editorialHeadline.color : "#f59e0b")}
        />
      ) : null}

      {/* Linked Secondary Objects (Parametric Vector Follower, Physical Stamp Slam, Marker Sweep, Odometer) */}
      {showOverlay && props.linkedSecondaryObjects && Array.isArray(props.linkedSecondaryObjects) ? (
        props.linkedSecondaryObjects.map((obj: any, idx: number) => {
          if (obj.type === "svg_procedural_marker" || obj.type === "marker_sweep") {
            return (
              <ProceduralMarkerSweep
                key={`sec-marker-${idx}`}
                startFrame={obj.sweep_start_frame || obj.startFrame || 10}
                durationFrames={obj.sweep_duration_frames || obj.durationFrames || 12}
                color={obj.color || "#ffe600"}
                blendMode={obj.blend_mode || "multiply"}
              />
            );
          }
          if (obj.type === "stamp" || obj.type === "stamp_slam") {
            return (
              <div
                key={`sec-stamp-${idx}`}
                style={{
                  position: "absolute",
                  left: `${obj.x_pct || 65}%`,
                  top: `${obj.y_pct || 45}%`,
                  transform: "translate(-50%, -50%)",
                  zIndex: 28,
                  pointerEvents: "none",
                }}
              >
                <PhysicalStampSlam
                  label={obj.label || "CONFIDENTIAL"}
                  subLabel={obj.subLabel || obj.sub_label}
                  theme={obj.theme || "danger"}
                  color={obj.color}
                  slamFrame={obj.slam_frame || obj.slamFrame || 15}
                  rotation={obj.rot_deg || obj.rotation || -4}
                />
              </div>
            );
          }
          if (obj.type === "odometer" || obj.type === "counter_rollup") {
            return (
              <div
                key={`sec-odo-${idx}`}
                style={{
                  position: "absolute",
                  left: `${obj.x_pct || 50}%`,
                  top: `${obj.y_pct || 40}%`,
                  transform: "translate(-50%, -50%)",
                  zIndex: 28,
                  pointerEvents: "none",
                }}
              >
                <OdometerRollup
                  startValue={obj.start_value ?? 0}
                  endValue={obj.end_value ?? 0}
                  prefix={obj.prefix ?? ""}
                  suffix={obj.suffix ?? ""}
                  label={obj.label || ""}
                  subLabel={obj.sub_label || obj.subLabel}
                  startFrame={obj.start_frame || 5}
                  durationFrames={obj.duration_frames || 25}
                />
              </div>
            );
          }
          if (obj.src) {
            return (
              <ProceduralMotionFollower
                key={`sec-obj-${idx}`}
                motionPath={obj.motion_path || obj.motionPath}
                width={width}
                height={height}
                zIndex={20}
              >
                <Img
                  src={resolveSrc(obj.src)}
                  style={{
                    maxWidth: 450,
                    maxHeight: 450,
                    objectFit: "contain",
                    filter: "drop-shadow(0 15px 30px rgba(0,0,0,0.8))",
                  }}
                />
              </ProceduralMotionFollower>
            );
          }
          return null;
        })
      ) : null}

      {/* Floating Minimalist Subtitle with Intelligent Auto-Dodge (Vox Motion Engine 2.0) */}
      {words.length > 0 ? (
        <div style={subtitleContainerStyle}>
          {/* Header Speaker / Subject Minimalist Pill Tag */}
          {showSpeakerTag && rawSpeakerTag ? (
            <div
              style={{
                display: "inline-flex",
                alignItems: "center",
                gap: 6,
                padding: "3px 10px",
                backgroundColor: "rgba(10, 15, 24, 0.78)",
                border: "1px solid rgba(242, 166, 59, 0.45)",
                borderRadius: 4,
                marginBottom: 6,
                boxShadow: "0 2px 8px rgba(0, 0, 0, 0.6)",
              }}
            >
              <span style={{ fontSize: 11 }}>📜</span>
              <span
                style={{
                  color: "#ffd166",
                  fontSize: 12,
                  fontWeight: 800,
                  letterSpacing: 1.2,
                  textTransform: "uppercase",
                  fontFamily: "'Zen Kaku Gothic New', 'Segoe UI', Roboto, sans-serif",
                  fontFeatureSettings: '"palt" 1',
                }}
              >
                {rawSpeakerTag}
              </span>
            </div>
          ) : null}

          {/* Karaoke Word-Highlight Subtitle Line (Floating Minimalist - Duty Cycle Aware) */}
          {(props.karaokeMode || props.karaoke_mode || (isFullBleedOverlay ? "dim" : "full")) !== "off" ? (
            <div
              style={{
                fontFamily: "'Zen Kaku Gothic New', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif",
                fontFeatureSettings: '"palt" 1',
                fontSize: subtitleFontSize,
                lineHeight: 1.35,
                color: "#FFFFFF",
                textAlign: subtitleTextAlign,
                textShadow:
                  "0 2px 4px rgba(0, 0, 0, 0.95), 0 0 14px rgba(0, 0, 0, 0.9), 0 4px 20px rgba(0, 0, 0, 0.85)",
                opacity: (props.karaokeMode || props.karaoke_mode || (isFullBleedOverlay ? "dim" : "full")) === "dim" ? 0.78 : 1.0,
              }}
            >
              {visibleWords.map((w, wIdx) => {
                const currentGlobalIdx = chunkStartWord + wIdx;
                const isPast = currentGlobalIdx < activeGlobalWordIdx;
                const isActive = currentGlobalIdx === activeGlobalWordIdx;
                const kMode = props.karaokeMode || props.karaoke_mode || (isFullBleedOverlay ? "dim" : "full");
                const isDim = kMode === "dim";

                if (isActive) {
                  return (
                    <span
                      key={wIdx}
                      style={{
                        color: isDim ? "#FFFFFF" : "#ffd166",
                        fontWeight: 900,
                        textShadow: isDim
                          ? "0 0 10px rgba(255, 255, 255, 0.75), 0 2px 6px rgba(0, 0, 0, 1)"
                          : "0 0 16px rgba(255, 209, 102, 0.95), 0 2px 6px rgba(0, 0, 0, 1)",
                        marginRight: 8,
                        display: "inline-block",
                        transform: isDim ? "scale(1.0)" : "scale(1.08)",
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
                        color: isDim ? "rgba(255, 255, 255, 0.82)" : "#FFFFFF",
                        fontWeight: 700,
                        textShadow: "0 2px 4px rgba(0, 0, 0, 0.9)",
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
                      color: isDim ? "rgba(255, 255, 255, 0.35)" : "rgba(255, 255, 255, 0.45)",
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
          ) : null}
        </div>
      ) : null}    </AbsoluteFill>
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
    const paperTheme =
      s.papercraft_theme ||
      s.paperTheme ||
      (s.forensicOverlay?.type === "market_depth" || s.forensicOverlay?.type === "circuit_breaker_dial"
        ? "blueprint"
        : "parchment");
    const last = raw[raw.length - 1];
    if (last && last.src === src && last.paperTheme === paperTheme) {
      last.end += dur;
    } else {
      raw.push({ src, paperTheme, start: cursor, end: cursor + dur });
    }
    cursor += dur;
  });
  return raw.map((seg, i) => {
    const next = raw[i + 1];
    const fadeIn = i === 0 ? 0 : Math.min(fadeFrames, seg.end - seg.start);
    const fadeOutExtend = next ? Math.min(fadeFrames, next.end - next.start) : 0;
    return {
      src: seg.src,
      paperTheme: seg.paperTheme,
      from: seg.start,
      durationInFrames: seg.end - seg.start + fadeOutExtend,
      fadeInFrames: fadeIn,
    };
  });
};

const BackgroundSegment = ({
  src,
  fadeInFrames,
  durationInFrames,
  hasForeground = false,
  paperTheme = "parchment",
}: {
  src: string | null;
  fadeInFrames: number;
  durationInFrames: number;
  hasForeground?: boolean;
  paperTheme?: any;
}) => {
  const frame = useCurrentFrame();
  const dur = durationInFrames || 300;
  const opacity =
    fadeInFrames > 0
      ? interpolate(frame, [0, fadeInFrames], [0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        })
      : 1;

  const validTheme = ["parchment", "blueprint", "manila", "vintage_map"].includes(paperTheme)
    ? paperTheme
    : "parchment";

  const isVideo = src && (src.endsWith(".mp4") || src.endsWith(".webm") || src.includes(".mp4"));

  return (
    <VoxPaperBackdrop theme={validTheme} bgImage={isVideo ? null : src} opacity={opacity}>
      {isVideo && src ? (
        <AbsoluteFill style={{ opacity }}>
          <Video
            src={resolveSrc(src)}
            style={{
              width: "100%",
              height: "100%",
              objectFit: "cover",
              filter:
                validTheme === "blueprint"
                  ? "brightness(0.65) contrast(1.15) saturate(0.5) hue-rotate(180deg)"
                  : "brightness(0.90) saturate(0.7) sepia(0.20) contrast(1.05)",
            }}
            muted
            loop
          />
          <div
            style={{
              position: "absolute",
              inset: 0,
              backgroundColor: validTheme === "blueprint" ? "#1e293b" : "#F5F2EB",
              opacity: 0.28,
              mixBlendMode: "multiply",
            }}
          />
        </AbsoluteFill>
      ) : null}
    </VoxPaperBackdrop>
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
    const explicitFg = s.primary_hero?.src || s.foreground || null;
    const motionPath = s.primary_hero?.motion_path || s.motion_path || s.motionPath || null;
    const last = raw[raw.length - 1];
    const heldFg = last && last.bgId === bgId ? last.src : null;
    const effectiveFg = explicitFg || heldFg;
    if (last && last.bgId === bgId && last.src === effectiveFg && !motionPath) {
      last.end += dur;
    } else {
      raw.push({
        src: effectiveFg,
        bgId,
        start: cursor,
        end: cursor + dur,
        fadeFrames: s.foregroundFadeFrames ? s.foregroundFadeFrames : defaultFadeFrames,
        position: s.foregroundPosition,
        motionPath,
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
const _auditedForegroundCoverageKeys = new WeakSet();
const auditForegroundCoverage = (scenes, foregroundSegments) => {
  // Render runs this component body once per output frame -- dedupe by
  // scenes object reference so this only actually runs once per distinct episode props.
  if (_auditedForegroundCoverageKeys.has(scenes)) return;
  _auditedForegroundCoverageKeys.add(scenes);
  const bgIds = computeBackgroundSegmentIds(scenes);
  const maxBgId = bgIds.length ? bgIds[bgIds.length - 1] : -1;
  for (let bgId = 0; bgId <= maxBgId; bgId += 1) {
    const count = foregroundSegments.filter((seg) => seg.bgId === bgId).length;
    if (count === 0) {
      // In Vox Documentary Style, full-frame evidence (documents, maps, charts) without foreground is valid
    } else if (count > 2) {
      console.warn(
        "[Rule 52.3 audit] background segment " + bgId + " has " + count + " distinct foregrounds -- rule caps this at 2 cores per background."
      );
    }
  }
};

// Anti-Flicker Card & Overlay Segmentation (Rule 122 & Zero-Flicker Architecture)
// Groups consecutive scenes that share identical forensic overlays, stat cards,
// or explicit card_segment_key into a single persistent sequence.
// Prevents React unmount/remount on scene cuts and eliminates spring slam flickering.
const SPECIALIZED_CHART_OVERLAY_TYPES = new Set([
  "financial_chart",
  "circuit_breaker_dial",
  "threshold_ratio",
  "grid_ratio",
  "ratio_grid",
  "market_depth",
  "causal_chain",
  "timeline_stepper",
  "kinetic_counter",
]);

const computeOverlayKey = (s: any) => {
  const ov = s.forensicOverlay || s.forensic_overlay;
  const ovType = ov?.type;
  if (!ovType || !SPECIALIZED_CHART_OVERLAY_TYPES.has(ovType)) return null;

  const variant = s.layoutVariant || s.sceneLayoutMode;
  if (variant === "kinetic_headline" || variant === "evidence_dossier") return null;

  const pos = s.foregroundPosition || "left";
  return JSON.stringify({
    ovType,
    ovTitle: ov?.title,
    ovPayload: ov?.payload,
    pos,
  });
};

const buildOverlaySegments = (scenes: any[]) => {
  const raw: any[] = [];
  let cursor = 0;
  scenes.forEach((s) => {
    const dur = Math.max(1, Math.round(s.durationInFrames ? s.durationInFrames : 1));
    const key = computeOverlayKey(s);
    const last = raw[raw.length - 1];
    const effectiveOv = key ? (s.forensicOverlay || s.forensic_overlay) : null;

    if (key && last && last.key === key) {
      last.end += dur;
    } else if (key && effectiveOv) {
      raw.push({
        key,
        start: cursor,
        end: cursor + dur,
        forensicOverlay: effectiveOv,
        statValue: undefined,
        statLabel: undefined,
        stampBadge: undefined,
        isLeft: s.foregroundPosition === "left",
        hasForeground: Boolean(s.foreground || s.primary_hero),
      });
    }
    cursor += dur;
  });
  return raw.map((seg) => ({
    from: seg.start,
    durationInFrames: seg.end - seg.start,
    forensicOverlay: seg.forensicOverlay,
    statValue: seg.statValue,
    statLabel: seg.statLabel,
    stampBadge: seg.stampBadge,
    isLeft: seg.isLeft,
    hasForeground: seg.hasForeground,
  }));
};

const OverlaySegmentView = ({
  forensicOverlay,
  statValue,
  statLabel,
  stampBadge,
  isLeft,
  hasForeground,
  durationInFrames = 180,
}: {
  forensicOverlay?: any;
  statValue?: string;
  statLabel?: string;
  stampBadge?: string;
  isLeft: boolean;
  hasForeground?: boolean;
  durationInFrames?: number;
}) => {
  const dur = Math.max(1, durationInFrames);

  // Stage 4 Entrance: Card drops in after background establishes
  const cardStartFrame = Math.min(25, Math.round(dur * 0.12));

  // Stage 6 Slam timing: hits around 65% of segment duration
  const slamFrame = Math.min(180, Math.max(25, Math.round(dur * 0.65)));

  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      {/* Stage 4/5: Evidentiary Stat Paper Note (Zero Emoji) */}
      {statValue && !forensicOverlay ? (
        <PaperStatCard
          statValue={String(statValue)}
          statLabel={statLabel ? String(statLabel) : undefined}
          isLeft={isLeft}
          dropFrame={cardStartFrame}
          top={68}
        />
      ) : null}

      <VoxOverlayLayer
        forensicOverlay={forensicOverlay}
        isLeft={isLeft}
        hasForeground={hasForeground}
        statValue={statValue}
        statLabel={statLabel}
      />

      {stampBadge ? (
        <ForensicStampBadge
          badge={String(stampBadge)}
          isLeft={isLeft}
          hasStatCard={Boolean(statValue && !forensicOverlay)}
          durationInFrames={dur}
          slamFrame={slamFrame}
        />
      ) : null}
    </AbsoluteFill>
  );
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
          backgroundColor: "rgba(10, 15, 24, 0.96)",
          border: "1.5px solid rgba(242, 166, 59, 0.45)",
          borderRadius: 8,
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

const CinematicVignette: React.FC<{ active?: boolean; strong?: boolean }> = ({ active = true, strong = false }) => {
  if (!active) return null;
  const edgeAlpha = strong ? 0.85 : 0.65;
  const innerRadius = strong ? "48%" : "65%";
  return (
    <div
      style={{
        position: "absolute",
        top: 0,
        left: 0,
        width: "100%",
        height: "100%",
        background: `radial-gradient(ellipse at center, transparent ${innerRadius}, rgba(0, 0, 0, ${edgeAlpha}) 100%)`,
        zIndex: 10,
        pointerEvents: "none",
      }}
    />
  );
};

const CinematicOverlay: React.FC<{
  filmGrain?: boolean;
  grainOpacity?: number;
  digitalGlitch?: boolean;
  highContrast?: boolean;
  relFrame?: number;
}> = ({ filmGrain, grainOpacity, digitalGlitch, highContrast, relFrame = 0 }) => {
  const isGlitchFrame = digitalGlitch && relFrame < 6 && (relFrame % 2 === 1);
  return (
    <AbsoluteFill style={{ zIndex: 20, pointerEvents: "none" }}>
      {/* Cinematic editorial tone wash */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          background: highContrast
            ? "linear-gradient(135deg, rgba(20, 28, 45, 0.12) 0%, rgba(45, 25, 15, 0.10) 100%)"
            : "linear-gradient(135deg, rgba(20, 28, 45, 0.05) 0%, rgba(45, 25, 15, 0.04) 100%)",
        }}
      />
      {/* Film Grain Subtle Noise Texture Layer (Optimized 16px grid: 8,100 tiles vs 129,600 tiles for fast CPU raster) */}
      {filmGrain ? (
        <div
          style={{
            position: "absolute",
            inset: 0,
            opacity: typeof grainOpacity === "number" ? grainOpacity : 0.07,
            backgroundImage: "radial-gradient(rgba(255, 255, 255, 0.22) 1.2px, transparent 1.2px)",
            backgroundSize: "16px 16px",
          }}
        />
      ) : null}
      {/* Metric Shock Digital Chromatic Glitch Bar */}
      {isGlitchFrame ? (
        <div
          style={{
            position: "absolute",
            top: `${(relFrame * 17) % 80}%`,
            left: 0,
            right: 0,
            height: 14,
            background: "rgba(239, 68, 68, 0.35)",
            boxShadow: "0 0 12px rgba(56, 189, 248, 0.45)",
            transform: `skewX(${relFrame % 2 === 0 ? 8 : -8}deg)`,
          }}
        />
      ) : null}
    </AbsoluteFill>
  );
};

// === CINEMATIC TRANSITIONS SYSTEM (Rule 122, Rule 128 & Bo-tu-dien-Transition-Animation) ===
export const CinematicTransitionOverlay: React.FC<{
  transitionOut: string | undefined;
  relFrame: number;
  durationInFrames: number;
}> = ({ transitionOut, relFrame, durationInFrames }) => {
  if (!transitionOut || transitionOut === "hard_cut") return null;

  // 1. Paper Tear: diagonal jagged ripped paper edge sliding across screen (frames 0-8)
  if (transitionOut === "paper_tear") {
    if (relFrame > 8) return null;
    const tearProgress = interpolate(relFrame, [0, 8], [-100, 100], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    return (
      <AbsoluteFill style={{ zIndex: 40, pointerEvents: "none", overflow: "hidden" }}>
        <div
          style={{
            position: "absolute",
            top: 0,
            left: `${tearProgress}%`,
            width: 90,
            height: "100%",
            background: "linear-gradient(90deg, transparent 0%, rgba(248, 245, 235, 0.95) 40%, rgba(220, 215, 200, 0.9) 60%, transparent 100%)",
            boxShadow: "0 0 25px rgba(0,0,0,0.55)",
            transform: "skewX(-14deg)",
          }}
        />
      </AbsoluteFill>
    );
  }

  // 2. Ink Bleed: dark organic radial blotch spreading and dissolving (frames 0-9)
  if (transitionOut === "ink_bleed") {
    if (relFrame > 9) return null;
    const inkOpacity = interpolate(relFrame, [0, 2, 9], [0.95, 0.75, 0], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    const inkScale = interpolate(relFrame, [0, 9], [0.9, 1.4], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    return (
      <AbsoluteFill
        style={{
          zIndex: 40,
          pointerEvents: "none",
          opacity: inkOpacity,
          background: "radial-gradient(circle at 50% 50%, rgba(10, 14, 22, 0.96) 0%, rgba(18, 24, 38, 0.7) 45%, transparent 75%)",
          transform: `scale(${inkScale})`,
        }}
      />
    );
  }

  // 3. Light Leak: warm vintage anamorphic flare burst across corner (frames 0-8)
  if (transitionOut === "light_leak") {
    if (relFrame > 8) return null;
    const leakOpacity = interpolate(relFrame, [0, 2, 8], [0, 0.82, 0], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    return (
      <AbsoluteFill
        style={{
          zIndex: 40,
          pointerEvents: "none",
          opacity: leakOpacity,
          background: "radial-gradient(ellipse at 88% 12%, rgba(255, 195, 95, 0.88) 0%, rgba(255, 115, 30, 0.52) 40%, rgba(255, 60, 10, 0.18) 65%, transparent 85%)",
        }}
      />
    );
  }

  // 4. Circle Wipe / Iris: circular aperture expanding from center (frames 0-7)
  if (transitionOut === "circle_wipe") {
    if (relFrame > 8) return null;
    const irisRadius = interpolate(relFrame, [0, 7], [0, 120], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    return (
      <AbsoluteFill
        style={{
          zIndex: 40,
          pointerEvents: "none",
          background: INK,
          maskImage: `radial-gradient(circle at 50% 50%, transparent ${irisRadius}%, black ${irisRadius + 1}%)`,
          WebkitMaskImage: `radial-gradient(circle at 50% 50%, transparent ${irisRadius}%, black ${irisRadius + 1}%)`,
        }}
      />
    );
  }

  // 5. Smash Cut: single-frame abrupt black punch (frame 0)
  if (transitionOut === "smash_cut") {
    if (relFrame === 0) {
      return (
        <AbsoluteFill style={{ zIndex: 45, backgroundColor: "#000000", pointerEvents: "none" }} />
      );
    }
    return null;
  }

  // 6. Stop Motion Flicker Cut: 3-frame rapid shutter strobe
  if (transitionOut === "stop_motion_flicker_cut") {
    if (relFrame > 4) return null;
    const strobe = interpolate(relFrame, [0, 1, 2, 3, 4], [0.35, 0, 0.2, 0, 0]);
    if (strobe <= 0.01) return null;
    return (
      <AbsoluteFill style={{ zIndex: 40, backgroundColor: "#000000", opacity: strobe, pointerEvents: "none" }} />
    );
  }

  // 7. Vox Push-Zoom Match Cut: rapid 7-frame editorial momentum push with optical punch (Benchmark cXQuNBZA0FA 07:15)
  if (transitionOut === "vox_push_zoom" || transitionOut === "push_zoom") {
    if (relFrame > 7) return null;
    const pFlash = interpolate(relFrame, [0, 1, 7], [0.18, 0.08, 0], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    const vigPunch = interpolate(relFrame, [0, 2, 7], [0.45, 0.20, 0], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    return (
      <AbsoluteFill
        style={{
          zIndex: 42,
          pointerEvents: "none",
          backgroundColor: `rgba(255, 255, 255, ${pFlash})`,
          background: `radial-gradient(circle at center, rgba(255, 255, 255, ${pFlash}) 0%, rgba(0, 0, 0, ${vigPunch}) 100%)`,
        }}
      />
    );
  }

  // 8. Vox Directional Paper Wipe: crisp angled paper banner sweep across screen (Benchmark cXQuNBZA0FA 07:45)
  if (transitionOut === "vox_paper_wipe" || transitionOut === "paper_wipe") {
    if (relFrame > 8) return null;
    const wipeX = interpolate(relFrame, [0, 8], [-120, 120], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.bezier(0.2, 0.8, 0.2, 1),
    });
    return (
      <AbsoluteFill style={{ zIndex: 45, pointerEvents: "none", overflow: "hidden" }}>
        <div
          style={{
            position: "absolute",
            top: "-10%",
            left: `${wipeX}%`,
            width: "35%",
            height: "120%",
            background: "linear-gradient(105deg, #18181b 0%, #eab308 50%, #f4eedd 100%)",
            boxShadow: "-10px 0 30px rgba(0,0,0,0.6), 10px 0 30px rgba(0,0,0,0.6)",
            transform: "rotate(6deg)",
          }}
        />
      </AbsoluteFill>
    );
  }

  // 9. Vox Tape Snap: semi-transparent masking tape strip stitching the cut (Benchmark cXQuNBZA0FA)
  if (transitionOut === "vox_tape_snap" || transitionOut === "tape_snap") {
    if (relFrame > 10) return null;
    const tapeScaleY = interpolate(relFrame, [0, 3], [0, 1], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.out(Easing.back(1.5)),
    });
    const tapeFade = interpolate(relFrame, [6, 10], [0.85, 0], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    return (
      <AbsoluteFill style={{ zIndex: 46, pointerEvents: "none", display: "flex", alignItems: "center", justifyContent: "center" }}>
        <div
          style={{
            width: "280px",
            height: "44px",
            background: "rgba(244, 238, 221, 0.82)",
            border: "1px dashed rgba(180, 160, 120, 0.6)",
            boxShadow: "0 4px 12px rgba(0,0,0,0.35)",
            transform: `rotate(-12deg) scaleY(${tapeScaleY})`,
            opacity: tapeFade,
            borderRadius: "2px",
          }}
        />
      </AbsoluteFill>
    );
  }

  if (
    transitionOut === "push_through" ||
    transitionOut === "paper_slide" ||
    transitionOut === "match_cut"
  ) {
    return (
      <PushThroughTransitionOverlay
        transitionOut={transitionOut}
        relFrame={relFrame}
      />
    );
  }

  return null;
};

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

  if (mov === "push_through") {
    // Camera plunges through focal document into new board
    const pThrough = interpolate(f, [0, 9, dur], [1.18, 1.01, 1.045], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.bezier(0.16, 1, 0.3, 1),
    });
    return `scale(${pThrough})`;
  }

  if (mov === "paper_slide") {
    // Lateral tabletop slide settling into board focus
    const slideX = interpolate(f, [0, 8, dur], [28, 0, -4], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.bezier(0.22, 1, 0.36, 1),
    });
    return `scale(1.03) translateX(${slideX.toFixed(1)}px)`;
  }

  if (mov === "push_zoom" || mov === "vox_push_zoom" || mov === "match_cut") {
    // 8-frame momentum punch: punch in from 1.10 down to 1.02 settling to 1.04
    const pZoom = interpolate(f, [0, 8, dur], [1.10, 1.02, 1.045], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.bezier(0.16, 1, 0.3, 1),
    });
    return `scale(${pZoom})`;
  }

  if (mov === "dramatic_push") {
    // High-stakes investigative dramatic push
    const maxScale = tensionLevel === "high" ? 1.12 : 1.08;
    const scale = interpolate(f, [0, 15, dur], [1.0, maxScale * 0.95, maxScale], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.bezier(0.16, 1, 0.3, 1),
    });
    return `scale(${scale})`;
  }

  if (mov === "forensic_lock") {
    // Rapid deceleration into a rock-solid forensic examination position
    const snap = interpolate(f, [0, 8, dur], [0.98, 1.035, 1.04], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.bezier(0.16, 1, 0.3, 1),
    });
    return `scale(${snap}) rotate(-0.35deg)`;
  }

  if (mov === "subtle_drift") {
    // Organic slow documentary camera glide
    const panX = interpolate(f, [0, dur], [-10, 10], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.bezier(0.25, 0.1, 0.25, 1.0),
    });
    const panY = interpolate(f, [0, dur], [-4, 4], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    const scale = interpolate(f, [0, dur], [1.01, 1.035], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    return `scale(${scale}) translate(${panX.toFixed(2)}px, ${panY.toFixed(2)}px)`;
  }

  if (mov === "counter_rollup") {
    // Punchy focus while metric rollup counts up
    const scale = interpolate(f, [0, 20, dur], [1.0, 1.05, 1.06], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.bezier(0.16, 1, 0.3, 1),
    });
    return `scale(${scale})`;
  }

  if (mov === "yellow_marker_highlight") {
    // Forensic focus locked on highlighted document
    const scale = interpolate(f, [0, 12, dur], [1.0, 1.045, 1.05], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.bezier(0.16, 1, 0.3, 1),
    });
    return `scale(${scale})`;
  }

  if (mov === "snap_zoom") {
    // Sharp punch-in within first 8 frames, then subtle creep
    const scale = interpolate(f, [0, 8, dur], [1.0, 1.10, 1.12], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.bezier(0.16, 1, 0.3, 1),
    });
    return `scale(${scale})`;
  }

  if (mov === "slow_push_in") {
    const maxScale = tensionLevel === "high" ? 1.06 : 1.035;
    const scale = interpolate(f, [0, dur], [1.0, maxScale], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.bezier(0.25, 0.1, 0.25, 1.0),
    });
    return `scale(${scale})`;
  }

  if (mov === "slow_pull_out") {
    const startScale = tensionLevel === "high" ? 1.06 : 1.035;
    const scale = interpolate(f, [0, dur], [startScale, 1.0], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.bezier(0.25, 0.1, 0.25, 1.0),
    });
    return `scale(${scale})`;
  }

  if (mov === "cinematic_pan") {
    // Subtle horizontal tracking (-18px to +18px) with 1.03 base scale
    const panX = interpolate(f, [0, dur], [-18, 18], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.bezier(0.25, 0.1, 0.25, 1.0),
    });
    return `scale(1.03) translateX(${panX}px)`;
  }

  if (mov === "macro_tilt") {
    // Vertical tilt (-12px to +12px)
    const tiltY = interpolate(f, [0, dur], [-12, 12], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.bezier(0.25, 0.1, 0.25, 1.0),
    });
    return `scale(1.03) translateY(${tiltY}px)`;
  }

  if (mov === "handheld_shake") {
    // Controlled documentary tension jitter
    const intensity = tensionLevel === "high" ? 2.5 : 1.2;
    const shakeX = Math.sin(f * 0.45) * intensity + Math.cos(f * 0.8) * (intensity * 0.4);
    const shakeY = Math.cos(f * 0.35) * (intensity * 0.6) + Math.sin(f * 0.7) * (intensity * 0.3);
    const scale = interpolate(f, [0, dur], [1.02, 1.04], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    return `scale(${scale}) translate(${shakeX.toFixed(2)}px, ${shakeY.toFixed(2)}px)`;
  }

  if (mov === "continuous_drift") {
    // Vox/Veo continuous momentum: smooth directional glide without abrupt stops
    const panX = interpolate(f, [0, dur], [-14, 14], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.bezier(0.33, 1, 0.68, 1),
    });
    const panY = interpolate(f, [0, dur], [-6, 6], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.bezier(0.33, 1, 0.68, 1),
    });
    const scale = interpolate(f, [0, dur], [1.01, 1.045], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.bezier(0.25, 0.1, 0.25, 1.0),
    });
    return `scale(${scale}) translate(${panX.toFixed(2)}px, ${panY.toFixed(2)}px)`;
  }

  if (mov === "seamless_whip_pan") {
    // High-velocity lateral transition in first 6 frames settling into slow glide
    const whipX = interpolate(f, [0, 6, dur], [35, 0, -8], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.bezier(0.16, 1, 0.3, 1),
    });
    const scale = interpolate(f, [0, 6, dur], [1.06, 1.02, 1.03], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    return `scale(${scale}) translateX(${whipX.toFixed(2)}px)`;
  }

  if (mov === "macro_orbit") {
    // Elliptical 2.5D orbit around focal evidence
    const angle = (f / dur) * Math.PI * 0.75;
    const orbitX = Math.sin(angle) * 16;
    const orbitY = (1 - Math.cos(angle)) * 8;
    const scale = interpolate(f, [0, dur], [1.02, 1.05], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    return `scale(${scale}) translate(${orbitX.toFixed(2)}px, ${orbitY.toFixed(2)}px)`;
  }

  if (mov === "cinematic_orbit") {
    // Subtle orbital tilt + push
    const rot = interpolate(f, [0, dur], [-0.6, 0.6], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    const scale = interpolate(f, [0, dur], [1.02, 1.045], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    return `scale(${scale}) rotate(${rot.toFixed(2)}deg)`;
  }

  if (mov === "dolly_zoom") {
    // Vertigo opposing zoom/fov effect: scale down background while shifting perspective
    const scale = interpolate(f, [0, dur], [1.12, 1.01], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.bezier(0.16, 1, 0.3, 1),
    });
    const panY = interpolate(f, [0, dur], [8, -4], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    return `scale(${scale}) translateY(${panY.toFixed(2)}px)`;
  }

  if (mov === "whip_zoom") {
    // Ultra high-velocity punch-in in first 4 frames with micro overshoot
    const scale = interpolate(f, [0, 4, 10, dur], [1.0, 1.15, 1.11, 1.13], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.bezier(0.16, 1, 0.3, 1),
    });
    return `scale(${scale})`;
  }

  if (mov === "focus_breathe_push") {
    // Push-in with subtle optical lens breathing pulse in first 12 frames
    const breathe = interpolate(f, [0, 4, 8, 14, dur], [1.0, 1.04, 0.99, 1.02, 1.06], {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.bezier(0.25, 0.1, 0.25, 1.0),
    });
    return `scale(${breathe})`;
  }

  // Fallback subtle Ken Burns slow zoom
  const scale = interpolate(f, [0, dur], [1.0, 1.03], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.25, 0.1, 0.25, 1.0),
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

// Living Micro-Life Layer (Rule 122 & YouTube Benchmark cXQuNBZA0FA Parity)
// Provides continuous tactile micro-dynamics (floating paper motes, ambient light breathing)
// even during Permanent Lock windows (7.0 - 10.0s), preventing the static dead-cardboard look.
export const LivingMicroLifeLayer: React.FC<{ frame: number }> = ({ frame }) => {
  const p1X = (Math.sin(frame * 0.02) * 18 + 120) % 1920;
  const p1Y = (Math.cos(frame * 0.015) * 12 + 250) % 1080;
  const p2X = (Math.cos(frame * 0.025) * 14 + 1400) % 1920;
  const p2Y = (Math.sin(frame * 0.018) * 16 + 680) % 1080;
  const p3X = (Math.sin(frame * 0.012) * 22 + 960) % 1920;
  const p3Y = (Math.cos(frame * 0.022) * 15 + 400) % 1080;

  return (
    <AbsoluteFill style={{ pointerEvents: "none", zIndex: 38, overflow: "hidden" }}>
      {/* Living Paper Ambient Light Breathing */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          background: "radial-gradient(ellipse at 45% 40%, rgba(255, 235, 190, 0.035) 0%, transparent 70%)",
          opacity: 1 + Math.sin(frame * 0.06) * 0.15,
        }}
      />
      {/* Tactile Paper Dust Motes */}
      <div
        style={{
          position: "absolute",
          left: p1X,
          top: p1Y,
          width: 3,
          height: 3,
          borderRadius: "50%",
          backgroundColor: "rgba(255, 255, 255, 0.28)",
          boxShadow: "0 0 4px rgba(255, 255, 255, 0.4)",
          opacity: 0.6 + Math.sin(frame * 0.04) * 0.3,
        }}
      />
      <div
        style={{
          position: "absolute",
          left: p2X,
          top: p2Y,
          width: 2.5,
          height: 2.5,
          borderRadius: "50%",
          backgroundColor: "rgba(242, 166, 59, 0.35)",
          boxShadow: "0 0 3px rgba(242, 166, 59, 0.45)",
          opacity: 0.5 + Math.cos(frame * 0.05) * 0.25,
        }}
      />
      <div
        style={{
          position: "absolute",
          left: p3X,
          top: p3Y,
          width: 2,
          height: 2,
          borderRadius: "50%",
          backgroundColor: "rgba(255, 255, 255, 0.22)",
          opacity: 0.4 + Math.sin(frame * 0.03) * 0.2,
        }}
      />
    </AbsoluteFill>
  );
};

const totalSceneFrames = (scenes) =>
  (scenes || []).reduce((sum, s) => sum + Math.max(1, Math.round(s.durationInFrames ? s.durationInFrames : 1)), 0);

/**
 * Master TwoLayerEpisode Container Component (Rule 125 Single Truth).
 * Unifies 7-layer tactile paper build-on assemblies (VoxBuildOnStage) with:
 * - Anti-flicker Evidentiary Forensic Overlays & Stat Paper Notes (OverlaySegmentView)
 * - Faster-Whisper millisecond word-level Karaoke Subtitles & Speaker Tags (TwoLayerScene)
 * - Tactile Paper Foley SFX, LivingMicroLifeLayer, Optical FX, and TopProgressBar.
 */
export const TwoLayerEpisode: React.FC<{
  scenes?: any[];
  audioMaster?: string;
  bgmFile?: string;
  bgmVolume?: number;
  includeAudio?: boolean;
  fps?: number;
  width?: number;
  height?: number;
}> = (props) => {
  const scenes = props.scenes || [];
  const cfg = useVideoConfig();
  const currentFrame = useCurrentFrame();

  const currentSceneInfo = getCurrentSceneInfo(scenes, currentFrame);
  const currentCameraMov = currentSceneInfo
    ? currentSceneInfo.scene.cameraMovement ||
      (currentSceneInfo.scene.camera ? currentSceneInfo.scene.camera.movement : undefined) ||
      currentSceneInfo.scene.motionDirective
    : undefined;
  const currentDur = currentSceneInfo ? currentSceneInfo.durationInFrames : 300;

  const overlaySegments = React.useMemo(
    () => buildOverlaySegments(scenes),
    [scenes]
  );

  const sceneSequences = React.useMemo(() => {
    let cursor = 0;
    return scenes.map((s, idx) => {
      const dur = Math.max(
        1,
        Math.round(
          s.durationInFrames
            ? s.durationInFrames
            : s.durationSec
            ? s.durationSec * (cfg.fps || 30)
            : 150
        )
      );
      const from = cursor;
      cursor += dur;

      const durationSec = dur / (cfg.fps || 30);
      const bgRaw = s.background || s.backgroundSrc || s.targetBackground;
      const bgSrc = bgRaw ? resolveSrc(bgRaw) : undefined;

      const heroRaw = (s.foreground !== undefined && s.foreground !== null) ? (s.foreground || undefined) : (s.heroSrc || s.primary_hero?.src || s.targetHeroSrc);
      const heroSrc = heroRaw ? resolveSrc(heroRaw) : undefined;

      const fgPos = s.foregroundPosition || (idx % 2 === 0 ? "left" : "right");
      const hasOv = Boolean(s.forensicOverlay || s.forensic_overlay || s.statValue);
      const defaultHeroXPct = hasOv ? (fgPos === "left" ? 28 : 72) : (fgPos === "left" ? 34 : 66);
      const resolvedHeroPosition =
        s.heroPosition && s.heroPosition.xPct !== 50
          ? s.heroPosition
          : { xPct: defaultHeroXPct, yPct: 54, widthPct: hasOv ? 34 : 38 };

      const rawCutouts = s.supportingCutouts || s.supporting_cutouts || [];
      const resolvedCutouts = rawCutouts
        .filter((c: any) => Boolean(c && (c.src || (c.label && !/^MEMO #|^RECORD #/i.test(String(c.label))))))
        .map((c: any, cIdx: number) => ({
          ...c,
          id: c.id || `cutout-${idx}-${cIdx}`,
          src: c.src ? resolveSrc(c.src) : undefined,
          xPct: c.xPct !== undefined ? c.xPct : (c.x !== undefined ? c.x : 26 + cIdx * 48),
          yPct: c.yPct !== undefined ? c.yPct : (c.y !== undefined ? c.y : 60),
          widthPct: c.widthPct !== undefined ? c.widthPct : (c.scale ? Math.round(c.scale * 50) : 22),
          hasPin: c.hasPin !== undefined ? c.hasPin : cIdx % 2 === 0,
          hasTape: c.hasTape !== undefined ? c.hasTape : cIdx % 2 === 1,
        }));

      const rawYarns =
        s.yarns ||
        s.radiatingConnections ||
        s.radiating_connections ||
        (s.connection ? [s.connection] : []);

      const cleanHeadline =
        typeof s.headline === "string" && s.headline.trim() && s.headline.trim().toUpperCase() !== "ACT"
          ? s.headline.trim()
          : (typeof s.editorialHeadline === "string" && s.editorialHeadline.trim()
            ? s.editorialHeadline.trim()
            : (typeof s.headline?.text === "string" ? s.headline.text : undefined));

      const cleanSubtitle = s.subtitle || s.actTitle || s.speakerTag || undefined;
      const resolvedLayoutVariant =
        s.layoutVariant ||
        s.sceneLayoutMode ||
        (idx === 0 || idx % 6 === 0
          ? "paper_collage"
          : idx % 6 === 1 || idx % 6 === 4
          ? "cinematic_doc"
          : idx % 6 === 2
          ? "kinetic_headline"
          : "evidence_dossier");

      return (
        <Sequence
          key={s.id || s.scene_id || `vox-beat-${idx}`}
          from={from}
          durationInFrames={dur}
          name={cleanHeadline || `Scene ${idx + 1}`}
        >
          <VoxBuildOnStage
            headline={cleanHeadline}
            subtitle={cleanSubtitle}
            theme={s.theme || s.papercraft_theme || s.paperTheme || "newsprint-editorial"}
            backgroundSrc={bgSrc}
            heroSrc={heroSrc}
            heroLabel={s.heroLabel || s.speakerTag}
            heroPosition={resolvedHeroPosition}
            supportingCutouts={resolvedCutouts}
            yarns={rawYarns}
            stampText={s.stampText}
            stampColor={s.stampColor || "#dc2626"}
            hasMarkerHighlight={s.hasMarkerHighlight !== false}
            durationSec={durationSec}
            layoutVariant={resolvedLayoutVariant}
            sceneIndex={idx}
            cameraMovement={s.cameraMovement || (s.camera ? s.camera.movement : undefined)}
          />
          <TwoLayerScene
            background={bgRaw}
            showBackground={false}
            showForeground={false}
            showOverlay={false}
            showSupportingCutouts={false}
            foreground={heroRaw}
            foregroundPosition={fgPos}
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
            transition_out={s.transition_out || s.transitionOut || s.transition}
            motionDirective={s.motionDirective}
            sourceCredit={s.sourceCredit || s.source_credit}
            disclosureBadge={s.disclosureBadge}
            actTitle={s.actTitle}
            sceneIndex={idx}
            headline={cleanHeadline}
            highlightWord={s.highlightWord || s.highlight_word}
            category={s.category}
            subtext={s.subtext}
            accentColor={s.accentColor || s.accent_color}
            linkedSecondaryObjects={s.linked_secondary_objects || s.linkedSecondaryObjects}
            primaryHero={s.primary_hero || s.primaryHero}
            virtualCamera={s.virtual_camera || s.virtualCamera}
            connection={s.connection}
            connections={s.connections}
            radiatingConnections={s.radiatingConnections || s.radiating_connections}
            editorialHeadline={s.editorialHeadline || s.editorial_headline}
          />
        </Sequence>
      );
    });
  }, [scenes, cfg.fps]);

  // Only mount internal <Audio> tags when explicitly requested via includeAudio=true
  // (Standard B6 renders twolayer_silent.mp4 and muxes master audio + BGM ducking in S7)
  const includeAudio = Boolean(props.includeAudio);
  const audioMaster = includeAudio && props.audioMaster ? resolveSrc(props.audioMaster) : null;
  const bgmFile = includeAudio && props.bgmFile ? resolveSrc(props.bgmFile) : null;
  const bgmVolume = props.bgmVolume !== undefined ? props.bgmVolume : 0.12;

  return (
    <AbsoluteFill style={{ backgroundColor: "#0f172a" }}>
      {sceneSequences}

      {/* Anti-Flicker Continuous Forensic Overlay & Stat Card Segments */}
      <VoxParallaxLayer depth="midground" cameraMovement={currentCameraMov} durationInFrames={currentDur}>
        {overlaySegments.map((seg, i) => (
          <Sequence
            key={`overlayseg-${i}`}
            from={seg.from}
            durationInFrames={seg.durationInFrames}
            name={`overlay-segment-${i + 1}`}
          >
            <OverlaySegmentView
              forensicOverlay={seg.forensicOverlay}
              statValue={seg.statValue}
              statLabel={seg.statLabel}
              stampBadge={seg.stampBadge}
              isLeft={seg.isLeft}
              hasForeground={seg.hasForeground}
              durationInFrames={seg.durationInFrames}
            />
          </Sequence>
        ))}
      </VoxParallaxLayer>

      <LivingMicroLifeLayer frame={currentFrame} />
      <VoxAtmosphericLighting intensity={0.85} />
      <CinematicVignette
        active={currentSceneInfo?.scene?.opticalFx?.vignette !== false}
        strong={Boolean(currentSceneInfo?.scene?.opticalFx?.high_contrast)}
      />
      <CinematicOverlay
        filmGrain={Boolean(currentSceneInfo?.scene?.opticalFx?.film_grain)}
        grainOpacity={currentSceneInfo?.scene?.opticalFx?.film_grain_opacity}
        digitalGlitch={Boolean(currentSceneInfo?.scene?.opticalFx?.digital_glitch)}
        highContrast={Boolean(currentSceneInfo?.scene?.opticalFx?.high_contrast)}
        relFrame={currentSceneInfo?.relFrame}
      />
      {currentSceneInfo && (
        <CinematicTransitionOverlay
          transitionOut={
            currentSceneInfo.scene.transition_out ||
            currentSceneInfo.scene.transitionOut ||
            currentSceneInfo.scene.transition
          }
          relFrame={currentSceneInfo.relFrame}
          durationInFrames={currentSceneInfo.durationInFrames}
        />
      )}
      <TopProgressBar scenes={scenes} currentFrame={currentFrame} totalFrames={totalSceneFrames(scenes)} />

      {audioMaster && <Audio src={audioMaster} />}
      {bgmFile && <Audio src={bgmFile} volume={bgmVolume} />}
    </AbsoluteFill>
  );
};

export const VoxBuildOnEpisode = TwoLayerEpisode;

const RemotionRoot = () => {
  return (
    <>
      {/* Primary Canonical TwoLayerEpisode Composition (Rule 125 Single Truth) */}
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
      {/* VoxBuildOnStage alias wired to unified TwoLayerEpisode engine */}
      <Composition
        id="VoxBuildOnStage"
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
