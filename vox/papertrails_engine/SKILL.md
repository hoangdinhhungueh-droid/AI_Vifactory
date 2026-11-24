---
name: papertrails-video
description: Turn a voiceover into narrated paper-world video.
license: MIT
compatibility: Requires local shell, Python 3.12 for ASR, Node.js 22.12+, FFmpeg, and Chromium WebGL2.
metadata:
  version: "0.2.1"
  upstream: "https://github.com/xikhar/papertrails"
  upstream-author: "Shikhar"
  platforms: "windows,linux,macos"
---

# Papertrails Voice-to-Video

Turn ONE supplied voiceover into a finished MP4 in a pop-up paper-book world. You are the director: transcribe the audio, understand what is said, stage literal visual beats, render, and verify. This is a local coding-agent skill, not a hosted text-to-video service and not an MP3 upload website.

## When to Use

- The user supplies a voice/audio/narration and asks for a paper-cut, pop-up book, Papertrails, or narrated animation video.
- The user says “input một voice, ra một video”. Do the complete workflow without asking them to write a transcript, storyboard, or shell commands.
- Do not use for live-action, photoreal people, arbitrary cinematic acting, or voice cloning. No voice is regenerated: keep the user's original audio.

## Prerequisites

Read `references/setup.md`, `references/timeline.md`, and `references/direction.md`. Locate this skill directory from the loaded SKILL.md path; call it `SKILL_ROOT`. Resolve every bundled script relative to that path, not the user's current directory. Use the coding agent's shell/file/image tools. In Hermes use `terminal`, `read_file`, `patch`/`write_file`, and `vision_analyze`; other agents use equivalent native tools.

Run the following from SKILL_ROOT only if its runtime is missing:

```text
python scripts/setup.py --with-asr
```

This installs local npm dependencies, Chromium, and `.venv-asr` using uv. It never edits agent settings. First ASR use downloads model weights to `.cache/whisper`; later use is local. Prefer Python 3.12 for the pinned ASR wheels. Existing timed transcripts bypass ASR. Check free space before downloads and render; there is no paid generation API in this skill.

## Procedure

### 1. Ingest the one voice

1. Resolve the attached audio's actual file path. If none was supplied, ask only for the audio. Do not fabricate speech or silently use test fixtures.
2. Create a NEW project folder outside the skill tree, such as the user's workspace `videos/<topic>/`. Never replace an approved project.
3. Determine ratio from the request: Shorts/Reels/TikTok → portrait; otherwise landscape. Audio determines duration; do not stretch audio to fit a guessed minute count.
4. Run with the ASR venv's Python (Windows `.venv-asr/Scripts/python.exe`; macOS/Linux `.venv-asr/bin/python`):

```text
<ASR_PYTHON> scripts/pipeline.py prepare --audio "<voice.mp3>" --project "<project>" --format landscape --language auto
```

Default model `small` is CPU/int8 multilingual. For explicitly Vietnamese speech use `--language vi`. Use `--model tiny` only for a clearly labeled fast draft, not as a claim of accurate Vietnamese transcription. A local faster-whisper model directory also works. If the user already provided measured Whisper JSON/SRT, add `--transcript "<captions.srt>"`; do not require a second input.
5. Read `transcript.txt`, `transcript.json`, and `timeline.json`. Preserve original voice in `media/voice.<ext>`. ASR failure, no speech, invalid timing, or missing dependencies must STOP with the actual error. Never substitute a canned script or a guessed timed transcript.

**Complete when:** measured voice duration, actual recognized text, and timed captions exist. State any uncertain names in project notes, not as invented facts.

### 2. Direct the film yourself

The Python starter uses a LIMITED bilingual keyword table. It is **not** a semantic director. Do not deliver it without your own scene review.

1. Read the whole narration, then refine EACH scene against its specific spoken idea. Preserve timings; split/merge at measured word/sentence boundaries when necessary.
2. Each scene needs a concrete subject, visible action, location, and framing. The `visual` string is your planning note, NOT a prompt interpreted by an AI generator. Actual output is controlled by `prop`, `action`, `biome`, `night`, and `camera` or by your code extension.
3. Use the supplied props for matching subjects: coins for money, factory for manufacturing, forest for forest protection, clock for time, book for learning. Voice/recording ideas: `voice-note`, `mic`; captions/subtitles: `bubble`; making a film/video: `film`. Use `grow` for things that appear or spread, and vary `camera` (`push`, `low`, `crane`, `orbit`) between consecutive shots. For a subject outside the library, implement it in the engine's video module. A book plus a long unrelated subtitle is not an adequate illustration.
4. Keep the paper style: folded edges, printed/card textures, warm paper palette, small traveller in an actual 3D pop-up set. The original walking toy is a visual foundation, not the entire story.
5. Vary composition with semantic changes. Do not reuse identical shots or make camera motion stand in for subject action. Avoid tiny unreadable text or a paper prop blocking the traveller.
6. Captions come from actual measured words or segments. Do not put the full transcript into a title, invent numbers, or invent chart values. A generic chart prop is symbolic, never evidence of real data.
7. Record per-shot intent in `DIRECTION.md`; set `timeline.direction.status` to `agent-reviewed` only after reviewing every shot. Work autonomously unless input is genuinely missing or the user asked for approval gates.

