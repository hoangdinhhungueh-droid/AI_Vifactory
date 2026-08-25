"""Story Quality Scorer - FREE, deterministic pre-production gate.

Notion AI is the deep creative judge. This module is a cheap MECHANICAL
pre-filter that blocks obviously-weak stories before they burn render/Veo
budget. Pure stdlib (re/os) - no network, no paid API, fully testable.

Signals are heuristic but generalize across the drama/fiction domain this
product targets:
  - hook: curiosity OR reversal/contrast + emotion + length + specificity
  - trend_fit: keyword presence w/ stemming + a small theme lexicon
  - character: named-cast recurrence (consistency)
  - twist: twist-cue density + payoff position
  - structure: length / beats / ending payoff

Public API:
    score_story(story_text=..., hook_3s=..., trend_keywords=[...],
                character_pack=[...]) -> dict
"""
from __future__ import annotations

import os
import re
from collections import Counter


def _envf(name: str, default: float) -> float:
    try:
        return float(os.getenv(name, str(default)))
    except Exception:
        return float(default)


def gate() -> dict:
    """Gate thresholds (env-overridable so Notion AI can tune w/o code change)."""
    return {
        "hook_min":    _envf("VF_QUAL_HOOK_MIN", 7.0),
        "trend_min":   _envf("VF_QUAL_TREND_MIN", 6.0),
        "char_min":    _envf("VF_QUAL_CHAR_MIN", 6.0),
        "overall_min": _envf("VF_QUAL_OVERALL_MIN", 6.5),
    }


_SENT_RE = re.compile(r"(?<=[.!?])\s+")
_WORD_RE = re.compile(r"[A-Za-z']+")
_NAME_RE = re.compile(r"\b[A-Z][a-z]{2,}\b")
_SPECIFIC_RE = re.compile(r"\b(?:mon|tues|wednes|thurs|fri|satur|sun)day\b|\d", re.IGNORECASE)

CURIOSITY_CUES = (
    "why", "how", "what if", "nobody knew", "no one knew", "secret", "hidden",
    "until", "but then", "never expected", "didn't know", "did not know",
    "the truth", "everything changed", "what happened", "should have",
)
REVERSAL_HINTS = (";", " by ", " until ", " but ", " then ", " within ", " days later", " overnight")
TWIST_CUES = (
    "but ", "however", "suddenly", "turned out", "revealed", "realized",
    "discovered", "betrayed", "twist", "little did", "unbeknownst",
    "all along", "in fact", "actually", "to her surprise", "to his surprise",
    "what he didn't know", "what she didn't know", "plot twist",
)
EMOTION_CUES = (
    "love", "hate", "fear", "betray", "revenge", "tears", "heart", "scream",
    "broke", "shattered", "rage", "desperate", "trembl", "alone", "lost",
    "die", "death", "kill", "secret", "lie", "trust", "promise", "fired",
)
ENDING_CUES = (
    "finally", "in the end", "at last", "never again", "forever", "always",
    "one step ahead", "too late",
)
# Lightweight theme expansion so thematic trend keywords match morphological /
# semantic surface variants without embeddings. Extend freely.
THEME_LEXICON = {
    "betrayal": ("betray", "backstab", "cheat", "deceiv", "lied", "double-cross", "stab"),
    "revenge": ("revenge", "payback", "vengeance", "one step ahead", "took everything back", "got even", "retribution"),
    "corporate": ("company", "client", "account", "contract", "boss", "office", "ceo", "partner", "firm", "bankrupt", "business"),
    "family": ("mother", "father", "sister", "brother", "son", "daughter", "family", "inherit", "will"),
    "secret": ("secret", "hidden", "clause", "truth", "reveal", "unknown"),
    "love": ("love", "heart", "marry", "wedding", "romance", "kiss"),
    "money": ("money", "rich", "wealth", "fortune", "bankrupt", "million", "debt", "account"),
}
STOPWORDS = {
    "The", "A", "An", "And", "Or", "But", "She", "He", "They", "It", "His",
    "Her", "Their", "You", "We", "That", "This", "When", "Then", "One",
}


def _sentences(text: str):
    text = (text or "").strip()
    if not text:
        return []
    return [s.strip() for s in _SENT_RE.split(text) if s.strip()]


def _wc(text: str) -> int:
    return len(_WORD_RE.findall(text or ""))


def _kw_present(kw: str, low: str) -> bool:
    kw = kw.strip().lower()
    if not kw:
        return False
    if kw in low:
        return True
    if len(kw) >= 4 and kw[:5] in low:  # stem/prefix match (betrayal~betrayed)
        return True
    for token in THEME_LEXICON.get(kw, ()):  # theme expansion
        if token in low:
            return True
    parts = [p for p in re.findall(r"[a-z]+", kw) if len(p) >= 4]
    if len(parts) >= 2 and all(p[:5] in low for p in parts):
        return True
    return False


