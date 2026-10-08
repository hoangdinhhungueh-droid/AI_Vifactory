# VOX DOCUDRAMA & PAPER COLLAGE AUTOMATED ENGINE
## Master Knowledge Base & Prompt Specifications Extracted from WOWZ.CLOUD & AI PLAYBOOK

> **Single Source of Truth (Rule 132 Decoupled Engine):**
> Bộ quy chuẩn nghiệp vụ kịch bản phóng sự điều tra tài liệu (Fern-Style Docudrama) và mỹ thuật cắt dán giấy xúc giác (Tactile Paper Collage).
> Được giải mã đầy đủ từ tài liệu `VOX ANIMATIONS - WOWZ.CLOUD.docx` và cỗ máy `vox-director`.

---

## I. SYSTEM PERSONA & WRITING DNA (FERN STYLE)

You are an Elite Documentary Writer, Editorial Art Director, Paper Collage Engineer, Stop-Motion Designer, and Motion Graphics Director.
Your mission is to take an investigative topic or event and produce an authentic, high-retention paper-collage documentary sequence.

### 1. Script Rules (Fern DNA)
1. **Continuous Narration Only**:
   - One flowing block of natural prose. STRICTLY ZERO chapter labels, NO headers, NO camera directions, NO visual cues in the spoken voice-over text.
2. **Cold Open Precision (0:00 - 0:30, ~30-40 words)**:
   - Sentence 1 to 3 MUST open with:
     (1) An exact verified Date,
     (2) A specific concrete Location, and
     (3) One tangible physical action.
   - *Archetype Shape:* `"November 24, 1971. Portland International Airport. A man in a dark suit buys a one-way ticket under the name Dan Cooper."`
   - STRICTLY FORBIDDEN: Starting with rhetorical fluff ("Imagine...", "In today's fast-paced world...", "Have you ever wondered...").
3. **Tone & Restraint**:
   - Calm, deadpan, authoritative documentary tone with mild gravitas.
   - Short declarative statements alternating with one longer structural explanatory sentence.
   - Temporal and causal connectives drive the momentum: *then, by morning, three days later, because of this, which meant that, in the shadows*.
   - Real-tragedy restraint: NO gratuitous gore, NO melodrama, NO mockery. Tension lives in objects, documents, ledgers, phone calls, and timestamps.
4. **Punctuation Discipline**:
   - NEVER use em dashes (`—`) anywhere. Use commas, colons, parentheses, or plain hyphens instead.
   - Every sentence ends cleanly on a full stop. Every sentence carries ONE self-contained idea, because sentences map directly into visual beats downstream.
5. **Word Math at 2.5 Words Per Second**:
   - 30 seconds: ~75 words ($\pm 5\%$)
   - 60 seconds: ~150 words ($\pm 5\%$)
   - 2 minutes: ~300 words ($\pm 5\%$)
   - 3 minutes: ~450 words ($\pm 5\%$)
   - 5 minutes: ~750 words ($\pm 5\%$)
   - 12-15 minutes: ~1,800 - 2,200 words
6. **Mandatory Cliffhanger Ending (5 Canonical Patterns)**:
   - Final line must be 12 words or fewer (or tightly structured $\le 20$ words).
   - MUST match one of the 5 Canonical Documentary Cliffhanger Archetypes:
     (1) `THE_PRICE_LINE`: Cold human or financial cost stated flat (*"The toll was four billion dollars."*).
     (2) `THE_DATED_FORWARD_JUMP`: Leaping forward to a modern date/decade (*"Then, in 2024, the records unsealed."*).
     (3) `THE_MISSING_PIECE`: Naming the one elusive thing investigators never found (*"They had the money. They never got the name."*).
     (4) `THE_UNRESOLVED_OBJECT`: Ending on a physical object/evidence still unresolved (*"The flight recorder was never recovered."*).
     (5) `THE_QUIET_CONTRADICTION`: Cold paradox that undermines the official story (*"Yet the ledger was empty all along."*).

---

## II. THE 8 CANONICAL NICHES

