import React from "react";
import {
  AbsoluteFill,
  Audio,
  Sequence,
  spring,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
  Img,
} from "remotion";
import {
  LivingCamera,
  VoxConnectedNetwork,
  VoxKineticHeadline,
  VoxKineticCounter,
  VoxDynamicChart,
  VoxForensicPaper,
} from "./components/vox";

const INK = "#070b12";
const LIGHT = "#f8fafc";
const ACCENT_GOLD = "#f59e0b";
const ACCENT_RED = "#ef4444";
const ACCENT_CYAN = "#38bdf8";

// Tactical Background Grid Layer with Vignette & Subtle Breathing
const TacticalBackground = ({ title, code }: { title?: string; code?: string }) => {
  const frame = useCurrentFrame();

  const gridDrift = Math.sin((frame / 30) * 0.4) * 6;

  return (
    <AbsoluteFill style={{ backgroundColor: INK, overflow: "hidden" }}>
      {/* Blueprint Grid Pattern */}
      <div
        style={{
          position: "absolute",
          width: "120%",
          height: "120%",
          left: "-10%",
          top: "-10%",
          backgroundImage: `
            radial-gradient(rgba(245, 158, 11, 0.08) 1.5px, transparent 1.5px),
            linear-gradient(to right, rgba(255, 255, 255, 0.035) 1px, transparent 1px),
            linear-gradient(to bottom, rgba(255, 255, 255, 0.035) 1px, transparent 1px)
          `,
          backgroundSize: "32px 32px, 160px 160px, 160px 160px",
          transform: `translate3d(0, ${gridDrift}px, 0)`,
        }}
      />

      {/* Atmospheric Vignette & Deep Blue Gradient Wash */}
      <div
        style={{
          position: "absolute",
          inset: 0,
          background: `
            radial-gradient(ellipse at 50% 30%, rgba(26, 43, 76, 0.35) 0%, transparent 70%),
            radial-gradient(ellipse at 50% 50%, transparent 40%, rgba(5, 8, 14, 0.95) 100%)
          `,
        }}
      />

      {/* Top Telemetry Watermark */}
      <div
        style={{
          position: "absolute",
          top: 36,
          left: 48,
          right: 48,
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          fontFamily: "'Courier New', monospace",
          fontSize: 12,
          fontWeight: 800,
          letterSpacing: 2,
          color: "rgba(255, 255, 255, 0.35)",
          borderBottom: "1px solid rgba(255, 255, 255, 0.08)",
          paddingBottom: 10,
          zIndex: 10,
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: 8 }}>
          <span style={{ color: ACCENT_GOLD }}>●</span>
          <span>{title || "VOX INVESTIGATIVE VISUAL REPORT // CASE DOSSIER"}</span>
        </div>
        <div>{code || "DEPT. FORENSIC AUDIT // EXHIBIT-42"}</div>
      </div>
    </AbsoluteFill>
  );
};