def _score_hook(first_sentence: str, hook_3s):
    s = (hook_3s or first_sentence or "").strip()
    if not s:
        return 0.0, ["no hook text"]
    low = s.lower()
    n = _wc(low)
    score = 3.0
    reasons = []
    if any(c in low for c in CURIOSITY_CUES):
        score += 2.5; reasons.append("curiosity/open-loop cue")
    elif any(h in low for h in REVERSAL_HINTS):
        score += 2.0; reasons.append("reversal/contrast hook")
    else:
        reasons.append("no curiosity/reversal cue")
    if any(c in low for c in EMOTION_CUES):
        score += 1.5; reasons.append("emotional/conflict cue")
    if 6 <= n <= 22:
        score += 1.5; reasons.append(f"good length ({n}w)")
    elif n < 6:
        score += 0.3; reasons.append(f"too short ({n}w)")
    else:
        score += 0.5; reasons.append(f"long ({n}w)")
    if _SPECIFIC_RE.search(s) or len(_NAME_RE.findall(s)) >= 1:
        score += 1.0; reasons.append("specific detail (name/number/day)")
    if s.endswith("?") or "..." in s:
        score += 0.7; reasons.append("open-ended punctuation")
    if hook_3s and hook_3s.strip():
        score += 0.8; reasons.append("explicit hook_3s supplied")
    return round(min(10.0, score), 2), reasons


def _score_trend_fit(text: str, trend_keywords):
    kws = [str(k).strip() for k in (trend_keywords or []) if str(k).strip()]
    if not kws:
        return 6.0, ["no trend_keywords supplied -> neutral 6.0"]
    low = text.lower()
    hits = [k for k in kws if _kw_present(k, low)]
    frac = len(hits) / max(1, len(kws))
    score = 3.0 + frac * 7.0
    return round(min(10.0, score), 2), [f"{len(hits)}/{len(kws)} trend themes present"]


def _score_character(text: str, character_pack):
    reasons = []
    names = []
    for c in (character_pack or []):
        if isinstance(c, dict):
            nm = (c.get("name") or c.get("id") or "").strip()
        else:
            nm = str(c).strip()
        if nm:
            names.append(nm)
    low = text.lower()
    if names:
        counts = {nm: low.count(nm.lower()) for nm in names}
        present = [nm for nm, ct in counts.items() if ct >= 1]
        recurring = [nm for nm, ct in counts.items() if ct >= 2]
        score = 3.0
        score += 3.0 * (len(present) / max(1, len(names)))
        score += 3.0 * (len(recurring) / max(1, len(names)))
        reasons.append(f"{len(present)}/{len(names)} named chars present, {len(recurring)} recurring")
        if recurring and len(recurring) == len(names):
            score += 1.0; reasons.append("all chars recurring (consistent cast)")
        return round(min(10.0, score), 2), reasons
    found = [w for w in _NAME_RE.findall(text) if w not in STOPWORDS]
    cnt = Counter(found)
    recurring = [w for w, c in cnt.items() if c >= 2]
    score = 3.0 + min(5.0, len(recurring) * 1.5)
    reasons.append(f"no character_pack; {len(recurring)} recurring proper noun(s) detected")
    return round(min(10.0, score), 2), reasons


def _score_twist(text: str):
    sents = _sentences(text)
    if not sents:
        return 0.0, ["empty"]
    low_sents = [s.lower() for s in sents]
    twist_idx = [i for i, s in enumerate(low_sents) if any(c in s for c in TWIST_CUES)]
    n = len(sents)
    score = 2.0 + min(5.0, len(twist_idx) * 1.5)
    reasons = [f"{len(twist_idx)} twist-cue sentence(s)"]
    if any(i >= (2 * n) // 3 for i in twist_idx):
        score += 2.0; reasons.append("twist in final third (payoff)")
    return round(min(10.0, score), 2), reasons


def _score_structure(text: str):
    n = _wc(text)
    paras = [p for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
    sents = _sentences(text)
    score = 2.0
    reasons = []
    if n >= 60:
        score += 2.0; reasons.append(f"adequate length ({n}w)")
    elif n >= 30:
        score += 1.0; reasons.append(f"short ({n}w)")
    else:
        reasons.append(f"very short ({n}w)")
    if len(sents) >= 4:
        score += 1.5; reasons.append(f"{len(sents)} sentences")
    if len(paras) >= 2:
        score += 1.5; reasons.append(f"{len(paras)} beats/paragraphs")
    if any(c in text.lower() for c in ENDING_CUES):
        score += 1.0; reasons.append("ending/payoff cue")
    return round(min(10.0, score), 2), reasons


WEIGHTS = {"hook": 0.30, "trend_fit": 0.20, "character": 0.20, "twist": 0.15, "structure": 0.15}


def score_story(*, story_text: str, hook_3s=None, trend_keywords=None, character_pack=None) -> dict:
    text = (story_text or "").strip()
    sents = _sentences(text)
    first = sents[0] if sents else ""
    sub, reasons = {}, {}
    sub["hook"], reasons["hook"] = _score_hook(first, hook_3s)
    sub["trend_fit"], reasons["trend_fit"] = _score_trend_fit(text, trend_keywords)
    sub["character"], reasons["character"] = _score_character(text, character_pack)
    sub["twist"], reasons["twist"] = _score_twist(text)
    sub["structure"], reasons["structure"] = _score_structure(text)
    overall = round(sum(sub[k] * w for k, w in WEIGHTS.items()), 2)
    g = gate()
    blocking = []
    if sub["hook"] < g["hook_min"]:
        blocking.append(f"hook {sub['hook']} < {g['hook_min']}")
    if sub["trend_fit"] < g["trend_min"]:
        blocking.append(f"trend_fit {sub['trend_fit']} < {g['trend_min']}")
    if sub["character"] < g["char_min"]:
        blocking.append(f"character {sub['character']} < {g['char_min']}")
    if overall < g["overall_min"]:
        blocking.append(f"overall {overall} < {g['overall_min']}")
    return {
        "quality_score": overall,
        "sub_scores": sub,
        "passed": len(blocking) == 0,
        "blocking": blocking,
        "reasons": reasons,
        "gate": g,
    }