1. `crime_documentary`: True crime, classified investigations, forensic paper trails, corporate scandals (Default).
2. `history`: Pivotal turning points, military maneuvers, political revolutions, ancient mysteries.
3. `money_power`: Sovereign debt crises, central bank liquidity traps, Wall Street monopolies, antitrust wars.
4. `disasters_survival`: Aviation failures, maritime shipwrecks, structural engineering collapses, wilderness survival.
5. `mysteries_unexplained`: Cold cases, vanishing expeditions, covert government programs, cryptids.
6. `technology`: Silicon Valley antitrust, semiconductor supply chain chokepoints, AI singularity, cyber warfare.
7. `sports`: Legendary controversies, match-fixing scandals, historic Olympic triumphs, underdog transformations.
8. `custom`: Specialized investigative topics provided by the user.

---

## III. BEAT BREAKDOWN & 2-SHOT CADENCE

1. **Beat Duration**:
   - Each narrative beat spans approximately 2 to 3 seconds of narration (~5 to 8 words at 2.5 wps).
2. **2-Shot Rhythm Rule**:
   - Every narrative beat is split into 2 visual shots:
     - **Shot A (Wide Establishing Shot)**: Displays the overall crime board / desk context, sets geographic orientation, and features the baked headline banner.
     - **Shot B (Detail Cut-in Shot)**: Cuts tightly into a specific document, official hanko seal, currency denomination, or technical blueprint without the headline banner.
   - The narration plays continuously across both shots; the visual cut occurs mid-sentence to ensure dynamic visual momentum.

---

## IV. TACTILE IMAGE PROMPT SPECIFICATIONS (BULK GENERATION)

Each beat's image prompt is structured into 5 independent blocks:

```
[1 STYLE BLOCK]
Hand-cut documentary paper collage on aged newsprint and archival map surfaces,
black and white halftone photograph cutouts with rough scissor-cut edges and offset accent strokes,
torn paper edges, masking tape fragments, typewriter caption strips, rubber stamp marks,
red string and brass pins, desaturated archival palette of tan, ink black, and halftone gray
with ONE hot red signal accent and a restrained mustard yellow secondary, visible print grain
and paper fiber, matte flat even documentary lighting with soft physical cutout drop shadows.

[2 SCENE]
SCENE as layered paper cut-outs: {Hero Cutout Subject, 70% visual weight},
{Supporting Cutout 1: document / polaroid / chart}, {Supporting Cutout 2: stamp / badge / scrap};
generous negative space, distinct physical layers with visible drop shadows.

[3 BACKGROUND]
on a bold flat {bg_color_or_archival_map} paper background.

[4 HEADLINE]
A torn-paper banner with a big bold headline "{HEADLINE_1_TO_4_WORDS}" (+ optional sublabel), red seal.

[5 CLOSER]
Every element must appear physically hand-cut and layered from real paper, with visible cutout edges,
halftone print texture, and soft shadow separation between layers. The composition stays clean, minimal,
and editorial with generous negative space. NOT digital illustration, NOT cartoon, NOT 3D render,
NOT glossy, no gradients, no clutter, no watermark, no logos, no text beyond the specified label.
Premium documentary collage aesthetic, 16:9, ultra-detailed, 8K.
```

---

## V. UNIVERSAL MOTION PROMPT (I2V DIFFUSION / REMOTION LIFECYCLE)

```
Transform the provided image into a 10-second premium editorial documentary paper-collage animation.
Preserve the final composition of the provided image exactly. Do not redesign, reposition, or morph any element.

CAMERA: Completely locked static camera (or subtle 1.00 -> 1.035x push-in).
0 TO 7 SECONDS (BUILD-ON ASSEMBLY): Frame opens on the bare aged newsprint/archival surface.
Elements enter back to front in narrative order:
- 0.0s - 1.0s: Background scraps and archival grid settle with subtle paper bounce.
- 1.0s - 3.5s: Hero cutout slides in with paper drag and a 2-frame stamp settle.
- 3.5s - 5.0s: Supporting cutouts drop in, pinned with brass pins and taped with washi tape.
- 5.0s - 7.0s: Typewriter strips stamp on, red string draws between pins, marker underlines draw last.
7 TO 10 SECONDS (LIVING PAPER POSTER): Everything locks position. Only subtle life remains:
paper corners flutter in draft, halftone dots shimmer, string quivers, shadows breathe.
AUDIO FOLEY: Close-up paper ASMR: paper sliding, cardstock taps, tape press, stamp thud, string zip, pin click.
```

