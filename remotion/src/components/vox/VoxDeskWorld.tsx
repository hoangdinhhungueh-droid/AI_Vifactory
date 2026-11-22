import React from "react";
import {
  AbsoluteFill,
  Audio,
  interpolate,
  spring,
  useCurrentFrame,
  useVideoConfig,
  Easing,
  Img,
  staticFile
} from "remotion";
import { SPRING_PRESETS } from "./springPresets";
import { VoxConnectingYarn } from "./papercraft/VoxConnectingYarn";
import { VoxDimensionLine } from "./papercraft/VoxDimensionLine";
import { WordTimestamp } from "../../types";

export interface EvidenceNode {
  id: string;
  label: string;
  subLabel?: string;
  stat_value?: string;
  x: number;
  y: number;
  rotation?: number;
  delay_sec?: number;
}

export interface SemanticYarn {
  from_x: number;
  from_y: number;
  to_x: number;
  to_y: number;
  label?: string;
  color?: string;
  delay_sec?: number;
}

export interface DimensionLineSpec {
  startX: number;
  endX: number;
  y: number;
  label: string;
  color?: string;
  delay_sec?: number;
}

export interface StampSpec {
  text: string;
  color?: string;
  x: number;
  y: number;
  delay_sec?: number;
}

export interface DeskStationProps {
  station_id: string;
  scene_id: string;
  title: string;
  center_x: number;
  center_y: number;
  dwell_duration_sec: number;
  hero_asset: {
    id: string;
    title: string;
    src: string;
    width: number;
    height: number;
    x: number;
    y: number;
    rotation?: number;
  };
  evidence_nodes?: EvidenceNode[];
  semantic_yarns?: SemanticYarn[];
  dimension_lines?: DimensionLineSpec[];
  stamp?: StampSpec;
}

export interface GlobalYarnProps {
  id: string;
  from_x: number;
  from_y: number;
  to_x: number;
  to_y: number;
  label: string;
  color?: string;
  delay_sec: number;
}

export interface VoxDeskWorldProps {
  act_id?: string;
  act_title?: string;
  world_width?: number;
  world_height?: number;
  stations: DeskStationProps[];
  global_yarns?: GlobalYarnProps[];
  subtitles?: WordTimestamp[];
  audio_src?: string;
}

