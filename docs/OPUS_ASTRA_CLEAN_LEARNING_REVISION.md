# 🏛️ OPUS 5.5 & ASTRA 6 JOINT ARCHITECTURAL REVISION
## Standard Protocol: "Học Sạch" Generalized Multi-Motion Pipeline (Zero-Hardcode Mandate)

> **Source Video:** [How to Make Viral Vox-Style Videos with AI](https://youtu.be/cXQuNBZA0FA) (AI PLAYBOOK)  
> **Convergence Lead:** Claude Opus 5.5 (Master Visual Architect)  
> **Forensic Auditor:** GPT-6-Astra (System Linter & Anti-Bias Gate)  
> **Date:** 2026-10-02 03:49:20  
> **Mandate Compliance:** Rule 118, 120, 122, 128, 132, 136

---

## 1. PHẦN I: BẢN THIẾT KẾ KIẾN TRÚC "HỌC SẠCH" (CLAUDE OPUS 5.5)

# VF Pipeline: Visual Architecture Revision Plan ("Học Sạch")

A few notes on scope first:

- I'm Claude. I'm not "Opus 5.5" or "Astra 6".
- I can't watch YouTube videos. This plan is built from the frame analysis you pasted, which cuts off at 00:41. Seconds 41–49 aren't covered.
- I haven't read your Remotion or B3 code yet. The contracts below are written generically. Point me at the repo and I'll map them onto your actual components and remove the MH370 relics.

The core idea of "học sạch" is simple. The Coca-Cola clip is treated only as evidence of a grammar. No topic, entity, date, or string from it may enter the pipeline. What we keep is how scenes are built and how they move, never what they show.

---

## 1. The "Học Sạch" Grammar

### 1.1 Scene as a formal structure

```
Scene      S = ⟨theme, archetype, E[], camera, duration⟩
Element    e = ⟨layer, role, content, anchor, motion_in, motion_idle, motion_out, t_in⟩
Beat grid  t_in(k) = t₀ + k·Δ,   Δ ∈ [4, 8] frames @30fps (≈130–270ms)
```

### 1.2 The 7-layer collage stack (back → front)

| Layer | Role | Abstracted from | Motion family |
|---|---|---|---|
| L1 Substrate | Paper/grid/blueprint texture | grid paper, ledger, crosshair card | camera drift only |
| L2 Context plate | Spatial frame: map, desk, chart axes, ledger page | world map (00:39), counter (00:34), ledger (00:40) | drop, slide, fade-scale |
| L3 Hero metaphor | One symbolic object, 35–50% of frame | megaphone (00:36), tincture bottle (00:33) | pop/zoom-in, then idle sway |
| L4 Supporting cutouts | 1–3 polaroids, portraits with sticker border, badges | polaroids (00:36, 00:41), round badges (00:35) | staggered drop/pop, idle float |
| L5 Data & vectors | Arrows, curves, bars, grid fills | exponential arrow (00:34), radiating vectors (00:39), cell fills (00:40) | stroke draw, grow, radiate, fill |
| L6 Typography | Editorial headline, 1–4 words | "HUMBLE START", "MARKETING WINS", "EVERYWHERE" | stamp / torn-label slap |
| L7 Chrome & atmosphere | Masthead banner, grain, vignette, dust | "STRATEGY – VOL. 4, NO. 2" | slide-down, flicker |

### 1.3 Composition archetypes (topic-free)

These are the reusable patterns the clip demonstrates. Each is a relation type, not a subject.

| Archetype | Narrative relation | Signature motion |
|---|---|---|
| `ORIGIN_CARD` | beginnings, founding, "in year X…" | card drop + giant numeral stamp |
| `GROWTH_CURVE` | rise, scale, compounding | axis draw → bar grow → arrow draw → badges pop along path |
| `MORPH_REVEAL` | transformation (A becomes B) | element morphs (bars → skyline) |
| `AMPLIFIER` | influence, propaganda, messaging | hero zoom + stamp burst + torn label |
| `PROLIFERATION` | multiplication, spread of instances | N items sprout on staggered beat |
| `RADIATION` | expansion from a center, contagion, export | N vectors fire from origin to targets |
| `SATURATION_GRID` | ubiquity, coverage, market share | grid cells fill → cutouts drop into filled cells |
| `CONFRONTATION` | conflict, rivalry, A vs B | two heroes slide in from opposite sides, vector clash at center |

`CONFRONTATION` isn't in the clip. It's an extension built from the same primitives, and you'll need it for corporate-battle and geopolitics content.

### 1.4 Motion primitive vocabulary

| Primitive | Definition (Remotion `spring`/`interpolate`) |
|---|---|
| `drop` | y: −h → 0, rotate: ±8° → ±2°, spring(damping 12) |
| `stamp` | scale 1.4 → 1.0 overshoot, 2-frame shake ±3px, optional ink-burst |
| `pop` | scale 0 → 1, spring(damping 9, mass 0.6) |
| `draw` | strokeDashoffset L → 0, ease-out, 12–20 frames |
| `grow` | scaleY 0 → 1 from baseline, staggered per bar |
| `radiate` | N × `draw` from shared origin, Δ = 3 frames |
| `fill` | cell opacity/scale 0 → 1, scan order (row-major or distance-from-origin) |
| `slap` | torn label: x offset + rotate −6° → −2°, slight scale settle |
| idle `float` | y += A·sin(2πt/T), A = 2–4px, T = 2–3s, phase-randomized |
| idle `sway` | rotate += 1–1.5°·sin(...) |
| camera | scale 1.00 → 1.05–1.08 over scene + 1–2% pan |

### 1.5 Density law (observed: 4–6 micro-motions per 2–3s scene)

```
motions_in_scene  ∈ [4, 6]           (entry + accent events)
elements_on_screen ≤ 6               (excluding L1, L7)
concurrent_entries ≤ 2               at any frame
max_gap_between_events ≤ 0.8s        (no "dead" stretch)
ambient_motion_active = true         every frame (camera + ≥1 idle)
```

---

## 2. Dynamic Visual Inference in B3 Director Plan

### 2.1 Inference pipeline per narration sentence

```
narration sentence
  → [a] semantic frame: entities, numbers, dates, places, actors, sentiment
  → [b] relation classification → archetype (table 1.3)
  → [c] core_idea (abstract noun phrase, language-neutral)
  → [d] visual_metaphor (tangible, cutout-able object)
  → [e] editorial_headline (1–4 words, target market language)
  → [f] theme (tone classifier)
  → [g] supporting_cutouts (1–3, grounded in entities)
  → [h] connecting_vectors (only if archetype requires them)
  → [i] grounding validator (reject anything not traceable to narration)
```

### 2.2 Field rules

**`core_idea`**: abstract and topic-independent, e.g. "small origin → dominant scale", "information suppression", "debt contagion". It drives archetype choice and is never rendered.

**`editorial_headline`**:
- 1–4 words, imperative or verdict tone ("HUMBLE START" style).
- Written in the market language. Length budget is measured in display width: Latin ≤ 18 chars, CJK ≤ 8 glyphs, Vietnamese counted with diacritics accounted for in font metrics.
- Must paraphrase the narration. No invented claims.

**`visual_metaphor`**:
- A single physical object that can be shot as a clean cutout (megaphone, padlock, hourglass, chess piece, cracked piggy bank).
- No logos, trademarks, or real people as the metaphor. Real people go in `supporting_cutouts`, sourced from licensed or public-domain archives.
- Must be culturally legible in the target market. B3 gets a `market` input, and a per-market blocklist can veto symbols.

**`theme`** (tone classifier):

| Signal | Theme |
|---|---|
| history, origins, culture, business rise | `vintage_paper` |
| crime, disaster, investigation, scandal | `dark_forensic` |
| strategy, technology, systems, how-it-works | `blueprint` |

**`supporting_cutouts`**: each is `{kind: polaroid | portrait | badge | chart_token, query, caption?}`. `query` is a search/generation prompt for the asset stage. B3 never emits URLs.

**`connecting_vectors`**:
- `radiating`: `{origin, targets[]}`
- `point_to_point`: `{from, to, curvature}`

Coordinates are semantic anchors (`geo:lat,lon`, `el:hero.right`, `el:cutout[1].top`), resolved to pixels by Remotion. B3 never emits pixels.

### 2.3 B3 output schema

```ts
// b3/schema.ts: single source of truth shared with Remotion
import { z } from "zod";

export const Anchor = z.string().regex(/^(geo:-?\d+(\.\d+)?,-?\d+(\.\d+)?|el:[a-z0-9_.\[\]]+|grid:\d+,\d+)$/);

export const Vector = z.discriminatedUnion("type", [
  z.object({ type: z.literal("radiating"), origin: Anchor, targets: z.array(Anchor).min(2).max(8) }),
  z.object({ type: z.literal("point_to_point"), from: Anchor, to: Anchor, curvature: z.number().min(-1).max(1) }),
]);

export const Cutout = z.object({
  kind: z.enum(["polaroid", "portrait", "badge", "chart_token"]),
  query: z.string().min(3),           // asset search/gen prompt, not a URL
  caption: z.string().max(24).optional(),
});

export const ScenePlan = z.object({
  scene_id: z.string(),
  market: z.enum(["en", "vi", "ja", "ko"]),
  source_text: z.string(),            // the narration sentence (for grounding)
  duration_s: z.number().min(2).max(6),
  core_idea: z.string(),
  archetype: z.enum(["ORIGIN_CARD","GROWTH_CURVE","MORPH_REVEAL","AMPLIFIER",
                     "PROLIFERATION","RADIATION","SATURATION_GRID","CONFRONTATION"]),
  theme: z.enum(["vintage_paper", "dark_forensic", "blueprint"]),
  editorial_headline: z.string().min(1),
  masthead: z.string().optional(),    // L7 chrome, also derived, never default
  visual_metaphor: z.object({ object: z.string(), query: z.string() }),
  supporting_cutouts: z.array(Cutout).max(3),
  connecting_vectors: z.array(Vector).max(2),
  key_figure: z.string().optional(),  // e.g. a year or number to stamp, from narration only
});
export type ScenePlan = z.infer<typeof ScenePlan>;
```

### 2.4 Grounding validator (anti-hardcode at the data level)

Run this after B3 and before render:

- Every number or date in `key_figure`, `caption`, or `editorial_headline` must appear in `source_text`, or in the episode research notes passed to B3.
- Reject any token on a contamination blocklist built from tutorial artifacts (`Coca-Cola`, `Pemberton`, `1886`, `MH370`, etc.). This catches LLM leakage from few-shot examples.
- Few-shot examples given to B3 must use synthetic topics that never appear in production, so the model learns the structure without copying the content.

### 2.5 Topic-agnostic check (same grammar, different worlds)

| Narration (paraphrased) | Archetype | Metaphor | Headline (market) | Theme |
|---|---|---|---|---|
| A small regional bank's bad loans spread to lenders across Asia | `RADIATION` | cracked domino | "LÂY LAN" (vi) | `dark_forensic` |
| A startup went from a garage to 40 countries in a decade | `GROWTH_CURVE` | seedling in a pot | "GARAGE TO GLOBE" (en) | `vintage_paper` |
| Two chipmakers fight over a single supplier | `CONFRONTATION` | tug-of-war rope | "供給戦争" (ja) | `blueprint` |

---

## 3. Zero-Hardcode Remotion Contract

### 3.1 Rules

1. Content props have no defaults. Every text, number, image, and anchor field is required, or optional with omit-on-absent behavior. No `defaultProps` containing words.
2. Style has defaults, but only from theme tokens. Colors, fonts, paper textures, and stroke widths come from `themes/{theme}.ts`, keyed by `theme` and `market` (font stacks for vi/ja/ko).
3. Missing means omitted, not substituted. If `supporting_cutouts` is empty, that layer doesn't render. Nothing like "Flight 370" can ever appear as a fallback.
4. Assets are resolved upstream. The asset stage turns `query` into `src` before render. Remotion receives `ResolvedScenePlan` with `src` fields and never fetches or guesses.
5. Remotion parses props with the same schema B3 uses: `ScenePlan.parse(props)` at composition entry. Invalid props fail the render loudly.

### 3.2 Composition shape

```tsx
// remotion/Scene.tsx
import { AbsoluteFill, useVideoConfig } from "remotion";
import { ResolvedScenePlan } from "../b3/schema-resolved";
import { themeTokens } from "./themes";
import { buildTimeline } from "./choreography/scheduler";
import { ARCHETYPES } from "./archetypes";

export const Scene: React.FC<{ plan: unknown }> = ({ plan: raw }) => {
  const plan = ResolvedScenePlan.parse(raw);           // fail fast, no silent defaults
  const { fps } = useVideoConfig();
  const tokens = themeTokens(plan.theme, plan.market); // style only
  const timeline = buildTimeline(plan, fps);           // see section 4
  const Layout = ARCHETYPES[plan.archetype];           // archetype = layout + anchor map, no text

  return (
    <AbsoluteFill style={{ background: tokens.substrate }}>
      <Layout plan={plan} tokens={tokens} timeline={timeline} />
    </AbsoluteFill>
  );
};
```

### 3.3 Enforcement in CI

- ESLint `react/jsx-no-literals` on `remotion/**`, with an allowlist limited to punctuation and symbols.
- A custom lint or grep gate that fails on string literals over 3 chars in `remotion/components/**` and `remotion/archetypes/**`.
- Contamination test: render each archetype with fuzzed props (random synthetic text in all 4 locales), then OCR sampled frames and assert that every detected word exists in the props.
- Snapshot tests per archetype × theme × market, using synthetic fixtures only.

---

## 4. Continuous Motion Without Overcrowding

### 4.1 Three-tier motion model

| Tier | Purpose | Always on? | Budget |
|---|---|---|---|
| A: Ambient | Prevents dead frames | Yes, every frame | camera push + idle float/sway on all settled elements + grain flicker |
| B: Entry beats | Builds the collage | Scheduled | 3–5 events, staggered |
| C: Accent | One payoff moment | Once per scene | stamp, vector radiate, or morph |

Tier A guarantees life. Tiers B and C carry the story. Clutter comes from too many Tier B and C events, never from Tier A.

### 4.2 Scheduler

```ts
// remotion/choreography/scheduler.ts
export function buildTimeline(plan: ResolvedScenePlan, fps: number) {
  const total = Math.round(plan.duration_s * fps);
  const maxElements = Math.min(6, Math.floor(plan.duration_s * 1.5) + 1); // 3s→5, 5s→6

  // Priority order: context → hero → headline → cutouts → vectors → chrome
  const queue = rankElements(plan).slice(0, maxElements);

  const delta = clamp(Math.round(total * 0.06), 4, 8);   // beat spacing in frames
  const accentAt = Math.round(total * 0.45);              // payoff lands near mid-scene
  const settleBy = Math.round(total * 0.7);               // all entries done by 70%

  let t = 2; // tiny lead-in so frame 0 isn't empty
  const events = queue.map((el) => {
    const ev = { el, t_in: t, motion: el.isAccent ? accentAt : t };
    t += el.isAccent ? 0 : delta;
    return ev;
  });

  assertNoConcurrencyAbove(events, 2);   // ≤2 entries overlapping
  assertMaxGap(events, 0.8 * fps);       // no >0.8s silence in Tier B/C
  assertBefore(events, settleBy);        // leave the final 30% for reading + ambient

  return { events, ambient: { cameraScale: [1.0, 1.06], idleAmp: 3, idlePeriod: 2.4 * fps } };
}
```

### 4.3 Anti-clutter rules

- One hero only, at 35–50% of frame area. Supporting cutouts are ≤ 18% each.
- At most one headline (L6) and one masthead (L7) per scene. The masthead is optional and capped at one every 3 scenes, so it doesn't become wallpaper.
- Headline reading hold: once stamped, the headline stays still (idle only) for ≥ 0.6s + 0.04s per character.
- Safe zones: headline and hero keep an 8% margin, cutouts avoid the subtitle band, and an occlusion check rejects layouts where any element covers more than 30% of the headline box.
- Vectors: max 8 per `radiating` (matches 00:39) and max 2 vector groups per scene.
- Pruning order when over budget: chrome → 3rd cutout → 2nd vector group → 2nd cutout. Hero and headline are never pruned.

### 4.4 Automated QA on rendered output

- Dead-frame detector: mean absolute frame difference per frame must stay above threshold ε. Any run longer than 6 frames below ε fails.
- Clutter score: count of salient regions (edge-density clusters) per frame ≤ 7.
- Legibility: headline contrast ≥ 4.5:1 against its local background, checked on the settled frame.
- Grounding OCR: same contamination test as 3.3, run on real episodes.

---

## Rollout Order

1. Shared `ScenePlan` zod schema, contamination blocklist, and grounding validator.
2. Remotion audit: remove all literal content and `defaultProps` (MH370 etc.), then add lint gates.
3. Build motion primitives and the scheduler, then implement archetypes one at a time (start with `GROWTH_CURVE` and `RADIATION`, which exercise the most primitives).
4. Rewrite the B3 prompt with synthetic few-shots plus archetype and theme rules.
5. Add QA detectors to the render pipeline.

If you share the repo paths for B3 and the Remotion components, I'll start with step 2. That's where the existing hardcode lives, and it's the quickest win.

---

## 2. PHẦN II: KIỂM TOÁN ĐỐI KHÁNG & PHÊ DUYỆT KHẾ ƯỚC (GPT-6-ASTRA)

# Astra Forensic Audit — “Học Sạch” Architectural Revision

## 1. Executive Verdict

**VERDICT: REVISE**

The proposal has a strong separation between semantic content, visual grammar, asset resolution, and rendering. However, it is **not yet compliant with the iron laws**, particularly:

1. **Rule 128 violation:** concrete tutorial-topic names appear in the proposed contamination mechanism and examples.
2. **Rule 136 exposure:** asset and fallback provenance are not fully isolated from visible render output.
3. **Schema incompleteness:** `VoxCompositeStageProps` and `ResolvedScenePlan` are referenced but not actually defined or verified.
4. **Grounding is weaker than claimed:** the validator checks numbers and dates, but not unsupported semantic claims, entities, captions, or generated asset content.
5. **Scheduler correctness is underspecified:** concurrency, event duration, reading holds, and accent overlap are not formally enforced.
6. **CPU-render risk:** procedural grain, per-frame path calculations, idle motion on every element, and OCR/QA assumptions may exceed the `≤0.08 s/frame` CPU budget.

The proposal is suitable as a **design direction**, but not as an enforceable production contract.

---

# 2. Adversarial Findings

## 2.1 Rule 128 — Zero Semantic Bias and Generic Contract

### Finding: contamination blocklist is itself hardcoded semantic content

The proposal requires a blocklist containing specific tutorial artifacts:

```text
Coca-Cola, Pemberton, 1886, MH370, ...
```

This directly conflicts with:

> Schema and prompt must be 100% generic and may not hardcode specific names or events.

Even if used only for testing, those strings become semantic knowledge embedded in the pipeline. They are also incomplete: a finite blocklist cannot prove topic independence.

### Required correction

Replace topic-specific contamination terms with a **content-independent provenance policy**:

- Every rendered token must have a provenance pointer.
- Every token must be traceable to:
  - narration input,
  - approved research notes,
  - or an explicitly permitted system label.
- Tutorial fixtures must live outside production code and production prompts.
- Synthetic test fixtures must be generated at test time or loaded from isolated test data.
- No tutorial names, dates, entities, hashes, or filenames may appear in:
  - schemas,
  - prompts,
  - Python,
  - default props,
  - test snapshots,
  - render components,
  - or production configuration.

A generic validator should reject **unprovenanced content**, not merely known contaminated content.

---

## 2.2 Rule 132 — Python Must Be a Pure Transmission Layer

The proposal does not explicitly violate Rule 132, but it does not enforce it.

The audit must verify that all `.py` files contain only:

- transport,
- serialization,
- validation invocation,
- process orchestration,
- retry handling,
- logging,
- and artifact movement.

They must not contain:

- business prompts,
- narrative templates,
- archetype descriptions,
- editorial wording,
- hardcoded examples,
- topic lists,
- or fallback story text.

### Required CI gate

Add a Python static scan that rejects:

- long natural-language string literals,
- prompt-like keys such as `system_prompt`, `story_prompt`, `editorial_prompt`,
- known narrative field values,
- embedded example paragraphs,
- and unapproved semantic constants.

The scanner itself must use generic rules, not a list of tutorial names.

---

## 2.3 Rule 136 — Zero Asset Leak

The proposal correctly states that Remotion should not fetch or guess assets. However, the contract does not prevent leakage of internal asset metadata.

Potential leaks include:

- asset filename rendered as an `alt` label,
- object key displayed during missing-asset handling,
- hash shown in an error badge,
- query text used as visible fallback text,
- URI or storage path placed in an accessibility label,
- debug overlay enabled in production,
- React error boundary exposing asset IDs,
- placeholder text such as `"missing image"` or `"fallback"`.

### Required correction

Separate asset identity from presentation:

```ts
type ResolvedAsset = {
  asset_id: string;       // internal, never rendered
  src: string;            // render-only source
  width: number;
  height: number;
  kind: "image" | "svg" | "video";
  provenance_id: string;  // internal audit metadata
};
```

Rendering components must receive only the fields required for visual composition. They must never render:

- `asset_id`,
- `provenance_id`,
- filename,
- hash,
- storage URI,
- search query,
- generation prompt,
- or failure reason.

Missing assets must cause a controlled validation failure or omission. They must not produce textual placeholders.

---

# 3. B3 Director Plan Audit

## 3.1 Positive aspects

The proposal correctly establishes:

- a finite archetype vocabulary,
- semantic anchors instead of pixel coordinates,
- explicit market and theme fields,
- a separation between asset queries and asset URLs,
- bounded cutouts and vector counts,
- an explicit grounding stage,
- and no direct asset fetching inside Remotion.

These are sound architectural choices.

## 3.2 Hidden schema risks

### A. `source_text` is not sufficient grounding evidence

The proposal says:

```ts
source_text: z.string()
```

But a string alone has no provenance, version, language, or scope.

Recommended structure:

```ts
const SourceRef = z.object({
  text: z.string().min(1),
  source_id: z.string().min(1),
  language: z.string().min(2),
  sentence_index: z.number().int().nonnegative(),
});
```

The source identifier is metadata and must never be rendered.

### B. `core_idea` can contain unsupported claims

The validator only specifies checks for numbers and dates. It does not validate:

- named entities,
- causal claims,
- geographic claims,
- sentiment,
- comparative claims,
- superlatives,
- or implied relationships.

For example, a narration stating “sales increased” could be transformed into a headline implying “market domination.” Numeric validation would not catch this.

The system needs either:

1. a structured claim ledger, or
2. a semantic entailment check against approved source material.

At minimum, every rendered text item should carry:

```ts
type TextProvenance = {
  source_ref: string;
  source_span?: [number, number];
  claim_ids?: string[];
};
```

### C. `editorial_headline` has inadequate language constraints

The proposal uses character-count rules in prose but does not encode them in the schema.

Missing controls:

- maximum rendered width,
- font fallback availability,
- line count,
- forbidden control characters,
- unsupported glyph detection,
- bidi safety,
- punctuation normalization,
- and locale-specific casing behavior.

Character count is not a reliable substitute for display width, especially for Vietnamese, Japanese, Korean, and mixed-script text.

The render validator should measure actual text using the selected font metrics.

### D. `query` fields are uncontrolled semantic injection surfaces

These fields are not rendered, but they influence the asset-generation stage:

```ts
visual_metaphor.query
supporting_cutouts[].query
```

They require:

- maximum length,
- no embedded URLs,
- no file paths,
- no executable syntax,
- no hidden instructions,
- no direct entity substitution unless grounded,
- and explicit provenance.

Use a structured query representation where practical:

```ts
const AssetIntent = z.object({
  subject: z.string().min(1),
  visual_style: z.string().min(1),
  restrictions: z.array(z.string()).max(8),
  provenance: z.string().min(1),
});
```

The asset stage may compile this into a provider-specific prompt. The provider prompt should not be passed to the renderer.

### E. `key_figure` is too permissive

```ts
key_figure: z.string().optional()
```

This permits arbitrary text, not merely a figure. It should be a typed value:

```ts
const Figure = z.object({
  value: z.union([z.number(), z.string().regex(/^[0-9][0-9.,/%+\- ]*$/)]),
  source_ref: z.string().min(1),
});
```

If dates or labels are required, they should be separate typed fields rather than one unconstrained string.

### F. `Anchor` is fragile and not fully generic

The regex is narrow:

```ts
/^... el:[a-z0-9_.\[\]]+ .../
```

Potential problems:

- no hyphens,
- no namespaced IDs,
- no stable UUID-like references,
- ambiguous array notation,
- no validation that referenced elements exist,
- no validation that `geo` anchors are meaningful for the selected archetype,
- no protection against anchor collisions.

Anchor validation must occur in two stages:

1. lexical validation,
2. referential validation against the scene’s declared element IDs.

---

# 4. `VoxCompositeStageProps` Verification

## 4.1 Verification status

A formal verification cannot be completed because the proposal does not provide the actual `VoxCompositeStageProps` definition.

The proposal only provides:

```tsx
<Scene plan={raw} />
```

and references:

```ts
ResolvedScenePlan.parse(raw)
```

Therefore, the following remain unverified:

- whether props have content defaults,
- whether asset IDs can leak,
- whether unknown keys are rejected,
- whether `ResolvedScenePlan` differs from `ScenePlan`,
- whether source metadata can reach visible components,
- whether frame rate and dimensions are validated,
- whether timing values are bounded,
- whether captions have provenance,
- and whether omission semantics are enforced.

## 4.2 Required minimum contract

A compliant stage contract should resemble:

```ts
const VoxCompositeStageProps = z.object({
  schema_version: z.string().regex(/^\d+\.\d+\.\d+$/),
  scene: ResolvedScenePlan,
  render: z.object({
    fps: z.number().int().positive(),
    width: z.number().int().positive(),
    height: z.number().int().positive(),
    frame_start: z.number().int().nonnegative(),
    frame_end: z.number().int().positive(),
  }),
  policy: z.object({
    allow_debug_overlay: z.literal(false),
    allow_visible_asset_metadata: z.literal(false),
  }),
}).strict();
```

The actual implementation may use a different shape, but it must satisfy these invariants:

### Content invariants

- No visible text defaults.
- No default image, number, title, entity, date, or caption.
- Empty optional collections produce omission, not substitution.
- All visible text has provenance.
- All rendered asset sources are resolved upstream.

### Security invariants

- Strict parsing rejects unknown keys.
- Internal metadata is not passed to visual leaf components.
- No URL or filesystem fallback is generated in Remotion.
- No debug metadata is visible in production.

### Timing invariants

- Duration, frame range, and FPS are consistent.
- All event times are within the scene range.
- No negative or NaN timing values.
- All animation parameters are finite and bounded.

### Internationalization invariants

- Locale is explicit.
- Font availability is preflighted.
- Glyph fallback is detected before render.
- Width and contrast are evaluated using actual rendered text.

---

# 5. Scheduler and Motion Audit

## 5.1 Event overlap is not actually proven

The proposal says:

```ts
assertNoConcurrencyAbove(events, 2)
```

But each event has only `t_in`; no event duration is defined. Two entries can have overlapping motion intervals even if their start times are separated.

Every event requires:

```ts
{
  id,
  start_frame,
  end_frame,
  layer,
  priority,
  motion,
  accent
}
```

Concurrency must be calculated over `[start_frame, end_frame]`, not only at event start.

## 5.2 Accent scheduling can collide

This code assigns an accent to `accentAt`:

```ts
motion: el.isAccent ? accentAt : t
```

Multiple elements marked `isAccent` receive the same time. There is no assertion that only one accent exists.

Required rule:

```ts
count(accent_events) <= 1
```

or explicit accent grouping with a bounded group duration.

## 5.3 The scheduler does not ensure the reading hold

The proposal specifies:

> headline stays still for at least 0.6 seconds plus 0.04 seconds per character

But the scheduler does not reserve that hold window. Later entries, camera motion, or accents can overlap the headline.

The scheduler must reserve a protected interval:

```ts
headline_settle_frame + required_reading_frames
```

and reject any event that materially occludes or distracts during that interval.

## 5.4 Density law is not consistently enforceable

The proposal contains several overlapping limits:

- 4–6 motions per scene,
- at most 6 elements,
- at most 2 concurrent entries,
- 3–5 entry events,
- one accent,
- no gap over 0.8 seconds.

These constraints can conflict for short scenes. For example, a two-second scene may not support six meaningful entries while also preserving a reading hold and a clean payoff.

The scheduler needs a deterministic priority policy:

1. narration-critical element,
2. hero,
3. headline,
4. one supporting element,
5. one vector/accent,
6. optional chrome.

The system should permit a lower density for short scenes rather than force artificial motion.

---

# 6. CPU Render Health

## 6.1 Risk areas

The following features may violate the `≤0.08 s/frame` CPU target:

- per-frame procedural grain generation,
- per-frame SVG path construction,
- repeated text measurement,
- idle transforms recalculated for every element,
- multiple SVG vector strokes,
- edge-density analysis during render,
- dynamic blur, shadows, or filters,
- OCR integrated into the render loop,
- React tree reconstruction on every frame,
- image decoding during composition rendering.

The proposal does not provide a benchmark strategy.

## 6.2 Required implementation policy

### Precompute

Precompute once per scene:

- path geometry,
- dash lengths,
- event timeline,
- anchor resolution,
- layout boxes,
- text metrics,
- random phases,
- and asset dimensions.

### Use compositor-friendly animation

Prefer:

- `transform`,
- `opacity`,
- static SVG geometry,
- CSS animation-compatible values,
- and precomputed keyframes.

Avoid per-frame:

- pixel generation,
- layout measurement,
- path parsing,
- asset lookup,
- font discovery,
- and large object allocation.

### Grain policy

Grain must use one of:

- a pre-generated static texture,
- a cached deterministic texture sequence,
- or a low-cost opacity modulation over a static overlay.

It must not generate random pixels per frame.

### Benchmark gate

CI should render representative scenes on the target VPS and record:

- mean frame time,
- p95 frame time,
- peak memory,
- total render duration,
- and frame time by archetype.

Required gate:

```text
p95 frame time <= 0.08 s
no sustained run above 0.12 s/frame
no unbounded memory growth
```

The exact threshold should be measured with production resolution and actual fonts/assets.

---

# 7. QA Design Issues

## 7.1 Dead-frame detector is too naive

Mean absolute frame difference can fail in both directions:

- legitimate reading holds may be flagged as dead,
- grain or camera movement may pass while the scene is semantically static.

Use separate signals:

- global motion,
- semantic element motion,
- camera motion,
- and intended hold intervals.

A protected reading hold should be exempt from the dead-frame rule.

## 7.2 OCR contamination test is unreliable as specified

This assertion is unsafe:

> every detected OCR word exists in the props

OCR produces:

- false characters,
- merged words,
- missing diacritics,
- hallucinated glyphs from texture,
- and errors on rotated labels.

A robust version should:

- normalize Unicode,
- compare token spans with tolerance,
- ignore low-confidence OCR,
- exclude non-texture regions,
- maintain a whitelist of allowed system symbols,
- and map each text-bearing layer to its expected provenance.

## 7.3 Clutter score needs calibration

“Salient regions ≤ 7” is not portable across:

- resolutions,
- locales,
- high-contrast themes,
- dense chart scenes,
- and different asset styles.

The score should be calibrated against labeled fixtures and evaluated per archetype. It should be a warning initially, then a hard gate once stable.

---

# 8. Final “Học Sạch” Standard Protocol

## A. Contract and schema

- [ ] One versioned canonical schema exists.
- [ ] `ScenePlan` and `ResolvedScenePlan` have explicit, tested differences.
- [ ] `VoxCompositeStageProps` is defined and parsed with strict validation.
- [ ] No content-bearing defaults exist anywhere.
- [ ] Optional content omits cleanly.
- [ ] Unknown keys are rejected.
- [ ] All numeric fields are finite and bounded.
- [ ] All timing fields use one declared unit.
- [ ] All anchors resolve to declared elements.
- [ ] All visible text has provenance.
- [ ] All figures and dates are typed, not free-form where avoidable.

## B. Zero semantic bias

- [ ] No production schema contains tutorial-specific names, dates, entities, or events.
- [ ] No production prompt contains tutorial-specific examples.
- [ ] No Python file contains narrative or business prompt text.
- [ ] Test fixtures are isolated from production configuration.
- [ ] Grounding checks reject unsupported content by provenance, not by a topic-specific blacklist.
- [ ] Core ideas, headlines, captions, and asset intents are traceable to approved source material.

## C. Asset isolation

- [ ] Asset resolution occurs upstream.
- [ ] Remotion never searches, fetches, or guesses assets.
- [ ] Missing assets cause omission or controlled failure.
- [ ] Filenames, hashes, paths, queries, and provider metadata are never rendered.
- [ ] Asset IDs are internal-only.
- [ ] Production debug overlays are disabled and schema-enforced.

## D. Motion and layout

- [ ] Event intervals, not only start times, are validated.
- [ ] Accent count is bounded.
- [ ] Concurrency is measured over time intervals.
- [ ] Headline reading holds are reserved.
- [ ] Occlusion is checked after final layout.
- [ ] Short scenes may use reduced density.
- [ ] Camera and idle motion do not compromise legibility.
- [ ] All animation values are deterministic and finite.

## E. Internationalization

- [ ] Locale is explicit.
- [ ] Font availability is preflighted.
- [ ] Actual text width is measured with the selected font.
- [ ] Diacritics and complex scripts are tested.
- [ ] Unsupported glyphs fail validation before rendering.
- [ ] Headline limits are width-based, not only character-based.

## F. CPU and render health

- [ ] Geometry and timelines are precomputed.
- [ ] Grain is cached or static.
- [ ] No per-frame asset resolution or text measurement occurs.
- [ ] No unbounded procedural loops exist.
- [ ] p95 frame time is ≤ 0.08 seconds on the target CPU.
- [ ] Memory usage remains stable.
- [ ] Each archetype has a benchmark fixture.

## G. QA and release gates

- [ ] Synthetic-property fuzz tests pass.
- [ ] OCR checks tolerate normal recognition errors.
- [ ] Provenance checks cover every visible text layer.
- [ ] Asset-leak scans pass.
- [ ] Literal-content lint passes.
- [ ] No default visible content exists.
- [ ] Snapshot tests use isolated synthetic fixtures.
- [ ] Rendered output is inspected at frame 0, entry, accent, settle, and final frames.
- [ ] Release artifacts contain no debug metadata or internal identifiers.

---

# 9. Final Determination

## VERDICT: REVISE

The proposal demonstrates a credible visual grammar and a good high-level separation of concerns. It is **not yet an approved VF production architecture** because the enforcement layer is incomplete.

The blocking issues are:

1. tutorial-specific contamination strings violate the generic-contract rule;
2. `VoxCompositeStageProps` is not supplied and therefore cannot be verified;
3. provenance-based grounding is incomplete;
4. asset metadata leakage is not formally prevented;
5. scheduler invariants are asserted but not mathematically defined;
6. CPU performance controls are descriptive rather than benchmark-enforced.

After removing all semantic fixtures from production code, defining the complete strict props contract, adding provenance-aware validation, isolating asset metadata, and passing the CPU benchmark gates, the proposal may be resubmitted for **PASS**.

---

## 3. PHẦN III: QUY TẮC BẤT BIẾN KẾT LUẬN (CONVERGENCE AGREEMENT)

1. **Khử nhiễm 100% Hardcode trong Remotion (`VoxCompositeStage.tsx`):**
   - Loại bỏ toàn bộ các chuỗi text cố định mang tính topic bias (MH370, Coca-Cola, năm 1886).
   - Component chuyển sang cơ chế **Conditional Dynamic Rendering**: Chỉ render những gì được truyền vào từ Props.
2. **Ngữ pháp suy luận động trong B3 Director Plan:**
   - Mỗi câu kịch bản B2 được phân tích AST thành: `core_idea` -> `editorial_headline` (1-4 từ) -> `visual_metaphor` -> `theme` -> `supporting_cutouts` -> `connecting_vectors`.
   - Áp dụng phổ quát cho mọi thị trường (EN, VN, JP, KR) và mọi đề tài (tài chính, địa chính trị, công nghệ, lịch sử).
3. **Pure Transmission Engine (Rule 132):**
   - Code Python chỉ đóng vai trò truyền dẫn cấu trúc dữ liệu JSON sạch. Không nhúng text kịch bản cụ thể vào file mã nguồn.