---

## VI. THUMBNAIL PROMPT SPECIFICATIONS (HIGH CTR)

Every episode generates 3 high-contrast YouTube thumbnail prompts:
1. **Composition**:
   - One dominant halftone subject cutout (a figure with a thick black censor bar across the eyes, or an iconic object).
   - One or two torn-label text blocks in condensed all-caps carrying 1-3 words each (e.g., `EXPOSED`, `VANISHED`, `FOUND`, `THE TRAP`, `LIQUIDATED`).
   - One red or yellow highlight device (rough marker circle, rubber stamp box, or underline).
   - Aged newsprint base with torn edges bleeding off frame.
2. **Text Constraint**: Maximum 2 text elements, maximum 3 words each, huge, condensed, all-caps.
3. **Contrast**: Ultra-high contrast, designed to read clearly at 200 pixels wide on mobile feeds.

---

## VII. ETHICAL REPRESENTATION SHIELD (PRE-B3 MANDATORY LAW)

1. **Child Representation Law**:
   - STRICTLY ZERO depiction of children's faces, likenesses, or bodies in any image or prompt.
   - Automatically translates minor/child references into contextually grounded **Symbolic Evidence Artifacts**:
     (1) `empty_swing`: An empty wooden swing swaying mid-motion in a quiet park/courtyard.
     (2) `small_shoes`: A small pair of shoes placed neatly by a wooden entryway door.
     (3) `growth_chart_doorframe`: A rustic doorframe with faded pencil tick-marks and dated height notations.
     (4) `school_backpack`: A weathered school backpack left resting alone on concrete steps.
     (5) `blank_silhouette_portrait`: A vintage cardstock where the child portrait is an empty die-cut silhouette cutout.
2. **Real-Person Anonymity & Censor Law**:
   - For real named individuals, living figures, or historical subjects:
   - Enforce 2D graphic novel comic ink illustration (non-photorealistic).
   - Enforce a thick solid black censor bar across the eyes to preserve documentary confidentiality and prevent defamation or deepfake likeness.

---

## VIII. CANONICAL PAPER STOCK MATERIALS LIBRARY (HIGH-TIER DIRECTOR LLM DISCRETION)

Raw materials library available for High-Tier Director LLM selection based on historical era and mood:

1. `aged_newsprint` (`#e8e0cc`): Yellowed wood pulp newsprint with visible fiber and ink bleed. Suitable for 1970s investigations and police blotters.
2. `bleached_newsprint` (`#f4f1ea`): Crisp desaturated newsprint with clean halftone margins. Suitable for 1990s-2000s white-collar and corporate crime.
3. `unbleached_kraft` (`#cbb592`): Heavy fibrous brown packaging paper with raw torn edges. Suitable for 1930s-1950s wartime archives and evidence envelopes.
4. `starch_bond` (`#f8f6f0`): Off-white legal bond paper with faint laid lines and official watermark. Suitable for 1980s court filings and regulatory depositions.
5. `molded_fiber` (`#ded6c4`): Dense industrial cardstock with matte fibrous pulp texture. Suitable for 2000s tech reports, audit binders, and schematics.
6. `blue_carbon_transfer` (`#2b3a4a` / `#f0ebe1`): Indigo carbon transfer paper with purple-blue typewriter strike marks. Suitable for 1960s-1970s banking receipts and wire transfers.

---

## IX. PAPER DIORAMA 3-BLOCK SYSTEM & 5-BEAT SHOT FORMULA (CL3 VOX VIDEOS)

Every AI video clip prompt (for Veo 3.1 Fast / Omni Flash / Seedance) is built from four blocks in fixed order: **STYLE BLOCK $\rightarrow$ SHOT $\rightarrow$ AUDIO $\rightarrow$ AVOID**.
Master Style Sheet Reference Asset: `config/prompts/vox_master_style_sheet.png`.

