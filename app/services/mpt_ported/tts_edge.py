"""MPT-G2-1/G2-2 - TTS Edge-TTS synthesizer + SSML builder."""
import asyncio, os, re, tempfile
from pathlib import Path
from typing import Optional
import aiofiles

SSML_SUPPORTED_VOICES = {
    "en-US-AriaNeural":      ["cheerful","empathetic","fearful","sad","angry","excited","gentle","hopeful"],
    "en-US-ChristopherNeural":       ["cheerful","newscast","angry","sad"],
    "en-GB-SoniaNeural":     ["cheerful","sad"],
    "vi-VN-HoaiMyNeural":    [],
    "vi-VN-NamMinhNeural":   [],
    "zh-CN-XiaoxiaoNeural":  ["cheerful","angry","fearful","sad","gentle"],
    "ja-JP-NanamiNeural":    ["cheerful","sad","angry"],
    "ko-KR-SunHiNeural":     ["cheerful","sad"],
}

# FIX 07/08/2026 (EP005 QC feedback): default was "en-US-AriaNeural" (FEMALE)
# even though the locked decision (Decisions Log + "05 - Stage Details S1-S9"
# spec: "Voice giong dan ong trung nien") requires a middle-aged MALE voice,
# and EP004 was already tuned for GuyNeural's pacing (see rate/pitch FIX
# 29/07/2026 below, calibrated for the male voice's faster delivery). Aria
# leaking back in as the default was a real regression -- fixed here.
DEFAULT_VOICE = "en-US-ChristopherNeural"

# ENHANCE 05/08/2026: auto-emphasis for narration. Wrap standout statistics
# (numbers, percentages, money, magnitudes, years -- min 2 digits) in
# <emphasis> so documentary narration stresses key data points instead of
# reading everything flat. Runs AFTER XML-escaping, so the regex only ever
# sees plain digits/words and can never introduce unescaped &, <, > into the
# SSML document.
#
# NOTE 07/08/2026: build_ssml()/_apply_emphasis() below are NO LONGER used to
# build the `text` argument passed to edge_tts.Communicate() -- see the FIX
# note inside synthesize() for why. Kept here only as reference/for any
# future direct SSML-capable backend.
_EMPHASIS_RE = re.compile(
    r"\b\d[\d,]*(?:\.\d+)?\s?(?:%|percent|million|billion|trillion)?\b",
    re.IGNORECASE,
)


def _apply_emphasis(safe_text: str, level: str = "moderate") -> str:
    """Wrap standalone numbers/statistics in <emphasis>. Skips bare 1-digit
    tokens (e.g. filler like "a 5 minute walk") so only meaningful stats
    (years, percents, money, counts >= 2 digits) get stressed. Trailing
    punctuation/whitespace picked up by the regex (e.g. "1220, ") is moved
    back outside the tag so pauses/commas read naturally."""
    def _wrap(m: "re.Match[str]") -> str:
        tok = m.group(0)
        core = tok.rstrip(", \t")
        trailing = tok[len(core):]
        digits = re.sub(r"[^\d]", "", core)
        if len(digits) < 2 or not core:
            return tok
        return f'<emphasis level="{level}">{core}</emphasis>{trailing}'
    return _EMPHASIS_RE.sub(_wrap, safe_text)


def build_ssml(text: str, voice: str, style: Optional[str] = None,
               rate: str = "+0%", pitch: str = "+0Hz",
               emphasize: bool = True) -> str:
    """Build SSML markup for edge-tts.

    NOT currently fed into edge_tts.Communicate() -- see synthesize() FIX
    note (07/08/2026). Kept for reference / potential future backend that
    accepts raw SSML directly.
    """
    supported = SSML_SUPPORTED_VOICES.get(voice, [])
    if style and style not in supported:
        # Fallback: drop style silently, keep prosody
        style = None

    # Escape XML special chars
    safe = text.replace("&","&amp;").replace("<","&lt;").replace(">","&gt;")

    # ENHANCE 05/08/2026: emphasis pass runs AFTER escaping (safe: regex only
    # matches digit tokens, never touches escaped entities like "&amp;").
    if emphasize:
        safe = _apply_emphasis(safe)

    prosody = f'<prosody rate="{rate}" pitch="{pitch}">{safe}</prosody>'
    if style:
        inner = f'<mstts:express-as style="{style}">{prosody}</mstts:express-as>'
    else:
        inner = prosody

    ssml = (
        '<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis"'
        ' xmlns:mstts="http://www.w3.org/2001/mstts"'
        f' xml:lang="{voice[:5]}">'
        f'<voice name="{voice}"><prosody rate="{rate}" pitch="{pitch}">{inner}</voice>'
        '</speak>'
    )
    return ssml


