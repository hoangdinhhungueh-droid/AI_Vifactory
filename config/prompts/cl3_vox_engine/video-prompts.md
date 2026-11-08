# Paper Diorama Prompt System

A repeatable system for writing AI video clip prompts in the aged-newsprint cutout-collage style. Every prompt is built from four blocks in fixed order: **STYLE BLOCK → SHOT → AUDIO → AVOID**.

---

## 1. Choose a Style Block

Pick whichever serves the shot. The style block is a fixed preamble — use it verbatim once chosen, but the choice is per clip, not per video. A restrained data beat wants Flat Parallax; a big reveal wants Deep Diorama. Choose for the moment.

### A. Flat Parallax (documentary, restrained)

> Use the attached style sheet as the strict visual system — match its aged-newsprint collage surface on cream archival paper (#F4F1EA), cool backlit light table (#F7F9FB) with whiteboard erased ghost strokes (7% opacity), desaturated archival palette with one hot crimson accent, Swiss extreme scale contrast (condensed headline typography with giant stat numbers 30-35% mass vs precision IBM Plex Mono source tags on 6x12 chips), halftone black-and-white cutout people with rough white keylines and misregistration ink shadows (+8px offset pop), Ben-Day halftone density fields, pitted rubber stamps, and its print-grain finish. Do NOT copy the sheet's layout; it defines the language, not the composition. Layers sit at distinct depths like a paper diorama — true parallax with 3-plane depth separation (foreground tool, anchored midground document, receding background plane), never glossy 3D. Backgrounds are muted archival fields, varying per clip within this palette. Motion: snappy cubic-bezier(.7, 0, .2, 1) ease-in with mechanical back-overshoot and settle within 0.2s - 0.3s, staggered entrances, dimension line rides with arrowhead taps and mechanical counter ticks; stamp slams drop in 0.09s from 2.6x to 1x with damped micro-bounce and 1-frame camera shake; one slow camera move per clip. Objects lock into dead-stop hold with 12fps paper grain flutter and micro shadow breathing <= 2px conforming to readcheck formula max(1.8s, chars/4.5 + 1.5s, VO + 0.6s). Audio: sound design only — tactile paper pops, thwips, soft ink squelch stamps, ticks, and ducked silence before slams. No music. No voice-over. Keep bottom 20% of the surface completely empty, plain bare cream paper only. No text, no objects, no cards in the bottom fifth.

### B. Deep Diorama (cinematic, camera-as-actor)

> Use the attached style sheet for materials only — aged-print collage textures on aged archival cream newsprint (#F4F1EA), tan kraft cardstock (#C9BB9C), and cool backlit light table (#F7F9FB) with faint erased whiteboard ghost strokes (7% opacity), halftone black-and-white cutout people with rough keylines and misregistration ink shadows (+8px offset pop in crimson red or mustard gold), Ben-Day halftone density fields, pitted rubber stamps, Swiss extreme scale contrast (giant stat numbers 30-35% mass vs precision IBM Plex Mono source tags on 6x12 chips), acrylic loupe portals with pincushion barrel distortion and edge chromatic aberration, and authentic print grain. Do NOT copy the sheet's layout or its flatness: every clip is a deep 3D paper diorama — cutouts are physical layers separated in real space, strong shallow depth of field, foreground elements crossing close to the lens. The camera is an actor with disciplined kinematics: smooth 24/30fps tracking along one committed vector, decelerating smoothly to a steady resting hold. Multi-plane stereoscopic depth: 1.4x fast foreground tool travel, 1.0x tack-sharp focal plane, 0.3x slow background drift. Motion: snappy cubic-bezier(.7, 0, .2, 1) ease-in with mechanical back-overshoot and settle within 0.2s-0.3s; stamp slams drop in 0.09s from 2.6x to 1x with damped micro-bounce and 1-frame camera shake; dimension line rides with arrowhead taps and mechanical counter ticks. Dual-rate motion: smooth 24/30fps camera, while paper grain, drop shadows, and line-boil breathe at 12fps (on twos). Hold duration conforms to readcheck formula max(1.8s, chars/4.5 + 1.5s, VO + 0.6s). Audio: sound design only — tactile paper pops, whooshes, soft ink squelch stamps, ticks, and ducked silence before slams. No music. No voice-over. Keep bottom 20% of the surface completely empty, plain bare cream paper only. No text, no objects, no cards in the bottom fifth.

### C. Locked Stage (no style sheet attached — self-describing)

> Documentary cutout-collage stage with Opuscar core boxes (archive-lighttable, swiss-motion, halftone-dossier): a locked, muted archival background (#F4F1EA / cool backlit light table #F7F9FB with faint 7% ghost strokes). Midground: black-and-white halftone cutouts (60lpi) with rough white keylines, misregistration ink shadows (+8px offset), and pitted rubber stamps. Foreground: structures, props, and Swiss extreme scale contrast (giant stat numbers 30-35% mass vs precision IBM Plex Mono source tags on 6x12 chips). Desaturated palette plus one hot red accent, secondary mustard gold. Snappy cubic-bezier(.7, 0, .2, 1) ease-in with mechanical back-overshoot <= 0.3s, stamp slam drop in 0.09s, dimension line rides with arrowhead taps and mechanical counter ticks. Locked into 12fps living hold on twos adhering to readcheck formula. Camera: subtle slow drift only, never cuts, ending with a precise settle. Audio: sound design only with ducked silence before slams. No music, no narration.

Swap the background clause when the shot needs it, e.g. *"a flat city-skyline silhouette cutout against a muted dusk-toned archival sky, print-grain texture, locked for this shot."*

---

## 2. Write the SHOT

One sentence-block. Always contains these five beats, in roughly this order:

| Beat | Function | Examples from the corpus |
|---|---|---|
| **Background** | Sets the depth field | "a faded world map tilted in perspective, far out of focus" · "stacked newspaper front pages receding in deep perspective" · "a collage field of ledger sheets and ticker strips at depth" |
| **MG** | The subject cutouts | "cutouts of Sam Altman, Elon Musk and Donald Trump work one large hand-pump" · "an iceberg cutout floats with only its tip above a paper waterline" |
| **FG** | The data element | "a counter ticks up to `$1.2T` (giant number)" · "a red stat number reads `POWER DEMAND ↑`" |
| **Camera** | ONE committed move | dive through · orbit quarter turn · whip ×3 · lateral track · climb alongside · push-in · ride the loop like a rail |
| **Settle** | Where the clip ends | "Settle deep, looking up at the tip far above." · "Settle on the sliver in macro." · "Settle mid-orbit." |

### Rules

- **One camera move per clip.** Never two. Never a cut.
- **Always end on "Settle on…"** — this is non-negotiable and tells the model where to park the final frame.
- **Tag every text element** with its type in parens: `(headline)`, `(label)`, `(counter)`, `(giant number)`.
- **Stagger everything.** Nothing enters simultaneously.
- **Logos must be "attached… flat, unmodified"** — never described, never invented.
- **Depth is the story.** State what crosses the lens, what blurs, what racks into focus.

### Camera move library

`push-in` · `slow drift lateral` · `dive through a layer` · `orbit quarter turn` · `whip ×2–3, each landing hard` · `fast lateral track then hard stop with overshoot` · `climb alongside a rising element` · `fly low between columns` · `ride a path like a rail` · `macro slide along an object, rack focus tip→subject`

### Escalation devices

- **ALERT WASH** — frame floods to hot accent. Save it for the single biggest beat.
- **Freeze before contact** — "everything freezes one millimeter before contact."
- **Counter slam** — number flies at the lens and snaps into razor focus while everything blurs.
- **Accelerating loop** — same geometry, each lap faster.

---

## 3. Write the AUDIO

Format: `AUDIO: [2–3 sounds, comma separated] — sound design only, no music, no narration.`

Sound must mirror the camera move:

| Move | Sound |
|---|---|
| Dive | submerge whoosh, deep pressure hum |
| Whips | three whip whooshes, pops landing each hit |
| Track + stall | track rumble, stall click, drain hiss |
| Contact / wash | rising air riser, deep sub thud on contact |
| Loop | accelerating ticks, whoosh per lap |
| Tension hold | rubber creak, room tone falling to near silence |

Bed options: `low newsroom hum` · `low hum` · `room tone`.

---

## 4. Write the AVOID

Use the block matching your style choice. Verbatim.

### For Flat Parallax (A) and Locked Stage (C)

> AVOID: no glossy CG 3D, no lens flares, no camera cuts within the clip, no full-color midground portraits (people stay halftone black-and-white), no warped or gibberish text, no invented logos, no watermarks, no simultaneous entrances, no music, no soundtrack, no voice-over, no narration, no lyrics

### For Deep Diorama (B)

> AVOID: no flat single-plane composition, no static locked-off camera, no glossy plastic CG (depth stays papercraft), no full-color midground portraits (people stay halftone black-and-white), no warped or gibberish text, no invented logos, no watermarks, no music, no soundtrack, no voice-over, no narration, no lyrics

Add `no UI or glass elements` when the shot involves screens, dashboards, or tech.

---

## 5. Fill-in Template

```
[STYLE BLOCK A / B / C — verbatim]
SHOT:
Background: [depth field, often out of focus].
MG: [subject cutouts, staggered entrance].
FG: [counter / stat number / label] reading "[TEXT]" ([type tag]).
[Camera: ONE committed move, describing what crosses the lens and what racks focus].
Settle [final frame].
AUDIO: [sound 1], [sound 2], [sound 3] — sound design only, no music, no narration.
AVOID: [matching AVOID block]
```

---

## 6. Sequencing a Video

- **Choose the style block per clip.** Match it to the beat: Flat Parallax for restrained data moments, Deep Diorama for reveals and escalation, Locked Stage when no sheet is attached. The materials stay constant across blocks, so the world holds even when the depth treatment shifts.
- **Use the shift as a tool.** Dropping from Deep Diorama into Flat Parallax reads as a breath; jumping the other way reads as a lift.
- **Vary the background per clip** — always inside the palette.
- **Vary the camera move per clip** — never two dives in a row.
- **Chain clips** by reusing geometry: build the loop, then ride the loop, then blow past it. Reference it explicitly: *"The triangle loop from the previous clip runs faster each lap."*
- **Reserve ALERT WASH** for one clip per video.
- **End the sequence on a held tension frame**, not a resolve — e.g. the frozen pin, the trembling summit, the wobbling slab.
```
