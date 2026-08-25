import React from "react";
import {
  AbsoluteFill,
  Audio,
  interpolate,
  staticFile,
  useCurrentFrame,
  useVideoConfig,
} from "remotion";

const INK = "#05090d";
const LIGHT = "#ffffff";

const clamp01 = (v) => Math.max(0, Math.min(1, v));

const outline = (px, color) => {
  const dirs = [[-1, -1], [1, -1], [-1, 1], [1, 1], [0, -1], [0, 1], [-1, 0], [1, 0]];
  const parts = dirs.map((d) => `${d[0] * px}px ${d[1] * px}px 0 ${color}`);
  parts.push(`0 ${px * 2}px ${px * 3}px rgba(0,0,0,0.6)`);
  return parts.join(", ");
};

const GiraffeIcon = ({ accent, k }) => (
  <svg width={140 * k} height={210 * k} viewBox="0 0 200 300">
    <rect x="70" y="150" width="60" height="100" rx="18" fill={accent} />
    <rect x="72" y="248" width="18" height="42" fill={accent} />
    <rect x="112" y="248" width="18" height="42" fill={accent} />
    <path d="M96 40 C86 90 84 120 96 155" stroke={accent} strokeWidth="18" strokeLinecap="round" fill="none" />
    <circle cx="92" cy="30" r="26" fill={accent} />
    <circle cx="82" cy="22" r="6" fill={INK} />
    <circle cx="100" cy="70" r="7" fill={INK} opacity="0.7" />
    <circle cx="118" cy="110" r="7" fill={INK} opacity="0.7" />
    <circle cx="88" cy="190" r="7" fill={INK} opacity="0.7" />
  </svg>
);

const CartIcon = ({ accent, k }) => (
  <svg width={180 * k} height={180 * k} viewBox="0 0 200 200">
    <path d="M15 15 H45 L65 125 H165 L185 45 H55" fill="none" stroke={accent} strokeWidth="14" strokeLinejoin="round" strokeLinecap="round" />
    <circle cx="80" cy="155" r="16" fill={accent} />
    <circle cx="150" cy="155" r="16" fill={accent} />
  </svg>
);

const BinderIcon = ({ accent, k }) => (
  <svg width={170 * k} height={170 * k} viewBox="0 0 200 200">
    <rect x="30" y="45" width="140" height="130" rx="12" fill="none" stroke={accent} strokeWidth="12" />
    <rect x="68" y="20" width="64" height="34" rx="8" fill={accent} />
    <line x1="55" y1="95" x2="145" y2="95" stroke={accent} strokeWidth="9" strokeLinecap="round" />
    <line x1="55" y1="120" x2="145" y2="120" stroke={accent} strokeWidth="9" strokeLinecap="round" />
    <line x1="55" y1="145" x2="115" y2="145" stroke={accent} strokeWidth="9" strokeLinecap="round" />
  </svg>
);

const EnvelopeIcon = ({ accent, k }) => (
  <svg width={190 * k} height={140 * k} viewBox="0 0 200 150">
    <rect x="10" y="15" width="180" height="120" rx="10" fill="none" stroke={accent} strokeWidth="12" />
    <path d="M14 20 L100 95 L186 20" fill="none" stroke={accent} strokeWidth="12" strokeLinejoin="round" strokeLinecap="round" />
  </svg>
);

const TagIcon = ({ accent, k }) => (
  <svg width={170 * k} height={150 * k} viewBox="0 0 200 160">
    <path d="M20 20 H110 L185 80 L110 140 H20 Z" fill="none" stroke={accent} strokeWidth="12" strokeLinejoin="round" strokeLinecap="round" />
    <circle cx="55" cy="55" r="13" fill={accent} />
  </svg>
);

const ICONS = { giraffe: GiraffeIcon, cart: CartIcon, binder: BinderIcon, envelope: EnvelopeIcon, tag: TagIcon };

