"""MPT-G3-3 - Karaoke subtitle renderer via FFmpeg."""
import asyncio, os
from pathlib import Path

SUBTITLE_POSITION = os.getenv("SUBTITLE_POSITION", "bottom")
NOTO_FONT_PATH = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"

FONT_BY_LANG = {
    "zh": NOTO_FONT_PATH,
    "ja": NOTO_FONT_PATH,
    "ko": NOTO_FONT_PATH,
    "en": "",
}

MARGIN_V = {"bottom": 80, "top": 40}

# --- 2.7: Subtitle reading-speed cap (chars-per-second) ---------------------
# Timing always follows the real voiceover (never stretched/shortened for
# reading-speed reasons); this is a detection-only quality gate that flags
# segments a human would find too fast to read, so upstream script writing
# can be tightened. Default 20 CPS ~= Netflix adult-content reading-speed
# guideline (~200 WPM English); override via env without a redeploy.
SUBTITLE_CPS_CAP = float(os.getenv("SUBTITLE_CPS_CAP", "20"))
# Max characters on one subtitle cue before we refuse to merge two chunks
# into it (avoids on-screen text overflow when closing a CPS gap).
MAX_LINE_CHARS = int(os.getenv("SUBTITLE_MAX_LINE_CHARS", "42"))

# FIX 29/07/2026: minimum cue size. The CPS splitter could close a cue on
# a single leftover word, which showed up on EP004 around 3:26-3:28 as
# one word per frame. A cue must carry enough words and enough screen
# time to be readable.
MIN_CUE_WORDS = int(os.getenv("SUBTITLE_MIN_CUE_WORDS", "3"))
MIN_CUE_MS = int(os.getenv("SUBTITLE_MIN_CUE_MS", "700"))


def _merge_tiny_cues(chunks: list, min_words: int = None,
                     min_ms: int = None) -> list:
    """Fold undersized cues into a neighbour so no cue shows 1-2 words.

    Timing stays audio-accurate: merging only ever unions two adjacent
    windows, it never invents or shifts a boundary.
    """
    mw = MIN_CUE_WORDS if min_words is None else min_words
    mm = MIN_CUE_MS if min_ms is None else min_ms
    if not chunks:
        return chunks
    out = []
    for ch in chunks:
        txt = (ch.get("text") or "").strip()
        n_words = len(txt.split())
        dur_ms = max(ch.get("end_ms", 0) - ch.get("start_ms", 0), 0)
        if (n_words < mw or dur_ms < mm) and out:
            prev = out[-1]
            merged = ((prev.get("text") or "").strip() + " " + txt).strip()
            if len(merged) <= MAX_LINE_CHARS * 2:
                prev["text"] = merged
                prev["end_ms"] = ch.get("end_ms", prev.get("end_ms"))
                prev["words"] = (prev.get("words") or []) + (ch.get("words") or [])
                continue
        out.append(dict(ch))
    # A tiny FIRST cue has no previous neighbour: fold it forward instead.
    if len(out) > 1:
        first, nxt = out[0], out[1]
        if len((first.get("text") or "").split()) < mw:
            merged = ((first.get("text") or "").strip() + " "
                      + (nxt.get("text") or "").strip()).strip()
            if len(merged) <= MAX_LINE_CHARS * 2:
                nxt["text"] = merged
                nxt["start_ms"] = first.get("start_ms", nxt.get("start_ms"))
                nxt["words"] = (first.get("words") or []) + (nxt.get("words") or [])
                out = out[1:]
    return out