export const VoxDeskWorld: React.FC<VoxDeskWorldProps> = ({
  act_id = "ACT I",
  act_title = "THE COLLAPSE OF GENERAL PANTS CO.",
  world_width = 3840,
  world_height = 2160,
  stations = [],
  global_yarns = [],
  subtitles = [],
  audio_src,
}) => {
  const frame = useCurrentFrame();
  const { fps, width: viewW, height: viewH } = useVideoConfig();

  // Define the 4 station timing markers in frames (30fps)
  // Station 1: 0 to 223 (7.42s)
  // Station 2: 223 to 458 (7.84s -> cum 15.26s)
  // Station 3: 458 to 706 (8.26s -> cum 23.52s)
  // Station 4: 706 to 962 (8.55s -> cum 32.07s)
  const f1_end = 223;
  const f2_end = 458;
  const f3_end = 706;
  const f4_end = 962;

  const panFrames = 38; // ~1.25s pan duration

  // --- CAMERA COORDINATE CHOREOGRAPHY (Continuous Journey) ---
  let targetCamX = 960;
  let targetCamY = 540;
  let camZoom = 1.0;

  if (frame <= f1_end - panFrames) {
    // Station 1 Dwell
    targetCamX = 960;
    targetCamY = 540;
  } else if (frame <= f1_end) {
    // Pan 1: Station 1 -> Station 2 (rightward pan)
    const panProgress = interpolate(frame, [f1_end - panFrames, f1_end], [0, 1], {
      easing: Easing.bezier(0.25, 0.1, 0.25, 1.0),
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    targetCamX = interpolate(panProgress, [0, 1], [960, 2880]);
    targetCamY = 540;
  } else if (frame <= f2_end - panFrames) {
    // Station 2 Dwell
    targetCamX = 2880;
    targetCamY = 540;
  } else if (frame <= f2_end) {
    // Pan 2: Station 2 -> Station 3 (downward pan)
    const panProgress = interpolate(frame, [f2_end - panFrames, f2_end], [0, 1], {
      easing: Easing.bezier(0.25, 0.1, 0.25, 1.0),
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    targetCamX = 2880;
    targetCamY = interpolate(panProgress, [0, 1], [540, 1620]);
  } else if (frame <= f3_end - panFrames) {
    // Station 3 Dwell
    targetCamX = 2880;
    targetCamY = 1620;
  } else if (frame <= f3_end) {
    // Pan 3: Station 3 -> Station 4 (leftward pan)
    const panProgress = interpolate(frame, [f3_end - panFrames, f3_end], [0, 1], {
      easing: Easing.bezier(0.25, 0.1, 0.25, 1.0),
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
    });
    targetCamX = interpolate(panProgress, [0, 1], [2880, 960]);
    targetCamY = 1620;
  } else {
    // Station 4 Dwell
    targetCamX = 960;
    targetCamY = 1620;
  }

  // Camera world transform
  const worldTranslateX = viewW / 2 - targetCamX * camZoom;
  const worldTranslateY = viewH / 2 - targetCamY * camZoom;

  // Subtitle synchronization (Faster-Whisper milliseconds)
  const currentTimeSec = frame / fps;
  let activeWord = "";
  let fullSentence = "";
  if (subtitles && subtitles.length > 0) {
    const activeEntry = subtitles.find(
      (w) => currentTimeSec >= w.start && currentTimeSec <= w.end
    );
    if (activeEntry) {
      activeWord = activeEntry.word;
    }
    // Find sentence context within ~3 seconds
    const contextWords = subtitles.filter(
      (w) => Math.abs(w.start - currentTimeSec) < 3.2
    );
    fullSentence = contextWords.map((w) => w.word).join(" ");
  }

  return (
    <AbsoluteFill style={{ backgroundColor: "#0A0D12", overflow: "hidden" }}>
      {audio_src && (
        <Audio
          src={
            audio_src.startsWith("http") || audio_src.startsWith("/")
              ? audio_src
              : staticFile(audio_src)
          }
        />
      )}
      {/* =========================================================================
          TOP PERSISTENT ACT HEADER & INVESTIGATION PROGRESS
          ========================================================================= */}
      <div
        style={{
          position: "absolute",
          top: 24,
          left: 48,
          right: 48,
          zIndex: 100,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          pointerEvents: "none",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div
            style={{
              backgroundColor: "#D62E1F",
              color: "#FFF",
              fontFamily: "'IBM Plex Mono', monospace",
              fontWeight: 800,
              fontSize: 14,
              letterSpacing: 2,
              padding: "4px 10px",
              borderRadius: 2,
            }}
          >
            {act_id}
          </div>
          <div
            style={{
              fontFamily: "'Syne', sans-serif",
              fontWeight: 800,
              fontSize: 16,
              color: "#1A1A1A",
              backgroundColor: "rgba(247, 244, 235, 0.92)",
              padding: "4px 14px",
              borderRadius: 2,
              border: "1px solid rgba(0,0,0,0.12)",
              letterSpacing: 1.5,
              textTransform: "uppercase",
            }}
          >
            {act_title}
          </div>
        </div>

        {/* Station indicator breadcrumb */}
        <div
          style={{
            fontFamily: "'IBM Plex Mono', monospace",
            fontSize: 13,
            color: "#FAF6EE",
            backgroundColor: "rgba(10, 15, 20, 0.75)",
            padding: "4px 12px",
            borderRadius: 2,
            border: "1px solid rgba(255,255,255,0.15)",
          }}
        >
          DESKWORLD CANVAS // 3840x2160
        </div>
      </div>

      {/* =========================================================================
          CONTINUOUS DESKWORLD CANVAS (3840 x 2160)
          ========================================================================= */}
      <div
        style={{
          position: "absolute",
          width: world_width,
          height: world_height,
          transform: `translate(${worldTranslateX}px, ${worldTranslateY}px) scale(${camZoom})`,
          transformOrigin: "0 0",
          backgroundColor: "#F4F1EA", // Authentic warm newsprint / archival paper base
          backgroundImage: `
            radial-gradient(#C4B59D 1.2px, transparent 1.2px),
            linear-gradient(to right, rgba(0,0,0,0.03) 1px, transparent 1px),
            linear-gradient(to bottom, rgba(0,0,0,0.03) 1px, transparent 1px)
          `,
          backgroundSize: "32px 32px, 120px 120px, 120px 120px",
        }}
      >
        {/* Subtle Archival Grid Divisions dividing the 4 quadrants */}
        <div
          style={{
            position: "absolute",
            left: 1920,
            top: 0,
            bottom: 0,
            width: 2,
            backgroundColor: "rgba(160, 30, 20, 0.15)",
            borderRight: "1px dashed rgba(0,0,0,0.2)",
          }}
        />
        <div
          style={{
            position: "absolute",
            top: 1080,
            left: 0,
            right: 0,
            height: 2,
            backgroundColor: "rgba(160, 30, 20, 0.15)",
            borderBottom: "1px dashed rgba(0,0,0,0.2)",
          }}
        />

        {/* ---------------------------------------------------------------------
            GLOBAL INTER-STATION CONNECTING YARNS (Physical Desk Continuum)
            --------------------------------------------------------------------- */}
        {global_yarns && global_yarns.map((gy, gIdx) => {
          const yarnStartFrame = Math.round(gy.delay_sec * fps);
          if (frame < yarnStartFrame) return null;
          return (
            <VoxConnectingYarn
              key={`global-yarn-${gIdx}`}
              fromX={(gy.from_x / world_width) * 100}
              fromY={(gy.from_y / world_height) * 100}
              toX={(gy.to_x / world_width) * 100}
              toY={(gy.to_y / world_height) * 100}
              color={gy.color || "#D62E1F"}
              yarnThickness={5.5}
              drawStartFrame={yarnStartFrame}
              drawDuration={24}
              label={gy.label}
              showPins={true}
              pinSize={32}
            />
          );
        })}

        {/* ---------------------------------------------------------------------
            RENDER THE 4 STATIONS (Evidence Assemblies)
            --------------------------------------------------------------------- */}
        {stations.map((st, sIdx) => {
          // Calculate station-relative timing
          let stationStartFrame = 0;
          if (sIdx === 1) stationStartFrame = f1_end - panFrames;
          if (sIdx === 2) stationStartFrame = f2_end - panFrames;
          if (sIdx === 3) stationStartFrame = f3_end - panFrames;

          const relFrame = Math.max(0, frame - stationStartFrame);

          // Hero impact spring (authentic Z-drop, 12fps stepped feel)
          const heroSpring = spring({
            frame: relFrame,
            fps,
            config: SPRING_PRESETS.opuscarSnappy,
          });
          const heroScale = interpolate(heroSpring, [0, 0.75, 1], [1.2, 0.98, 1.0]);
          const heroOpacity = interpolate(heroSpring, [0, 0.3, 1], [0, 1, 1]);

          // Hero Asset
          const hero = st.hero_asset;

          return (
            <div
              key={st.station_id}
              style={{
                position: "absolute",
                left: 0,
                top: 0,
                width: "100%",
                height: "100%",
                pointerEvents: "none",
              }}
            >
              {/* STATION TITLE STAMP AT TOP-LEFT OF QUADRANT */}
              <div
                style={{
                  position: "absolute",
                  left: st.center_x - 840,
                  top: st.center_y - 480,
                  zIndex: 20,
                  opacity: interpolate(heroSpring, [0, 1], [0, 0.85]),
                }}
              >
                <span
                  style={{
                    fontFamily: "'Syne', sans-serif",
                    fontWeight: 900,
                    fontSize: 32,
                    letterSpacing: 2,
                    color: "#1A1A1A",
                    textTransform: "uppercase",
                  }}
                >
                  {st.title}
                </span>
                <div
                  style={{
                    width: "100%",
                    height: 3,
                    backgroundColor: "#D62E1F",
                    marginTop: 4,
                  }}
                />
              </div>

              {/* HERO ASSET (Strictly Z-Drop Impact, Zero Horizontal Glide) */}
              <div
                style={{
                  position: "absolute",
                  left: hero.x,
                  top: hero.y,
                  width: hero.width,
                  height: hero.height,
                  zIndex: 30,
                  transform: `scale(${heroScale}) rotate(${hero.rotation || 0}deg)`,
                  opacity: heroOpacity,
                  filter: "drop-shadow(0 14px 28px rgba(0,0,0,0.32))",
                }}
              >
                <Img
                  src={staticFile(hero.src)}
                  style={{
                    width: "100%",
                    height: "100%",
                    objectFit: "contain",
                  }}
                />
              </div>

              {/* LOCAL EVIDENCE NODES (Sequential Word-Level Revelations) */}
              {st.evidence_nodes && st.evidence_nodes.map((node, nIdx) => {
                const nodeDelayFrames = Math.round(
                  fps * (node.delay_sec !== undefined ? node.delay_sec : 1.5)
                );
                const nodeRel = Math.max(0, relFrame - nodeDelayFrames);
                const nodeSpring = spring({
                  frame: nodeRel,
                  fps,
                  config: SPRING_PRESETS.opuscarSnappy,
                });
                if (relFrame < nodeDelayFrames) return null;

                const nScale = interpolate(nodeSpring, [0, 0.75, 1], [1.18, 0.98, 1.0]);
                const nOpacity = interpolate(nodeSpring, [0, 0.3, 1], [0, 1, 1]);

                return (
                  <div
                    key={`node-${st.station_id}-${nIdx}`}
                    style={{
                      position: "absolute",
                      left: node.x,
                      top: node.y,
                      zIndex: 35,
                      transform: `scale(${nScale}) rotate(${node.rotation || 0}deg)`,
                      opacity: nOpacity,
                      backgroundColor: node.stat_value ? "#D62E1F" : "#FFFFFF",
                      color: node.stat_value ? "#FFFFFF" : "#1A1A1A",
                      padding: node.stat_value ? "14px 22px" : "12px 18px",
                      borderRadius: 2,
                      boxShadow: "0 8px 24px rgba(0,0,0,0.22)",
                      border: node.stat_value ? "2px solid #991B1B" : "1px solid #D1D5DB",
                      maxWidth: 340,
                    }}
                  >
                    {node.stat_value ? (
                      <div>
                        <div
                          style={{
                            fontFamily: "'IBM Plex Mono', monospace",
                            fontSize: 11,
                            letterSpacing: 1.5,
                            opacity: 0.85,
                            textTransform: "uppercase",
                          }}
                        >
                          {node.label}
                        </div>
                        <div
                          style={{
                            fontFamily: "'Syne', sans-serif",
                            fontWeight: 900,
                            fontSize: 42,
                            lineHeight: 1.05,
                            letterSpacing: -1,
                          }}
                        >
                          {node.stat_value}
                        </div>
                      </div>
                    ) : (
                      <div>
                        <div
                          style={{
                            fontFamily: "'Syne', sans-serif",
                            fontWeight: 800,
                            fontSize: 14,
                            textTransform: "uppercase",
                            letterSpacing: 0.5,
                            color: "#B91C1C",
                          }}
                        >
                          {node.label}
                        </div>
                        {node.subLabel && (
                          <div
                            style={{
                              fontFamily: "'IBM Plex Mono', monospace",
                              fontSize: 12,
                              color: "#4B5563",
                              marginTop: 4,
                            }}
                          >
                            {node.subLabel}
                          </div>
                        )}
                      </div>
                    )}
                  </div>
                );
              })}

              {/* LOCAL SEMANTIC YARNS */}
              {st.semantic_yarns && st.semantic_yarns.map((sy, syIdx) => {
                const sYarnDelayFrames = Math.round(
                  fps * (sy.delay_sec !== undefined ? sy.delay_sec : 1.2)
                );
                if (relFrame < sYarnDelayFrames) return null;
                return (
                  <VoxConnectingYarn
                    key={`local-yarn-${st.station_id}-${syIdx}`}
                    fromX={(sy.from_x / world_width) * 100}
                    fromY={(sy.from_y / world_height) * 100}
                    toX={(sy.to_x / world_width) * 100}
                    toY={(sy.to_y / world_height) * 100}
                    color={sy.color || "#D62E1F"}
                    yarnThickness={4.5}
                    drawStartFrame={sYarnDelayFrames}
                    drawDuration={18}
                    label={sy.label}
                    showPins={true}
                    pinSize={24}
                  />
                );
              })}

              {/* LOCAL DIMENSION LINES */}
              {st.dimension_lines && st.dimension_lines.map((dim, dIdx) => {
                const dimDelayFrames = Math.round(
                  fps * (dim.delay_sec !== undefined ? dim.delay_sec : 2.0)
                );
                if (relFrame < dimDelayFrames) return null;
                return (
                  <VoxDimensionLine
                    key={`dim-${st.station_id}-${dIdx}`}
                    startX={(dim.startX / world_width) * 100}
                    endX={(dim.endX / world_width) * 100}
                    y={(dim.y / world_height) * 100}
                    label={dim.label}
                    color={dim.color || "#DC2626"}
                    startFrame={dimDelayFrames}
                  />
                );
              })}

              {/* RUBBER STAMP SLAM AT PAYOFF */}
              {st.stamp && (() => {
                const stampDelay = Math.round(fps * (st.stamp.delay_sec || 3.5));
                const stampRel = Math.max(0, relFrame - stampDelay);
                if (relFrame < stampDelay) return null;

                const stampSpring = spring({
                  frame: stampRel,
                  fps,
                  config: { damping: 12, mass: 0.35, stiffness: 420 },
                });
                const sScale = interpolate(stampSpring, [0, 0.7, 1], [2.2, 0.94, 1.0]);
                const sOpacity = interpolate(stampSpring, [0, 0.2, 1], [0, 0.9, 0.9]);

                return (
                  <div
                    style={{
                      position: "absolute",
                      left: st.stamp.x,
                      top: st.stamp.y,
                      zIndex: 45,
                      transform: `scale(${sScale}) rotate(-12deg)`,
                      opacity: sOpacity,
                      border: `4px solid ${st.stamp.color || "#D62E1F"}`,
                      borderRadius: 4,
                      padding: "8px 18px",
                      fontFamily: "'Syne', sans-serif",
                      fontWeight: 900,
                      fontSize: 22,
                      letterSpacing: 2,
                      color: st.stamp.color || "#D62E1F",
                      textTransform: "uppercase",
                      backgroundColor: "rgba(244, 241, 234, 0.85)",
                    }}
                  >
                    {st.stamp.text}
                  </div>
                );
              })()}
            </div>
          );
        })}
      </div>

      {/* =========================================================================
          BOTTOM KARAOKE SUBTITLE STRIP (Faster-Whisper Millisecond Sync)
          ========================================================================= */}
      {fullSentence && (
        <div
          style={{
            position: "absolute",
            bottom: 36,
            left: "50%",
            transform: "translateX(-50%)",
            zIndex: 100,
            maxWidth: 1200,
            textAlign: "center",
          }}
        >
          <div
            style={{
              display: "inline-block",
              backgroundColor: "rgba(10, 15, 20, 0.88)",
              backdropFilter: "blur(8px)",
              padding: "10px 24px",
              borderRadius: 6,
              border: "1px solid rgba(255,255,255,0.12)",
              boxShadow: "0 12px 32px rgba(0,0,0,0.45)",
            }}
          >
            <span
              style={{
                fontFamily: "'Syne', sans-serif",
                fontWeight: 700,
                fontSize: 24,
                color: "#E5E7EB",
                letterSpacing: 0.5,
              }}
            >
              {fullSentence.split(" ").map((w, idx) => {
                const isHighlight =
                  activeWord &&
                  w.toLowerCase().replace(/[^a-z0-9]/g, "") ===
                    activeWord.toLowerCase().replace(/[^a-z0-9]/g, "");
                return (
                  <span
                    key={`word-${idx}`}
                    style={{
                      color: isHighlight ? "#F59E0B" : "#FFFFFF",
                      fontWeight: isHighlight ? 900 : 600,
                      textShadow: isHighlight
                        ? "0 0 16px rgba(245, 158, 11, 0.75)"
                        : "none",
                      marginRight: 8,
                    }}
                  >
                    {w}
                  </span>
                );
              })}
            </span>
          </div>
        </div>
      )}
    </AbsoluteFill>
  );
};