const ARCS = [
  {
    name: "ORIGIN", start: 0, end: 76.02,
    accent: "#f4c95d", bgFrom: "#3a2e05", bgTo: "#0c0a03", icon: "giraffe",
    beats: [
      { t: 0.0, kind: "caption", text: "What if the toy store that raised a generation wasn't killed by Amazon \u2014" },
      { t: 4.7, kind: "caption", text: "\u2014 not by bad management, but by the people who promised to save it?" },
      { t: 9.56, kind: "caption", text: "How does a company go from the biggest toy retailer on Earth\u2026 to zero, in 13 years?" },
      { t: 15.72, kind: "stat", value: "1948", label: "Charles Lazarus opens his first store" },
      { t: 21.74, kind: "caption", text: "A single baby-furniture shop in Washington, D.C." },
      { t: 30.84, kind: "caption", text: "The toys sold faster than anything else in the store." },
      { t: 40.88, kind: "caption", text: "1957 \u2014 renamed Toys R Us. The first big-box toy store in America." },
      { t: 53.2, kind: "stat", value: "1965", label: "Mascot Geoffrey the Giraffe gets his name" },
      { t: 58.52, kind: "caption", text: "For the next 50 years, that giraffe greets children at the door." },
      { t: 72.56, kind: "caption", text: "Keep that number in mind \u2014 it will come back." },
    ],
  },
  {
    name: "RISE", start: 76.02, end: 119.64,
    accent: "#e2434f", bgFrom: "#3a0f14", bgTo: "#0c0503", icon: "cart",
    beats: [
      { t: 76.02, kind: "stat", value: "1978", label: "Toys R Us goes public on the NYSE" },
      { t: 85.82, kind: "caption", text: "By the early 90s: already a billion-dollar business." },
      { t: 94.56, kind: "caption", text: "Crushing smaller toy shops \u2014 the same way big-box would later be crushed." },
      { t: 98.08, kind: "stat", value: "1,499", label: "Stores worldwide at the all-time peak, Jan 2005" },
      { t: 108.2, kind: "caption", text: "That number was the peak. It never got that big again." },
    ],
  },
  {
    name: "THE DEAL", start: 119.64, end: 203.5,
    accent: "#4fb8ad", bgFrom: "#0f2a2a", bgTo: "#051010", icon: "binder",
    beats: [
      { t: 119.64, kind: "caption", text: "Its debt had just been downgraded to junk status." },
      { t: 129.86, kind: "caption", text: "Wall Street read that downgrade as a for-sale sign." },
      { t: 134.4, kind: "caption", text: "KKR, Bain Capital, and Vornado Realty Trust show up with an offer." },
      { t: 145.28, kind: "stat", value: "$6.6B", label: "The 2005 buyout price, paid by KKR, Bain, Vornado" },
      { t: 150.5, kind: "caption", text: "The press releases called it a rescue." },
      { t: 152.52, kind: "caption", text: "What almost nobody noticed was how it would actually be paid." },
      { t: 163.66, kind: "stat", value: "$5.3B", label: "Of that price, loaded onto the company as debt" },
      { t: 175.68, kind: "caption", text: "That debt was placed directly onto Toys R Us itself." },
      { t: 180.78, kind: "stat", value: "$128M", label: "In fees collected by the buyers" },
      { t: 198.02, kind: "caption", text: "They were paid by the company\u2026 to indebt the company." },
    ],
  },
  {
    name: "COLLAPSE", start: 203.5, end: 353.56,
    accent: "#8fa3b0", bgFrom: "#23262b", bgTo: "#07080a", icon: "envelope",
    beats: [
      { t: 203.5, kind: "caption", text: "For a while, nobody had to reckon with it. The stores stayed full." },
      { t: 222.12, kind: "stat", value: "$400M", label: "Owed in interest, every single year" },
      { t: 239.86, kind: "caption", text: "$400 million a year does not just disappear." },
      { t: 250.88, kind: "caption", text: "The shelves were quietly emptying, one under-funded remodel at a time." },
      { t: 267.52, kind: "caption", text: "Walmart and Target undercut on price. Amazon undercut on convenience." },
      { t: 288.54, kind: "caption", text: "The debt was refinanced again and again \u2014 generating new fees every time." },
      { t: 312.3, kind: "stat", value: "$4.9B", label: "In debt at the 2017 bankruptcy filing" },
      { t: 335.16, kind: "caption", text: "Suppliers tightened credit right before the holidays." },
    ],
  },
  {
    name: "AFTERMATH", start: 353.56, end: 470.05,
    accent: "#c9ced3", bgFrom: "#2b2f33", bgTo: "#07080a", icon: "tag",
    beats: [
      { t: 353.56, kind: "caption", text: "Toys R Us announces it will close every single U.S. store." },
      { t: 359.62, kind: "stat", value: "735", label: "U.S. stores closed in the 2018 liquidation" },
      { t: 363.0, kind: "stat", value: "33,000", label: "Employees who lost their jobs" },
      { t: 384.92, kind: "caption", text: "Workers picket outside KKR's own headquarters." },
      { t: 388.64, kind: "caption", text: "They win a $20M hardship fund, a fraction of what the firms already collected." },
      { t: 398.62, kind: "caption", text: "Charles Lazarus dies one week after the liquidation is announced." },
      { t: 408.8, kind: "stat", value: "70 yrs", label: "From first store, 1948, to closure, 2018" },
      { t: 422.32, kind: "caption", text: "So what really killed Toys R Us?" },
      { t: 429.34, kind: "caption", text: "The answer is a financing structure, not Amazon, not one bad Christmas." },
      { t: 462.7, kind: "caption", text: "It fell because somebody else's debt had been standing on its shoulders the entire time." },
    ],
  },
];

const findArc = (t) => {
  for (const a of ARCS) {
    if (t >= a.start && t < a.end) return a;
  }
  return ARCS[ARCS.length - 1];
};

const activeBeat = (arc, t) => {
  let cur = null;
  let next = null;
  for (let i = 0; i < arc.beats.length; i++) {
    if (arc.beats[i].t <= t) {
      cur = arc.beats[i];
    } else {
      next = arc.beats[i];
      break;
    }
  }
  const nextT = next ? next.t : arc.end;
  return { beat: cur, nextT };
};

