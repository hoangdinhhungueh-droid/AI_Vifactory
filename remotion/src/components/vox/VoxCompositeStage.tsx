import React from "react";
import { interpolate, spring, useCurrentFrame, useVideoConfig, Easing, Img, staticFile } from "remotion";
import { SPRING_PRESETS } from "./springPresets";

export interface VoxCompositeStageProps {
  /** Scene Title / Header */
  title?: string;
  badge?: string;
  category?: string;

  /** Stage Dimensions / Layout */
  layout?: "full_bleed_focus" | "split_right" | "split_left" | string;

  /** Background Configuration */
  backgroundType?: "vintage_map" | "blueprint_grid" | "archival_desk" | "dark_forensic";
  backgroundLabel?: string;

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

  /** Connecting Vector Arrow / Red Yarn */
  connection?: {
    fromX?: number; // % of board width
    fromY?: number; // % of board height
    toX?: number;   // % of board width
    toY?: number;   // % of board height
    label?: string; // e.g. "40 MIN TO DISAPPEARANCE"
    color?: string; // default red #ef4444 or gold #f59e0b
    drawStartFrame?: number; // default 32
    drawDuration?: number;   // default 20
    isYarn?: boolean;        // textured red yarn vs neon arrow
  };

  /** Red Rubber Stamp / Certification */
  stampText?: string; // e.g. "239 PEOPLE", "CRIMINAL FRAUD", "RESTRICTED"
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
  backgroundType = "vintage_map",
  backgroundLabel = "SOUTHEAST ASIA NAUTICAL SECTOR // RADAR SWEEP",
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

