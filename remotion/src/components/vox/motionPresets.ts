/**
 * motionPresets.ts — Parameterized 3-Tier Motion Architecture (Vox Engine v3).
 * Governed by the 4 Golden Cinematography Laws from Boss Claude Opus 5.5:
 *   Law 1: Optical Rest Anchor (gaze fixation at center)
 *   Law 2: Velocity Budget (calm=0.08, standard=0.15, punch=0.35) & Asymmetric Deceleration (30% acc, 70% dec)
 *   Law 3: Camera-Object Kinematic Coupling (reacts to physical events with 2-4 frame lag)
 *   Law 4: Spatial Horizon & Perspective Consistency (no in-shot roll)
 */

export type MotionTier = "calm" | "standard" | "punch";

export type CameraPose = {
  cx: number;    // viewport center X ratio (0..1, default 0.5)
  cy: number;    // viewport center Y ratio (0..1, default 0.5)
  zoom: number;  // 1.0 = native frame, max 1.15 to preserve pixel density
  roll: number;  // subtle fixed tilt degrees (-5..5)
};

export interface SteppedPose {
  frame: number;          // Target transition start frame or keyframe mark
  scale: number;          // Scale factor (e.g. 1.0, 1.35, 1.70)
  x?: number;             // Pixel offset X
  y?: number;             // Pixel offset Y
  rotateZ?: number;       // Rotation in degrees (dutch angle, rake, tracking)
  rotation?: number;      // Backward compatible alias for rotateZ
  hold?: number;          // Hold duration in frames (dead-stop lock)
  whipFrames?: number;    // Duration of rapid transition (<= 8-12 frames)
  whipDuration?: number;  // Backward compatible alias for whipFrames
  curve?: "whip" | "glide" | "staccato" | "dutch";
  impactShake?: number;   // Amplitude in px for landing impact shake (e.g. 3px for stamp)
  microDrift?: number;    // Amplitude in px for living loupe/micro-drift during hold
  lock?: boolean;         // Explicit dead-stop lock flag (defaults to true)
  overshoot?: number;     // % overshoot before clamp
}

export type MotionPreset = {
  id: string;
  name: string;
  tier: MotionTier;
  from: CameraPose;
  to: CameraPose;
  holdInFrames: number;      // Initial resting hold (at least 6-12 frames)
  holdOutFrames: number;     // Final resting landing hold (at least 18-24 frames)
  reactDelayFrames: number;  // Natural human operator reaction lag (2-4 frames)
  settle: "ease" | "spring";
  driftAmplitude: number;    // Micro living drift amplitude (0.001 - 0.003)
  steppedPunches?: SteppedPose[]; // Vox Stepped Framing & Kinetic Dead-Stop Locks
};

export const SPEED_BUDGET: Record<MotionTier, number> = {
  calm: 0.08,      // max 8% screen width per second
  standard: 0.15,  // max 15% screen width per second
  punch: 0.35,     // max 35% screen width per second (max 10 frames with blur)
};

/**
 * MICRO_WHIP_SPRING — Authoritative Spring Config for Vox Stepped Punches.
 * overshootClamping: true is MANDATORY to enforce absolute rock-solid dead-stop lock.
 */
export const MICRO_WHIP_SPRING = {
  damping: 200,
  mass: 0.4,
  stiffness: 260,
  overshootClamping: true, // Dead-stop lock
};