const GradientBG = ({ from, to, progress }) => (
  <AbsoluteFill
    style={{
      background: `radial-gradient(120% 100% at 30% 20%, ${to} 0%, ${from} 60%, ${to} 100%)`,
      transform: `scale(${1 + progress * 0.09})`,
    }}
  />
);

export const FullStory = () => {
  const frame = useCurrentFrame();
  const { fps, width } = useVideoConfig();
  const k = width / 1536;
  const t = frame / fps;

  const arc = findArc(t);
  const arcProgress = clamp01((t - arc.start) / (arc.end - arc.start));
  const { beat, nextT } = activeBeat(arc, t);

  const fadeIn = beat ? clamp01((t - beat.t) / 0.4) : 0;
  const fadeOut = beat ? clamp01((nextT - t) / 0.4) : 0;
  const contentOpacity = Math.min(fadeIn, fadeOut);

  const distToStart = t - arc.start;
  const distToEnd = arc.end - t;
  let boundaryDark = 0;
  if (distToStart < 0.5) boundaryDark = 1 - distToStart / 0.5;
  if (distToEnd < 0.5) boundaryDark = Math.max(boundaryDark, 1 - distToEnd / 0.5);

  const floatY = Math.sin((frame / 30) * 1.4) * 10 * k;
  const floatR = Math.sin((frame / 30) * 0.9) * 3;

  const Icon = ICONS[arc.icon];

  const isStat = beat && beat.kind === "stat";
  const popScale = beat ? interpolate(clamp01((t - beat.t) / 0.35), [0, 1], [0.7, 1], { extrapolateRight: "clamp" }) : 1;

  const totalDur = 470.047347;
  const progressPct = clamp01(t / totalDur) * 100;

  return (
    <AbsoluteFill style={{ backgroundColor: INK }}>
      <GradientBG from={arc.bgFrom} to={arc.bgTo} progress={arcProgress} />

      <AbsoluteFill
        style={{
          justifyContent: "flex-start",
          alignItems: "flex-end",
          padding: 48 * k,
        }}
      >
        <div
          style={{
            transform: `translateY(${floatY}px) rotate(${floatR}deg)`,
            opacity: 0.9,
          }}
        >
          <Icon accent={arc.accent} k={k} />
        </div>
      </AbsoluteFill>

      <AbsoluteFill
        style={{
          justifyContent: "center",
          alignItems: "flex-start",
          padding: 90 * k,
          paddingRight: width * 0.32,
        }}
      >
        {beat ? (
          <div style={{ opacity: contentOpacity, transform: `scale(${isStat ? popScale : 1})` }}>
            {isStat ? (
              <>
                <div
                  style={{
                    fontFamily: "Arial, Helvetica, sans-serif",
                    fontWeight: 900,
                    fontSize: 150 * k,
                    lineHeight: 1,
                    color: arc.accent,
                    textShadow: outline(Math.max(2, 4 * k), INK),
                  }}
                >
                  {beat.value}
                </div>
                <div
                  style={{
                    width: Math.min(520, beat.label.length * 14) * k,
                    height: 6 * k,
                    background: arc.accent,
                    marginTop: 10 * k,
                    marginBottom: 16 * k,
                    opacity: 0.85,
                  }}
                />
                <div
                  style={{
                    fontFamily: "Arial, Helvetica, sans-serif",
                    fontWeight: 700,
                    fontSize: 38 * k,
                    letterSpacing: 1 * k,
                    color: LIGHT,
                    maxWidth: width * 0.5,
                    textShadow: outline(Math.max(1, 3 * k), INK),
                  }}
                >
                  {beat.label}
                </div>
              </>
            ) : (
              <div
                style={{
                  fontFamily: "Arial, Helvetica, sans-serif",
                  fontWeight: 800,
                  fontSize: 46 * k,
                  lineHeight: 1.25,
                  color: LIGHT,
                  maxWidth: width * 0.52,
                  textShadow: outline(Math.max(1, 3 * k), INK),
                }}
              >
                {beat.text}
              </div>
            )}
          </div>
        ) : null}
      </AbsoluteFill>

      <AbsoluteFill
        style={{
          justifyContent: "flex-start",
          alignItems: "flex-start",
          padding: 40 * k,
        }}
      >
        <div
          style={{
            fontFamily: "Arial, Helvetica, sans-serif",
            fontWeight: 900,
            fontSize: 22 * k,
            letterSpacing: 3 * k,
            color: arc.accent,
            opacity: 0.85,
            textShadow: outline(1 * k, INK),
          }}
        >
          TOYS R US \u00b7 {arc.name}
        </div>
      </AbsoluteFill>

      <AbsoluteFill style={{ justifyContent: "flex-end" }}>
        <div style={{ height: 6 * k, width: "100%", background: "rgba(255,255,255,0.12)" }}>
          <div style={{ height: "100%", width: `${progressPct}%`, background: arc.accent }} />
        </div>
      </AbsoluteFill>

      <AbsoluteFill style={{ backgroundColor: "#000", opacity: boundaryDark * 0.5 }} />

      <Audio src={staticFile("audio_norm.mp3")} />
    </AbsoluteFill>
  );
};