async def synthesize(
    text: str,
    voice: str = DEFAULT_VOICE,
    output_path: str = "/tmp/vf/tts_out.mp3",
    style: Optional[str] = None,
    rate: str = "+0%",
    pitch: str = "+0Hz",
    retries: int = 3,
    emphasize: bool = True,
) -> str:
    """Synthesize text to mp3 using edge-tts. Returns output_path.

    FIX 07/08/2026 (EP005 QC feedback -- garbled "mstts equals http://...
    mstts.xml" audio/subtitle heard at the very START of narration):
    edge_tts.Communicate() ALWAYS builds its OWN <speak>/<voice>/<prosody>
    SSML envelope internally (see mkssml() in edge_tts/communicate.py) and
    ESCAPES whatever `text` you give it (via escape(remove_incompatible_
    characters(text))) before embedding it as literal content inside that
    envelope. The previous code (ENHANCE 05/08/2026) passed our own
    pre-built build_ssml() output -- a full <speak version="1.0" ...
    xmlns:mstts="http://www.w3.org/2001/mstts">...<voice>...</voice></speak>
    document -- as `text=` to Communicate(). That whole string got escaped
    and embedded as literal spoken words inside edge_tts's own wrapper,
    so the TTS engine read our own XML tags/attributes out loud at the
    start of narration ("mstts equals http forward slash forward slash
    www.w3.org slash 2001 slash mstts xml" = literal reading of
    xmlns:mstts="http://www.w3.org/2001/mstts" xml:lang=...).
    This library version has NO supported way to inject custom SSML
    (<emphasis>, <mstts:express-as style=...>) through Communicate() --
    every call must use PLAIN narration text plus the rate/pitch/volume
    kwargs it exposes natively. build_ssml()/_apply_emphasis() are kept
    above for reference but are no longer used here.
    """
    import edge_tts

    Path(output_path).parent.mkdir(parents=True, exist_ok=True)

    if style:
        # Not supported through this library's Communicate() API (would
        # require raw SSML injection, which double-escapes -- see FIX note
        # above). Surface this loudly instead of silently dropping it.
        print(f"[tts_edge] style='{style}' requested but NOT applied -- "
              f"edge_tts.Communicate() does not support custom SSML/express-as "
              f"in this library version; using plain rate/pitch prosody only.")

    last_exc = None
    for attempt in range(retries):
        try:
            communicate = edge_tts.Communicate(text=text, voice=voice, rate=rate, pitch=pitch)
            await communicate.save(output_path)
            # Verify output
            size = os.path.getsize(output_path)
            if size < 1024:
                raise ValueError(f"Output too small: {size} bytes")
            return output_path
        except Exception as e:
            last_exc = e
            if attempt < retries - 1:
                await asyncio.sleep(2 ** attempt)
    raise RuntimeError(f"edge-tts synthesize failed after {retries} attempts: {last_exc}")


async def synthesize_with_fallback(
    text: str,
    voice: str = DEFAULT_VOICE,
    output_path: str = "/tmp/vf/tts_out.mp3",
    style: Optional[str] = None,
    backend: str = "auto",
    # FIX 29/07/2026: pacing controls were defined on synthesize() but never
    # reachable from the pipeline, so narration always ran at +0%.
    rate: str = "+0%",
    pitch: str = "+0Hz",
    # ENHANCE 05/08/2026: SSML auto-emphasis toggle, wired end-to-end from
    # run_s4 the same way rate/pitch already are. NOTE 07/08/2026: no longer
    # has any effect for the edge backend (see synthesize() FIX note) --
    # kept in the signature for backward compatibility with call sites.
    emphasize: bool = True,
) -> dict:
    """Try edge-tts first; fall back to piper if backend=auto and edge fails."""
    if backend in ("edge", "auto"):
        try:
            path = await synthesize(text, voice, output_path, style, rate, pitch, emphasize=emphasize)
            return {"path": path, "backend": "edge", "voice": voice}
        except Exception as e:
            if backend == "edge":
                raise
            print(f"[tts_edge] edge failed: {e} — trying piper fallback")
    # Piper fallback
    from .tts_piper import synthesize_piper
    piper_path = output_path.replace(".mp3", "_piper.wav")
    path = await synthesize_piper(text, output_path=piper_path)
    return {"path": path, "backend": "piper", "voice": voice}