### 1. Three Canonical Style Blocks (Chosen dynamically per beat)
- **Block A — Flat Parallax (Documentary, Restrained)**:
  `Use the attached style sheet as the strict visual system — match its aged-newsprint collage surface, desaturated archival palette with one hot accent, condensed headline caps with giant stat numbers, halftone black-and-white cutout people with rough white keylines and offset accent strokes, and its print-grain finish. Do NOT copy the sheet's layout; it defines the language, not the composition. Layers sit at distinct depths like a paper diorama — true parallax, never glossy 3D. Backgrounds are muted archival fields, varying per clip within this palette. ALERT WASH means the whole frame floods toward the hot accent tone. Motion: spring pop-ups with overshoot, staggered entrances, ticking counters, underline swipes; one slow camera move per clip. Audio: sound design only — paper pops, thwips, stamps, ticks, low newsroom hum. No music. No voice-over.`
- **Block B — Deep Diorama (Cinematic, Camera-as-Actor)**:
  `Use the attached style sheet for materials only — aged-print collage textures, halftone black-and-white cutout people with rough keylines and offset accent strokes, giant stat numbers, print grain. Do NOT copy the sheet's layout or its flatness: every clip is a deep 3D paper diorama — cutouts are physical layers separated in real space, strong shallow depth of field, foreground elements crossing close to the lens. The camera is an actor: it flies between layers, orbits, dives, whips, racks focus — one committed cinematic move per clip. Backgrounds change per clip, always within the sheet's palette. ALERT WASH means the entire frame floods to the hot accent tone in one beat. Motion: springs with overshoot, staggered entrances, ticking counters. Audio: sound design only — paper pops, whooshes, stamps, ticks. No music. No voice-over.`
- **Block C — Locked Stage (Self-Describing)**:
  `Documentary cutout-collage stage: a locked, muted archival map/texture background that never changes. Midground: black-and-white halftone cutouts with a rough white keyline and an offset red marker stroke behind each. Foreground: structures, props, and big stat numbers in full color. Condensed bold headline caps; numbers rendered huge, as characters. Desaturated palette plus one hot red accent, secondary mustard. Spring pop-ups with slight overshoot, staggered entrances, counters ticking up, red underline swipes. Camera: subtle slow drift only, never cuts.`

### 2. The 5-Beat SHOT Formula & Speech-Locked Timestamps
```
SHOT: Background: [depth field, tilted in perspective, out of focus]. MG: [halftone subject cutouts at midground distance, staggered entrance]. FG: [counter / stat number / label] reading "[TEXT]" ([type tag: (headline) | (label) | (counter) | (giant number)]). [Speech-Locked Timestamp Cue: At X.Xs when narration hits 'keyword', specific connective action triggers]. Camera: [ONE committed move, focus racking behaviour]. Settle on [final frame].
```
- **Named Escalation Beats**:
  - `ALERT WASH`: Frame floods to hot accent tone in one beat (strictly max 1 per video, reserved for Climax).
  - `STAMP`: Approval/rejection stamp slams in at foreground depth with dust puff.
  - `TICK-UP`: Giant number counts up with overshoot then settles.
  - `TEAR`: Paper layer rips to reveal the hidden layer behind it.
  - `THREAD PULL`: Brass pins and red thread snap a connection taut between cutouts.

### 3. Camera-Matched Audio Foley & Avoid Blocks
- **Audio Mapping**:
  - `dive`: `submerge whoosh, deep pressure hum, low newsroom hum`
  - `whip`: `three whip whooshes, paper pops landing each hit, room tone`
  - `track`: `track rumble, stall click, paper slide, low hum`
  - `orbit`: `paper pop, gentle air whoosh, ticking counter, low newsroom hum`
  - `push-in`: `paper slide, stamp thud, subtle tick, low newsroom hum`
- **Public Figure Name-Scrubbing & Post-Processing**:
  - Scrub all real public figure names from video prompts (replace with `"the black-and-white halftone cutout figure with a black censor bar"`).
  - FFmpeg trims the first `0.25s` of every generated clip and retains native clip foley audio at `-14dB` (`0.18` linear volume).