// Scene 1: The Kinetic Hook (0 - 180 frames = 6.0s)
const Scene1Hook = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  // Avatar spring entrance
  const avatarSpring = spring({
    frame: Math.max(0, frame - 15),
    fps,
    config: { damping: 12, mass: 0.6, stiffness: 120 },
  });

  return (
    <AbsoluteFill>
      <TacticalBackground title="PROLOGUE // THE $63.4 BILLION APPARITION" code="ARCHIVE: SEC-ENR-01" />

      <LivingCamera windowMode="snap_focus">
        <AbsoluteFill style={{ display: "flex", justifyContent: "center", alignItems: "center" }}>
          {/* Kinetic Headline with Yellow Marker Highlight */}
          <div style={{ width: 1400, height: 600, position: "relative", zIndex: 20 }}>
            <VoxKineticHeadline
              headline="HOW A $63.4 BILLION ENERGY EMPIRE VANISHED OVERNIGHT"
              highlightWord="$63.4"
              category="CORPORATE FORENSIC INVESTIGATION"
              subtext="A mathematical fiction engineered through 3,000 offshore shell entities."
              accentColor="#f59e0b"
            />
          </div>

          {/* Floating Cutout Subject (Jeffrey Skilling) entering right side with spring */}
          <div
            style={{
              position: "absolute",
              right: 120,
              bottom: 40,
              width: 480,
              height: 640,
              opacity: avatarSpring,
              transform: `translate3d(${(1 - avatarSpring) * 80}px, 0, 0) rotate(${avatarSpring * 2.5 - 2.5}deg)`,
              filter: "drop-shadow(0 30px 50px rgba(0,0,0,0.85)) drop-shadow(0 6px 16px rgba(0,0,0,0.60))",
              zIndex: 15,
            }}
          >
            <Img
              src={staticFile("fg_jeff_skilling.png")}
              style={{
                width: "100%",
                height: "100%",
                objectFit: "contain",
                objectPosition: "bottom",
                filter: "brightness(1.08) contrast(1.18)",
              }}
            />
          </div>
        </AbsoluteFill>
      </LivingCamera>
    </AbsoluteFill>
  );
};

// Scene 2: The Multi-Entity Network with Dynamic Curved Arrows (180 - 540 frames = 12.0s)
const Scene2Network = () => {
  const nodes = [
    {
      id: "ken_lay",
      label: "KENNETH LAY",
      subtext: "Chairman & Political Liaison",
      image_src: "fg_ken_lay.png",
      x_pct: 18,
      y_pct: 30,
      enter_frame: 10,
      theme: "danger" as const,
      badge: "EXECUTIVE SUITE",
    },
    {
      id: "skilling",
      label: "JEFFREY SKILLING",
      subtext: "Architect of Mark-to-Market",
      image_src: "fg_jeff_skilling.png",
      x_pct: 50,
      y_pct: 22,
      enter_frame: 25,
      theme: "gold" as const,
      badge: "CHIEF OPERATING OFFICER",
    },
    {
      id: "fastow",
      label: "ANDREW FASTOW",
      subtext: "Chief Financial Officer",
      image_src: "fg_andy_fastow.png",
      x_pct: 82,
      y_pct: 32,
      enter_frame: 45,
      theme: "danger" as const,
      badge: "SPE CREATOR",
    },
    {
      id: "chewco",
      label: "CHEWCO & LJM NETWORKS",
      subtext: "Off-Balance Sheet Debt Sinkhole",
      image_src: "fg_auditor.png",
      x_pct: 72,
      y_pct: 76,
      enter_frame: 75,
      theme: "warning" as const,
      badge: "SPECIAL PURPOSE ENTITIES",
    },
    {
      id: "sec",
      label: "SEC & WHISTLEBLOWERS",
      subtext: "Forensic Investigation Unit",
      image_src: "fg_sec_investigator.png",
      x_pct: 24,
      y_pct: 76,
      enter_frame: 110,
      theme: "cyan" as const,
      badge: "ENFORCEMENT ACTION",
    },
  ];

  const edges = [
    {
      from: "ken_lay",
      to: "skilling",
      label: "MANDATE: UNLIMITED GROWTH",
      start_frame: 40,
      duration_frames: 22,
      color: "#f59e0b",
      curve_offset: -40,
      pulse: true,
    },
    {
      from: "skilling",
      to: "fastow",
      label: "AUTHORIZATION TO HIDE $3.8B",
      start_frame: 70,
      duration_frames: 24,
      color: "#f59e0b",
      curve_offset: -35,
      pulse: true,
    },
    {
      from: "fastow",
      to: "chewco",
      label: "+$1.2B TOXIC DEBT SIPHON",
      start_frame: 100,
      duration_frames: 24,
      color: "#ef4444",
      curve_offset: 45,
      pulse: true,
    },
    {
      from: "sec",
      to: "chewco",
      label: "FORENSIC SUBPOENA ISSUED",
      start_frame: 140,
      duration_frames: 26,
      color: "#38bdf8",
      curve_offset: -20,
      style: "dashed" as const,
      pulse: true,
    },
  ];

  return (
    <AbsoluteFill>
      <TacticalBackground title="ACT II // CORPORATE SHADOW PIPELINE" code="MAP ID: 884-CAUSAL-NET" />

      <LivingCamera windowMode="reveal">
        <AbsoluteFill style={{ display: "flex", justifyContent: "center", alignItems: "center" }}>
          <VoxConnectedNetwork
            title="INSTITUTIONAL CAPITAL TRANSMISSION // CAUSAL SHADOW NETWORK"
            badge="OFF-BALANCE SHEET FRAUD VECTOR"
            layout="full_bleed_focus"
            nodes={nodes}
            edges={edges}
          />
        </AbsoluteFill>
      </LivingCamera>
    </AbsoluteFill>
  );
};

