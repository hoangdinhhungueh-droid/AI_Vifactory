"""Scene expander (S2 helper) -- deterministic, FREE, no-LLM, no-quota.

Notion is the brain: an episode brain_input.json authors the story plus a
`scene_budget` (how many images per narrative beat), a `prompt_template`, an
`art_style.style_prompt` (the unified visual DNA) and a few `scenes` that act as
seed exemplars. This module expands all of that into the full list of per-scene
image/motion prompts (~target_image_count, each ~1500 chars) needed for a
documentary-style cut sequence at whatever per-cut duration S5 uses.

Design goals:
  * No external API / LLM / paid call -> safe on the free daily pipeline.
  * Every prompt carries the same visual DNA (palette, light, negative space,
    no faces / no text / no numbers / no logos) so the film stays cohesive.
  * Distinctness comes from rotating symbolic motifs (per beat) x composition x
    light x camera, so even a reused motif yields a visually different frame.
  * render_type='ken_burns_image' -> S5 routes each scene through the free
    Antigravity Google Image-still + Ken Burns path (no Veo, no PEXELS key, no character_pack).
  * aspect_label (03/07, Content Spec v1.1): frame ratio wording is NOT
    hard-coded -- callers pass "16:9 widescreen" for long-form YouTube or
    "9:16 vertical" (default, back-compat) for short funnel, so the prompt
    text never contradicts the actual render aspect.

Entry point: expand_scenes(...).
"""
from __future__ import annotations
import os

import logging
import re

logger = logging.getLogger(__name__)

DEFAULT_ASPECT_LABEL = os.getenv("VF_ASPECT_LABEL") or ("9:16 vertical" if os.getenv("VF_IMAGE_ASPECT", "16:9") == "9:16" else "16:9 widescreen")

# --- symbolic motif bank (SUBJECT/ACTION only; DNA appended separately) ------
# Keys are matched as substrings against the normalised scene_budget beat label.
_MOTIF_BANK = {
    "cold open": [
        "a single crimson indicator pulsing on a wall of dead, dark trading screens at night",
        "one abandoned office chair turned away from a bank of black monitors",
        "a lone desk lamp throwing a hard cone of light across a deserted trading floor",
        "a frozen wall clock above an empty dealing desk in the dead of night",
        "a thin crimson line of light under a sealed glass office door",
    ],
    "founding": [
        "a weathered cotton bale resting in a shaft of dusty warehouse light",
        "an old brass merchant scale balanced in deep shadow",
        "a hand-lettered ledger lying open on a worn wooden counter",
        "a single freight rail line vanishing toward a pale horizon",
        "a tarnished pocket watch laid on an aged leather-bound book",
    ],
    "peak": [
        "a glass skyscraper rising into a cold sky, dwarfing everything below",
        "an immaculate marble lobby stretching into mirrored infinity",
        "a sweeping aerial of a financial district at its glittering height",
        "a single gleaming corner office at the very top of a dark tower",
        "a crystal trophy catching one hard beam of light on a dark shelf",
    ],
    "mechanism": [
        "thousands of identical paper documents fanning out into a dark void",
        "a labyrinth of interlocking pipes funneling into one fragile glass sphere",
        "small house-shaped tokens being fed into a vast grinding machine",
        "a complex web of taut threads knotting around a single weak strand",
        "stacked transparent boxes nested inside one another, hollow at the core",
    ],
    "leverage": [
        "a precarious tower of monolithic blocks leaning far past balance over a void",
        "a single slender pillar bearing the impossible weight of a massive slab",
        "a thin wire stretched to breaking under an enormous suspended mass",
        "a ledger half-hidden behind a heavy curtain, edges faintly glowing",
        "a house of cards built absurdly tall in a darkened room",
    ],
    "timeline": [
        "a row of calendar pages curling and darkening one after another",
        "a wall of clocks all sliding toward the same final hour",
        "a single domino mid-fall in a long receding line",
        "a corridor of closing steel shutters receding into dark",
        "a ticking second hand frozen a moment before midnight",
    ],
    "rescue": [
        "two empty chairs at opposite ends of a long negotiating table",
        "a single unsigned document and a silent telephone under a cold beam",
        "a lifeline rope fraying just out of reach above a void",
        "a closed bank door with the lights going dark behind the glass",
        "a rescue boat turning away from a foundering silhouette",
    ],
    "cause": [
        "five cracks spreading from a single point across dark glass",
        "a row of warning lights ignored on a shadowed control panel",
        "a king-piece toppling alone on an abandoned dark board",
        "a chain with one obviously over-stressed, deforming link",
        "a single loose bolt beside a vast straining steel beam",
    ],
    "global": [
        "a dark globe laced with thin glowing lines blinking out one by one",
        "anonymous figures carrying plain cardboard boxes out into the night",
        "a falling blade of light plunging across a continent-sized map",
        "shuttered shopfronts receding down an empty grey street",
        "a tide of shadow sweeping over a sprawling city grid",
    ],
    "reform": [
        "a heavy new statute book closing over an old cracked ledger",
        "fresh steel scaffolding rising around a scarred stone facade",
        "a thick protective wall being built around a fragile glass core",
        "a vault door being reinforced with bright new bolts",
        "a set of balanced weights re-leveled on a steady scale",
    ],
    "lesson": [
        "a single crimson indicator pulsing again on a wall of dark screens, the loop returning",
        "a lone candle flame steady against vast surrounding darkness",
        "a fragile glass sphere held in a single beam, faintly cracked",
        "a thin horizon line of dawn behind a silent skyline",
        "a frozen clock at 1:45, hands still in the dark",
    ],
}

