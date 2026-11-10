import React from "react";
import {
  AbsoluteFill,
  Audio,
  interpolate,
  Sequence,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
  Img,
} from "remotion";
import { VoxTornPaper } from "./papercraft/VoxTornPaper";
import { VoxWashiTape } from "./papercraft/VoxWashiTape";
import { VoxBrassPin } from "./papercraft/VoxBrassPin";
import { VoxConnectingYarn } from "./papercraft/VoxConnectingYarn";
import { PhysicalStampSlam } from "../kinetics/PhysicalStampSlam";
import { ProceduralMarkerSweep } from "../kinetics/ProceduralMarkerSweep";

export interface WordTimestamp {
  word: string;
  start: number;
  end: number;
  start_ms: number;
  end_ms: number;
}

export interface BroadcastVoxBenchmarkProps {
  variant?: "cinematic_investigation" | "tactile_paper_collage";
  subtitles?: WordTimestamp[];
  bgImageSrc?: string;
  heroImageSrc?: string;
  audioNarrationSrc?: string;
}

const DEFAULT_SUBTITLES: WordTimestamp[] = [
  { word: "英国", start: 0.0, end: 0.46, start_ms: 0.0, end_ms: 460.0 },
  { word: "の", start: 0.46, end: 0.68, start_ms: 460.0, end_ms: 680.0 },
  { word: "専門家", start: 0.68, end: 1.42, start_ms: 680.0, end_ms: 1420.0 },
  { word: "が", start: 1.42, end: 1.62, start_ms: 1420.0, end_ms: 1620.0 },
  { word: "警告", start: 1.62, end: 2.24, start_ms: 1620.0, end_ms: 2240.0 },
  { word: "する、", start: 2.24, end: 2.78, start_ms: 2240.0, end_ms: 2780.0 },
  { word: "身代金", start: 2.78, end: 3.42, start_ms: 2780.0, end_ms: 3420.0 },
  { word: "交渉", start: 3.42, end: 3.96, start_ms: 3420.0, end_ms: 3960.0 },
  { word: "の", start: 3.96, end: 4.14, start_ms: 3960.0, end_ms: 4140.0 },
  { word: "効率", start: 4.14, end: 4.58, start_ms: 4140.0, end_ms: 4580.0 },
  { word: "10倍。", start: 4.58, end: 5.38, start_ms: 4580.0, end_ms: 5380.0 },
];

