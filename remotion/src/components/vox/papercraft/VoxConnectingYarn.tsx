import React from "react";
import { Easing, interpolate, spring, useCurrentFrame, useVideoConfig } from "remotion";
import { VoxBrassPin } from "./VoxBrassPin";

export interface VoxConnectingYarnProps {
  fromX: number; // % of canvas width (0-100) or px if > 100
  fromY: number; // % of canvas height (0-100) or px if > 100
  toX: number;   // % of canvas width (0-100) or px if > 100
  toY: number;   // % of canvas height (0-100) or px if > 100
  color?: string; // default #dc2626 (crimson red yarn)
  yarnThickness?: number; // default 4.2
  sagAmount?: number;     // optional catenary curve sag in px (default auto-scaled to distance)
  drawStartFrame?: number; // default 15
  drawDuration?: number;   // default 20
  label?: string;          // optional pinned evidence label
  showPins?: boolean;      // default true: pins yarn ends into the corkboard/paper
  pinSize?: number;        // default 24
  width?: number;
  height?: number;
  style?: React.CSSProperties;
}

/**
 * VoxConnectingYarn: Tactile Handcrafted 3D Red Woolen Yarn Component.
 *
 * Implements Rule 122 & Vox Documentary Reference Parity:
 * - Natural gravitational catenary sag based on Euclidean distance
 * - 3D twisted multi-ply woolen cord texture with diffuse cast paper shadow
 * - Spiral fiber braiding overlay simulating authentic twisted string
 * - Loop knots anchoring onto 3D metallic brass pushpins
 */