_DEFAULT_MOTIFS = [
    "a symbolic editorial still of consequence and collapse in the 2008 financial era",
    "an austere arrangement of finance-era objects in vast negative space",
    "a single charged object isolated in a pool of hard directional light",
    "a stark architectural void with one small telling detail",
]

# {aspect} placeholder is substituted with the caller-supplied aspect_label.
_COMPOSITIONS = [
    "full-bleed {aspect}, subject anchored low-left with vast empty space above, strong negative space",
    "centered symmetrical framing with deep one-point perspective receding into shadow",
    "extreme low angle looking up, towering negative space, subject pinned to the lower third",
    "high overhead top-down view, geometry receding to a flat far horizon",
    "tight detail insert, shallow depth of field, one foreground object dominating the frame",
    "wide establishing shot, a single small subject dwarfed by surrounding darkness",
]

_LIGHTS = [
    "one hard directional light raking from frame-left, deep chiaroscuro and long shadows",
    "a single cold overhead beam carving the subject out of black negative space",
    "low crimson backlight rimming the subject while its core stays in shadow",
    "harsh side light with half the frame swallowed by teal-blue darkness",
]

_CAMERAS = [
    "Slow push-in toward the focal object; faint dust motes drift through the beam; no static",
    "Slow aerial drift with subtle parallax; the light shifts a half-stop colder; no static",
    "Camera tilts up the structure as tension rises; shadows lengthen; no static",
    "Slow lateral dolly revealing the depth of the cold space; no static",
    "Rack focus pull from a foreground object to the dim background; no static",
    "Locked hard-cut frame with internal motion only -- flicker, drifting shadow, settling dust; no static",
]

_ATMOS = [
    "cold institutional emptiness",
    "a sense of impending, irreversible loss",
    "muted desaturated teal-blue and slate-gray tones",
    "a single restrained crimson accent",
    "fine cinematic film grain",
    "soft vignette darkening the edges",
    "still, breathless air",
    "weight and gravity in every shadow",
    "non-photoreal editorial illustration texture",
    "vast quiet negative space",
    "documentary gravitas",
    "the hush before a collapse",
]

_DNA_OBJECTS = (
    "symbolic objects of the 2008 financial era -- screens, ledgers, vault doors, "
    "stacked leaning blocks, cardboard boxes, paper documents -- strictly no readable "
    "text, no numbers, no logos, no faces, no identifiable real people"
)
# {aspect} placeholder is substituted with the caller-supplied aspect_label.
_DNA_GRADE = (
    "editorial documentary illustration, non-photoreal, desaturated teal-blue and "
    "slate-gray palette with a single crimson accent, one hard directional light "
    "source, deep chiaroscuro, strong negative space, subtle film grain and vignette, "
    "{aspect}, one cohesive visual DNA across the entire film"
)


