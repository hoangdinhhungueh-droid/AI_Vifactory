# 🛡️ HARDENING BACKLOG & CONCRETE CODE PATCHES (AVF-E2E-008)

> **Audit Date**: 2026-10-17  
> **Auditor**: Worker Gemini 3.8 Flash High (Antigravity IDE) under Boss Claude Opus 5.5 Supervision  
> **Scope**: Prioritized Actionable Hardening Fixes Ranked by Impact × Urgency.

---

## 1. Prioritized Hardening Backlog

| Rank | Issue ID | Target File & Coordinate | Description | Severity | Impact |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **P0** | **CR-01a** | `stages/s09_voice_tts.py#L50,L115` | S9 must emit valid ASS subtitles (`subtitles.ass`) alongside `word_timestamps.json` | Critical | Enables libass in FFmpeg / Remotion assembly without syntax error |
| **P0** | **CR-01b** | `vox/assemble.py#L55` | Support MP3 audio duration probing via `ffprobe` when `wave.open` encounters non-WAV | Critical | Prevents `wave.Error: file does not start with RIFF id` |
| **P1** | **CR-02** | `stages/s08_video_gen.py#L75,L86` | Use `get_ffmpeg_binary()` instead of hardcoded `"ffmpeg"`; eliminate raw dummy byte fallback | High | Eliminates clip corruption across Windows / non-standard VPS PATH |
| **P2** | **CR-03** | `app/services/quota_manager.py#L96,L114` | Replace bare `except:` with specific exception handling | Medium | Prevents swallowing system control signals |
| **P2** | **CR-04** | `vox/assemble.py#L49` | Log stderr on `cmd_concat` failure | Medium | Transparent forensic diagnostics on concat failures |

---

## 2. Concrete Code Patches

### Patch 1: `stages/s09_voice_tts.py` (Generate ASS subtitles for S10)
```python
# Create authentic ASS subtitles file for ffmpeg libass burning in S10
ass_file = ctx.paths.audio_dir / "subtitles.ass"
ass_lines = [
    "[Script Info]",
    "Title: Vox Tactile Subtitles",
    "ScriptType: v4.00+",
    "WrapStyle: 0",
    "PlayResX: 1920",
    "PlayResY: 1080",
    "",
    "[V4+ Styles]",
    "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding",
    "Style: Default,Arial,64,&H00FFFFFF,&H0000FFFF,&H00141414,&H80000000,-1,0,0,0,100,100,0,0,1,4,2,2,80,80,90,1",
    "",
    "[Events]",
    "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text"
]

# Group words into subtitle events
words_per_event = 6
for i in range(0, len(subtitles), words_per_event):
    chunk = subtitles[i:i + words_per_event]
    if not chunk:
        break
    s_start = chunk[0]["start"]
    s_end = chunk[-1]["end"]
    chunk_text = " ".join(w["word"] for w in chunk)
    
    def _to_ass_time(sec: float) -> str:
        h = int(sec // 3600)
        m = int((sec % 3600) // 60)
        s = int(sec % 60)
        cs = int(round((sec - int(sec)) * 100))
        return f"{h}:{m:02d}:{s:02d}.{cs:02d}"

    ass_lines.append(f"Dialogue: 0,{_to_ass_time(s_start)},{_to_ass_time(s_end)},Default,,0,0,0,,{chunk_text}")

ass_file.write_text("\n".join(ass_lines), encoding="utf-8")
```

### Patch 2: `vox/assemble.py` (Resilient audio duration probe)
```python
    # Measure exact audio duration to avoid premature truncation
    import json
    import wave
    audio_dur = 0.0
    try:
        with wave.open(str(audio_wav), "rb") as wf:
            audio_dur = wf.getnframes() / float(wf.getframerate())
    except Exception:
        # Fallback to ffprobe for MP3 / AAC / non-WAV streams
        from vox.ffmpeg_utils import get_ffprobe_binary
        ffprobe_bin = get_ffprobe_binary()
        cmd_p = [ffprobe_bin, "-v", "error", "-show_entries", "format=duration", "-of", "json", str(audio_wav)]
        res_p = subprocess.run(cmd_p, capture_output=True, text=True)
        if res_p.returncode == 0:
            try:
                audio_dur = float(json.loads(res_p.stdout).get("format", {}).get("duration", 0.0))
            except Exception:
                audio_dur = 0.0
```

### Patch 3: `stages/s08_video_gen.py` (Dynamic FFmpeg resolution)
```python
    from vox.ffmpeg_utils import get_ffmpeg_binary
    ffmpeg_bin = get_ffmpeg_binary()
    # Replace hardcoded "ffmpeg" with ffmpeg_bin
```

### Patch 4: `app/services/quota_manager.py` (Replace bare except)
```python
    # Replace lines 96 and 114:
    except (ValueError, TypeError, OSError):
        return True / return 0
```
