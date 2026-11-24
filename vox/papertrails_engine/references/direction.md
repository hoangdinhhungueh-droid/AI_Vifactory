# Direction: narration is the authority

## Voice-first, not background-first

1. Read the sentence belonging to this shot, then surrounding context. Do not choose a background and try to justify it later.
2. Write a concrete tuple: **subject → action → consequence**. Example: “factories increase output” → paper factory → gears/smoke/output parcels animate → output pile grows. Not merely “forest camera flythrough with a subtitle about manufacturing”.
3. Start with the supplied props only where they actually fit. Extend video geometry/action code for important unmatched concepts instead of using a coin/book for everything.
4. A 2.5D/3D paper set should remain spatial: page, standing cards/buildings, paper edges, directional light, and shadows. Do not flatten it into a slide deck.
5. Camera movement is composition, not subject action. A clock hand, a page unfolding, a product emerging, a character walking to an object, or a growing stack supplies visible action.

## Pacing

- Follow measured clauses. Aim for one fresh visual beat every 2–5 seconds, but do not cut through a word just to hit a fixed interval.
- Establish a location, show the action closer, then reveal its result. A new framing must carry new information.
- Keep deliberate pauses from the voice; visual movement can continue, but do not stretch the video beyond the source recording merely to display an end card.
- For sustained silence, inspect the audio/transcript. ASR can hallucinate. Never fill silence with invented narration.
- Avoid constant whip pans, random zoom punches, repeated orbit shots, and camera drift that makes paper look like it is sliding apart.

## Captions and labels

- Use original spoken language, including Vietnamese marks. ASR errors must not be “corrected” by making up facts.
- Captions lower on screen with enough safe margin; titles near the upper safe area. Do not place both over the key prop.
- Caption phrases should fit one or two lines. With segment-only timing, manually measured phrase splits are better than an unreadable paragraph; do not pretend guessed word timing is exact.
- Avoid dense labels. A title is a short distilled idea, not a second copy of a long subtitle.

## Shot review table

Maintain this in the project's DIRECTION.md:

| Shot | Measured time | Spoken idea | Implemented prop/action | Camera | Source/uncertainty | Checked stills |
|---|---|---|---|---|---|---|
| shot-001 | actual timestamps | actual words | real code control, not only visual prose | actual preset | if factual | file paths |

For each shot inspect start/mid/end and cut transitions. Look for cropped/floating props, the traveller hidden behind geometry, unreadable text, and identical repeated staging. Verify motion from two nearby frames when needed; one pretty still is not evidence of animation.

## Unsupported subjects

Specific architecture, people interacting, products, cars, machines, or historical events may not exist in the starter library. Build suitable paper props/actions in the video module. Do not imply an illustration is a photograph or a realistic likeness. If the requested action exceeds what was implemented, name that limitation before calling the output final.

## Truth and rights

Do not invent names, dates, statistics, quotes, logos, or chart values. User narration is supplied content, not automatically verified reporting; for claims that matter, retain uncertainty or research primary sources at the user's direction. The scene JSON must not alter the soundtrack. Keep the upstream MIT notice; source voice/music permissions remain the user's separate responsibility.