def _norm(s: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", (s or "").lower()).strip()


def _motifs_for(beat_label: str) -> list:
    n = _norm(beat_label)
    for key, motifs in _MOTIF_BANK.items():
        if key in n:
            return motifs
    return _DEFAULT_MOTIFS


def _pad_to_target(text: str, target: int) -> str:
    out = text
    i = 0
    while len(out) < max(0, target - 40) and i < len(_ATMOS) * 6:
        out += ", " + _ATMOS[i % len(_ATMOS)]
        i += 1
    return out


# --- FIX 29/07/2026 prompt-language hardening ------------------------------
# Do duoc, khong suy dien: cung 1 prompt scene 27 EP004 sinh ra dung 1 loi tren
# nhieu) -> loi nam o NGON NGU PROMPT, doi model khong sua duoc.

# (1) Menh de "danh san cho the so lieu se dan vao sau" -> model ve luon cai the.
_CARD_RESERVE_WORDS = (
    "graphic number card", "number card", "stat card", "overlay card",
    "added afterwards", "placed there afterwards", "placed afterwards",
    "reserved for", "left clear so", "kept clear so", "so a graphic",
)
# (2) Menh de phu dinh: Antigravity Google Image khong co negative prompt -> tokens duong.
_NEG_CLAUSE_RE = re.compile(
    r"^(?:and\s+)?(?:strictly\s+|absolutely\s+)?(?:no|not|never|avoid|avoiding|"
    r"without|free\s+of|excluding)\b", re.I)

_ZONE_PHRASE = {
    "top_left": "upper-left", "top_right": "upper-right",
    "bottom_left": "lower-left", "bottom_right": "lower-right",
    "top_third": "upper", "lower_third": "lower", "bottom_third": "lower",
    "left_third": "left", "right_third": "right",
}

# Thay the DUONG cho cac menh de phu dinh vua bo di: dien dat cung y nghia
# nhung bang thu model co the VE duoc, thay vi thu no khong the "khong ve".
_POSITIVE_STYLE_GUARD = (
    "flat two-dimensional vector artwork with clean solid colour fills, "
    "every surface blank and unlettered, plain unbranded objects"
)


_ZONE_OPPOSITE = {
    "top_left": "lower-right half",
    "top_right": "lower-left half",
    "bottom_left": "upper-right half",
    "bottom_right": "upper-left half",
}


def sanitize_image_prompt(prompt: str, safe_zone: str = "") -> str:
    """Bo 2 loai menh de gay hai khoi image prompt, thay bang dien dat duong.

    Tra ve prompt da lam sach. Khong bao gio raise: neu tat ca menh de bi bo
    (khong the xay ra voi prompt hop le) thi giu nguyen prompt goc.
    """
    if not prompt or not prompt.strip():
        return prompt
    if os.getenv("VF_PROMPT_SANITIZE", "1").strip() != "1":
        return prompt

    clauses = [c.strip() for c in prompt.split(",")]
    kept, n_card, n_neg = [], 0, 0
    for c in clauses:
        if not c:
            continue
        low = c.lower()
        if any(w in low for w in _CARD_RESERVE_WORDS):
            n_card += 1
            continue
        if _NEG_CLAUSE_RE.match(low):
            n_neg += 1
            continue
        kept.append(c)

    if not kept:
        logger.warning("[prompt-sanitize] bo het menh de -> giu nguyen prompt goc")
        return prompt

    out = ", ".join(kept)

    # Phan duoi day duoc NOI THEM, nen phai chua cho no truoc khi cat tran,
    # neu khong tran do dai se cat mat chinh cau mo ta vung trong.
    tail = ""
    if n_card:
        mode = (os.getenv("VF_PROMPT_ZONE_MODE", "describe") or "describe").strip().lower()
        zone = _ZONE_PHRASE.get(str(safe_zone or "").strip().lower())
        opposite = _ZONE_OPPOSITE.get(str(safe_zone or "").strip().lower())
        if mode == "silent":
            # Khong noi gi ve vung an toan: moi lan nhac den vung do la mot lan
            # model co co de VE vao do.
            tail = ""
        elif mode == "negspace" and opposite:
            # Dieu huong BO CUC thay vi mo ta cho trong: don toan bo chu the sang
            # phia doi dien, cho trong xuat hien nhu he qua.
            tail = (", the subject and every object are composed entirely in the "
                    "%s of the frame, wide open empty background occupying the "
                    "whole %s" % (opposite, zone or "opposite corner"))
        elif zone:
            tail = (", the %s area of the frame is plain flat unbroken background "
                    "surface, an empty stretch of floor and wall with nothing "
                    "standing in it" % zone)
        else:
            tail = (", one plain flat unbroken stretch of background surface with "
                    "nothing standing in it")
    if n_neg:
        tail += ", " + _POSITIVE_STYLE_GUARD

    try:
        maxlen = int(os.getenv("VF_PROMPT_MAXLEN", "700") or "700")
    except ValueError:
        maxlen = 700
    if maxlen > 0:
        out = _trim_to_maxlen(out, max(120, maxlen - len(tail)))
    out += tail

    if n_card or n_neg:
        logger.info("[prompt-sanitize] bo %d menh de card-reservation, %d menh de phu dinh; %d -> %d ky tu",
                    n_card, n_neg, len(prompt), len(out))
    return out


def _trim_to_maxlen(prompt: str, maxlen: int) -> str:
    """Cat prompt tai bien menh de gan nhat truoc maxlen (khong cat giua tu)."""
    if maxlen <= 0 or len(prompt) <= maxlen:
        return prompt
    cut = prompt.rfind(", ", 0, maxlen)
    return prompt[:cut] if cut > int(maxlen * 0.5) else prompt[:maxlen]


def build_image_prompt(motif: str, style_prompt: str, comp: str, light: str,
                       char_target: int = 1500,
                       aspect_label: str = DEFAULT_ASPECT_LABEL,
                       safe_zone: str = "") -> str:
    comp_r = comp.format(aspect=aspect_label) if "{aspect}" in comp else comp
    dna_grade_r = _DNA_GRADE.format(aspect=aspect_label)
    style_r = (style_prompt or "").strip().rstrip(".")
    motif_r = motif.strip().rstrip(".")

    # (3) STYLE LEN DAU. Model distilled 4-8 step (Antigravity Google Image) bam manh nhat
    # vao dau prompt; de style o cuoi la de no bi bo roi dau tien.
    if os.getenv("VF_PROMPT_STYLE_FIRST", "1").strip() == "1":
        parts = [style_r, dna_grade_r, motif_r, comp_r, light, _DNA_OBJECTS]
    else:
        parts = [motif_r, comp_r, light, style_r, _DNA_OBJECTS, dna_grade_r]

    prompt = ", ".join(p for p in parts if p)
    prompt = sanitize_image_prompt(prompt, safe_zone=safe_zone)

    # (3b) Padding bang tu _ATMOS chi de dat cho du char_target lam loang prompt.
    # Mac dinh TAT. Bat lai bang VF_PROMPT_PAD=1 neu can so sanh A/B.
    if os.getenv("VF_PROMPT_PAD", "0").strip() == "1":
        prompt = _pad_to_target(prompt, char_target)

    return _trim_to_maxlen(prompt, int(os.getenv("VF_PROMPT_MAXLEN", "700") or 700))


_REMOTION_BEATS = ("rise", "peak", "collapse", "aftermath")
_REMOTION_ZONES = ("top_left", "top_right", "bottom_left", "bottom_right")
# 27/07/2026: EP003 real-failure fix -- some S2/story authoring paths emit
# a 'thirds' vocabulary instead of the Locked corner enum above (12/12 stat
# cards silently dropped in bernie-madoff-2026-ep003). Alias the observed
# legacy values onto the nearest valid corner instead of dropping the block,
# so a story authoring regression degrades gracefully instead of losing the
# overlay entirely. Does not relax validation for anything NOT in this map.
_REMOTION_ZONE_ALIASES = {
    "top_third": "top_left",
    "upper_third": "top_left",
    "lower_third": "bottom_left",
    "bottom_third": "bottom_left",
    "left_third": "top_left",
    "right_third": "top_right",
}
_REMOTION_KEYS = ("enabled", "stat_value", "stat_label", "story_beat",
                  "has_chart_in_bg", "safe_zone", "accent_override")


def _norm_remotion(raw, beat_label=""):
    """Validate a Notion/S2-authored `remotion` block (schema duyet 26/07/2026).

    VPS never invents these values: if Notion did not author a valid block the
    scene simply renders without an overlay card. Only whitelisted keys survive.
    """
    if not isinstance(raw, dict):
        return None
    if not bool(raw.get("enabled")):
        return None
    sb = str(raw.get("story_beat") or "").strip().lower()
    if sb not in _REMOTION_BEATS:
        lab = str(beat_label or "").strip().lower()
        sb = next((x for x in _REMOTION_BEATS if x in lab), "")
    if sb not in _REMOTION_BEATS:
        logger.warning("[S2-remotion] drop: story_beat khong hop le (%r)", raw.get("story_beat"))
        return None
    sz = str(raw.get("safe_zone") or "").strip().lower()
    if sz not in _REMOTION_ZONES and sz in _REMOTION_ZONE_ALIASES:
        _aliased = _REMOTION_ZONE_ALIASES[sz]
        logger.warning("[S2-remotion] safe_zone alias %r -> %r (legacy thirds vocab)", sz, _aliased)
        sz = _aliased
    if sz not in _REMOTION_ZONES:
        logger.warning("[S2-remotion] drop: safe_zone khong hop le (%r)", raw.get("safe_zone"))
        return None
    sv = str(raw.get("stat_value") or "").strip()
    if not sv:
        logger.warning("[S2-remotion] drop: thieu stat_value")
        return None
    acc = raw.get("accent_override")
    acc = acc.strip() if isinstance(acc, str) and acc.strip() else None
    if acc and not re.fullmatch(r"#[0-9a-fA-F]{6}", acc):
        logger.warning("[S2-remotion] bo accent_override khong hop le (%r)", acc)
        acc = None
    unknown = [k for k in raw if k not in _REMOTION_KEYS]
    if unknown:
        logger.warning("[S2-remotion] bo qua key la: %s", unknown)
    return {
        "enabled": True,
        "stat_value": sv,
        "stat_label": str(raw.get("stat_label") or "").strip(),
        "story_beat": sb,
        "has_chart_in_bg": bool(raw.get("has_chart_in_bg")),
        "safe_zone": sz,
        "accent_override": acc,
    }


def expand_scenes(*, story: str = "", scene_budget: list = None,
                  style_prompt: str = "", prompt_template: str = None,
                  seed_exemplars: list = None, target_count: int = None,
                  char_target: int = 1500,
                  aspect_label: str = DEFAULT_ASPECT_LABEL) -> list:
    """Expand a story + scene_budget into a full list of scene prompt dicts.

    Returns a list of {image_prompt, motion_prompt, render_type, beat}.
    Deterministic and side-effect free (no network, no LLM).

    aspect_label: text describing the render aspect (e.g. "16:9 widescreen"
    for long-form YouTube per Content Spec v1.1, or "9:16 vertical" for short
    funnel). Threaded into the composition/DNA text so it never contradicts
    the actual render aspect.
    """
    seed_exemplars = [s for s in (seed_exemplars or []) if isinstance(s, dict)]
    budget = [b for b in (scene_budget or [])
              if isinstance(b, dict) and int(b.get("images") or 0) > 0]
    if not budget:
        tc = int(target_count or 120)
        budget = [{"beat": "default", "images": tc}]

    scenes = []
    ci = li = mi = 0
    for b in budget:
        label = str(b.get("beat", "")).strip()
        count = int(b.get("images") or 0)
        motifs = _motifs_for(label)
        for j in range(count):
            motif = motifs[j % len(motifs)]
            comp = _COMPOSITIONS[ci % len(_COMPOSITIONS)]; ci += 1
            light = _LIGHTS[li % len(_LIGHTS)]; li += 1
            motion = _CAMERAS[mi % len(_CAMERAS)]; mi += 1
            ip = build_image_prompt(motif, style_prompt, comp, light, char_target,
                                     aspect_label=aspect_label)
            scenes.append({
                "image_prompt": ip,
                "motion_prompt": motion,
                "render_type": "ken_burns_image",
                "beat": label,
                "is_hero_reference": False,
                "reuse_of": str(b.get("reuse_of", "") or "").strip(),
                "remotion": _norm_remotion(b.get("remotion"), label),
            })

    if target_count and len(scenes) > int(target_count):
        scenes = scenes[:int(target_count)]

    logger.info(
        "[S2-expander] story->%d scenes across %d beats (style=%s, aspect=%s, ~%d chars/prompt)",
        len(scenes), len(budget), bool(style_prompt), aspect_label, char_target)
    return scenes
