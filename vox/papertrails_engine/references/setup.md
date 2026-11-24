# Runtime setup

## Requirements

- Node.js 22.12 or newer; npm; Python 3.12 recommended for ASR wheels.
- `ffmpeg` and `ffprobe` on PATH, with H.264 (`libx264`) and AAC support.
- `uv` for the setup helper; otherwise create a Python venv manually below.
- Chromium with WebGL2. Headless software WebGL is supported where Chromium/OS permit it; containers may require extra browser system libraries.
- Several GB free disk for node packages, browser, ASR model/cache, and video. Intermediate stills can use more. Check the actual target disk, not only the system drive.

From the package root, via the agent's shell tool:

```text
python scripts/setup.py --with-asr
```

The helper runs locked `npm ci` at root and `engine/`, Playwright Chromium installation, `uv venv .venv-asr --python 3.12`, and installs pinned `requirements-asr.txt` locally. It does not install FFmpeg or change global configuration. A `.venv-asr` already in use is reused, not deleted.

Manual ASR setup without uv:

```text
python3.12 -m venv .venv-asr
<venv-python> -m pip install -r requirements-asr.txt
```

On Windows the system Python launcher equivalent is `py -3.12 -m venv .venv-asr`. `<venv-python>` is `.venv-asr/Scripts/python.exe` on Windows, `.venv-asr/bin/python` elsewhere. Do not mix machine Python/pip versions.

Manual renderer setup:

```text
npm ci
npm --prefix engine ci
node node_modules/playwright/cli.js install chromium
```

On Linux, missing OS browser dependencies must be installed by the machine administrator or through the normal Playwright documented setup. Do not request elevated permissions or bypass a tool denial automatically.

## First voice recognition

The default model is `small`, multilingual, CPU/int8. For Vietnamese, use `--language vi`. Model weights download into this package's `.cache/whisper` on first use. Supply `--model "<local-faster-whisper-model-dir>"` for offline use. Model download uses Hugging Face, not a paid transcription API; first download still needs network access. A `--model tiny` engineering test does not establish Vietnamese transcription quality.

If an existing timed transcript is supplied, ordinary Python can run:

```text
python scripts/pipeline.py prepare --audio "voice.wav" --transcript "captions.srt" --project "<new-project>"
```

A plain `.txt` script has no measured timing and is rejected; it must be aligned to real audio, not distributed evenly across an imagined duration.

## Troubleshooting

- **ASR not imported:** use the local venv Python, not the Python used to launch the agent.
- **PyAV metadata_errors failure:** use the shipped lock; faster-whisper 1.2.1 is incompatible with the PyAV 19 `av.open` API observed during testing. The lock uses PyAV 16.1.0.
- **No speech:** stop. Check whether the file really contains speech. Never render a made-up transcript.
- **Model download blocked:** use a legitimately obtained local model or the user's measured SRT/JSON. Do not disable TLS verification.
- **WebGL context unavailable:** report the browser error and environment. Do not silently output blank frames or a different art style.
- **Output already exists:** render a new version filename. Approved footage and timelines are not disposable.
- **Python writes Unicode badly in terminal:** keep JSON/text files UTF-8 and read them with file tools. Do not strip Vietnamese accents from captions; accent stripping is only for keyword matching.
- **Relocating a project:** `timeline.audio` points to the copied voice by absolute path. Update it to the relocated `media/voice.<ext>` and verify the stored source hash. Do not accidentally mux a different recording.

## Agent installation

`scripts/install.py` defaults to DRY_RUN and requires `--apply`. It copies portable source/assets, not venvs, caches, voices, or test output. It refuses existing targets and source/destination nesting. `--skills-dir` overrides discovery explicitly. Hermes uses active `HERMES_HOME` only; no other profile is changed.

The ZIP is a source skill package. Coding agents with local tools can run it; a hosted chat sandbox may lack WebGL, model downloads, or system dependencies. Do not promise identical runtime availability across every UI.
