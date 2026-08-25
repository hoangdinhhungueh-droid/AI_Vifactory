import React from "react";
import {
  AbsoluteFill,
  Easing,
  interpolate,
  Sequence,
  spring,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

const INK = "#05090d";
const LIGHT = "#ffffff";

const fmtInt = (n) => {
  const sign = n < 0 ? "-" : "";
  const s = Math.round(Math.abs(n)).toString();
  const parts = [];
  let rest = s;
  while (rest.length > 3) {
    parts.unshift(rest.slice(-3));
    rest = rest.slice(0, -3);
  }
  parts.unshift(rest);
  return sign + parts.join(",");
};

const outline = (px, color) => {
  const dirs = [[-1, -1], [1, -1], [-1, 1], [1, 1], [0, -1], [0, 1], [-1, 0], [1, 0]];
  const parts = dirs.map((d) => `${d[0] * px}px ${d[1] * px}px 0 ${color}`);
  parts.push(`0 ${px * 2}px ${px * 3}px rgba(0,0,0,0.55)`);
  return parts.join(", ");
};

const GradientBG = ({ from, to, angle }) => (
  <AbsoluteFill
    style={{
      background: `linear-gradient(${angle || 135}deg, ${from} 0%, ${to} 100%)`,
    }}
  />
);

const AnimatedCounter = ({
  frame,
  from = 0,
  to,
  startFrame = 0,
  durFrames = 45,
  prefix = "",
  suffix = "",
  decimals = 0,
  fontSize = 150,
  color = "#ffd166",
}) => {
  const local = frame - startFrame;
  const t = interpolate(local, [0, durFrames], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const val = from + (to - from) * t;
  const shown = decimals > 0 ? val.toFixed(decimals) : fmtInt(val);
  return (
    <div
      style={{
        fontFamily: "Arial, Helvetica, sans-serif",
        fontWeight: 900,
        fontSize,
        lineHeight: 1,
        color,
        textShadow: outline(4, INK),
      }}
    >
      {prefix}
      {shown}
      {suffix}
    </div>
  );
};

const CoinIcon = ({ progress, accent }) => {
  const scale = interpolate(progress, [0, 1], [0.4, 1]);
  const rot = interpolate(progress, [0, 1], [-25, 0]);
  return (
    <svg
      width={180}
      height={180}
      viewBox="0 0 180 180"
      style={{ transform: `scale(${scale}) rotate(${rot}deg)`, opacity: progress }}
    >
      <circle cx="90" cy="90" r="76" fill="none" stroke={accent} strokeWidth="10" />
      <circle cx="90" cy="90" r="76" fill={INK} opacity="0.15" />
      <text
        x="90"
        y="118"
        fontSize="90"
        fontWeight="900"
        fill={accent}
        textAnchor="middle"
        fontFamily="Arial, Helvetica, sans-serif"
      >
        $
      </text>
    </svg>
  );
};

const BoxXIcon = ({ progress, accent }) => {
  const scale = interpolate(progress, [0, 1], [0.5, 1]);
  const rot = interpolate(progress, [0, 1], [8, 0]);
  return (
    <svg
      width={180}
      height={180}
      viewBox="0 0 180 180"
      style={{ transform: `scale(${scale}) rotate(${rot}deg)`, opacity: progress }}
    >
      <rect x="20" y="20" width="140" height="140" rx="14" fill="none" stroke={accent} strokeWidth="10" />
      <line x1="38" y1="38" x2="142" y2="142" stroke={accent} strokeWidth="10" strokeLinecap="round" />
      <line x1="142" y1="38" x2="38" y2="142" stroke={accent} strokeWidth="10" strokeLinecap="round" />
    </svg>
  );
};

const HookScene = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const iconP = spring({ frame, fps, config: { damping: 14 } });
  const labelOpacity = interpolate(frame, [30, 45], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <AbsoluteFill>
      <GradientBG from="#0a1730" to="#05090d" angle={150} />
      <AbsoluteFill
        style={{
          justifyContent: "center",
          alignItems: "center",
          flexDirection: "column",
          gap: 18,
        }}
      >
        <CoinIcon progress={iconP} accent="#f2a63b" />
        <AnimatedCounter
          frame={frame}
          to={6.6}
          decimals={1}
          startFrame={10}
          durFrames={50}
          prefix="$"
          suffix="B"
          fontSize={170}
          color="#f2a63b"
        />
        <div
          style={{
            fontFamily: "Arial, Helvetica, sans-serif",
            fontWeight: 700,
            fontSize: 40,
            letterSpacing: 3,
            color: LIGHT,
            opacity: labelOpacity,
            textShadow: outline(2, INK),
          }}
        >
          LEVERAGED BUYOUT PRICE
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

const Bar = ({ x, targetH, maxH, color, frame, startFrame, label, valueNode }) => {
  const h = interpolate(frame - startFrame, [0, 55], [0, targetH], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  return (
    <g>
      <rect x={x} y={maxH - h} width={140} height={h} fill={color} rx={10} />
      <foreignObject x={x - 40} y={maxH - h - 90} width={220} height={80}>
        {valueNode}
      </foreignObject>
      <text x={x + 70} y={maxH + 46} fontSize="26" fontWeight="700" fill={LIGHT} textAnchor="middle" fontFamily="Arial, Helvetica, sans-serif">
        {label}
      </text>
    </g>
  );
};

const BarChartScene = () => {
  const frame = useCurrentFrame();
  const maxH = 380;
  return (
    <AbsoluteFill>
      <GradientBG from="#1a0f14" to="#05090d" angle={150} />
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
        <svg width={900} height={520} viewBox="0 0 900 520">
          <line x1="60" y1={maxH} x2="840" y2={maxH} stroke="#8fa3b0" strokeWidth="4" />
          <Bar
            x={220}
            targetH={maxH * 0.95}
            maxH={maxH}
            color="#c81e3a"
            frame={frame}
            startFrame={10}
            label="DEBT LOADED ON"
            valueNode={
              <div style={{ fontFamily: "Arial, Helvetica, sans-serif", fontWeight: 900, fontSize: 40, color: "#c81e3a", textAlign: "center" }}>
                $5.3B
              </div>
            }
          />
          <Bar
            x={540}
            targetH={maxH * 0.32}
            maxH={maxH}
            color="#ffd166"
            frame={frame}
            startFrame={40}
            label="INTEREST / YEAR"
            valueNode={
              <div style={{ fontFamily: "Arial, Helvetica, sans-serif", fontWeight: 900, fontSize: 40, color: "#ffd166", textAlign: "center" }}>
                $400M
              </div>
            }
          />
        </svg>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

const LineChartScene = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const points = [
    { x: 60, y: 340, year: "1978", label: "IPO" },
    { x: 280, y: 40, year: "2005", label: "1,499 stores" },
    { x: 560, y: 130, year: "2017", label: "735 stores" },
    { x: 820, y: 380, year: "2018", label: "Liquidated" },
  ];
  const pathStr = points.map((p, i) => `${i === 0 ? "M" : "L"}${p.x},${p.y}`).join(" ");
  const drawP = interpolate(frame, [10, 90], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
    easing: Easing.out(Easing.cubic),
  });
  const pathLen = 1100;
  return (
    <AbsoluteFill>
      <GradientBG from="#101a1a" to="#05090d" angle={150} />
      <AbsoluteFill style={{ justifyContent: "center", alignItems: "center" }}>
        <svg width={900} height={480} viewBox="0 0 900 420">
          {[0, 1, 2, 3].map((i) => (
            <line key={i} x1="40" y1={90 + i * 90} x2="860" y2={90 + i * 90} stroke="#243447" strokeWidth="2" />
          ))}
          <path
            d={pathStr}
            fill="none"
            stroke="#c81e3a"
            strokeWidth="8"
            strokeLinecap="round"
            strokeDasharray={pathLen}
            strokeDashoffset={pathLen * (1 - drawP)}
          />
          {points.map((p, i) => {
            const appear = spring({ frame: frame - (20 + i * 22), fps, config: { damping: 12 } });
            return (
              <g key={i} opacity={appear} style={{ transformOrigin: `${p.x}px ${p.y}px`, transform: `scale(${0.6 + 0.4 * appear})` }}>
                <circle cx={p.x} cy={p.y} r="12" fill="#ffd166" />
                <text x={p.x} y={p.y - 24} fontSize="24" fontWeight="700" fill={LIGHT} textAnchor="middle" fontFamily="Arial, Helvetica, sans-serif">
                  {p.label}
                </text>
                <text x={p.x} y="410" fontSize="22" fontWeight="700" fill="#8fa3b0" textAnchor="middle" fontFamily="Arial, Helvetica, sans-serif">
                  {p.year}
                </text>
              </g>
            );
          })}
        </svg>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

const AftermathScene = () => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const iconP = spring({ frame, fps, config: { damping: 14 } });
  const labelOpacity = interpolate(frame, [30, 45], [0, 1], {
    extrapolateLeft: "clamp",
    extrapolateRight: "clamp",
  });
  return (
    <AbsoluteFill>
      <GradientBG from="#2b2f33" to="#05090d" angle={150} />
      <AbsoluteFill
        style={{
          justifyContent: "center",
          alignItems: "center",
          flexDirection: "column",
          gap: 18,
        }}
      >
        <BoxXIcon progress={iconP} accent="#8fa3b0" />
        <AnimatedCounter
          frame={frame}
          to={33000}
          startFrame={10}
          durFrames={55}
          fontSize={150}
          color="#8fa3b0"
        />
        <div
          style={{
            fontFamily: "Arial, Helvetica, sans-serif",
            fontWeight: 700,
            fontSize: 40,
            letterSpacing: 3,
            color: LIGHT,
            opacity: labelOpacity,
            textShadow: outline(2, INK),
          }}
        >
          JOBS LOST
        </div>
      </AbsoluteFill>
    </AbsoluteFill>
  );
};

export const DataStoryTest = () => {
  return (
    <AbsoluteFill style={{ backgroundColor: INK }}>
      <Sequence from={0} durationInFrames={150}>
        <HookScene />
      </Sequence>
      <Sequence from={150} durationInFrames={150}>
        <BarChartScene />
      </Sequence>
      <Sequence from={300} durationInFrames={150}>
        <LineChartScene />
      </Sequence>
      <Sequence from={450} durationInFrames={150}>
        <AftermathScene />
      </Sequence>
    </AbsoluteFill>
  );
};
