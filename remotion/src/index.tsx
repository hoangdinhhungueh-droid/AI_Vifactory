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
import { DataStoryTest } from "./DataStoryTest";
import { FullStory } from "./FullStory";
import {
  VoxOverlayLayer,
  VoxAtmosphericLighting,
  VoxParallaxLayer,
  VoxThresholdRatio,
  VoxKineticTypography,
  VoxSourceCredit,
  VoxDisclosureBadge,
} from "./components/vox";
import { EvidenceProp3D } from "./components/EvidenceProp3D";
import { WordTimestamp } from "./types";
import { VoxelStopMotionVideo, calculateTotalFrames } from "./components/VoxelStopMotionVideo";

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
const ForegroundLayer = ({ src, position, fadeFrames, durationInFrames, width, height, cadence = "cutout" }: any) => {
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

  // Vox Engine 3.0: Integer divisor cadence stepping (10fps default = hold 3, 15fps = hold 2, 30fps = hold 1)
  const targetFps = cadence === "smooth" ? 30 : cadence === "fluid" ? 15 : cadence === "archival" ? 6 : 10;
  const hold = Math.max(1, Math.round(30 / targetFps));
  const steppedFrame = Math.floor(frame / hold) * hold;
  const cell = computeForegroundCell(width, height, position, aspect);
  const slideIn = interpolate(steppedFrame, [0, fadeFrames], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const offscreenX = position === "left" ? -(cell.left + cell.width) : width - cell.left;
  const translateX = offscreenX * (1 - slideIn);

  // VOX Stop-Motion micro-jitter & organic paper rotation
  const jitterSeed = Math.floor(steppedFrame);
  const jitterX = ((Math.sin(jitterSeed * 3.7) * 1000) % 2.5) - 1.25;
  const jitterY = ((Math.cos(jitterSeed * 2.9) * 1000) % 2.5) - 1.25;
  const jitterRot = ((Math.sin(jitterSeed * 1.3) * 1000) % 1.6) - 0.8;

  return (
    <div
      style={{
        position: "absolute",
        left: cell.left,
        top: cell.top,
        width: cell.width,
        height: cell.height,
        opacity,
        transform: `translateX(${translateX}px) translate(${jitterX.toFixed(1)}px, ${jitterY.toFixed(1)}px) rotate(${jitterRot.toFixed(1)}deg)`,
        // Signature VOX Tactile Paper Cutout Sticker Edge + High-Performance 3D Double Drop Shadow
        filter:
          "drop-shadow(0 25px 35px rgba(0, 0, 0, 0.85)) drop-shadow(0 5px 15px rgba(0, 0, 0, 0.60)) drop-shadow(0 0 1.5px rgba(255, 255, 255, 0.70))",
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
          filter: "brightness(1.08) contrast(1.20) saturate(1.10)",
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
}: {
  badge: string;
  isLeft?: boolean;
  hasStatCard?: boolean;
}) => {
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
  const isAlert = ["基準値超過", "EXCEEDED", "超過", "VOID", "CRITICAL", "ALERT"].some((k) => bUp.includes(k));
  const isAuth = ["未回答", "記録なし", "確認できず", "EVIDENCE", "RESTRICTED", "AUDIT", "CONFIDENTIAL"].some((k) => bUp.includes(k));

  const mainColor = isAlert ? "#ef4444" : isAuth ? "#f59e0b" : "#10b981";
  const borderColor = isAlert ? "rgba(239, 68, 68, 0.85)" : isAuth ? "rgba(245, 158, 11, 0.85)" : "rgba(16, 185, 129, 0.85)";
  const bg = isAlert ? "rgba(45, 10, 15, 0.92)" : isAuth ? "rgba(40, 25, 10, 0.92)" : "rgba(10, 35, 20, 0.92)";
  const icon = isAlert ? "🚨" : isAuth ? "📁" : "⚖️";

  return (
    <div
      style={{
        position: "absolute",
        top: hasStatCard ? 175 : 65,
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
    <AbsoluteFill style={{ backgroundColor: showBackground ? INK : "transparent", opacity: entranceOpacity }}>
      {showBackground && background ? (
        <AbsoluteFill>
          <Img
            src={resolveSrc(background)}
            style={{
              width: "100%",
              height: "100%",
              objectFit: "cover",
              transform: "scale(1.06)",
              filter: "brightness(0.32) saturate(0.40) contrast(1.08) blur(14px)",
            }}
          />
          <div
            style={{
              position: "absolute",
              inset: 0,
              background:
                "radial-gradient(circle at 50% 48%, rgba(255, 255, 255, 0.08) 0%, rgba(0, 0, 0, 0.65) 55%, rgba(5, 9, 13, 0.95) 100%)",
              pointerEvents: "none",
            }}
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
          cadence={props.cadence}
        />
      ) : null}

      {/* Top Safe-Zone Animated Stat / Financial Alert Card */}
      {showOverlay && statValue ? (
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

      {/* Vox-Style Explanatory Motion Engine (Rule 122 & Rule 128) */}
      {showOverlay ? (
        <VoxOverlayLayer forensicOverlay={forensicOverlay} isLeft={isLeft} />
      ) : null}

      {/* Forensic Stamp Slam Badge (Rule 122 Acting & Evidence Props) */}
      {showOverlay && stampBadge ? (
        <ForensicStampBadge badge={String(stampBadge)} isLeft={isLeft} hasStatCard={Boolean(statValue)} />
      ) : null}

      {/* Vox Kinetic Typography (Word-Level Whisper Keywords Burst) */}
      {hasExactSubtitles ? (
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

const BackgroundSegment = ({ src, fadeInFrames, durationInFrames, hasForeground = false }: { src: string | null; fadeInFrames: number; durationInFrames: number; hasForeground?: boolean }) => {
  const frame = useCurrentFrame();
  const dur = durationInFrames || 300;
  const opacity =
    fadeInFrames > 0
      ? interpolate(frame, [0, fadeInFrames], [0, 1], {
          extrapolateLeft: "clamp",
          extrapolateRight: "clamp",
        })
      : 1;
  // Subtle, smooth editorial zoom (1.0 -> 1.03) without fighting outer camera
  const scale = interpolate(frame, [0, dur], [1.0, 1.03], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  const filterStyle = hasForeground
    ? "brightness(0.68) saturate(0.75) contrast(1.06) blur(7px)"
    : "brightness(0.92) saturate(0.95) contrast(1.04) blur(0px)";

  const vignetteStyle = hasForeground
    ? "radial-gradient(circle at 50% 48%, rgba(255, 255, 255, 0.05) 0%, rgba(0, 0, 0, 0.40) 55%, rgba(5, 9, 13, 0.82) 100%)"
    : "radial-gradient(circle at 50% 48%, transparent 50%, rgba(5, 9, 13, 0.40) 100%)";

  return (
    <AbsoluteFill style={{ overflow: "hidden", backgroundColor: "#0b0f17" }}>
      {/* Vox Tactical Investigation Canvas: Blueprint Grid & Subtle Halftone Matrix */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundImage:
            "linear-gradient(to right, rgba(255, 255, 255, 0.035) 1px, transparent 1px), linear-gradient(to bottom, rgba(255, 255, 255, 0.035) 1px, transparent 1px)",
          backgroundSize: "60px 60px",
          pointerEvents: "none",
        }}
      />
      <div
        style={{
          position: "absolute",
          inset: 0,
          backgroundImage: "radial-gradient(rgba(255, 255, 255, 0.06) 1px, transparent 1px)",
          backgroundSize: "30px 30px",
          pointerEvents: "none",
        }}
      />

      {src ? (
        <AbsoluteFill style={{ opacity }}>
          {src.endsWith(".mp4") || src.endsWith(".webm") || src.includes(".mp4") ? (
            <Video
              src={resolveSrc(src)}
              style={{
                width: "100%",
                height: "100%",
                objectFit: "cover",
              }}
              muted
              loop
            />
          ) : (
            <Img
              src={resolveSrc(src)}
              style={{
                width: "100%",
                height: "100%",
                objectFit: "cover",
                transform: `scale(${scale * 1.06})`,
                filter: filterStyle,
                transition: "filter 0.3s ease",
              }}
            />
          )}
          {/* Vox Investigation Spotlight & Dark Vignette overlay (Dynamic according to foreground presence) */}
          <div
            style={{
              position: "absolute",
              inset: 0,
              background: vignetteStyle,
              pointerEvents: "none",
            }}
          />
        </AbsoluteFill>
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
const computeOverlayKey = (s: any) => {
  const explicitKey = s.card_segment_key || s.cardSegmentKey;
  if (explicitKey) return explicitKey;

  const ov = s.forensicOverlay || s.forensic_overlay;
  const statVal = s.statValue;
  const statLbl = s.statLabel;
  const badge = s.stampBadge || s.stamp_badge;
  if (!ov && !statVal && !badge) return null;

  const pos = s.foregroundPosition || "left";
  return JSON.stringify({
    ovType: ov?.type,
    ovTitle: ov?.title,
    ovPayload: ov?.payload,
    statVal,
    statLbl,
    badge,
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
    if (key && last && last.key === key) {
      last.end += dur;
    } else if (key) {
      raw.push({
        key,
        start: cursor,
        end: cursor + dur,
        forensicOverlay: s.forensicOverlay || s.forensic_overlay,
        statValue: s.statValue,
        statLabel: s.statLabel,
        stampBadge: s.stampBadge || s.stamp_badge,
        isLeft: s.foregroundPosition === "left",
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
  }));
};

const OverlaySegmentView = ({
  forensicOverlay,
  statValue,
  statLabel,
  stampBadge,
  isLeft,
}: {
  forensicOverlay?: any;
  statValue?: string;
  statLabel?: string;
  stampBadge?: string;
  isLeft: boolean;
}) => {
  const frame = useCurrentFrame();
  const statSpring = interpolate(frame, [0, 15], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  return (
    <AbsoluteFill style={{ pointerEvents: "none" }}>
      {statValue && (!forensicOverlay || (typeof forensicOverlay === "object" && forensicOverlay?.type !== "kinetic_counter")) ? (
        <div
          style={{
            position: "absolute",
            top: 60,
            left: isLeft ? "auto" : 70,
            right: isLeft ? 70 : "auto",
            zIndex: 30,
            backgroundColor: "#faf7ee",
            border: "2px solid #b45309",
            borderRadius: 6,
            padding: "14px 24px",
            boxShadow: "0 18px 40px rgba(0,0,0,0.6), 0 2px 6px rgba(0,0,0,0.3)",
            transform: `scale(${statSpring}) rotate(-1.5deg)`,
            opacity: statSpring,
            display: "flex",
            flexDirection: "column",
            gap: 2,
            fontFamily: "'Courier Prime', 'Special Elite', 'Courier New', Courier, monospace",
          }}
        >
          <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
            <span style={{ fontSize: 20 }}>📊</span>
            <div
              style={{
                color: "#b45309",
                fontSize: 34,
                fontWeight: 900,
                letterSpacing: 1,
              }}
            >
              {statValue}
            </div>
          </div>
          {statLabel ? (
            <div
              style={{
                color: "#475569",
                fontSize: 12,
                fontWeight: 700,
                letterSpacing: 1.5,
                textTransform: "uppercase",
              }}
            >
              {statLabel}
            </div>
          ) : null}
        </div>
      ) : null}

      <VoxOverlayLayer
        forensicOverlay={forensicOverlay}
        isLeft={isLeft}
        statValue={statValue}
        statLabel={statLabel}
      />

      {stampBadge ? (
        <ForensicStampBadge badge={String(stampBadge)} isLeft={isLeft} hasStatCard={Boolean(statValue)} />
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

const CinematicVignette = () => (
  <div
    style={{
      position: "absolute",
      top: 0,
      left: 0,
      width: "100%",
      height: "100%",
      background: "radial-gradient(ellipse at center, transparent 65%, rgba(0, 0, 0, 0.65) 100%)",
      zIndex: 10,
      pointerEvents: "none",
    }}
  />
);

const CinematicOverlay = () => (
  <AbsoluteFill style={{ zIndex: 20, pointerEvents: "none" }}>
    {/* Cinematic high-contrast editorial tone wash without CPU blend-mode */}
    <div
      style={{
        position: "absolute",
        inset: 0,
        background: "linear-gradient(135deg, rgba(20, 28, 45, 0.05) 0%, rgba(45, 25, 15, 0.04) 100%)",
      }}
    />
  </AbsoluteFill>
);

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

export const TwoLayerEpisode = (props) => {
  const scenes = props.scenes ? props.scenes : [];
  const backgroundFadeFrames = props.backgroundFadeFrames
    ? props.backgroundFadeFrames
    : BACKGROUND_TRANSITION_FRAMES;
  const backgroundSegments = React.useMemo(
    () => buildBackgroundSegments(scenes, backgroundFadeFrames),
    [scenes, backgroundFadeFrames]
  );
  const foregroundSegments = React.useMemo(
    () => buildForegroundSegments(scenes, 15),
    [scenes]
  );
  const overlaySegments = React.useMemo(
    () => buildOverlaySegments(scenes),
    [scenes]
  );
  if (typeof console !== "undefined" && console.warn) {
    auditForegroundCoverage(scenes, foregroundSegments);
  }
  const cfg = useVideoConfig();
  const width = cfg.width;
  const height = cfg.height;
  const currentFrame = useCurrentFrame();

  const currentSceneInfo = getCurrentSceneInfo(scenes, currentFrame);
  const currentCameraMov = currentSceneInfo
    ? currentSceneInfo.scene.cameraMovement || (currentSceneInfo.scene.camera ? currentSceneInfo.scene.camera.movement : undefined)
    : undefined;
  const currentDur = currentSceneInfo ? currentSceneInfo.durationInFrames : 300;
  const cameraTransform = currentSceneInfo
    ? computeCameraTransform(
        currentSceneInfo.scene.cameraMovement || (currentSceneInfo.scene.camera ? currentSceneInfo.scene.camera.movement : undefined),
        currentSceneInfo.scene.tensionLevel || (currentSceneInfo.scene.camera ? currentSceneInfo.scene.camera.tension_level : undefined),
        currentSceneInfo.relFrame,
        currentSceneInfo.durationInFrames
      )
    : "scale(1.0)";

  // Fake Focus Breathing & Motion Defocus Pulse (Rule 122 & "The Sauce" VOX optical aesthetic)
  const focusBlurPx = React.useMemo(() => {
    if (!currentSceneInfo) return 0;
    const { relFrame } = currentSceneInfo;
    const mov = currentCameraMov;
    if (mov === "focus_breathe_push") {
      return interpolate(relFrame, [0, 3, 6, 12, 15, 18], [0, 2.5, 0, 0, 1.8, 0], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      });
    }
    if (mov === "whip_zoom") {
      return interpolate(relFrame, [0, 2, 5], [0, 3.2, 0], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      });
    }
    if (mov === "snap_zoom" || mov === "seamless_whip_pan") {
      return interpolate(relFrame, [0, 2, 5], [0, 2.4, 0], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      });
    }
    if (mov === "dolly_zoom") {
      return interpolate(relFrame, [0, 4, 9], [0, 1.6, 0], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      });
    }
    if (relFrame <= 3) {
      return interpolate(relFrame, [0, 1, 3], [0, 0.8, 0], {
        extrapolateLeft: "clamp",
        extrapolateRight: "clamp",
      });
    }
    return 0;
  }, [currentSceneInfo, currentCameraMov]);

  const items = React.useMemo(() => {
    let cursor = 0;
    return scenes.map((s, i) => {
      const from = cursor;
      const dur = Math.max(1, Math.round(s.durationInFrames ? s.durationInFrames : 1));
      cursor += dur;
      return (
        <Sequence key={i} from={from} durationInFrames={dur} name={`scene-${i + 1}`}>
          <TwoLayerScene
            background={s.background}
            showBackground={false}
            showForeground={false}
            showOverlay={false}
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
            transition_out={s.transition_out || s.transitionOut}
            sourceCredit={s.sourceCredit || s.source_credit}
            disclosureBadge={s.disclosureBadge}
            actTitle={s.actTitle}
          />
        </Sequence>
      );
    });
  }, [scenes]);

  // Foley SFX Audio Layers (Tactile Paper, Thuds, Stamps)
  const foleyElements = React.useMemo(() => {
    let cursor = 0;
    const validSfx = [
      "sfx/counter_tick.mp3", "sfx/document_table_thud.mp3", "sfx/gavel_thud.mp3",
      "sfx/marker_stroke.mp3", "sfx/node_pop.mp3", "sfx/paper_crease_snap.mp3",
      "sfx/paper_page_turn.mp3", "sfx/paper_rustle.mp3", "sfx/paper_slide.mp3",
      "sfx/sonar_ping.mp3", "sfx/stamp_impact.mp3", "sfx/stamp_slam.mp3",
      "sfx/gauge_needle_hiss.mp3"
    ];
    return scenes.map((s, i) => {
      const from = cursor;
      const dur = Math.max(1, Math.round(s.durationInFrames ? s.durationInFrames : 1));
      cursor += dur;
      let foleySrc = s.foleysAudio || s.foleys_audio;
      if (!foleySrc) return null;
      if (!validSfx.includes(foleySrc) && !foleySrc.startsWith("http")) {
        console.warn(`[REMOTION SFX AUDIT] Scene ${i + 1} requested unverified SFX '${foleySrc}'. Skipped to prevent sound corruption.`);
        return null;
      }
      return (
        <Sequence key={`foley-${i}`} from={from} durationInFrames={Math.min(dur, 60)} name={`foley-${i + 1}`}>
          <Audio src={resolveSrc(foleySrc)} volume={0.85} />
        </Sequence>
      );
    });
  }, [scenes]);

  const audioMaster = props.audioMaster ? props.audioMaster : null;
  const bgmFile = props.bgmFile ? props.bgmFile : null;
  const bgmVolume = props.bgmVolume !== undefined ? props.bgmVolume : 0.15;

  // Auto-ducking BGM (-6dB = 0.5x volume) when Foley SFX triggers
  const getBgmVolume = React.useCallback(
    (frame: number) => {
      let multiplier = 1.0;
      let cursor = 0;
      for (let i = 0; i < scenes.length; i++) {
        const dur = Math.max(1, Math.round(scenes[i].durationInFrames ? scenes[i].durationInFrames : 1));
        if (scenes[i].foleysAudio || scenes[i].foleys_audio) {
          if (frame >= cursor && frame < cursor + 30) {
            const rel = frame - cursor;
            if (rel < 5) {
              multiplier = Math.min(multiplier, 1.0 - (rel / 5) * 0.5);
            } else if (rel < 20) {
              multiplier = Math.min(multiplier, 0.5);
            } else {
              multiplier = Math.min(multiplier, 0.5 + ((rel - 20) / 10) * 0.5);
            }
          }
        }
        cursor += dur;
      }
      return bgmVolume * multiplier;
    },
    [scenes, bgmVolume]
  );

  return (
    <AbsoluteFill style={{ backgroundColor: INK }}>
      {audioMaster ? (
        <Audio src={resolveSrc(audioMaster)} volume={1.0} />
      ) : null}
      {bgmFile ? (
        <Audio src={resolveSrc(bgmFile)} volume={getBgmVolume} />
      ) : null}
      {foleyElements}

      {/* Dynamic Cinematic Camera Container (Rule 122 & Rule 128) */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          transform: cameraTransform,
          filter: focusBlurPx > 0.05 ? `blur(${focusBlurPx.toFixed(1)}px)` : undefined,
          transformOrigin: "center center",
          willChange: "transform, filter",
        }}
      >
        <VoxParallaxLayer depth="background" cameraMovement={currentCameraMov} durationInFrames={currentDur}>
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
                hasForeground={Boolean(currentSceneInfo?.scene?.foreground || currentSceneInfo?.scene?.forensicOverlay || currentSceneInfo?.scene?.statValue)}
              />
            </Sequence>
          ))}
        </VoxParallaxLayer>
        <VoxParallaxLayer depth="foreground" cameraMovement={currentCameraMov} durationInFrames={currentDur}>
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
        </VoxParallaxLayer>
      </div>

      {/* Anti-Flicker Continuous Overlay Segments (Rule 122 & Zero-Flicker Architecture) */}
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
            />
          </Sequence>
        ))}
      </VoxParallaxLayer>

      {/* Subtitles, Speaker Tags, and Fixed UI Overlays */}
      {items}
      <VoxAtmosphericLighting intensity={0.9} />
      <CinematicVignette />
      <CinematicOverlay />
      {currentSceneInfo && (
        <CinematicTransitionOverlay
          transitionOut={currentSceneInfo.scene.transition_out || currentSceneInfo.scene.transitionOut}
          relFrame={currentSceneInfo.relFrame}
          durationInFrames={currentSceneInfo.durationInFrames}
        />
      )}
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
      {/* 3D Procedural Evidence Prop PoC (img2threejs technique) */}
      <Composition
        id="EvidenceProp3DTest"
        component={EvidenceProp3D}
        durationInFrames={90}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{
          title: "CONFIDENTIAL EVIDENCE // EXHIBIT A",
          subtitle: "IMPERIAL SEAL / AUTHENTICATION STAMP",
        }}
      />
      {/* Voxel & Stop-Motion Composition (Image-to-Video Engine) */}
      <Composition
        id="VoxelStopMotion"
        component={VoxelStopMotionVideo}
        durationInFrames={300}
        fps={30}
        width={1920}
        height={1080}
        defaultProps={{
          sceneMap: { project_id: "voxel_default", scenes: [] },
        }}
        calculateMetadata={({ props }: { props: any }) => {
          const fps = props.fps ? props.fps : 30;
          const width = props.width ? props.width : 1920;
          const height = props.height ? props.height : 1080;
          const sceneMap = props.sceneMap || { project_id: "voxel_default", scenes: [] };
          const total = calculateTotalFrames(sceneMap, fps);
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
