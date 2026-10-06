import React from "react";
import {
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
  Easing,
  Img,
} from "remotion";
import { SPRING_PRESETS } from "./springPresets";
import { useStopMotion } from "./useStopMotion";
import {
  VoxPaperBackdrop,
  VoxTornPaper,
  VoxBrassPin,
  VoxWashiTape,
  VoxStickerCutout,
  VoxConnectingYarn,
  VoxStampedLabel,
} from "./papercraft";

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
}

/**
 * VoxBuildOnStage: Authentic 7-Layer Tactile Paper Build-On Assembly Engine.
 * 
 * Recreates the WOWZ.CLOUD / AI Playbook Universal Video Motion sequence:
 * - 0.0s – 1.0s: Nền giấy cổ (Aged newsprint / archival surface) xuất hiện với spring overshoot.
 * - 1.0s – 3.5s: Hero cutout trượt vào từ cạnh khung hình với quán tính paper drag & 2-frame stamp settle.
 * - 3.5s – 5.0s: Supporting cutouts thả vào, ghim lại bằng ghim đồng (BrassPin), dán băng keo (WashiTape).
 * - 5.0s – 7.0s: Typewriter label stamp dập mạnh, dây nối đỏ vẽ từ ghim này sang ghim khác, marker vẽ nét dưới.
 * - 7.0s – 10.0s: Living Paper Poster Hold — cố định 100% vị trí, nhịp thở camera push 1.0 -> 1.03x,
 *                 bóng đổ thở nhẹ và rung giấy vật lý 12fps stop-motion jitter.
 */