**Complete when:** every narrated idea has an implemented visual, not just prose describing a nonexistent effect. Keep a clear note if the engine cannot depict something faithfully.

### 3. Inspect representative frames

Render stills from the start/middle/end of each shot, including transitions, using the renderer's `--stills` mode described in its `--help` output. Inspect the resulting images with the host's image tools. Check actual prop, Vietnamese glyphs, safe margins, no overlaps, and visible subject animation. Fix the relevant scene or engine code, then recheck those frames. Do not call a scene good from JSON or a child's claim alone.

### 4. Render and preserve the voice

```text
node scripts/render.mjs "<project>/timeline.json" "<project>/final.mp4" --quality med [--sfx] [--gpu]
python scripts/pipeline.py verify --video "<project>/final.mp4" --timeline "<project>/timeline.json"
```

Use `high` for final quality if practical; `low` only for a labeled technical preview. The renderer advances fixed simulation time frame by frame and muxes the supplied original voice. Never record the real-time browser animation as the final video. Do not add stock music, scrape images, call paid APIs, clone voices, or change source narration unless requested. `--sfx` (opt-in) only adds a soft synthesized paper flip at cuts under the untouched voice; say so when you use it. If the user supplies music, mix it under narration separately and preserve measured voice sync.

**Complete when:** a freshly produced, decodable H.264/AAC MP4 exists, with exact ratio/fps and voice-matched duration. The verify command checks media integrity, NOT visual meaning.

### 5. Verify and deliver

- Decode the final MP4, verify both streams, dimensions, FPS, frame count, and voice duration. Extract and inspect frames from the actual MP4, not only the browser.
- Compare the soundtrack with source timing near the start, middle, and end. ASR timestamps are estimates; describe word vs segment accuracy honestly.
- Keep `transcript.json`, `captions.srt`, editable `timeline.json`, and `DIRECTION.md` with the MP4. Record missing or approximate visuals explicitly.
- Deliver the actual file using the host's attachment/link mechanism, plus ratio, duration, and any real limitation in a short note. If no output was produced, say BLOCKED and why; never say “done” because scripts exist.

## Quick Reference

```text
python scripts/setup.py --with-asr
<ASR_PYTHON> scripts/pipeline.py prepare --audio "voice.wav" --project "<new-project>" --language vi --format portrait
node scripts/render.mjs "<new-project>/timeline.json" "<new-project>/final.mp4" --quality med
python scripts/pipeline.py verify --video "<new-project>/final.mp4" --timeline "<new-project>/timeline.json"
python -m unittest discover -s tests -p test_pipeline.py -v
npm test
```

In Hermes invoke each CLI with `terminal(command="...", workdir=SKILL_ROOT, timeout=...)`; do not ask the user to execute it. Read/write the project through file tools. Never edit another Hermes profile or install globally without the user's request.

## Pitfalls

- A skill is agent instructions plus runtime, not a video foundation model. It needs a coding agent with a local shell, browser/WebGL support, and file access. Merely uploading SKILL.md to a restricted chat may not run Chromium.
- Keyword selection can misread synonyms/context. You must direct the actual content. `visual` does not produce an image on its own.
- Whisper can miss names, hallucinate during silence, and misalign short utterances. Use voice as authority; never quietly replace it with synthetic speech.
- Use the venv Python, not a machine's unrelated Python. The pinned PyAV version is deliberate: newer PyAV removed an argument used by faster-whisper 1.2.1.
- First model/browser download needs network and disk. A corporate firewall or missing WebGL is a real blocker, not an excuse to fake output.
- CPU rendering can be slow (1080p `high` can exceed the 120 s per-frame timeout on SwiftShader). Add `--gpu` to render through the machine's GPU via ANGLE; keep CPU only where no GPU exists. Give measured progress only; no made-up “minutes remaining”. No benchmark on a tiny English fixture proves long Vietnamese production quality.
- Preserve the upstream MIT notice in `engine/LICENSE` and credit `rights/SOURCES.md`. User voice/music rights are independent of the code license.

## Verification

Definition of done is **one actual input voice → real transcription → agent-directed implemented shots → MP4 with original voice → decoded media checks and visual inspection**. Keep author tests, independent QA, actual ASR run, and visual QA as separate evidence; never treat one as proof of the others.
