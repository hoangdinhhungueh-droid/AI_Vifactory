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
};

export const SPEED_BUDGET: Record<MotionTier, number> = {
  calm: 0.08,      // max 8% screen width per second
  standard: 0.15,  // max 15% screen width per second
  punch: 0.35,     // max 35% screen width per second (max 10 frames with blur)
};

export const CANONICAL_MOTION_PRESETS: Record<number, MotionPreset> = {
  1: {
    id: "motion_1_unfold_diagonal_glide",
    name: "POP-UP UNFOLD & 90° DIAGONAL GLIDE",
    tier: "standard",
    from: { cx: 0.48, cy: 0.48, zoom: 1.0, roll: 0 },
    to: { cx: 0.52, cy: 0.52, zoom: 1.05, roll: 0 },
    holdInFrames: 10,
    holdOutFrames: 24,
    reactDelayFrames: 4,
    settle: "ease",
    driftAmplitude: 0.0015,
  },
  2: {
    id: "motion_2_stamp_impact_rack_focus",
    name: "SEAL STAMP IMPACT & SEQUENTIAL RACK FOCUS",
    tier: "standard",
    from: { cx: 0.50, cy: 0.50, zoom: 1.02, roll: 0 },
    to: { cx: 0.50, cy: 0.49, zoom: 1.06, roll: 0 },
    holdInFrames: 8,
    holdOutFrames: 24,
    reactDelayFrames: 3,
    settle: "spring",
    driftAmplitude: 0.0012,
  },
  3: {
    id: "motion_3_caliper_anchored_glide",
    name: "CALIPER CLAMP & ANCHORED MACRO GLIDE",
    tier: "calm",
    from: { cx: 0.49, cy: 0.50, zoom: 1.03, roll: 0 },
    to: { cx: 0.51, cy: 0.50, zoom: 1.07, roll: 0 },
    holdInFrames: 12,
    holdOutFrames: 24,
    reactDelayFrames: 3,
    settle: "ease",
    driftAmplitude: 0.001,
  },
  4: {
    id: "motion_4_yarn_motivated_follow_pan",
    name: "RED YARN TENSION & MOTIVATED FOLLOW-PAN",
    tier: "standard",
    from: { cx: 0.46, cy: 0.50, zoom: 1.0, roll: 0 },
    to: { cx: 0.54, cy: 0.50, zoom: 1.04, roll: 0 },
    holdInFrames: 8,
    holdOutFrames: 22,
    reactDelayFrames: 3,
    settle: "ease",
    driftAmplitude: 0.0018,
  },
  5: {
    id: "motion_5_loupe_pivot_orbit",
    name: "OPTICAL LOUPE & 8° PIVOT ORBIT",
    tier: "calm",
    from: { cx: 0.50, cy: 0.50, zoom: 1.04, roll: -3 },
    to: { cx: 0.50, cy: 0.50, zoom: 1.08, roll: 3 },
    holdInFrames: 10,
    holdOutFrames: 24,
    reactDelayFrames: 4,
    settle: "ease",
    driftAmplitude: 0.001,
  },
  6: {
    id: "motion_6_paradox_fixed_dutch_push",
    name: "PARADOX & FIXED DUTCH HIGHLIGHT PUSH",
    tier: "punch",
    from: { cx: 0.50, cy: 0.50, zoom: 1.0, roll: -4.5 },
    to: { cx: 0.50, cy: 0.50, zoom: 1.09, roll: -4.5 },
    holdInFrames: 6,
    holdOutFrames: 26,
    reactDelayFrames: 2,
    settle: "spring",
    driftAmplitude: 0.0015,
  },
};
