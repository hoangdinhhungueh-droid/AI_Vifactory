"""FFmpeg-native motion-graphics cards: animated intro hook + outro CTA.

Free, CPU-only. Replaces HyperFrames, which is NOT viable on this VPS:
the KVM CPU lacks SSE4.2/AVX (x86-64-v2) so prebuilt `sharp` binaries fail,
and the system libvips (8.15) is older than sharp 0.34's required 8.17.
These cards are generated at the exact target aspect size and inserted into
the clip list, so they flow through the existing xfade concat + render path
unchanged.
"""
import os
import asyncio
import logging
import textwrap

logger = logging.getLogger(__name__)

_FONT_CANDIDATES = [
    os.getenv("VF_CARD_FONT", ""),
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",
]
FONT_BOLD = next(
    (f for f in _FONT_CANDIDATES if f and os.path.exists(f)),
    _FONT_CANDIDATES[1],
)

INTRO_SEC = float(os.getenv("VF_CARD_INTRO_SEC", "2.5"))
OUTRO_SEC = float(os.getenv("VF_CARD_OUTRO_SEC", "3.0"))
BG = os.getenv("VF_CARD_BG", "0x0b0e14")

# CTA localized for Latin-script markets; DejaVu covers these (incl. Vietnamese).
# Non-Latin scripts (ja/ko/zh/hi/ar/th) fall back to English to avoid tofu boxes.
LATIN_CTA = {
    "en": "Follow for Part 2",
    "vi": "Theo d\u00f5i \u0111\u1ec3 xem Ph\u1ea7n 2",
    "es": "Sigue para la Parte 2",
    "pt": "Siga para a Parte 2",
    "fr": "Abonne-toi pour la Partie 2",
    "de": "Folge f\u00fcr Teil 2",
    "it": "Segui per la Parte 2",
    "id": "Ikuti untuk Bagian 2",
}


def cta_text(lang: str) -> str:
    return LATIN_CTA.get((lang or "en").lower(), LATIN_CTA["en"])


async def _run(cmd):
    proc = await asyncio.create_subprocess_exec(
        *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    _, err = await proc.communicate()
    return proc.returncode, err.decode(errors="ignore")[-400:]


async def _make_card(text, size, duration, out_path):
    W, H = size
    fs = min(64, max(30, W // 22))
    wrap_w = max(16, int(W / (fs * 0.55)))
    wrapped = textwrap.fill((text or "").strip(), width=wrap_w)
    tf = out_path + ".txt"
    with open(tf, "w", encoding="utf-8") as f:
        f.write(wrapped)
    fade_out_st = max(0.1, float(duration) - 0.5)
    vf = (
        "drawtext=fontfile=%s:textfile=%s:fontsize=%d:fontcolor=white:"
        "line_spacing=14:x=(w-text_w)/2:y=(h-text_h)/2,"
        "fade=t=in:st=0:d=0.5,fade=t=out:st=%.2f:d=0.5"
    ) % (FONT_BOLD, tf, fs, fade_out_st)
    cmd = [
        "ffmpeg", "-y", "-f", "lavfi", "-i",
        "color=c=%s:s=%dx%d:d=%s:r=30" % (BG, W, H, duration),
        "-vf", vf, "-t", str(duration),
        "-c:v", "libx264", "-preset", "fast", "-pix_fmt", "yuv420p",
        out_path,
    ]
    rc, err = await _run(cmd)
    if rc != 0 or not os.path.exists(out_path):
        logger.warning("[motion_cards] card failed (%s): %s", out_path, err)
        return None
    return out_path


async def build_cards(episode, aspect, out_dir, clip_paths):
    """Return clip list with intro hook + outro CTA cards (if enabled).

    Falls back to the original clip_paths on any error so render never breaks.
    """
    if os.getenv("VF_MOTION_CARDS", "1") == "0":
        return clip_paths
    render_arch = str(episode.get("render_architecture") or "").strip()
    if not render_arch and os.path.exists(os.path.join(out_dir, "brain_input.json")):
        try:
            import json as _json
            with open(os.path.join(out_dir, "brain_input.json"), "r", encoding="utf-8") as _bf:
                render_arch = str(_json.load(_bf).get("render_architecture") or "").strip()
        except Exception:
            pass
    if render_arch in ("two_layer_v1", "remotion_twolayer_karaoke_v4") or "twolayer" in render_arch or render_arch.startswith("two_layer"):
        logger.info("[motion_cards] skipping intro/outro cards for two-layer architecture (%s)", render_arch)
        return clip_paths
    try:
        from app.services.mpt_ported.video_render import ASPECT_SIZES
        size = ASPECT_SIZES.get(aspect)
        if not size:
            return clip_paths
        akey = aspect.replace(":", "")
        lang = episode.get("lang_code", "en")
        bi = episode.get("brain_input", {}) or {}
        hook = (episode.get("hook_3s") or bi.get("hook_3s") or "").strip()
        result = []
        if hook:
            ip = os.path.join(out_dir, "_card_intro_%s.mp4" % akey)
            c = await _make_card(hook, size, INTRO_SEC, ip)
            if c:
                result.append(c)
        result.extend(clip_paths)
        op = os.path.join(out_dir, "_card_outro_%s.mp4" % akey)
        c = await _make_card(cta_text(lang), size, OUTRO_SEC, op)
        if c:
            result.append(c)
        return result if result else clip_paths
    except Exception as e:
        logger.warning("[motion_cards] disabled due to error: %s", e)
        return clip_paths
