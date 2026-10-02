import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig, Easing, Img, staticFile } from "remotion";
import { SPRING_PRESETS } from "./springPresets";

export interface VoxConnectionItem {
  fromX: number; // % of board width
  fromY: number; // % of board height
  toX: number;   // % of board width
  toY: number;   // % of board height
  label?: string; // e.g. "40 MIN TO DISAPPEARANCE"
  color?: string; // default red #ef4444 or gold #f59e0b
  drawStartFrame?: number; // default 30
  drawDuration?: number;   // default 20
  isYarn?: boolean;        // textured red yarn vs neon arrow
}

export interface VoxSupportingCutoutItem {
  src?: string;
  icon?: string;
  label?: string;
  xPct: number; // % of board width
  yPct: number; // % of board height
  width?: number;
  height?: number;
  dropFrame?: number; // frame at which this element drops
  rotation?: number;  // degrees
}

export interface VoxCompositeStageProps {
  /** Scene Title / Header */
  title?: string;
  badge?: string;
  category?: string;

  /** Stage Dimensions / Layout */
  layout?: "full_bleed_focus" | "split_right" | "split_left" | string;

  /** Visual Theme: dark forensic dossier vs warm vintage paper (AI Playbook style) */
  theme?: "dark_forensic" | "vintage_paper" | "blueprint";

  /** Background Configuration */
  backgroundType?: "vintage_map" | "blueprint_grid" | "archival_desk" | "dark_forensic";
  backgroundLabel?: string;

  /** Large Editorial Headline Typography (1-4 Words, AI Playbook style) */
  editorialHeadline?: {
    text: string;
    subtext?: string;
    placement?: "top_center" | "stamp_overlay" | "background_large";
    color?: string;
    frame?: number;
  };

  /** Primary Dossier Document */
  dossierTitle?: string;
  dossierAgency?: string;
  dossierDate?: string;
  dossierText?: string;
  highlightPhrase?: string;
  redactedPhrases?: string[];
  dogEarCorner?: "top-right" | "bottom-right" | "none";

  /** Cutout Subject (Photo / Character / Asset) */
  cutoutSrc?: string;
  cutoutLabel?: string;
  cutoutRole?: string;
  cutoutPosition?: { xPct: number; yPct: number; width?: number; height?: number };

  /** Secondary / Supporting Cutouts & Badges (AI Playbook seconds 35, 38, 41) */
  supportingCutouts?: VoxSupportingCutoutItem[];

  /** Primary Connecting Vector Arrow / Red Yarn */
  connection?: VoxConnectionItem;

  /** Multiple Radiating Connections (AI Playbook seconds 39 & 47) */
  radiatingConnections?: VoxConnectionItem[];

  /** Red Rubber Stamp / Certification */
  stampText?: string; // e.g. "239 PEOPLE", "CRIMINAL FRAUD", "RESTRICTED", "MARKETING WINS"
  stampColor?: string; // default #dc2626
  stampFrame?: number; // default 65

  /** Pushpin / Tape Details */
  hasPushpin?: boolean;
  pinPosition?: { xPct: number; yPct: number };
  hasCornerTape?: boolean;
}