// Scene 3: The Quantitative Shock & Dynamic Financial Chart (540 - 840 frames = 10.0s)
const Scene3DataPunch = () => {
  return (
    <AbsoluteFill>
      <TacticalBackground title="ACT III // THE VALUATION COLLAPSE" code="DATA METRIC: ENR-NYSE" />

      <LivingCamera windowMode="document_inspect">
        <AbsoluteFill
          style={{
            display: "flex",
            flexDirection: "row",
            justifyContent: "center",
            alignItems: "center",
            gap: 50,
            padding: "0 80px",
          }}
        >
          {/* Left: Odometer Rolling Metric Counter */}
          <VoxKineticCounter
            title="ENRON MARKET VALUATION"
            badge="CRITICAL COLLAPSE"
            theme="noir_dossier"
            layout="floating_card"
            payload={{
              start_value: 63400,
              end_value: 268,
              prefix: "$",
              suffix: "M",
              unit: "",
              trend: "down",
            }}
          />

          {/* Right: Dynamic Financial Line Chart */}
          <VoxDynamicChart
            title="NYSE: ENR // 18-MONTH CATASTROPHIC PLUNGE"
            badge="SEC AUDIT FINDINGS"
            chartType="line"
            startValue={90.75}
            endValue={0.26}
            unit=""
            prefix="$"
            color="#ef4444"
            trend="down"
            data={[
              { label: "AUG 00", value: 90.75 },
              { label: "JAN 01", value: 82.0 },
              { label: "AUG 01", value: 42.5 },
              { label: "OCT 01", value: 15.4 },
              { label: "DEC 01", value: 0.26 },
            ]}
          />
        </AbsoluteFill>
      </LivingCamera>
    </AbsoluteFill>
  );
};

// Scene 4: Tactile Archival Docket & Stamp Slam (840 - 1140 frames = 10.0s)
const Scene4ForensicDossier = () => {
  return (
    <AbsoluteFill>
      <TacticalBackground title="ACT IV // FORENSIC PAPER TRAIL" code="RECORD: DOJ-0912-US" />

      <LivingCamera windowMode="focus">
        <AbsoluteFill style={{ display: "flex", justifyContent: "center", alignItems: "center" }}>
          <VoxForensicPaper
            title="U.S. DEPARTMENT OF JUSTICE // INDICTMENT DOCKET"
            documentNumber="DOC-DOJ-2001-ENR-CRIM"
            date="DECEMBER 2001"
            agency="FEDERAL BUREAU OF INVESTIGATION // FINANCIAL FRAUD TASK FORCE"
            bodyText="Upon forensic subpoena of off-balance sheet accounting ledgers, over $3.8 Billion in liabilities were intentionally transferred to special purpose entities without genuine independent equity capitalization."
            highlightedPhrase="intentionally transferred to special purpose entities"
            stampText="CRIMINAL FRAUD"
            stampColor="#ef4444"
            width={860}
            height={520}
          />
        </AbsoluteFill>
      </LivingCamera>
    </AbsoluteFill>
  );
};