export const VoxBuildOnStage: React.FC<VoxBuildOnStageProps> = ({
  headline = "THE IMPOSSIBLE CONTRADICTION",
  subtitle = "CLASSIFIED PAPER TRAIL // EXHIBIT A",
  theme = "newsprint-editorial",
  backgroundSrc,
  heroSrc,
  heroLabel = "PRIMARY OPERATOR",
  heroPosition = { xPct: 50, yPct: 52, widthPct: 36 },
  supportingCutouts = [],
  yarns = [],
  stampText = "CONFIDENTIAL // VERIFIED",
  stampColor = "#dc2626",
  hasMarkerHighlight = true,
  durationSec = 10,
}) => {
  const frame = useCurrentFrame();
  const { fps, width, height } = useVideoConfig();

  // 12fps Quantized Stop-Motion Jitter
  const { dx: jitterX, dy: jitterY, dRot: jitterRot } = useStopMotion(12, 1.2, 42);

  // Phase Timers in Frames (Adaptive to Beat Duration)
  const dSec = Math.max(1, durationSec || 10);
  const fTotal = Math.max(1, Math.round(fps * dSec));
  const speedRatio = dSec < 7.0 ? Math.max(0.2, dSec / 7.0) : 1.0;

  const fMid = Math.max(1, Math.round(fTotal * 0.65));
  const fEnd = Math.max(fMid + 1, fTotal);

  // Camera Micro-push (Hold Phase breathe 1.00 -> 1.035x)
  const cameraScale = interpolate(
    frame,
    [0, fMid, fEnd],
    [1.0, 1.015, 1.035],
    { extrapolateRight: "clamp" }
  );

  // 1. BASE BACKDROP ENTRANCE (0.0s - 1.0s)
  const backdropSpring = spring({
    frame,
    fps,
    config: SPRING_PRESETS.molassesBouncy,
  });
  const backdropScale = interpolate(backdropSpring, [0, 1], [0.94, 1.0]);
  const backdropOpacity = interpolate(backdropSpring, [0, 1], [0, 1]);

  // 2. HERO CUTOUT SLIDE & DRAG (1.0s - 3.5s)
  const heroDelayFrames = Math.round(fps * 1.0 * speedRatio);
  const heroSpring = spring({
    frame: Math.max(0, frame - heroDelayFrames),
    fps,
    config: SPRING_PRESETS.crispSnappy,
  });
  const heroStartX = -15; // slides in from off-screen left
  const heroTargetX = heroPosition.xPct;
  const heroCurrentX = interpolate(heroSpring, [0, 1], [heroStartX, heroTargetX]);
  const heroRotation = interpolate(heroSpring, [0, 0.8, 1], [-8, 2, 0]);
  const heroDropShadow = interpolate(heroSpring, [0, 1], [0, 18]);

  // 3. EDITORIAL HEADLINE STAMP (2.5s - 4.0s)
  const headlineDelayFrames = Math.round(fps * 2.2 * speedRatio);
  const headlineSpring = spring({
    frame: Math.max(0, frame - headlineDelayFrames),
    fps,
    config: SPRING_PRESETS.impactThud,
  });

  // 4. RUBBER STAMP SLAM (5.0s - 6.5s)
  const stampDelayFrames = Math.round(fps * 4.8 * speedRatio);
  const stampSpring = spring({
    frame: Math.max(0, frame - stampDelayFrames),
    fps,
    config: SPRING_PRESETS.impactThud,
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
        backgroundColor: "#0f172a", // Outer dark studio frame
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
          transform: `scale(${cameraScale}) translate(${jitterX}px, ${jitterY}px) rotate(${jitterRot}deg)`,
          transformOrigin: "center center",
          position: "relative",
        }}
      >
        {/* LAYER 0: BASE PAPER BACKDROP (0 - 1.0s) */}
        <div
          style={{
            position: "absolute",
            inset: "4%",
            backgroundColor: getThemeBackground(),
            borderRadius: "16px",
            boxShadow: "0 25px 60px -15px rgba(0,0,0,0.65), 0 0 0 1px rgba(0,0,0,0.1)",
            transform: `scale(${backdropScale})`,
            opacity: backdropOpacity,
            overflow: "hidden",
          }}
        >
          {backgroundSrc && (
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

          {/* Archival Map / Grid Coordinates watermark */}
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
            GRID REF // 35°41'22\"N 139°41'30\"E • DOC ID: RES-VOX-001
          </div>

          {/* EDITORIAL HEADLINE (Large Typography) */}
          <div
            style={{
              position: "absolute",
              top: "9%",
              left: "8%",
              right: "8%",
              zIndex: 10,
              opacity: interpolate(headlineSpring, [0, 1], [0, 1]),
              transform: `translateY(${interpolate(headlineSpring, [0, 1], [-20, 0])}px)`,
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
                fontSize: "44px",
                fontWeight: 900,
                color: "#18181b",
                lineHeight: 1.1,
                letterSpacing: "-0.03em",
                textTransform: "uppercase",
                fontFamily: "Impact, Inter, sans-serif",
                margin: 0,
                textShadow: "1px 1px 0 rgba(255,255,255,0.8)",
              }}
            >
              {headline}
            </h1>

            {/* Marker Underline Highlight */}
            {hasMarkerHighlight && (
              <div
                style={{
                  height: "8px",
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
                  mixBlendMode: "multiply",
                }}
              />
            )}
          </div>

          {/* LAYER 1: HERO CUTOUT SUBJECT (1.0s - 3.5s) */}
          <div
            style={{
              position: "absolute",
              left: `${heroCurrentX}%`,
              top: `${heroPosition.yPct}%`,
              width: `${heroPosition.widthPct}%`,
              transform: `translate(-50%, -50%) rotate(${heroRotation}deg)`,
              filter: `drop-shadow(0 ${heroDropShadow}px 24px rgba(0,0,0,0.35))`,
              zIndex: 30,
            }}
          >
            {heroSrc ? (
              <div style={{ position: "relative" }}>
                <Img
                  src={heroSrc}
                  style={{
                    width: "100%",
                    height: "auto",
                    display: "block",
                    filter: "contrast(1.15) grayscale(0.2)",
                  }}
                />
                {/* White Paper Cutout Border Simulation */}
                <div
                  style={{
                    position: "absolute",
                    inset: "-3px",
                    border: "2px solid rgba(255,255,255,0.9)",
                    pointerEvents: "none",
                    borderRadius: "4px",
                  }}
                />
              </div>
            ) : (
              /* Fallback Stylized Forensic Hero Badge */
              <div
                style={{
                  width: "280px",
                  height: "360px",
                  backgroundColor: "#e2e8f0",
                  border: "4px solid #ffffff",
                  boxShadow: "0 10px 25px rgba(0,0,0,0.25)",
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                  padding: "16px",
                  boxSizing: "border-box",
                }}
              >
                <div
                  style={{
                    width: "100%",
                    height: "75%",
                    backgroundColor: "#cbd5e1",
                    display: "flex",
                    alignItems: "center",
                    justifyContent: "center",
                    fontSize: "48px",
                  }}
                >
                  👤
                </div>
                <div
                  style={{
                    marginTop: "12px",
                    fontWeight: 800,
                    fontSize: "13px",
                    fontFamily: "monospace",
                    color: "#0f172a",
                    textAlign: "center",
                  }}
                >
                  {heroLabel}
                </div>
              </div>
            )}

            {/* Brass Pin on Hero Head */}
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

            {/* Corner Washi Tape */}
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
          </div>

          {/* LAYER 2: SUPPORTING CUTOUTS & EVIDENCE (3.5s - 5.0s) */}
          {supportingCutouts.map((cutout, idx) => {
            const defaultCutSec = (3.5 + idx * 0.4) * speedRatio;
            const cutDelayFrames = Math.round(
              fps * (cutout.delaySec !== undefined ? cutout.delaySec : defaultCutSec)
            );
            const cutSpring = spring({
              frame: Math.max(0, frame - cutDelayFrames),
              fps,
              config: SPRING_PRESETS.cardSlam,
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

          {/* LAYER 3: RED CONNECTING YARN LINES (5.0s - 7.0s) */}
          {yarns.map((yarn, yIdx) => {
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

          {/* LAYER 4: OFFICIAL RUBBER STAMP SLAM (5.0s - 6.5s) */}
          {stampText && (
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
        </div>
      </div>
    </div>
  );
};