def check_reading_speed(segments: list, cps_cap: float = None) -> list:
    """Flag segments whose chars-per-second exceeds cps_cap.

    Read-only: never mutates segment timing (audio sync is authoritative).
    Returns a list of dicts for segments over the cap; empty list means all
    segments are within the cap.
    """
    cap = cps_cap if cps_cap is not None else SUBTITLE_CPS_CAP
    over = []
    for i, seg in enumerate(segments):
        text = (seg.get("text") or "").strip()
        if not text:
            continue
        duration_sec = max(seg.get("end_ms", 0) - seg.get("start_ms", 0), 0) / 1000.0
        if duration_sec <= 0:
            continue
        char_count = len(text.replace(chr(10), ""))
        word_count = len(text.split())
        cps = char_count / duration_sec
        wpm = word_count / (duration_sec / 60.0)
        if cps > cap:
            over.append({
                "index": i,
                "text": text,
                "duration_sec": round(duration_sec, 2),
                "cps": round(cps, 1),
                "wpm": round(wpm, 1),
            })
    return over


def _split_by_words(words: list, cap: float) -> list:
    """Greedily group consecutive words into sub-cues so each cue stays at
    or under the CPS cap, using the ASR own word-level timestamps (free,
    no extra calls, audio-accurate)."""
    chunks = []
    cur = []
    cur_start = None
    for w in words:
        wt = (w.get("word") or "").strip()
        if not wt:
            continue
        if cur_start is None:
            cur_start = w["start_ms"]
        cur.append(w)
        text = " ".join((x.get("word") or "").strip() for x in cur).strip()
        dur = max(w["end_ms"] - cur_start, 0) / 1000.0
        cps = len(text.replace(chr(10), "")) / dur if dur > 0 else 0
        if cps > cap and len(cur) > 1:
            closing = cur[:-1]
            c_text = " ".join((x.get("word") or "").strip() for x in closing).strip()
            chunks.append({
                "start_ms": cur_start,
                "end_ms": closing[-1]["end_ms"],
                "text": c_text,
                "words": closing,
            })
            cur = [w]
            cur_start = w["start_ms"]
    if cur:
        c_text = " ".join((x.get("word") or "").strip() for x in cur).strip()
        chunks.append({
            "start_ms": cur_start,
            "end_ms": cur[-1]["end_ms"],
            "text": c_text,
            "words": cur,
        })
    return _merge_tiny_cues(chunks)