// Scene 5: Modern Mirror & Synthesis Outro (1140 - 1350 frames = 7.0s)
const Scene5Outro = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();

  const titleSpring = spring({
    frame,
    fps,
    config: { damping: 14, mass: 0.6, stiffness: 120 },
  });

  return (
    <AbsoluteFill>
      <TacticalBackground title="EPILOGUE // THE SYSTEMIC LESSON" code="VERDICT: GUILTY" />

      <LivingCamera windowMode="pull">
        <AbsoluteFill
          style={{
            display: "flex",
            flexDirection: "column",
            justifyContent: "center",
            alignItems: "center",
            padding: "0 140px",
            textAlign: "center",
          }}
        >
          <div
            style={{
              transform: `scale(${titleSpring})`,
              opacity: titleSpring,
              display: "flex",
              flexDirection: "column",
              alignItems: "center",
              gap: 20,
            }}
          >
            <div
              style={{
                border: "2px solid #f59e0b",
                color: "#f59e0b",
                backgroundColor: "rgba(245,158,11,0.1)",
                padding: "6px 20px",
                borderRadius: 20,
                fontSize: 13,
                fontWeight: 900,
                letterSpacing: 2,
                textTransform: "uppercase",
              }}
            >
              VOX STYLE MOTION ENGINE // CLAUDE OPUS 5.5 PROOF
            </div>

            <div
              style={{
                fontFamily: "Arial, Helvetica, sans-serif",
                fontSize: 54,
                fontWeight: 900,
                color: LIGHT,
                lineHeight: 1.15,
                maxWidth: 1100,
              }}
            >
              THE FAILURE WAS NEVER TECHNOLOGY. IT WAS A MATHEMATICAL ILLUSION PROTECTED BY SILENCE.
            </div>

            <div
              style={{
                fontFamily: "'Courier New', monospace",
                fontSize: 15,
                color: "#94a3b8",
                letterSpacing: 3,
                textTransform: "uppercase",
                marginTop: 10,
              }}
            >
              RENDERED 100% PROGRAMMATICALLY VIA REMOTION + SPRING FRAME MATH
            </div>
          </div>
        </AbsoluteFill>
      </LivingCamera>
    </AbsoluteFill>
  );
};

// Master Showcase Composition: 1350 frames = 45.0 seconds @ 30fps
export const VoxMasterShowcase: React.FC = () => {
  return (
    <AbsoluteFill style={{ backgroundColor: INK }}>
      {/* Background Cinematic Music Bed */}
      <Audio src={staticFile("assets/bgm/calm_004_fs725597.mp3")} volume={0.65} />

      {/* Sequence 1: The Kinetic Hook (0 - 180 = 6s) */}
      <Sequence from={0} durationInFrames={180}>
        <Scene1Hook />
      </Sequence>

      {/* Sequence 2: The Multi-Node Connected Network with Vector Arrows (180 - 540 = 12s) */}
      <Sequence from={180} durationInFrames={360}>
        <Scene2Network />
      </Sequence>

      {/* Sequence 3: The Quantitative Shock & Live Drawing Line Chart (540 - 840 = 10s) */}
      <Sequence from={540} durationInFrames={300}>
        <Scene3DataPunch />
      </Sequence>

      {/* Sequence 4: Tactile Dossier & Stamp Slam (840 - 1140 = 10s) */}
      <Sequence from={840} durationInFrames={300}>
        <Scene4ForensicDossier />
      </Sequence>

      {/* Sequence 5: Modern Mirror Outro (1140 - 1350 = 7s) */}
      <Sequence from={1140} durationInFrames={210}>
        <Scene5Outro />
      </Sequence>
    </AbsoluteFill>
  );
};
