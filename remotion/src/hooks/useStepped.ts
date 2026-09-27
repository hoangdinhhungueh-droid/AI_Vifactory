import { useCurrentFrame, useVideoConfig } from 'remotion';

// Rule 122 & Vox Motion Engine 3.0: Only integer divisors of timeline FPS (30fps)
export const CADENCE = {
  smooth: 30, // hold 1 — data reveal, hero video (30fps)
  fluid: 15, // hold 2 — cận-hero, dynamic transition (15fps)
  cutout: 10, // hold 3 — tactile paper-cutout foreground (10fps)
  archival: 6, // hold 5 — archival dossier, historical recall (6fps)
} as const;

export type CadenceKey = keyof typeof CADENCE;

/**
 * Quantizes frame count to integer hold steps.
 * Prevents irregular 2:3 fractional judder caused by 12fps on a 30fps timeline.
 */
export const useStepped = (cadence: CadenceKey = 'cutout'): number => {
  const frame = useCurrentFrame();
  const { fps } = useVideoConfig();
  const target = CADENCE[cadence] || CADENCE.cutout;

  if (fps % target !== 0) {
    throw new Error(
      `[useStepped] ${target}fps cannot evenly divide video timeline ${fps}fps. ` +
        `Valid target rates: ${Object.values(CADENCE).join(', ')}`
    );
  }

  const hold = fps / target; // integer hold: 1, 2, 3, or 5
  return Math.floor(frame / hold) * hold;
};

/**
 * Pure helper for stepped frame calculation outside hooks or inside loops.
 */
export const getSteppedFrame = (
  frame: number,
  fps: number = 30,
  cadence: CadenceKey = 'cutout'
): number => {
  const target = CADENCE[cadence] || CADENCE.cutout;
  const hold = Math.max(1, Math.round(fps / target));
  return Math.floor(frame / hold) * hold;
};
