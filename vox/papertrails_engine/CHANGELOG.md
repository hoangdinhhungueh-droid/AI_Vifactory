# Changelog

## 0.2.1 (2026-11-22)

- Fix: the encoder now limits output to `frames / fps` instead of the audio duration, so a duration that is not a whole number of frames can no longer drop the last frame and fail verification.
- Verification errors now report the probed size, frame count and audio presence.
- Packaging: `python scripts/package_skill.py --output <zip> --lite` builds a video-only package without the upstream interactive game entry, its art atlases, tests and dev reports (traced from the video entry's imports and fetches). The build script skips the game entry when it is absent.
- Scenes: optional paper `card` overlay (taped `note` with lines that write in, optional big chapter style; pinned `photo` with a marker ellipse and stamp). See references/timeline.md.


## 0.2.0 (2026-11-20)

- Captions: cream torn-paper strip with ink text (no dark bar). With measured `words`, the word being spoken is inked red; the pipeline now keeps word timings in each caption.
- Title: pinned paper tag that pops in at each cut. Every cut gets a 0.36 s paper page-wipe.
- Cameras: `push`, `low`, `crane`; consecutive shots in one biome view the set from a different side.
- Actions: `grow`; tile props (village, forest, house…) grow piece by piece on `grow`/`reveal`. Tile props are larger (village ×2.2, house ×2.0, forest ×1.6).
- Props: new `film`, `bubble`, `mic`; `factory` gets a turning gear, rising smoke and flickering windows; `voice-note`, `bubble`, `mic` follow the measured loudness of the original voice.
- Renderer: computes the voice envelope; `--sfx` (opt-in) mixes a synthesized paper flip under the untouched voice at cuts; `--gpu` renders through ANGLE (needed for 1080p `high` in practice).
- All existing tests pass (8 node, 10 python).
