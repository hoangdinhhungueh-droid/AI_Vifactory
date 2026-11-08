// remotion/src/components/vox/springPresets.ts
/**
 * Vox Masterclass Motion Graphics Spring Physics Presets
 * Calibrated specifically for tactile editorial documentarians (Vox, Johnny Harris).
 * Rule: Camera is critically damped (never bounces); only physical objects bounce.
 */

export const SPRING_PRESETS = {
  /** Paper sliding into frame with natural inertia and subtle overshoot */
  paperSlide: {
    mass: 1.2,
    stiffness: 90,
    damping: 16,
  },
  /** Heavy investigative dossier, thick binder, or official case file */
  paperHeavy: {
    mass: 1.8,
    stiffness: 70,
    damping: 18,
  },
  /** Red hanko seal stamp, price fraud stamp, or kinetic number impact */
  stamp: {
    mass: 0.5,
    stiffness: 400,
    damping: 14,
  },
  /** Staccato metric grid cells, chart bars, pop-in badges with lively bounce */
  chartPop: {
    mass: 0.6,
    stiffness: 220,
    damping: 12,
  },
  /** Text labels, captions, metadata tags — snaps firmly into place without bounce */
  labelSnap: {
    mass: 0.4,
    stiffness: 300,
    damping: 26,
  },
  /** Camera push-in, pan, or tilt — critically damped, perfectly smooth, zero overshoot */
  cameraMove: {
    mass: 1.0,
    stiffness: 60,
    damping: 30,
  },
  /** Opuscar Snappy ease-in (.7, 0, .2, 1) with mechanical back-overshoot, settling in 0.2s-0.3s */
  opuscarSnappy: {
    mass: 0.35,
    stiffness: 290,
    damping: 15,
  },
  /** Opuscar Stamp Slam: 0.09s drop from 2.6x to 1x with damped micro-bounce */
  opuscarStampSlam: {
    mass: 0.3,
    stiffness: 380,
    damping: 14,
  },
  /** Opuscar Dimension Line Ride: crisp arrowhead tap with mechanical counter tick lock */
  opuscarDimensionLine: {
    mass: 0.4,
    stiffness: 320,
    damping: 24,
  },
} as const;

export type SpringPresetName = keyof typeof SPRING_PRESETS;