export const CANONICAL_MOTION_PRESETS: Record<number, MotionPreset> = {
  1: {
    id: "motion_1_unfold_diagonal_glide",
    name: "POP-UP UNFOLD & 90° STEPPED TRACKING",
    tier: "standard",
    from: { cx: 0.48, cy: 0.48, zoom: 1.0, roll: 0 },
    to: { cx: 0.52, cy: 0.52, zoom: 1.05, roll: 0 },
    holdInFrames: 10,
    holdOutFrames: 24,
    reactDelayFrames: 4,
    settle: "ease",
    driftAmplitude: 0.0015,
    steppedPunches: [
      { frame: 0, scale: 1.00, rotateZ: 0, x: 0, y: 0, hold: 20 },
      { frame: 20, scale: 1.35, rotateZ: 45, x: 15, y: -15, hold: 40, whipFrames: 8, curve: "whip" },
      { frame: 68, scale: 1.70, rotateZ: 90, x: 30, y: -30, hold: 55, whipFrames: 7, curve: "whip" },
    ],
  },
  2: {
    id: "motion_2_stamp_impact_rack_focus",
    name: "SEAL STAMP IMPACT & STEPPED RAKE",
    tier: "standard",
    from: { cx: 0.50, cy: 0.50, zoom: 1.02, roll: 0 },
    to: { cx: 0.50, cy: 0.49, zoom: 1.06, roll: 0 },
    holdInFrames: 8,
    holdOutFrames: 24,
    reactDelayFrames: 3,
    settle: "spring",
    driftAmplitude: 0.0012,
    steppedPunches: [
      { frame: 0, scale: 1.00, rotateZ: 0, x: 0, y: 0, hold: 15 },
      { frame: 15, scale: 1.30, rotateZ: 15, x: 0, y: 10, hold: 35, whipFrames: 6, impactShake: 3, curve: "whip" },
      { frame: 56, scale: 1.65, rotateZ: 30, x: 0, y: 20, hold: 60, whipFrames: 9, curve: "whip" },
    ],
  },
  3: {
    id: "motion_3_caliper_anchored_glide",
    name: "CALIPER CLAMP & ODOMETER ROLLUP GLIDE",
    tier: "calm",
    from: { cx: 0.49, cy: 0.50, zoom: 1.03, roll: 0 },
    to: { cx: 0.51, cy: 0.50, zoom: 1.07, roll: 0 },
    holdInFrames: 12,
    holdOutFrames: 24,
    reactDelayFrames: 3,
    settle: "ease",
    driftAmplitude: 0.001,
    steppedPunches: [
      { frame: 0, scale: 1.00, rotateZ: 0, x: 0, y: 0, hold: 18 },
      { frame: 18, scale: 1.30, rotateZ: 0, x: 10, y: 0, hold: 45, whipFrames: 12, curve: "glide" },
      { frame: 75, scale: 1.75, rotateZ: 0, x: 20, y: 0, hold: 70, whipFrames: 7, curve: "whip" },
    ],
  },
  4: {
    id: "motion_4_yarn_motivated_follow_pan",
    name: "RED YARN VECTOR TRACE & STACCATO SNAP",
    tier: "standard",
    from: { cx: 0.46, cy: 0.50, zoom: 1.0, roll: 0 },
    to: { cx: 0.54, cy: 0.50, zoom: 1.04, roll: 0 },
    holdInFrames: 8,
    holdOutFrames: 22,
    reactDelayFrames: 3,
    settle: "ease",
    driftAmplitude: 0.0018,
    steppedPunches: [
      { frame: 0, scale: 1.00, rotateZ: 0, x: 0, y: 0, hold: 8 },
      { frame: 8, scale: 1.35, rotateZ: -2, x: -120, y: 40, hold: 20, whipFrames: 7, curve: "staccato" },
      { frame: 35, scale: 1.68, rotateZ: 1.5, x: 90, y: -60, hold: 25, whipFrames: 8, curve: "staccato" },
    ],
  },
  5: {
    id: "motion_5_loupe_pivot_orbit",
    name: "OPTICAL LOUPE & MICRO-INSPECTION PUNCH",
    tier: "calm",
    from: { cx: 0.50, cy: 0.50, zoom: 1.04, roll: -3 },
    to: { cx: 0.50, cy: 0.50, zoom: 1.08, roll: 3 },
    holdInFrames: 10,
    holdOutFrames: 24,
    reactDelayFrames: 4,
    settle: "ease",
    driftAmplitude: 0.001,
    steppedPunches: [
      { frame: 0, scale: 1.00, rotateZ: 0, x: 0, y: 0, hold: 10 },
      { frame: 10, scale: 1.90, rotateZ: 0, x: 30, y: -10, hold: 24, whipFrames: 10, microDrift: 2, curve: "whip" },
      { frame: 44, scale: 1.40, rotateZ: 0, x: 0, y: 0, hold: 25, whipFrames: 6, curve: "whip" },
    ],
  },
  6: {
    id: "motion_6_paradox_fixed_dutch_push",
    name: "PARADOX & FIXED DUTCH STEPPED HIGHLIGHT",
    tier: "punch",
    from: { cx: 0.50, cy: 0.50, zoom: 1.0, roll: -4.5 },
    to: { cx: 0.50, cy: 0.50, zoom: 1.09, roll: -4.5 },
    holdInFrames: 6,
    holdOutFrames: 26,
    reactDelayFrames: 2,
    settle: "spring",
    driftAmplitude: 0.0015,
    steppedPunches: [
      { frame: 0, scale: 1.00, rotateZ: 0, x: 0, y: 0, hold: 6 },
      { frame: 6, scale: 1.50, rotateZ: -8, x: 0, y: 0, hold: 30, whipFrames: 12, curve: "dutch" },
      { frame: 48, scale: 1.75, rotateZ: -8, x: 0, y: 0, hold: 40, whipFrames: 10, curve: "dutch" },
    ],
  },
};