  // Slow continuous living camera creep throughout the scene
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
  // PHASE 5: Dynamic Vector Arrow / Red Connecting Yarn (Frame 30-55)
  // ==========================================
  const drawStart = connection.drawStartFrame ?? 30;
  const drawDur = connection.drawDuration ?? 22;
  const drawProgress = interpolate(frame, [drawStart, drawStart + drawDur], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.bezier(0.16, 1, 0.3, 1),
  });

  // Vector coordinates
  const x1 = ((connection.fromX ?? 30) / 100) * boardW;
  const y1 = ((connection.fromY ?? 55) / 100) * boardH;
  const x2 = ((connection.toX ?? 68) / 100) * boardW;
  const y2 = ((connection.toY ?? 42) / 100) * boardH;

  const midX = (x1 + x2) / 2;
  const midY = (y1 + y2) / 2;
  const dx = x2 - x1;
  const dy = y2 - y1;
  const dist = Math.hypot(dx, dy);

  // Organic curve bulge
  const curveBulge = -40;
  const nx = -dy / (dist || 1);
  const ny = dx / (dist || 1);
  const cx = midX + nx * curveBulge;
  const cy = midY + ny * curveBulge;

  const pathD = `M ${x1} ${y1} Q ${cx} ${cy} ${x2} ${y2}`;
  const approxLen = dist * 1.15;
  const dashOffset = approxLen * (1 - drawProgress);

  // Arrowhead angle
  const tangentX = x2 - cx;
  const tangentY = y2 - cy;
  const angleDeg = (Math.atan2(tangentY, tangentX) * 180) / Math.PI;

  const labelSpring = spring({
    frame: Math.max(0, stepF - (drawStart + Math.round(drawDur * 0.4))),
    fps,
    config: SPRING_PRESETS.labelSnap,
  });

  // Traveling pulse dot
  const isDrawn = drawProgress >= 0.98;
  const pulseT = ((frame - (drawStart + drawDur)) * 0.04) % 1;
  const ptX = (1 - pulseT) * (1 - pulseT) * x1 + 2 * (1 - pulseT) * pulseT * cx + pulseT * pulseT * x2;
  const ptY = (1 - pulseT) * (1 - pulseT) * y1 + 2 * (1 - pulseT) * pulseT * cy + pulseT * pulseT * y2;

  // ==========================================
  // PHASE 6: Highlighter Sweep & Rubber Stamp Slam (Frame 50-80)
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

  return (
    <div
      style={{
        width: boardW,
        height: boardH,
        position: "relative",
        transform: `translate(${cameraPanX + shakeX}px, ${shakeY}px) scale(${masterSpring * cameraZoom})`,
        transformOrigin: "center center",
        backgroundColor: "#0d131f",
        backgroundImage: `
          radial-gradient(rgba(242, 166, 59, 0.08) 1.5px, transparent 1.5px),
          linear-gradient(to right, rgba(255, 255, 255, 0.03) 1px, transparent 1px),
          linear-gradient(to bottom, rgba(255, 255, 255, 0.03) 1px, transparent 1px)
        `,
        backgroundSize: "28px 28px, 140px 140px, 140px 140px",
        borderRadius: 16,
        border: "2px solid rgba(242, 166, 59, 0.5)",
        boxShadow: "0 30px 80px rgba(0, 0, 0, 0.85), inset 0 0 40px rgba(0, 0, 0, 0.6)",
        padding: "24px 32px",
        overflow: "hidden",
        fontFamily: "'Courier Prime', 'Special Elite', 'Courier New', monospace",
        color: "#ffffff",
      }}
    >
      {/* Top Telemetry Header */}
      <div
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          borderBottom: "1.5px solid rgba(255, 255, 255, 0.15)",
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
          <span style={{ color: "#fbbf24", fontSize: 14, fontWeight: 900, letterSpacing: 2 }}>
            {title}
          </span>
          <span style={{ color: "#94a3b8", fontSize: 11, letterSpacing: 1.2 }}>
            // {backgroundLabel}
          </span>
        </div>

        <div
          style={{
            border: "1.5px solid #ef4444",
            color: "#f87171",
            backgroundColor: "rgba(69, 26, 26, 0.6)",
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

      {/* SVG Canvas for Dynamic Curved Bezier Vector Arrow / Yarn */}
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

        {drawProgress > 0.02 ? (
          <g>
            {/* Shadow Track */}
            <path
              d={pathD}
              fill="none"
              stroke="rgba(0, 0, 0, 0.6)"
              strokeWidth={connection.isYarn ? 5 : 3}
              transform="translate(2, 4)"
            />

            {/* Glowing Connecting Vector Line / Red Yarn */}
            <path
              d={pathD}
              fill="none"
              stroke={connection.color || "#ef4444"}
              strokeWidth={connection.isYarn ? 4 : 3.5}
              strokeDasharray={approxLen}
              strokeDashoffset={dashOffset}
              filter="url(#yarnGlow)"
            />

            {/* Arrowhead / Needle Pin at Target */}
            {drawProgress >= 0.88 ? (
              <polygon
                points="0,-7 14,0 0,7"
                fill={connection.color || "#ef4444"}
                transform={`translate(${x2}, ${y2}) rotate(${angleDeg})`}
                style={{ transformOrigin: "0 0" }}
              />
            ) : null}

            {/* Traveling Pulse Particle */}
            {isDrawn ? (
              <circle cx={ptX} cy={ptY} r={5} fill="#ffffff" filter="url(#yarnGlow)" />
            ) : null}

            {/* Floating Label Pill Along Arrow Arc */}
            {connection.label && labelSpring > 0.05 ? (
              <g transform={`translate(${cx}, ${cy - 14}) scale(${labelSpring})`}>
                <rect
                  x={-((connection.label.length * 7.5 + 24) / 2)}
                  y={-14}
                  width={connection.label.length * 7.5 + 24}
                  height={28}
                  rx={6}
                  fill="rgba(15, 23, 42, 0.96)"
                  stroke={connection.color || "#ef4444"}
                  strokeWidth={1.5}
                />
                <text
                  x={0}
                  y={4}
                  textAnchor="middle"
                  fill={connection.color || "#ef4444"}
                  fontSize={11}
                  fontWeight={900}
                  letterSpacing={1.2}
                  fontFamily="'Courier New', monospace"
                >
                  {connection.label}
                </text>
              </g>
            ) : null}
          </g>
        ) : null}
      </svg>

      {/* Main Staging Workboard: Split Layout with Archival Dossier + Cutout */}
      <div style={{ display: "flex", gap: 36, height: "calc(100% - 60px)", position: "relative" }}>
        {/* Left Column: Tactile Archival Paper Dossier (Drops Frame 6) */}
        <div
          style={{
            flex: "1 1 58%",
            backgroundColor: "#f4ede1",
            color: "#1a1a1a",
            borderRadius: 6,
            padding: "24px 28px",
            boxShadow: `0 ${dossierShadow}px 45px rgba(0, 0, 0, 0.8), inset 0 0 30px rgba(180, 150, 110, 0.25)`,
            transform: `translateY(${dossierY}px) scale(${dossierScale}) rotate(-1.5deg)`,
            transformOrigin: "top left",
            opacity: interpolate(dossierDrop, [0, 0.2], [0, 1]),
            position: "relative",
            border: "1px solid #d4c5b0",
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

        {/* Right Column: Tactical Cutout Photo / Entity (Drops Frame 20) */}
        <div
          style={{
            flex: "1 1 38%",
            display: "flex",
            flexDirection: "column",
            alignItems: "center",
            justifyContent: "center",
            position: "relative",
            transform: `scale(${cutoutSpring})`,
            transformOrigin: "center center",
            zIndex: 18,
          }}
        >
          {/* Outer Archival Card Wrapper with White Cutout Edge */}
          <div
            style={{
              backgroundColor: "rgba(15, 23, 42, 0.95)",
              border: "2px solid #f59e0b",
              borderRadius: 12,
              padding: 16,
              boxShadow: "0 20px 50px rgba(0,0,0,0.8), 0 0 20px rgba(245, 158, 11, 0.3)",
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: 12,
              maxWidth: 380,
            }}
          >
            {/* Cutout Container */}
            <div
              style={{
                width: 280,
                height: 200,
                backgroundColor: "#020617",
                borderRadius: 8,
                border: "1.5px solid rgba(255,255,255,0.15)",
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
                <div style={{ textAlign: "center", color: "#f59e0b" }}>
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
                  color: "#ffffff",
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
                  color: "#fbbf24",
                  letterSpacing: 1.5,
                  marginTop: 3,
                }}
              >
                {cutoutRole}
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
