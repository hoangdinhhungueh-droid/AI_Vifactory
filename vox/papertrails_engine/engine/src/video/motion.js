// Pure stateless 3D animation primitives (Anticipation, Squash & Stretch, Arcs, Overlap).
export const clamp01 = x => Math.min(1, Math.max(0, x));
export const smooth = x => { const u = clamp01(x); return u * u * (3 - 2 * u); };
export const easeInOutCubic = x => { const u = clamp01(x); return u < 0.5 ? 4 * u * u * u : 1 - Math.pow(-2 * u + 2, 3) / 2; };
export const easeOutBack = x => { const u = clamp01(x); const c = 1.70158; return 1 + (c + 1) * Math.pow(u - 1, 3) + c * Math.pow(u - 1, 2); };

/** Volume-preserving Squash & Stretch around grounded Y base: sx * sy * sz ~= 1. */
export function squashPreserveVolume(sy) {
  const safeY = Math.max(0.55, Math.min(1.65, sy));
  const xz = 1 / Math.sqrt(safeY);
  return { sx: xz, sy: safeY, sz: xz };
}

/**
 * Delayed secondary overlap ramp (0..1) starting `delaySec` after trigger.
 */
export function overlap(local, triggerSec, delaySec = 0.08, durSec = 0.24) {
  return smooth((local - (triggerSec + delaySec)) / Math.max(0.05, durSec));
}

/**
 * 3-phase tactile strike envelope:
 * 1) Anticipation pull-back (-antDur..0 around contactSec)
 * 2) Snappy strike impact (0..strikeDur)
 * 3) Volume-preserving squash & damped settle overshoot (+settleDur)
 */
export function impactPulse(local, contactSec = 0.45, antDur = 0.14, strikeDur = 0.16, settleDur = 0.30) {
  const safeContact = Math.max(antDur + 0.05, contactSec);
  const tAnt = safeContact - antDur;
  if (local < tAnt) return { lift: 0, impact: 0, squashY: 1, settle: 0, struck: false };
  if (local < safeContact) {
    const u = smooth((local - tAnt) / antDur);
    return { lift: u, impact: 0, squashY: 1 + 0.12 * u, settle: 0, struck: false };
  }
  if (local < safeContact + strikeDur) {
    const u = easeInOutCubic((local - safeContact) / strikeDur);
    return { lift: 1 - u, impact: u, squashY: 1 - 0.18 * u, settle: 0, struck: u > 0.85 };
  }
  const s = clamp01((local - safeContact - strikeDur) / settleDur);
  const rebound = Math.sin(s * Math.PI) * Math.exp(-3.2 * s) * 0.14;
  return { lift: 0, impact: 1, squashY: 1 + rebound, settle: easeOutBack(s), struck: true };
}

/** Quadratic Bezier arc helper for thrown/sweeping paper props. */
export function bezierArc(a, b, liftY, u) {
  const t = clamp01(u), inv = 1 - t;
  return {
    x: inv * inv * a.x + 2 * inv * t * ((a.x + b.x) / 2) + t * t * b.x,
    y: inv * inv * a.y + 2 * inv * t * (Math.max(a.y, b.y) + liftY) + t * t * b.y,
    z: inv * inv * a.z + 2 * inv * t * ((a.z + b.z) / 2) + t * t * b.z,
  };
}
