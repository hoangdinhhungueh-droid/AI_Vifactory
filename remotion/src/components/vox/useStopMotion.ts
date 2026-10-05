import { useCurrentFrame, useVideoConfig } from "remotion";

export interface StopMotionState {
  qFrame: number;
  dx: number;
  dy: number;
  dRot: number;
  step: number;
}

/**
 * Deterministic 12fps Stop-Motion Quantizer & Tactile Paper Jitter Hook
 * Converts smooth 30fps interpolation into authentic 12fps (or 15fps) stepped
 * stop-motion animation ("on twos/threes") with subtle frame-stepped paper jitter.
 */
export const useStopMotion = (
  stopFps = 12,
  jitterPx = 1.1,
  seed = 1
): StopMotionState => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const step = Math.max(1, Math.round((fps || 30) / stopFps));
  const qFrame = Math.floor(frame / step) * step;

  // Deterministic hash per quantized step + seed
  const h1 = Math.sin(qFrame * 12.9898 + seed * 78.233) * 43758.5453;
  const h2 = Math.cos(qFrame * 45.164 + seed * 31.415) * 23421.6312;
  const h3 = Math.sin(qFrame * 93.712 + seed * 17.891) * 65432.1098;

  const r1 = h1 - Math.floor(h1);
  const r2 = h2 - Math.floor(h2);
  const r3 = h3 - Math.floor(h3);

  const dx = (r1 - 0.5) * 2 * jitterPx;
  const dy = (r2 - 0.5) * 2 * jitterPx;
  const dRot = (r3 - 0.5) * 0.65;

  return { qFrame, dx, dy, dRot, step };
};