export const VoxConnectingYarn: React.FC<VoxConnectingYarnProps> = ({
  fromX,
  fromY,
  toX,
  toY,
  color = "#dc2626",
  yarnThickness = 4.2,
  sagAmount,
  drawStartFrame = 15,
  drawDuration = 20,
  label,
  showPins = true,
  pinSize = 24,
  width: customW,
  height: customH,
  style,
}) => {
  const frame = useCurrentFrame();
  const { width: configW = 1920, height: configH = 1080 } = useVideoConfig();
  const width = customW || configW;
  const height = customH || configH;

  const drawProgress = interpolate(
    frame,
    [drawStartFrame, drawStartFrame + drawDuration],
    [0, 1],
    {
      extrapolateLeft: "clamp",
      extrapolateRight: "clamp",
      easing: Easing.bezier(0.16, 1, 0.3, 1),
    }
  );

  if (drawProgress < 0.005) return null;

  // Resolve pixel coordinates (handle either % 0-100 or raw px)
  const x1 = fromX <= 100 ? (fromX / 100) * width : fromX;
  const y1 = fromY <= 100 ? (fromY / 100) * height : fromY;
  const x2 = toX <= 100 ? (toX / 100) * width : toX;
  const y2 = toY <= 100 ? (toY / 100) * height : toY;

  // Euclidean distance between pin anchors
  const dx = x2 - x1;
  const dy = y2 - y1;
  const dist = Math.hypot(dx, dy);

  // Natural catenary sag (longer span = deeper physical slack)
  const effectiveSag =
    sagAmount !== undefined
      ? sagAmount
      : Math.min(80, Math.max(22, dist * 0.11));

  // Midpoint with downward gravity deflection
  const midX = (x1 + x2) / 2;
  const midY = (y1 + y2) / 2;
  const cx = midX;
  const cy = midY + effectiveSag;

  const pathD = `M ${x1} ${y1} Q ${cx} ${cy} ${x2} ${y2}`;
  // Arc length approximation for quadratic bezier curve
  const approxLen = dist * 1.15 + effectiveSag * 0.8;
  const dashOffset = approxLen * (1 - drawProgress);

  // Optional evidence label spring bounce
  const labelRel = Math.max(0, frame - (drawStartFrame + Math.round(drawDuration * 0.65)));
  const labelSpring = spring({
    frame: labelRel,
    fps: 30,
    config: { damping: 12, mass: 0.4, stiffness: 190 },
  });

  const filterId = `yarnShadow-${Math.round(x1)}-${Math.round(x2)}-${Math.round(y1)}`;

  return (
    <div
      style={{
        position: "absolute",
        inset: 0,
        pointerEvents: "none",
        zIndex: 26,
        ...style,
      }}
    >
      <svg
        width={width}
        height={height}
        viewBox={`0 0 ${width} ${height}`}
        style={{
          position: "absolute",
          top: 0,
          left: 0,
          width: "100%",
          height: "100%",
          overflow: "visible",
        }}
      >
        <defs>
          <filter id={filterId} x="-20%" y="-20%" width="150%" height="150%">
            <feGaussianBlur in="SourceAlpha" stdDeviation="4.5" />
            <feOffset dx="3" dy="9" result="offsetblur" />
            <feComponentTransfer>
              <feFuncA type="linear" slope="0.42" />
            </feComponentTransfer>
            <feMerge>
              <feMergeNode />
              <feMergeNode in="SourceGraphic" />
            </feMerge>
          </filter>
        </defs>

        {/* 1. PHYSICAL CAST SHADOW LAYER ONTO THE PAPER BACKGROUND */}
        <path
          d={pathD}
          fill="none"
          stroke="rgba(30, 15, 10, 0.45)"
          strokeWidth={yarnThickness + 3.5}
          strokeDasharray={approxLen}
          strokeDashoffset={dashOffset}
          strokeLinecap="round"
          transform="translate(3, 8)"
          filter="blur(3.5px)"
        />

        {/* 2. DEEP CRIMSON WOOL CORE BASE */}
        <path
          d={pathD}
          fill="none"
          stroke="#991b1b"
          strokeWidth={yarnThickness + 0.8}
          strokeDasharray={approxLen}
          strokeDashoffset={dashOffset}
          strokeLinecap="round"
        />

        {/* 3. PRIMARY VIBRANT WOOLEN BODY */}
        <path
          d={pathD}
          fill="none"
          stroke={color}
          strokeWidth={yarnThickness}
          strokeDasharray={approxLen}
          strokeDashoffset={dashOffset}
          strokeLinecap="round"
        />

        {/* 4. BRAIDED TWIST FIBER OVERLAY (Simulates 2-ply twisted woolen yarn) */}
        <path
          d={pathD}
          fill="none"
          stroke="rgba(254, 202, 202, 0.65)"
          strokeWidth={yarnThickness * 0.35}
          strokeDasharray="4 3"
          strokeDashoffset={dashOffset}
          strokeLinecap="round"
        />

        {/* 5. MICRO FIBER SHINE HIGHLIGHT */}
        <path
          d={pathD}
          fill="none"
          stroke="rgba(255, 255, 255, 0.45)"
          strokeWidth={Math.max(1, yarnThickness * 0.2)}
          strokeDasharray="2 6"
          strokeDashoffset={dashOffset + 2}
          strokeLinecap="round"
        />

        {/* 6. ANCHOR LOOP KNOTS AROUND PUSH PINS */}
        {drawProgress >= 0.05 && (
          <g>
            {/* Start Knot Loop */}
            <circle
              cx={x1}
              cy={y1}
              r={yarnThickness * 1.5}
              fill="none"
              stroke={color}
              strokeWidth={yarnThickness * 0.85}
              filter="drop-shadow(1px 3px 3px rgba(0,0,0,0.4))"
            />
            <circle
              cx={x1}
              cy={y1}
              r={yarnThickness * 0.6}
              fill="#7f1d1d"
            />
          </g>
        )}

        {drawProgress >= 0.95 && (
          <g>
            {/* End Knot Loop */}
            <circle
              cx={x2}
              cy={y2}
              r={yarnThickness * 1.5}
              fill="none"
              stroke={color}
              strokeWidth={yarnThickness * 0.85}
              filter="drop-shadow(1px 3px 3px rgba(0,0,0,0.4))"
            />
            <circle
              cx={x2}
              cy={y2}
              r={yarnThickness * 0.6}
              fill="#7f1d1d"
            />
          </g>
        )}

        {/* 7. PINNED EVIDENCE LABEL SUSPENDED ALONG THE CURVE */}
        {label && labelSpring > 0.05 && (
          <g transform={`translate(${cx}, ${cy - 14}) scale(${labelSpring})`}>
            <rect
              x={-((label.length * 8.5 + 28) / 2)}
              y={-14}
              width={label.length * 8.5 + 28}
              height={28}
              rx={3}
              fill="#FAF7EE"
              stroke="#991B1B"
              strokeWidth="1.5"
              filter="drop-shadow(0 4px 8px rgba(0,0,0,0.35))"
            />
            <text
              x={0}
              y={4.5}
              textAnchor="middle"
              fill="#0F172A"
              fontSize={11.5}
              fontWeight={900}
              letterSpacing={1.3}
              fontFamily="'Courier New', Courier, monospace"
            >
              {label}
            </text>
          </g>
        )}
      </svg>

      {/* 8. 3D BRASS PINS TACKING THE YARN INTO THE BOARD */}
      {showPins && (
        <>
          <VoxBrassPin
            x={x1}
            y={y1}
            size={pinSize}
            dropFrame={drawStartFrame}
          />
          {drawProgress >= 0.85 && (
            <VoxBrassPin
              x={x2}
              y={y2}
              size={pinSize}
              dropFrame={drawStartFrame + Math.round(drawDuration * 0.85)}
            />
          )}
        </>
      )}
    </div>
  );
};