def _split_proportional(text: str, start_ms: int, end_ms: int, cap: float) -> list:
    """Fallback when no word-level timestamps exist (e.g. Groq backend):
    split by word count and distribute time proportionally by character
    count. Approximate, but zero-cost and still bounded by the real audio
    window."""
    duration_sec = max(end_ms - start_ms, 0) / 1000.0
    char_count = len(text.replace(chr(10), ""))
    if duration_sec <= 0 or char_count == 0:
        return [{"start_ms": start_ms, "end_ms": end_ms, "text": text}]
    n_parts = max(int((char_count / duration_sec) / cap) + 1, 1)
    words = text.split()
    if not words or n_parts <= 1:
        return [{"start_ms": start_ms, "end_ms": end_ms, "text": text}]
    per_part = max(len(words) // n_parts, 1)
    parts = [words[i:i + per_part] for i in range(0, len(words), per_part)]
    total_chars = sum(len(" ".join(p)) for p in parts) or 1
    total_ms = end_ms - start_ms
    chunks = []
    cursor_ms = start_ms
    acc_chars = 0
    for idx, p in enumerate(parts):
        p_text = " ".join(p)
        acc_chars += len(p_text)
        part_end = end_ms if idx == len(parts) - 1 else start_ms + int(total_ms * (acc_chars / total_chars))
        chunks.append({"start_ms": cursor_ms, "end_ms": part_end, "text": p_text})
        cursor_ms = part_end
    return chunks


def _merge_over_cap(chunks: list, cap: float) -> list:
    """Second pass: if splitting left a lone chunk still over cap (a single
    word spoken too fast to split further), try merging it into a neighbor
    when the merged cue would still fit under cap. Reduces needless
    over-cap singletons without ever exceeding the cap elsewhere."""
    if not chunks:
        return chunks
    merged = [dict(c) for c in chunks]
    changed = True
    while changed:
        changed = False
        for i, c in enumerate(merged):
            dur = max(c["end_ms"] - c["start_ms"], 0) / 1000.0
            cps = len(c["text"].replace(chr(10), "")) / dur if dur > 0 else 0
            if cps <= cap:
                continue
            if i + 1 < len(merged):
                nxt = merged[i + 1]
                cand_text = c["text"] + " " + nxt["text"]
                cand_dur = max(nxt["end_ms"] - c["start_ms"], 0) / 1000.0
                cand_cps = len(cand_text.replace(chr(10), "")) / cand_dur if cand_dur > 0 else 0
                if cand_cps <= cap and len(cand_text) <= MAX_LINE_CHARS:
                    merged[i] = {"start_ms": c["start_ms"], "end_ms": nxt["end_ms"], "text": cand_text, "words": (c.get("words") or []) + (nxt.get("words") or [])}
                    del merged[i + 1]
                    changed = True
                    break
            if i - 1 >= 0:
                prev = merged[i - 1]
                cand_text = prev["text"] + " " + c["text"]
                cand_dur = max(c["end_ms"] - prev["start_ms"], 0) / 1000.0
                cand_cps = len(cand_text.replace(chr(10), "")) / cand_dur if cand_dur > 0 else 0
                if cand_cps <= cap and len(cand_text) <= MAX_LINE_CHARS:
                    merged[i - 1] = {"start_ms": prev["start_ms"], "end_ms": c["end_ms"], "text": cand_text, "words": (prev.get("words") or []) + (c.get("words") or [])}
                    del merged[i]
                    changed = True
                    break
    return merged


def _extend_into_gaps(chunks: list, cap: float, max_extend_ms: int = 400) -> list:
    """Final safety net for a cue still over cap after split+merge (typically
    a single word spoken too fast to split further). Borrows display time
    ONLY from real silence immediately before/after the cue -- never from a
    neighboring cue own speech window -- so voiceover sync and frame order
    are never broken, no cue ever overlaps another, and no text is ever
    dropped, shortened, or resized (so it cannot overflow on screen)."""
    if not chunks:
        return chunks
    result = [dict(c) for c in chunks]
    for i, c in enumerate(result):
        dur_ms = c["end_ms"] - c["start_ms"]
        dur = max(dur_ms, 0) / 1000.0
        char_count = len(c["text"].replace(chr(10), ""))
        cps = char_count / dur if dur > 0 else 0
        if cps <= cap:
            continue
        needed_ms = max(int(round((char_count / cap) * 1000)) - dur_ms, 0)
        if needed_ms <= 0:
            continue
        gap_after = (result[i + 1]["start_ms"] - c["end_ms"]) if i + 1 < len(result) else max_extend_ms
        extend_after = max(min(needed_ms, gap_after, max_extend_ms), 0)
        c["end_ms"] += extend_after
        needed_ms -= extend_after
        if needed_ms > 0:
            gap_before = (c["start_ms"] - result[i - 1]["end_ms"]) if i > 0 else max_extend_ms
            extend_before = max(min(needed_ms, gap_before, max_extend_ms), 0)
            c["start_ms"] -= extend_before
            needed_ms -= extend_before
        result[i] = c
    return result


def _est_lines(text: str, per_line: int = 42) -> int:
    """Estimate rendered subtitle line count (42-char line cap, ASS auto-wrap)."""
    t = (text or '').replace(chr(10), ' ').strip()
    if not t:
        return 0
    hard = t.count('\\N') + 1
    est = (len(t) + per_line - 1) // per_line
    return max(hard, est, 1)


def _linger_for_cps(chunks: list, cap: float, max_extend_ms: int = None,
                    max_overlap: int = 1, max_lines: int = None,
                    scene_len_ms: int = None) -> list:
    """Give over-cap cues extra reading time by letting them linger past their
    spoken window, overlapping the next cue. libass stacks the two overlapping
    events vertically, so the viewer sees up to `max_lines` lines at once.

    Never moves start_ms. Only end_ms is extended. Refuses the grant when the
    resulting on-screen stack would exceed max_lines.
    """
    if max_extend_ms is None:
        try:
            max_extend_ms = int(os.environ.get('SUBTITLE_LINGER_MAX_MS', '2000'))
        except ValueError:
            max_extend_ms = 2000
    if max_lines is None:
        try:
            max_lines = int(os.environ.get('SUBTITLE_MAX_LINES', '3'))
        except ValueError:
            max_lines = 3
    if scene_len_ms is None:
        try:
            scene_len_ms = int(float(os.environ.get('SUBTITLE_SCENE_LEN_MS', '0')))
        except ValueError:
            scene_len_ms = 0
    if not scene_len_ms or scene_len_ms <= 0:
        scene_len_ms = 0
    if max_extend_ms <= 0 or not chunks:
        return chunks

    out = [dict(c) for c in chunks]
    for i, c in enumerate(out):
        text = (c.get('text') or '').strip()
        if not text:
            continue
        dur_ms = max(c.get('end_ms', 0) - c.get('start_ms', 0), 0)
        if dur_ms <= 0:
            continue
        chars = len(text.replace(chr(10), ''))
        cps = chars / (dur_ms / 1000.0)
        if cps <= cap:
            continue
        need_ms = int((chars / float(cap)) * 1000.0) - dur_ms
        if need_ms <= 0:
            continue
        grant = min(need_ms, max_extend_ms)

        nxt = out[i + 1] if (i + 1) < len(out) else None
        if nxt is not None:
            if _est_lines(text) + _est_lines(nxt.get('text') or '') > max_lines:
                continue
            limit_idx = min(i + max_overlap, len(out) - 1)
            hard_end = out[limit_idx].get('end_ms', 0)
            grant = min(grant, max(hard_end - c.get('end_ms', 0), 0))

        if scene_len_ms:
            # SCENE-BOUNDARY GUARD 27/07/2026: a cue must never linger
            # past the still image it belongs to.
            end_ms = c.get('end_ms', 0)
            scene_end = ((end_ms // scene_len_ms) + 1) * scene_len_ms
            room = max(scene_end - end_ms, 0)
            if grant > room:
                grant = room
                c['cps_linger_clipped_by_scene'] = True
        if grant <= 0:
            continue
        c['end_ms'] = c.get('end_ms', 0) + grant
        c['cps_linger_ms'] = grant
    return out


def resplit_for_cps(segments: list, cps_cap: float = None, scene_len_ms: int = None) -> list:
    """Auto-split any subtitle cue whose CPS exceeds cap into smaller cues --
    for free, with no human step. Uses real word-level timestamps when
    available; falls back to proportional splitting otherwise. Never
    invents timing outside the original [start_ms, end_ms] window, so
    audio sync is preserved."""
    cap = cps_cap if cps_cap is not None else SUBTITLE_CPS_CAP
    out = []
    for seg in segments:
        text = (seg.get("text") or "").strip()
        start_ms = seg.get("start_ms", 0)
        end_ms = seg.get("end_ms", 0)
        duration_sec = max(end_ms - start_ms, 0) / 1000.0
        if not text or duration_sec <= 0:
            out.append({"start_ms": start_ms, "end_ms": end_ms, "text": text, "words": seg.get("words") or []})
            continue
        char_count = len(text.replace(chr(10), ""))
        cps = char_count / duration_sec
        if cps <= cap:
            out.append({"start_ms": start_ms, "end_ms": end_ms, "text": text, "words": seg.get("words") or []})
            continue
        words = seg.get("words")
        if words:
            split = _split_by_words(words, cap)
        else:
            split = _split_proportional(text, start_ms, end_ms, cap)
        split = split if split else [{"start_ms": start_ms, "end_ms": end_ms, "text": text}]
        split = _merge_over_cap(split, cap)
        out.extend(split)
    out = _extend_into_gaps(out, cap)
    out = _linger_for_cps(out, cap, scene_len_ms=scene_len_ms)
    return out



def _ms_to_ass(ms: int) -> str:
    h = ms // 3_600_000; ms %= 3_600_000
    m = ms // 60_000;    ms %= 60_000
    s = ms // 1_000;     cs = (ms % 1_000) // 10
    return f"{h}:{m:02d}:{s:02d}.{cs:02d}"


def _segments_to_ass(segments: list, font_path: str, position: str,
                     font_size: int = 52) -> str:
    """Convert segment list to ASS subtitle string."""
    marginv = MARGIN_V.get(position, 80)
    align = 2 if position == "bottom" else 8
    font_name = Path(font_path).stem if font_path else "Arial"

    header = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "PlayResX: 1080",
        "PlayResY: 1920",
        "",
        "[V4+ Styles]",
        (
            f"Style: Default,{font_name},{font_size},&H00FFFFFF,&H000000FF,"
            f"&H00000000,&HCC000000,-1,0,0,0,100,100,0,0,1,3,0,"
            f"{align},10,10,{marginv},1"
        ),
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]

    event_lines = []
    for seg in segments:
        start = _ms_to_ass(seg["start_ms"])
        end   = _ms_to_ass(seg["end_ms"])
        text  = seg["text"].replace("\n", "\\N")
        event_lines.append(f"Dialogue: 0,{start},{end},Default,,0,0,0,,{text}")

    return "\n".join(header + event_lines)


async def render_karaoke(
    video_path: str,
    segments: list,
    output_path: str,
    lang_code: str = "en",
    position: str = SUBTITLE_POSITION,
    font_size: int = 52,
) -> str:
    """
    Burns karaoke subtitles into video. marginv=80 for 9:16 bottom.
    Returns output_path.
    """
    font_path = FONT_BY_LANG.get(lang_code, "")
    ass_path = output_path.replace(".mp4", "_subs.ass")
    ass_content = _segments_to_ass(segments, font_path, position, font_size)
    with open(ass_path, "w", encoding="utf-8") as f:
        f.write(ass_content)

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    ass_escaped = ass_path.replace(":", "\\:")
    if font_path and Path(font_path).exists():
        vf = f"ass='{ass_escaped}':fontsdir=/usr/share/fonts"
    else:
        vf = f"ass='{ass_escaped}'"

    cmd = [
        "ffmpeg", "-y",
        "-i", video_path,
        "-vf", vf,
        "-c:a", "copy",
        "-preset", "fast",
        output_path
    ]
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
    )
    _, stderr = await proc.communicate()
    if proc.returncode != 0:
        raise RuntimeError(f"ffmpeg karaoke failed: {stderr.decode()[-300:]}")
    return output_path


# ---------------------------------------------------------------------------
# FLOW ENHANCE 27/07/2026 - karaoke ASS burn for FINAL renders (per aspect).
# Previously karaoke only ran in S6 when episode["video_path"] existed, which
# never happened (S6 runs before S7), so finals only carried plain SRT burn.
# ---------------------------------------------------------------------------

_ASS_RES_BY_ASPECT = {
    "16:9": (1920, 1080),
    "9:16": (1080, 1920),
    "1:1": (1080, 1080),
}
_ASS_FONT_BY_ASPECT = {"16:9": 54, "9:16": 60, "1:1": 52}
_ASS_MARGINV_BY_ASPECT = {"16:9": 90, "9:16": 260, "1:1": 130}


def karaoke_enabled() -> bool:
    return os.getenv("VF_KARAOKE_FINALS", "1") == "1"


def _ass_escape(text: str) -> str:
    return (text or "").replace("\\", "").replace("{", "(").replace("}", ")").replace("\n", "\\N")


def _karaoke_text(seg: dict) -> str:
    """Word-level \\k highlight when word timings exist, else plain text."""
    words = seg.get("words") or []
    if not words:
        return _ass_escape(seg.get("text", ""))
    parts = []
    prev_end = int(seg.get("start_ms", 0))
    for w in words:
        try:
            ws = int(w.get("start_ms", prev_end))
            we = int(w.get("end_ms", ws))
        except Exception:
            continue
        token = _ass_escape(str(w.get("word", w.get("text", ""))).strip())
        if not token:
            continue
        gap = max(0, ws - prev_end)
        dur = max(1, we - ws)
        if gap >= 20:
            parts.append("{\\k%d}" % int(round(gap / 10.0)))
        parts.append("{\\kf%d}%s " % (int(round(dur / 10.0)), token))
        prev_end = we
    out = "".join(parts).strip()
    return out or _ass_escape(seg.get("text", ""))


def segments_to_karaoke_ass(segments: list, aspect: str = "16:9",
                            lang_code: str = "en") -> str:
    resx, resy = _ASS_RES_BY_ASPECT.get(aspect, (1920, 1080))
    fsize = _ASS_FONT_BY_ASPECT.get(aspect, 54)
    marginv = _ASS_MARGINV_BY_ASPECT.get(aspect, 90)
    font_path = FONT_BY_LANG.get(lang_code, "")
    font_name = Path(font_path).stem if font_path else "DejaVu Sans"
    header = [
        "[Script Info]",
        "ScriptType: v4.00+",
        "WrapStyle: 0",
        "ScaledBorderAndShadow: yes",
        "PlayResX: %d" % resx,
        "PlayResY: %d" % resy,
        "",
        "[V4+ Styles]",
        "Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, "
        "OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, "
        "ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, "
        "Alignment, MarginL, MarginR, MarginV, Encoding",
        ("Style: Default,%s,%d,&H00F5D66B,&H00FFFFFF,&H00101010,&H80000000,"
         "-1,0,0,0,100,100,0,0,1,3,1,2,60,60,%d,1" % (font_name, fsize, marginv)),
        "",
        "[Events]",
        "Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text",
    ]
    events = []
    for seg in segments or []:
        try:
            start = _ms_to_ass(int(seg["start_ms"]))
            end = _ms_to_ass(int(seg["end_ms"]))
        except Exception:
            continue
        events.append("Dialogue: 0,%s,%s,Default,,0,0,0,,%s"
                      % (start, end, _karaoke_text(seg)))
    return "\n".join(header + events) + "\n"


async def burn_karaoke_for_aspect(src_path: str, output_path: str,
                                  segments: list, aspect: str,
                                  lang_code: str = "en") -> str:
    """Burn karaoke ASS into an already aspect-derived video. Audio copied."""
    import shutil as _shutil
    import tempfile as _tempfile

    if not segments:
        _shutil.copy(src_path, output_path)
        return output_path
    tmp_dir = _tempfile.mkdtemp(prefix="vf_kara_")
    try:
        ass_path = os.path.join(tmp_dir, "subs.ass")
        with open(ass_path, "w", encoding="utf-8") as f:
            f.write(segments_to_karaoke_ass(segments, aspect, lang_code))
        cmd = [
            "ffmpeg", "-y", "-nostdin",
            "-i", src_path,
            "-vf", "ass=subs.ass:fontsdir=/usr/share/fonts",
            "-c:v", "libx264", "-preset", "fast", "-crf", "20",
            "-pix_fmt", "yuv420p",
            "-c:a", "copy",
            output_path,
        ]
        proc = await asyncio.create_subprocess_exec(
            *cmd, cwd=tmp_dir,
            stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
        _, err = await proc.communicate()
        if proc.returncode != 0:
            raise RuntimeError("karaoke burn failed (%s): %s"
                               % (aspect, err.decode()[-300:]))
        return output_path
    finally:
        _shutil.rmtree(tmp_dir, ignore_errors=True)
