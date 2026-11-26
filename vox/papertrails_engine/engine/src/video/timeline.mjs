export const PROPS = ['none', 'village', 'forest', 'bridge', 'mountain', 'sun', 'moon', 'house', 'tree', 'book', 'coin', 'chart', 'factory', 'clock', 'people', 'water', 'globe', 'voice-note', 'edit-board', 'pop-up', 'film', 'bubble', 'mic', 'courthouse', 'gavel', 'ledger', 'container', 'vault', 'scale', 'contract', 'megaphone', 'briefcase', 'shield', 'hanko-stamp', 'brass-caliper', 'forensic-loupe'];
export const ACTIONS = ['walk', 'idle', 'reveal', 'celebrate', 'grow'];
export const CAMERAS = ['wide', 'close', 'orbit', 'top', 'push', 'low', 'crane'];
export function frameCount(t) { return Math.ceil(t.duration * t.fps - 1e-9); }
export function sampleTimeline(t, time) {
  const scene = t.scenes.find(s => time >= s.start && time < s.end) || t.scenes.at(-1);
  return { scene, local: Math.max(0, time - scene.start), progress: Math.min(1, Math.max(0, (time - scene.start) / (scene.end - scene.start))), ...captionAt(t, time) };
}
// The active caption plus, when measured word timings exist, which word is being spoken.
function captionAt(t, time) {
  const c = t.captions.find(c => time >= c.start && time < c.end);
  if (!c) return { caption: '', captionWords: null, captionIndex: -1, captionStart: 0 };
  const words = Array.isArray(c.words) && c.words.length ? c.words : null;
  let index = -1;
  if (words) for (let i = 0; i < words.length; i++) if (time >= words[i].start) index = i;
  return { caption: c.text, captionWords: words, captionIndex: index, captionStart: c.start };
}
export function seededRandom(seed) {
  return () => { seed |= 0; seed = seed + 0x6d2b79f5 | 0; let n = Math.imul(seed ^ seed >>> 15, 1 | seed); n ^= n + Math.imul(n ^ n >>> 7, 61 | n); return ((n ^ n >>> 14) >>> 0) / 4294967296; };
}
const check = (ok, message) => { if (!ok) throw new Error(`Invalid timeline: ${message}`); };
export function validateTimeline(t) {
  check(t && typeof t === 'object' && t.version === 1, 'version must be 1');
  check([t.width, t.height].every(n => Number.isInteger(n) && n >= 144 && n <= 3840 && n % 2 === 0), 'even dimensions between 144 and 3840');
  check(Math.abs(t.width / t.height - 16 / 9) < .005 || Math.abs(t.width / t.height - 9 / 16) < .005, 'aspect must be 16:9 or 9:16');
  check(Number.isInteger(t.fps) && t.fps >= 1 && t.fps <= 60, 'fps 1..60');
  check(Number.isInteger(t.seed) && t.seed >= 0 && t.seed <= 0xffffffff, 'seed must be a uint32');
  check(Number.isFinite(t.duration) && t.duration > 0 && t.duration <= 86400, 'duration 0..86400 seconds');
  check(typeof t.audio === 'string' && t.audio.length > 0, 'audio path required');
  check(Array.isArray(t.scenes) && t.scenes.length > 0, 'scenes required');
  const ids = new Set(); let end = 0;
  for (const s of t.scenes) {
    check(s && typeof s.id === 'string' && s.id.length > 0 && !ids.has(s.id), 'unique scene id required'); ids.add(s.id);
    check(Number.isFinite(s.start) && Number.isFinite(s.end) && Math.abs(s.start - end) < 1e-6 && s.end > s.start && s.end <= t.duration + 1e-6, `scene ${s.id} must be contiguous and within duration`); end = s.end;
    check(['heartland','desert','snow','blossom','pinewood'].includes(s.biome), 'unsupported biome');
    check(PROPS.includes(s.prop) && ACTIONS.includes(s.action) && CAMERAS.includes(s.camera), 'unsupported prop/action/camera');
    check(typeof s.night === 'boolean' && /^#[0-9a-f]{6}$/i.test(s.color), 'night boolean and #rrggbb color required');
    for (const k of ['narration','title','visual']) check(typeof s[k] === 'string', `${k} must be text`);
    if (s.card !== undefined) {
      const c = s.card;
      check(c && ['note','photo'].includes(c.kind), `scene ${s.id} card.kind must be note or photo`);
      check(c.head === undefined || typeof c.head === 'string', 'card.head must be text');
      check(c.lines === undefined || (Array.isArray(c.lines) && c.lines.length <= 12 && c.lines.every(l => typeof l === 'string')), 'card.lines must be up to 12 strings');
      check(c.side === undefined || ['left','right','center'].includes(c.side), 'card.side must be left, right or center');
      check(c.lineAt === undefined || (Array.isArray(c.lineAt) && c.lineAt.every(Number.isFinite)), 'card.lineAt must be numbers (seconds from scene start)');
      if (c.kind === 'photo') {
        check(typeof c.img === 'string' && /^data:image\/(jpeg|png|webp);base64,/.test(c.img), 'photo card needs an embedded data:image URI (no external URLs)');
        check(c.hl === undefined || (Array.isArray(c.hl) && c.hl.length === 4 && c.hl.every(Number.isFinite)), 'card.hl must be [x,y,w,h] in 0..1 image units');
      }
    }
    if (s.timing !== undefined) {
      const tm = s.timing;
      check(tm && typeof tm === 'object', `scene ${s.id} timing must be object`);
      if (tm.contactSec !== undefined) check(Number.isFinite(tm.contactSec) && tm.contactSec >= 0 && tm.contactSec <= (s.end - s.start) + 1e-6, `scene ${s.id} timing.contactSec must be within scene duration`);
    }
  }
  check(Math.abs(end - t.duration) < 1e-6, 'scenes must cover duration');
  if (t.foley_cues !== undefined) {
    check(Array.isArray(t.foley_cues), 'foley_cues must be array');
    for (const fc of t.foley_cues) {
      check(fc && Number.isFinite(fc.time_sec) && fc.time_sec >= 0 && fc.time_sec <= t.duration + 1e-6, 'foley cue time_sec within duration');
    }
  }
  check(Array.isArray(t.captions), 'captions array required'); let prev = 0;
  for (const c of t.captions) {
    check(c && Number.isFinite(c.start) && Number.isFinite(c.end) && c.start >= prev && c.end > c.start && c.end <= t.duration + 1e-6 && typeof c.text === 'string', 'captions must be ordered, non-overlapping, and within duration'); prev = c.end;
    if (c.words !== undefined) check(Array.isArray(c.words) && c.words.every(w => w && typeof w.word === 'string' && Number.isFinite(w.start) && Number.isFinite(w.end) && w.end >= w.start), 'caption words must be {word,start,end}');
  }
  return t;
}