export const VoxCompositeStage: React.FC<VoxCompositeStageProps> = ({
  title = "INCIDENT RECONSTRUCTION // FORENSIC TIMELINE",
  badge = "TACTILE DOSSIER // ACT I",
  category = "FLIGHT ANOMALY",
  layout = "full_bleed_focus",
  theme = "dark_forensic",
  backgroundType = "vintage_map",
  backgroundLabel = "SOUTHEAST ASIA NAUTICAL SECTOR // RADAR SWEEP",
  editorialHeadline,
  dossierTitle = "CIVILIAN RADAR TELEMETRY RECORD",
  dossierAgency = "DEPARTMENT OF CIVIL AVIATION",
  dossierDate = "MAR 8, 2014 // 01:19 UTC",
  dossierText = "Forty minutes after departure, transponder transmission abruptly terminated near waypoint IGARI. Military primary radar tracked an unidentified return executing an immediate westward tactical bank.",
  highlightPhrase = "executing an immediate westward tactical bank",
  redactedPhrases = ["CLASSIFIED PROTOCOL", "INTERCEPT DISPATCH"],
  dogEarCorner = "bottom-right",
  cutoutSrc,
  cutoutLabel = "BOEING 777-200ER",
  cutoutRole = "MALAYSIA AIRLINES // MH370",
  cutoutPosition = { xPct: 68, yPct: 42, width: 280, height: 280 },
  supportingCutouts = [],
  connection = {
    fromX: 30,
    fromY: 55,
    toX: 68,
    toY: 42,
    label: "40 MIN TO DISAPPEARANCE",
    color: "#ef4444",
    drawStartFrame: 30,
    drawDuration: 22,
    isYarn: true,
  },
  radiatingConnections = [],
  stampText = "239 PEOPLE",
  stampColor = "#dc2626",
  stampFrame = 62,
  hasPushpin = true,
  pinPosition = { xPct: 30, yPct: 55 },
  hasCornerTape = true,
}) => {
  const frame = useCurrentFrame();
  const { fps, width: canvasW = 1920, height: canvasH = 1080, durationInFrames = 150 } = useVideoConfig();

  // 12fps tactile stop-motion quantization
  const stepF = Math.floor(frame / 2.5) * 2.5;

  const isFullBleed = layout === "full_bleed_focus";
  const boardW = isFullBleed ? 1580 : 1050;
  const boardH = isFullBleed ? 880 : 640;

  // ==========================================
  // PHASE 1: Living Camera Drift & Master Canvas Entrance
  // ==========================================
  const masterSpring = spring({
    frame: stepF,
    fps,
    config: { damping: 14, mass: 0.7, stiffness: 110 },
  });

  // Slow continuous living camera creep throughout the scene (Vox / AI Playbook: drift <= 4%)
  const cameraZoom = interpolate(frame, [0, durationInFrames], [1.0, 1.045], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const cameraPanX = interpolate(frame, [0, durationInFrames], [0, -18], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });

  // Stamp impact screen shake
  const shakeFrame = Math.max(0, frame - stampFrame);
  const shakeAmp = interpolate(shakeFrame, [0, 2, 8, 16], [0, 7, 2, 0], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  const shakeX = Math.sin(shakeFrame * 2.8) * shakeAmp;
  const shakeY = Math.cos(shakeFrame * 3.2) * shakeAmp;

  // ==========================================
  // PHASE 2: Archival Paper Dossier Drop (Frame 6-18)
  // ==========================================
  const dossierDrop = spring({
    frame: Math.max(0, stepF - 6),
    fps,
    config: SPRING_PRESETS.paperSlide,
  });
  const dossierY = interpolate(dossierDrop, [0, 1], [-80, 0]);
  const dossierScale = interpolate(dossierDrop, [0, 1], [0.85, 1.0]);
  const dossierShadow = interpolate(dossierDrop, [0, 1], [40, 18]);

  // ==========================================
  // PHASE 3: Corner Masking Tape & Pushpin (Frame 16-25)
  // ==========================================
  const tapeSpring = spring({
    frame: Math.max(0, stepF - 16),
    fps,
    config: SPRING_PRESETS.labelSnap,
  });

  const pinSpring = spring({
    frame: Math.max(0, stepF - 20),
    fps,
    config: { damping: 9, mass: 0.4, stiffness: 240 },
  });

  // ==========================================
  // PHASE 4: Primary Photographic / Comic Cutout Drop (Frame 20-35)
  // ==========================================
  const cutoutSpring = spring({
    frame: Math.max(0, stepF - 20),
    fps,
    config: { damping: 11, mass: 0.55, stiffness: 130 },
  });

  // ==========================================
  // PHASE 5: Highlighter Sweep & Rubber Stamp Slam (Frame 50-80)
  // ==========================================
  const hlStart = 48;
  const hlProgress = interpolate(frame, [hlStart, hlStart + 24], [0, 100], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.2, 0.9, 0.4, 1),
  });

  const stampSpring = spring({
    frame: Math.max(0, frame - stampFrame),
    fps,
    config: SPRING_PRESETS.stamp,
  });
  const stampScale = interpolate(stampSpring, [0, 1], [2.2, 1.0]);
  const stampOpacity = interpolate(stampSpring, [0, 0.3], [0, 1], { extrapolateRight: "clamp" });

  // Editorial Headline Spring (if present)
  const edHeadFrame = editorialHeadline?.frame ?? 12;
  const headlineSpring = spring({
    frame: Math.max(0, stepF - edHeadFrame),
    fps,
    config: SPRING_PRESETS.stamp,
  });

  // Consolidate connections list
  const allConnections: VoxConnectionItem[] = [
    ...(connection ? [connection] : []),
    ...(radiatingConnections || []),
  ];

  // Theme styling rules
  const isVintagePaper = theme === "vintage_paper";
  const boardBg = isVintagePaper ? "#fbf8ee" : "#0d131f";
  const boardBorder = isVintagePaper ? "2px solid #c9b99a" : "2px solid rgba(242, 166, 59, 0.5)";
  const boardBoxShadow = isVintagePaper
    ? "0 30px 80px rgba(60, 45, 25, 0.35), inset 0 0 45px rgba(210, 180, 130, 0.2)"
    : "0 30px 80px rgba(0, 0, 0, 0.85), inset 0 0 40px rgba(0, 0, 0, 0.6)";
  const headerTextColor = isVintagePaper ? "#78350f" : "#fbbf24";
  const headerSubColor = isVintagePaper ? "#57534e" : "#94a3b8";

  return (
    <div
      style={{
        width: boardW,
        height: boardH,
        position: "relative",
        transform: `translate(${cameraPanX + shakeX}px, ${shakeY}px) scale(${masterSpring * cameraZoom})`,
        transformOrigin: "center center",
        backgroundColor: boardBg,
        backgroundImage: isVintagePaper
          ? `
            radial-gradient(rgba(120, 80, 40, 0.08) 1.5px, transparent 1.5px),
            linear-gradient(to right, rgba(0, 0, 0, 0.04) 1px, transparent 1px),
            linear-gradient(to bottom, rgba(0, 0, 0, 0.04) 1px, transparent 1px)
          `
          : `
            radial-gradient(rgba(242, 166, 59, 0.08) 1.5px, transparent 1.5px),
            linear-gradient(to right, rgba(255, 255, 255, 0.03) 1px, transparent 1px),
            linear-gradient(to bottom, rgba(255, 255, 255, 0.03) 1px, transparent 1px)
          `,
        backgroundSize: "28px 28px, 140px 140px, 140px 140px",
        borderRadius: 16,
        border: boardBorder,
        boxShadow: boardBoxShadow,
        padding: "24px 32px",
        overflow: "hidden",
        fontFamily: "'Courier Prime', 'Special Elite', 'Courier New', monospace",
        color: isVintagePaper ? "#1c1917" : "#ffffff",
      }}
    >
      {/* Background Large Editorial Headline (AI Playbook Prompt 2: 20-50% composition) */}
      {editorialHeadline && editorialHeadline.placement === "background_large" ? (
        <div
          style={{
            position: "absolute",
            top: "22%",
            left: "5%",
            width: "90%",
            textAlign: "center",
            fontSize: isFullBleed ? 130 : 96,
            fontWeight: 900,
            letterSpacing: 8,
            textTransform: "uppercase",
            color: editorialHeadline.color || (isVintagePaper ? "rgba(120, 53, 15, 0.12)" : "rgba(255, 255, 255, 0.06)"),
            fontFamily: "'Impact', 'Arial Black', sans-serif",
            userSelect: "none",
            pointerEvents: "none",
            zIndex: 5,
            transform: `scale(${interpolate(headlineSpring, [0, 1], [0.95, 1])})`,
          }}
        >
          {editorialHeadline.text}
        </div>
      ) : null}

      {/* Top Telemetry Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          borderBottom: isVintagePaper ? "1.5px solid rgba(0, 0, 0, 0.15)" : "1.5px solid rgba(255, 255, 255, 0.15)",
          paddingBottom: 12,
          marginBottom: 16,
          position: "relative",
          zIndex: 30,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <div
            style={{
              width: 10,
              height: 10,
              borderRadius: "50%",
              backgroundColor: "#ef4444",
              boxShadow: "0 0 10px #ef4444",
            }}
          />
          <span style={{ color: headerTextColor, fontSize: 14, fontWeight: 900, letterSpacing: 2 }}>
            {title}
          </span>
          <span style={{ color: headerSubColor, fontSize: 11, letterSpacing: 1.2 }}>
            // {backgroundLabel}
          </span>
        </div>

        <div
          style={{
            border: isVintagePaper ? "1.5px solid #991b1b" : "1.5px solid #ef4444",
            color: isVintagePaper ? "#991b1b" : "#f87171",
            backgroundColor: isVintagePaper ? "rgba(254, 226, 226, 0.7)" : "rgba(69, 26, 26, 0.6)",
            fontSize: 11,
            fontWeight: 900,
            letterSpacing: 1.5,
            padding: "3px 12px",
            borderRadius: 4,
          }}
        >
          {badge}
        </div>
      </div>

      {/* Stamped Editorial Headline Banner (Top Center or Overlay) */}
      {editorialHeadline && editorialHeadline.placement !== "background_large" ? (
        <div
          style={{
            position: "absolute",
            top: 58,
            left: "50%",
            transform: `translateX(-50%) scale(${headlineSpring}) rotate(${isVintagePaper ? "-1deg" : "0deg"})`,
            zIndex: 35,
            backgroundColor: isVintagePaper ? "#ffffff" : "#0f172a",
            border: `2.5px solid ${editorialHeadline.color || "#dc2626"}`,
            padding: "6px 24px",
            borderRadius: 4,
            boxShadow: "0 6px 20px rgba(0,0,0,0.3)",
            textAlign: "center",
          }}
        >
          <div
            style={{
              fontSize: 20,
              fontWeight: 900,
              letterSpacing: 3,
              color: editorialHeadline.color || (isVintagePaper ? "#991b1b" : "#f87171"),
              textTransform: "uppercase",
              fontFamily: "'Impact', 'Arial Black', sans-serif",
            }}
          >
            {editorialHeadline.text}
          </div>
          {editorialHeadline.subtext ? (
            <div
              style={{
                fontSize: 10,
                letterSpacing: 1.2,
                color: isVintagePaper ? "#57534e" : "#94a3b8",
                marginTop: 2,
              }}
            >
              {editorialHeadline.subtext}
            </div>
          ) : null}
        </div>
      ) : null}

      {/* SVG Canvas for Dynamic Curved Bezier Vector Arrows & Radiating Paths */}
      <svg
        width={boardW}
        height={boardH}
        viewBox={`0 0 ${boardW} ${boardH}`}
        style={{ position: "absolute", top: 0, left: 0, pointerEvents: "none", zIndex: 25 }}
      >
        <defs>
          <filter id="yarnGlow" x="-20%" y="-20%" width="140%" height="140%">
            <feGaussianBlur stdDeviation="3" result="blur" />
            <feComposite in="SourceGraphic" in2="blur" operator="over" />
          </filter>
        </defs>

        {allConnections.map((conn, cIdx) => {
          const drawStart = conn.drawStartFrame ?? (30 + cIdx * 6);
          const drawDur = conn.drawDuration ?? 20;
          const drawProgress = interpolate(frame, [drawStart, drawStart + drawDur], [0, 1], {
            extrapolateLeft: "clamp",
            extrapolateRight: "clamp",
            easing: Easing.bezier(0.16, 1, 0.3, 1),
          });

          if (drawProgress < 0.02) return null;

          const x1 = ((conn.fromX ?? 30) / 100) * boardW;
          const y1 = ((conn.fromY ?? 55) / 100) * boardH;
          const x2 = ((conn.toX ?? 68) / 100) * boardW;
          const y2 = ((conn.toY ?? 42) / 100) * boardH;

          const midX = (x1 + x2) / 2;
          const midY = (y1 + y2) / 2;
          const dx = x2 - x1;
          const dy = y2 - y1;
          const dist = Math.hypot(dx, dy);

          // Alternating curve bulge for radiating vectors
          const curveBulge = (cIdx % 2 === 0 ? -35 : 35);
          const nx = -dy / (dist || 1);
          const ny = dx / (dist || 1);
          const cx = midX + nx * curveBulge;
          const cy = midY + ny * curveBulge;

          const pathD = `M ${x1} ${y1} Q ${cx} ${cy} ${x2} ${y2}`;
          const approxLen = dist * 1.15;
          const dashOffset = approxLen * (1 - drawProgress);

          const tangentX = x2 - cx;
          const tangentY = y2 - cy;
          const angleDeg = (Math.atan2(tangentY, tangentX) * 180) / Math.PI;

          const isDrawn = drawProgress >= 0.98;
          const pulseT = ((frame - (drawStart + drawDur)) * 0.04) % 1;
          const ptX = (1 - pulseT) * (1 - pulseT) * x1 + 2 * (1 - pulseT) * pulseT * cx + pulseT * pulseT * x2;
          const ptY = (1 - pulseT) * (1 - pulseT) * y1 + 2 * (1 - pulseT) * pulseT * cy + pulseT * pulseT * y2;

          const labelSpring = spring({
            frame: Math.max(0, stepF - (drawStart + Math.round(drawDur * 0.4))),
            fps,
            config: SPRING_PRESETS.labelSnap,
          });

          return (
            <g key={cIdx}>
              {/* Shadow Track */}
              <path
                d={pathD}
                fill="none"
                stroke="rgba(0, 0, 0, 0.5)"
                strokeWidth={conn.isYarn ? 5 : 3}
                transform="translate(2, 4)"
              />

              {/* Glowing Vector Line / Red Yarn */}
              <path
                d={pathD}
                fill="none"
                stroke={conn.color || "#ef4444"}
                strokeWidth={conn.isYarn ? 4 : 3.5}
                strokeDasharray={approxLen}
                strokeDashoffset={dashOffset}
                filter="url(#yarnGlow)"
              />

              {/* Arrowhead at Target */}
              {drawProgress >= 0.88 ? (
                <polygon
                  points="0,-7 14,0 0,7"
                  fill={conn.color || "#ef4444"}
                  transform={`translate(${x2}, ${y2}) rotate(${angleDeg})`}
                  style={{ transformOrigin: "0 0" }}
                />
              ) : null}

              {/* Traveling Pulse Particle */}
              {isDrawn ? (
                <circle cx={ptX} cy={ptY} r={4.5} fill="#ffffff" filter="url(#yarnGlow)" />
              ) : null}

              {/* Floating Label Pill Along Arrow Arc */}
              {conn.label && labelSpring > 0.05 ? (
                <g transform={`translate(${cx}, ${cy - 14}) scale(${labelSpring})`}>
                  <rect
                    x={-((conn.label.length * 7.5 + 24) / 2)}
                    y={-14}
                    width={conn.label.length * 7.5 + 24}
                    height={28}
                    rx={6}
                    fill={isVintagePaper ? "rgba(255, 255, 255, 0.96)" : "rgba(15, 23, 42, 0.96)"}
                    stroke={conn.color || "#ef4444"}
                    strokeWidth={1.5}
                  />
                  <text
                    x={0}
                    y={4}
                    textAnchor="middle"
                    fill={conn.color || "#ef4444"}
                    fontSize={11}
                    fontWeight={900}
                    letterSpacing={1.2}
                    fontFamily="'Courier New', monospace"
                  >
                    {conn.label}
                  </text>
                </g>
              ) : null}
            </g>
          );
        })}
      </svg>

      {/* Main Staging Workboard: Split Layout with Archival Dossier + Cutout */}
      <div style={{ display: "flex", gap: 36, height: "calc(100% - 60px)", position: "relative" }}>
        {/* Left Column: Tactile Archival Paper Dossier (Drops Frame 6) */}
        <div
          style={{
            flex: "1 1 58%",
            backgroundColor: isVintagePaper ? "#ffffff" : "#f4ede1",
            color: "#1a1a1a",
            borderRadius: 6,
            padding: "24px 28px",
            boxShadow: `0 ${dossierShadow}px 45px rgba(0, 0, 0, ${isVintagePaper ? 0.35 : 0.8}), inset 0 0 30px rgba(180, 150, 110, 0.25)`,
            transform: `translateY(${dossierY}px) scale(${dossierScale}) rotate(-1.5deg)`,
            transformOrigin: "top left",
            opacity: interpolate(dossierDrop, [0, 0.2], [0, 1]),
            position: "relative",
            border: isVintagePaper ? "1px solid #e7e5e4" : "1px solid #d4c5b0",
            overflow: "hidden",
            zIndex: 15,
          }}
        >
          {/* Masking Tape on Top-Left Corner */}
          {hasCornerTape && tapeSpring > 0.02 ? (
            <div
              style={{
                position: "absolute",
                top: -12,
                left: -18,
                width: 90,
                height: 30,
                backgroundColor: "rgba(235, 220, 180, 0.85)",
                transform: "rotate(-32deg) scale(" + tapeSpring + ")",
                boxShadow: "0 2px 6px rgba(0,0,0,0.25)",
                border: "1px dashed rgba(160, 140, 100, 0.4)",
                zIndex: 20,
              }}
            />
          ) : null}

          {/* Brass Pushpin Pinned on Dossier */}
          {hasPushpin && pinSpring > 0.05 ? (
            <div
              style={{
                position: "absolute",
                top: 14,
                right: 18,
                width: 22,
                height: 22,
                borderRadius: "50%",
                background: "radial-gradient(circle at 35% 35%, #fde047, #ca8a04, #713f12)",
                boxShadow: "0 6px 14px rgba(0,0,0,0.6)",
                transform: `scale(${pinSpring})`,
                zIndex: 22,
              }}
            />
          ) : null}

          {/* Dossier Agency Header */}
          <div
            style={{
              display: "flex",
              justifyContent: "space-between",
              borderBottom: "1.5px solid #1a1a1a",
              paddingBottom: 8,
              marginBottom: 12,
              fontSize: 10,
              fontWeight: 800,
              letterSpacing: 1.2,
              color: "#334155",
            }}
          >
            <span>{dossierAgency}</span>
            <span>{dossierDate}</span>
          </div>

          <div
            style={{
              fontSize: 15,
              fontWeight: 900,
              letterSpacing: 1.2,
              textTransform: "uppercase",
              marginBottom: 12,
              color: "#0f172a",
            }}
          >
            {dossierTitle}
          </div>

          {/* Dossier Body Paragraph with Animated Highlighter Sweep */}
          <div
            style={{
              fontSize: 13,
              lineHeight: 1.6,
              color: "#1e293b",
              position: "relative",
              marginBottom: 16,
            }}
          >
            {dossierText.split(highlightPhrase).map((part, pIdx, arr) => (
              <React.Fragment key={pIdx}>
                {part}
                {pIdx < arr.length - 1 ? (
                  <span
                    style={{
                      background: `linear-gradient(90deg, #facc15 ${hlProgress}%, transparent ${hlProgress}%)`,
                      color: "#000000",
                      fontWeight: 900,
                      padding: "1px 3px",
                      borderRadius: 2,
                    }}
                  >
                    {highlightPhrase}
                  </span>
                ) : null}
              </React.Fragment>
            ))}
          </div>

          {/* Redacted Classified Clauses */}
          <div style={{ display: "flex", gap: 8, marginTop: 8 }}>
            {redactedPhrases.map((phrase, rIdx) => (
              <div
                key={rIdx}
                style={{
                  backgroundColor: "#000000",
                  color: "#000000",
                  fontSize: 10,
                  padding: "2px 8px",
                  borderRadius: 2,
                  letterSpacing: 1,
                  userSelect: "none",
                }}
              >
                {phrase}
              </div>
            ))}
          </div>

          {/* Slammed Red Rubber Stamp */}
          {stampText && frame >= stampFrame && stampOpacity > 0.05 ? (
            <div
              style={{
                position: "absolute",
                bottom: 24,
                right: 32,
                border: `3.5px solid ${stampColor}`,
                color: stampColor,
                padding: "6px 20px",
                fontSize: 22,
                fontWeight: 900,
                letterSpacing: 3,
                textTransform: "uppercase",
                transform: `rotate(-14deg) scale(${stampScale})`,
                transformOrigin: "center center",
                opacity: stampOpacity,
                borderRadius: 6,
                backgroundColor: "rgba(220, 38, 38, 0.06)",
                boxShadow: `0 4px 12px rgba(220, 38, 38, 0.3)`,
                zIndex: 25,
              }}
            >
              {stampText}
            </div>
          ) : null}
        </div>

        {/* Right Column: Tactical Cutout Photo & Supporting Cutouts */}
        <div
          style={{
            flex: "1 1 38%",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            position: "relative",
            zIndex: 18,
          }}
        >
          {/* Primary Archival Card Wrapper with White Cutout Edge */}
          <div
            style={{
              backgroundColor: isVintagePaper ? "#ffffff" : "rgba(15, 23, 42, 0.95)",
              border: isVintagePaper ? "2px solid #b45309" : "2px solid #f59e0b",
              borderRadius: 12,
              padding: 16,
              boxShadow: isVintagePaper
                ? "0 20px 45px rgba(70, 50, 30, 0.25)"
                : "0 20px 50px rgba(0,0,0,0.8), 0 0 20px rgba(245, 158, 11, 0.3)",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: 12,
              maxWidth: 380,
              transform: `scale(${cutoutSpring})`,
              transformOrigin: "center center",
            }}
          >
            {/* Cutout Container */}
            <div
              style={{
                width: 280,
                height: 200,
                backgroundColor: isVintagePaper ? "#f5f5f4" : "#020617",
                borderRadius: 8,
                border: isVintagePaper ? "1.5px solid #d6d3d1" : "1.5px solid rgba(255,255,255,0.15)",
                display: "flex",
                justifyContent: "center",
                alignItems: "center",
                overflow: "hidden",
                position: "relative",
              }}
            >
              {cutoutSrc ? (
                <Img
                  src={staticFile(cutoutSrc)}
                  style={{ width: "100%", height: "100%", objectFit: "contain" }}
                />
              ) : (
                <div style={{ textAlign: "center", color: isVintagePaper ? "#b45309" : "#f59e0b" }}>
                  <div style={{ fontSize: 36, fontWeight: 900 }}>✈️</div>
                  <div style={{ fontSize: 11, fontWeight: 700, letterSpacing: 1.5, marginTop: 6 }}>
                    {cutoutLabel}
                  </div>
                </div>
              )}
            </div>

            {/* Cutout Label Dossier */}
            <div style={{ textAlign: "center" }}>
              <div
                style={{
                  fontSize: 14,
                  fontWeight: 900,
                  color: isVintagePaper ? "#1c1917" : "#ffffff",
                  letterSpacing: 1,
                  textTransform: "uppercase",
                }}
              >
                {cutoutLabel}
              </div>
              <div
                style={{
                  fontSize: 11,
                  fontWeight: 700,
                  color: isVintagePaper ? "#b45309" : "#fbbf24",
                  letterSpacing: 1.5,
                  marginTop: 3,
                }}
              >
                {cutoutRole}
              </div>
            </div>
          </div>

          {/* Supporting Cutouts / Badges / Polaroids (AI Playbook multi-layer collage) */}
          {supportingCutouts.map((sc, scIdx) => {
            const dropF = sc.dropFrame ?? (26 + scIdx * 8);
            const scSpring = spring({
              frame: Math.max(0, stepF - dropF),
              fps,
              config: SPRING_PRESETS.paperSlide,
            });

            if (scSpring < 0.02) return null;

            return (
              <div
                key={scIdx}
                style={{
                  position: "absolute",
                  left: `${sc.xPct}%`,
                  top: `${sc.yPct}%`,
                  width: sc.width || 120,
                  height: sc.height || 120,
                  backgroundColor: isVintagePaper ? "#ffffff" : "#1e293b",
                  border: isVintagePaper ? "2px solid #d6d3d1" : "2px solid rgba(255,255,255,0.2)",
                  borderRadius: 8,
                  padding: 8,
                  boxShadow: "0 12px 28px rgba(0,0,0,0.35)",
                  transform: `scale(${scSpring}) rotate(${sc.rotation || (scIdx % 2 === 0 ? -4 : 5)}deg)`,
                  transformOrigin: "center center",
                  zIndex: 22 + scIdx,
                  display: "flex",
                  flexDirection: "column",
                  alignItems: "center",
                  justifyContent: "center",
                }}
              >
                {sc.src ? (
                  <Img
                    src={staticFile(sc.src)}
                    style={{ width: "100%", height: "80%", objectFit: "contain" }}
                  />
                ) : sc.icon ? (
                  <div style={{ fontSize: 32 }}>{sc.icon}</div>
                ) : null}

                {sc.label ? (
                  <div
                    style={{
                      fontSize: 9,
                      fontWeight: 900,
                      color: isVintagePaper ? "#1c1917" : "#f1f5f9",
                      letterSpacing: 0.8,
                      textAlign: "center",
                      marginTop: 4,
                      textTransform: "uppercase",
                    }}
                  >
                    {sc.label}
                  </div>
                ) : null}
              </div>
            );
          })}
        </div>
      </div>
    </div>
  );
};
