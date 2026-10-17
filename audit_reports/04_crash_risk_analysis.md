# 💥 CRASH RISK ANALYSIS & UNHANDLED EXCEPTION AUDIT (AVF-E2E-004)

> **Audit Date**: 2026-10-17  
> **Auditor**: Worker Gemini 3.8 Flash High (Antigravity IDE) under Boss Claude Opus 5.5 Supervision  
> **Scope**: Code paths that can hang, swallow errors, corrupt data, or crash without graceful recovery.

---

## 1. Summary of Identified Crash Risks by Severity

| Risk ID | Severity | File Coordinate | Root Cause & Failure Mode | Impact |
| :--- | :--- | :--- | :--- | :--- |
| **CR-01** | **CRITICAL** | `stages/s09_voice_tts.py#L50` & `stages/s10_render.py#L160` & `vox/assemble.py#L55,L92` | **Subtitle and Audio Format Type Mismatch in Modular Pipeline**:<br>1. S9 emits `subtitles_file = .../word_timestamps.json` (JSON).<br>2. S10 passes `subtitles_file` as `ass_file` to `assemble_final_video`.<br>3. `vox/assemble.py` executes `ffmpeg -vf subtitles='...word_timestamps.json'`. FFmpeg libass fails with exit code `3199971767` because libass rejects JSON.<br>4. `vox/assemble.py#L55` executes `wave.open(audio_wav)`. When S9 emits MP3 (`voice_narration.mp3`), `wave.open` crashes with `wave.Error: file does not start with RIFF id`. | Pipeline crashes at S10 Render. Unable to complete E2E run. |
| **CR-02** | **HIGH** | `stages/s08_video_gen.py#L75,L86` | **Hardcoded "ffmpeg" instead of `get_ffmpeg_binary()`**:<br>When `ffmpeg` is not in system PATH (e.g. Windows without global PATH or non-standard VPS path), `subprocess.run(["ffmpeg", ...])` throws `FileNotFoundError`. The except block falls back to writing 4108 bytes of invalid raw bytes (`b"\x00\x00\x00\x18ftypmp42" + ...`), poisoning S10 concat demuxer and violating Rule 118 (Zero-Mock Data). | Corrupted clip files created; renders crash downstream with cryptic error codes. |
| **CR-03** | **MEDIUM** | `app/services/quota_manager.py#L96,L114` | **Bare `except:` Clauses**:<br>Lines 96 and 114 catch bare `except:`, which catches `SystemExit`, `KeyboardInterrupt`, and masks unexpected syntax or typing bugs. | Swallows critical process control signals. |
| **CR-04** | **MEDIUM** | `vox/assemble.py#L49` | **Silent Subprocess Error in FFmpeg Concat**:<br>`subprocess.run(cmd_concat, capture_output=True, check=True)` captures stdout/stderr. When `CalledProcessError` is raised, stderr is hidden inside the exception object and not logged to console, leaving the operator blind to the root cause. | Diagnostics delay during rendering failures. |
| **CR-05** | **LOW** | `scripts/prompts_forge_poller.py#L94` | **Spawning Stub Image Script**:<br>Poller spawns `b4_generate_from_notion_prompts.py` which calls `gen_scene_image` (a placeholder stub returning `None`). It writes an empty `images_manifest.json` with 0 assets instead of waiting for Antigravity Playwright. | Phantom empty image manifests created on VPS if poller triggers before Human Gate 2. |

---

## 2. In-Depth Root Cause & Verification Details

### CR-01: Modular Pipeline S09 ➔ S10 Contract Mismatch (Reproduced Live)
- **Live Reproduction Command**:
  ```bash
  python -m orchestrator.run_pipeline --profile e2e_min --dry-run
  ```
- **Error Output**:
  ```
  File "stages/s10_render.py", line 165, in run
      assemble_final_video(clip_paths, Path(audio_file), ass_file, final_mp4)
    File "vox/assemble.py", line 49, in assemble_final_video
      subprocess.run(cmd_concat, capture_output=True, check=True)
  subprocess.CalledProcessError: Command '[...ffmpeg.exe, -y, -f, concat, ...]' returned non-zero exit status 3199971767.
  ```
- **Analysis**:
  1. In `stages/s09_voice_tts.py`:
     ```python
     audio_file = ctx.paths.audio_dir / "voice_narration.mp3"
     subtitles_file = ctx.paths.audio_dir / "word_timestamps.json"
     ```
  2. In `vox/assemble.py`:
     ```python
     with wave.open(str(audio_wav), "rb") as wf:
         audio_dur = wf.getnframes() / float(wf.getframerate())
     ```
     `wave.open` fails on MP3.
  3. `vox/assemble.py` executes:
     ```python
     "-vf", f"subtitles='{ass_escaped}'"
     ```
     FFmpeg `subtitles` filter fails on JSON files. It requires `.ass` or `.srt`.
- **Resolution**:
  1. In `stages/s09_voice_tts.py`: Generate an authentic broadcast-compliant `.ass` subtitle file using `vox.karaoke.generate_ass_subtitles` (or format standard ASS template with header + dialogue events) alongside `word_timestamps.json`. Set `"subtitles_file": str(ass_file)`.
  2. In `vox/assemble.py`: Guard audio duration calculation with a fallback to `ffprobe` (via `get_ffprobe_binary()`) so both WAV and MP3 files are seamlessly supported without relying solely on Python's built-in `wave` module.

---

### CR-02: Hardcoded "ffmpeg" Executable in S08 Video Gen
- **File**: `stages/s08_video_gen.py#L75,L86`
- **Analysis**:
  `stages/s08_video_gen.py` directly executes `cmd = ["ffmpeg", ...]`. When running on Windows without `ffmpeg` explicitly added to system PATH, `subprocess.run` fails. The code catches `Exception` and writes a 4108-byte dummy byte array.
- **Resolution**:
  Import `from vox.ffmpeg_utils import get_ffmpeg_binary` and invoke `cmd = [get_ffmpeg_binary(), ...]`. If video generation cannot proceed, fail-fast with a descriptive error instead of writing fake corrupted files.

---

### CR-03: Bare `except:` in Quota Manager
- **File**: `app/services/quota_manager.py#L96,L114`
- **Resolution**:
  Replace `except:` with `except (ValueError, TypeError, OSError):`.