export const BroadcastVoxBenchmark: React.FC<BroadcastVoxBenchmarkProps> = ({
  variant = "cinematic_investigation",
  subtitles = DEFAULT_SUBTITLES,
  bgImageSrc,
  heroImageSrc,
  audioNarrationSrc,
}) => {
  const frame = useCurrentFrame();
  const { fps = 30, width = 1920, height = 1080 } = useVideoConfig();

  // For tactile stop-motion mode, posterize time on twos (12fps feel)
  const isStopMotion = variant === "tactile_paper_collage";
  const steppedFrame = isStopMotion ? Math.floor(frame / 2) * 2 : frame;

  // Master Stepped Crash Zoom at frame 55 (approx 1.83s, right as "身代金交渉の効率10倍" begins)
  const punchStart = 55;
  const punchRel = Math.max(0, steppedFrame - punchStart);
  const punchSpring = spring({
    frame: punchRel,
    fps,
    config: { damping: 14, mass: 0.35, stiffness: 240 },
  });

  const zoomScale = interpolate(punchSpring, [0, 1], [1.0, 1.26]);
  const panX = interpolate(punchSpring, [0, 1], [0, -120]);
  const panY = interpolate(punchSpring, [0, 1], [0, -40]);
  const tiltDeg = interpolate(punchSpring, [0, 1], [0, -1.2]);

  // Impact shake when the red stamp hits at frame 80
  const slamTargetFrame = 80;
  const slamRel = steppedFrame - slamTargetFrame;
  const impactShakeY =
    slamRel === 1
      ? -7.0
      : slamRel === 2
      ? 5.0
      : slamRel === 3
      ? -3.0
      : slamRel === 4
      ? 1.5
      : 0;
  const impactFlash = slamRel === 1 ? 0.35 : slamRel === 2 ? 0.15 : 0;

  // Current time in milliseconds for Whisper karaoke
  const currentMs = (frame / fps) * 1000;

  // Background selection with safe staticFile fallback
  const resolvedBg = bgImageSrc
    ? bgImageSrc.startsWith("http")
      ? bgImageSrc
      : staticFile(bgImageSrc)
    : variant === "cinematic_investigation"
    ? staticFile("images/bg_forensic_archive_vault.png")
    : staticFile("images/opuscar_scene_02_bg.jpg");

  const resolvedHero = heroImageSrc
    ? heroImageSrc.startsWith("http")
      ? heroImageSrc
      : staticFile(heroImageSrc)
    : staticFile("images/fg_evidence_merchant_accounting_ledger.png");

  const resolvedAudio = audioNarrationSrc
    ? audioNarrationSrc.startsWith("http")
      ? audioNarrationSrc
      : staticFile(audioNarrationSrc)
    : staticFile("audio/scene_02_voice.mp3");

  const wordsToRender = subtitles && subtitles.length > 0 ? subtitles : DEFAULT_SUBTITLES;

  return (
    <AbsoluteFill style={{ backgroundColor: "#080c14", overflow: "hidden" }}>
      {/* AUDIO TRACKS: Narration + Subtle Ambient BGM + Tactile SFX */}
      <Audio src={resolvedAudio} volume={1.0} />
      <Audio src={staticFile("bgm/vox_cinematic_pulse.mp3")} volume={0.16} />
      
      {/* Paper deal SFX at frame 15 */}
      <Sequence from={15} durationInFrames={30}>
        <Audio src={staticFile("sfx/paper_slide.mp3")} volume={0.45} />
      </Sequence>

      {/* Highlighter marker stroke SFX at frame 30 */}
      <Sequence from={30} durationInFrames={35}>
        <Audio src={staticFile("sfx/marker_stroke.mp3")} volume={0.4} />
      </Sequence>

      {/* Heavy stamp impact SFX at frame 80 */}
      <Sequence from={80} durationInFrames={40}>
        <Audio src={staticFile("sfx/stamp_slam.mp3")} volume={0.85} />
      </Sequence>

      {/* MASTER LIVING CAMERA RIG WITH STEPPED CRASH ZOOM & IMPACT SHAKE */}
      <div
        style={{
          width: "100%",
          height: "100%",
          transform: `translate3d(${panX}px, ${panY + impactShakeY}px, 0) scale(${zoomScale}) rotate(${tiltDeg}deg)`,
          transformOrigin: "65% 50%",
          position: "relative",
        }}
      >
        {/* LAYER 0: CINEMATIC ARCHIVAL DESK BACKGROUND */}
        <AbsoluteFill>
          <Img
            src={resolvedBg}
            style={{
              width: "100%",
              height: "100%",
              objectFit: "cover",
              filter:
                variant === "cinematic_investigation"
                  ? "brightness(0.72) contrast(1.15) saturate(0.85)"
                  : "brightness(0.88) contrast(1.05)",
            }}
          />
          {/* Subtle Warm Spotlight Vignette */}
          <div
            style={{
              position: "absolute",
              inset: 0,
              background:
                "radial-gradient(circle at 60% 45%, rgba(254, 243, 199, 0.12) 0%, rgba(0, 0, 0, 0.65) 85%)",
              pointerEvents: "none",
            }}
          />
        </AbsoluteFill>

        {/* LAYER 1: HERO JAPANESE ACCOUNTING LEDGER (PHYSICAL EXHIBIT) */}
        <div
          style={{
            position: "absolute",
            right: "10%",
            top: "48%",
            width: "48%",
            transform: "translate(0, -50%) rotate(2.5deg)",
            filter: "drop-shadow(0 25px 50px rgba(0, 0, 0, 0.65))",
            zIndex: 10,
          }}
        >
          <div style={{ position: "relative" }}>
            <Img
              src={resolvedHero}
              style={{
                width: "100%",
                height: "auto",
                display: "block",
                filter: "contrast(1.08)",
              }}
            />

            {/* Tactile Halftone 10X Headline Cardstock Pinned onto Ledger */}
            <div
              style={{
                position: "absolute",
                right: "14%",
                top: "18%",
                backgroundColor: "#FAF7EE",
                border: "2px solid #0F172A",
                padding: "16px 26px",
                transform: "rotate(-3.5deg)",
                boxShadow: "0 16px 32px rgba(0, 0, 0, 0.45)",
                zIndex: 15,
              }}
            >
              {/* Washi tape pinning the 10X card */}
              <div style={{ position: "absolute", top: "-12px", right: "-14px", zIndex: 20 }}>
                <VoxWashiTape color="yellow" width={90} height={26} rotation={22} dropFrame={12} />
              </div>
              <div
                style={{
                  fontFamily: "'Impact', 'Arial Black', sans-serif",
                  fontSize: "82px",
                  lineHeight: "0.88",
                  color: "#0F172A",
                  letterSpacing: "0.02em",
                  textAlign: "center",
                }}
              >
                10X
              </div>
              <div
                style={{
                  fontFamily: "'Courier Prime', monospace",
                  fontSize: "11px",
                  fontWeight: 900,
                  color: "#DC2626",
                  letterSpacing: "0.18em",
                  marginTop: "6px",
                  textAlign: "center",
                  borderTop: "1.5px dashed #DC2626",
                  paddingTop: "4px",
                }}
              >
                NEGOTIATION EFFICIENCY
              </div>
            </div>

            {/* Official Red Rubber Stamp Slam onto the Ledger */}
            <PhysicalStampSlam
              label="EVIDENCE // VERIFIED"
              subLabel="CRIME FORENSIC DISPATCH"
              theme="danger"
              color="#DC2626"
              slamFrame={slamTargetFrame}
              rotation={-6.5}
              scaleMultiplier={1.15}
              style={{
                position: "absolute",
                left: "18%",
                bottom: "16%",
                zIndex: 25,
              }}
            />
          </div>
        </div>

        {/* LAYER 2: UK EXPERT DOSSIER CARD (SLIDES IN LIKE A DEALT POKER CARD) */}
        {(() => {
          const cardEntry = spring({
            frame: Math.max(0, steppedFrame - 15),
            fps,
            config: { damping: 13, mass: 0.5, stiffness: 180 },
          });
          const cardX = interpolate(cardEntry, [0, 1], [-450, 420]);
          const cardRot = interpolate(cardEntry, [0, 0.8, 1], [-12, -2, -3.5]);

          return (
            <VoxTornPaper
              width={460}
              height="auto"
              x={cardX}
              y={440}
              rotation={cardRot}
              color="cream"
              roughness="medium"
              hasTapeTopLeft={true}
              hasPinTopRight={true}
              style={{
                zIndex: 20,
              }}
            >
              {/* Dossier Header Tag */}
              <div
                style={{
                  display: "inline-block",
                  backgroundColor: "#0F172A",
                  color: "#F8FAFC",
                  fontFamily: "'Courier Prime', monospace",
                  fontSize: "11px",
                  fontWeight: 900,
                  letterSpacing: "0.14em",
                  padding: "3px 8px",
                  marginBottom: "12px",
                }}
              >
                UK FORENSIC EXPERT REPORT // 2026.10.09
              </div>

              {/* Japanese Warning Subject */}
              <div
                style={{
                  fontFamily: "'Hiragino Kaku Gothic ProN', 'Yu Gothic', sans-serif",
                  fontSize: "19px",
                  fontWeight: 900,
                  color: "#0F172A",
                  lineHeight: "1.4",
                  marginBottom: "14px",
                }}
              >
                英国の専門家が警告する重大事態
              </div>

              {/* Evidence Clause with Signature Procedural Fluorescent Marker Sweep */}
              <div style={{ marginBottom: "14px" }}>
                <ProceduralMarkerSweep
                  startFrame={30}
                  durationFrames={16}
                  color="#FFE600"
                  height="1.35em"
                  blendMode="multiply"
                >
                  <span
                    style={{
                      fontFamily: "'Hiragino Kaku Gothic ProN', sans-serif",
                      fontSize: "17px",
                      fontWeight: 900,
                      color: "#DC2626",
                    }}
                  >
                    「身代金交渉の効率10倍」
                  </span>
                </ProceduralMarkerSweep>
              </div>

              {/* Monospace Metadata Chips */}
              <div
                style={{
                  borderTop: "1px dashed rgba(15, 23, 42, 0.25)",
                  paddingTop: "10px",
                  display: "flex",
                  justifyContent: "space-between",
                  fontFamily: "'Courier Prime', monospace",
                  fontSize: "11px",
                  color: "#475569",
                }}
              >
                <span>SOURCE: SCOTLAND YARD CYBER</span>
                <span style={{ color: "#DC2626", fontWeight: 700 }}>STATUS: CONFIDENTIAL</span>
              </div>
            </VoxTornPaper>
          );
        })()}

        {/* LAYER 3: 3D CATENARY RED CONNECTING YARN */}
        {/* Connects the UK Dossier to the Ledger 10X Card */}
        <VoxConnectingYarn
          fromX={540}
          fromY={380}
          toX={1180}
          toY={430}
          color="#DC2626"
          yarnThickness={3.8}
          sagAmount={32}
          drawStartFrame={32}
          drawDuration={18}
          showPins={false}
        />

        {/* Impact White Flash Layer */}
        {impactFlash > 0 && (
          <AbsoluteFill
            style={{
              backgroundColor: "#FFFFFF",
              opacity: impactFlash,
              pointerEvents: "none",
              zIndex: 90,
            }}
          />
        )}

        {/* Subtle Archival Film / Paper Dust Grain */}
        <div
          style={{
            position: "absolute",
            inset: 0,
            backgroundImage:
              "radial-gradient(rgba(0, 0, 0, 0.08) 1px, transparent 1px), radial-gradient(rgba(255, 255, 255, 0.04) 1px, transparent 1px)",
            backgroundSize: "8px 8px, 12px 12px",
            backgroundPosition: `${(steppedFrame * 7) % 32}px ${(steppedFrame * 11) % 32}px`,
            pointerEvents: "none",
            opacity: isStopMotion ? 0.35 : 0.18,
            zIndex: 85,
          }}
        />
      </div>

      {/* FIXED BROADCAST HUD: TOP-LEFT ACT & LOWER-THIRD KARAOKE SUBTITLES */}
      {/* Top Left Editorial Header */}
      <div
        style={{
          position: "absolute",
          top: "48px",
          left: "56px",
          zIndex: 100,
          display: "flex",
          alignItems: "center",
          gap: "12px",
        }}
      >
        <span
          style={{
            backgroundColor: "#DC2626",
            color: "#FFFFFF",
            fontFamily: "'Courier Prime', monospace",
            fontSize: "12px",
            fontWeight: 900,
            letterSpacing: "0.16em",
            padding: "4px 10px",
            boxShadow: "0 4px 12px rgba(220, 38, 38, 0.4)",
          }}
        >
          ACT I // THE EXPOSURE
        </span>
        <span
          style={{
            fontFamily: "'Impact', 'Arial Black', sans-serif",
            fontSize: "20px",
            color: "#FFFFFF",
            letterSpacing: "0.08em",
            textTransform: "uppercase",
            textShadow: "0 2px 8px rgba(0,0,0,0.8)",
          }}
        >
          THE 10X MULTIPLIER
        </span>
      </div>

      {/* Elegant Broadcast Subtitle Glass Pill with Word-Level Whisper Karaoke */}
      <div
        style={{
          position: "absolute",
          bottom: "48px",
          left: "50%",
          transform: "translateX(-50%)",
          zIndex: 100,
          backgroundColor: "rgba(10, 15, 26, 0.85)",
          border: "1.5px solid rgba(255, 255, 255, 0.12)",
          borderRadius: "8px",
          padding: "10px 28px",
          boxShadow: "0 16px 36px rgba(0, 0, 0, 0.65), inset 0 1px 0 rgba(255,255,255,0.15)",
          backdropFilter: "blur(12px)",
          display: "flex",
          gap: "6px",
          alignItems: "center",
          whiteSpace: "nowrap",
        }}
      >
        {wordsToRender.map((w, wIdx) => {
          const isWordActive = currentMs >= w.start_ms && currentMs <= w.end_ms;
          const isWordPast = currentMs > w.end_ms;

          return (
            <span
              key={wIdx}
              style={{
                fontFamily: "'Hiragino Kaku Gothic ProN', 'Yu Gothic', sans-serif",
                fontSize: "25px",
                fontWeight: 900,
                color: isWordActive ? "#FDE047" : isWordPast ? "#FFFFFF" : "rgba(255, 255, 255, 0.4)",
                textShadow: isWordActive
                  ? "0 0 16px rgba(253, 224, 71, 0.7), 0 2px 6px rgba(0,0,0,0.9)"
                  : "0 2px 4px rgba(0,0,0,0.8)",
                transform: isWordActive ? "scale(1.08)" : "scale(1.0)",
                display: "inline-block",
                padding: "0 2px",
                transition: "none",
              }}
            >
              {w.word}
            </span>
          );
        })}
      </div>
    </AbsoluteFill>
  );
};
