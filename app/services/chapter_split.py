"""Chapter-split gate - full story -> chapters + per-chapter SEO metadata.

FREE, deterministic, no network. The 'full-story-first then gate' model:
Notion AI writes the ENTIRE story; this gate mechanically segments it and
emits the per-chapter metadata that the SEO stage (YouTube chapters, hooks,
durations) consumes downstream.

Per chapter dict:
    index, title (<=55), hook, twist, duration_est_s,
    summary_1_sentence (<=55), word_count, text

Public API:
    split_chapters(story_text, target_chapters=None, wpm=None) -> dict
"""
from __future__ import annotations

import os
import re


def _envf(n: str, d: float) -> float:
    try:
        return float(os.getenv(n, str(d)))
    except Exception:
        return float(d)


def _envi(n: str, d: int) -> int:
    try:
        return int(os.getenv(n, str(d)))
    except Exception:
        return int(d)


NARRATION_WPM = _envf("VF_NARRATION_WPM", 150.0)
DEFAULT_TARGET = _envi("VF_TARGET_CHAPTERS", 0)  # 0 = auto
WORDS_PER_CHAPTER = _envi("VF_WORDS_PER_CHAPTER", 180)
MAX_TITLE = 55
MAX_SUMMARY = 55

_SENT_RE = re.compile(r"(?<=[.!?])\s+")
_WORD_RE = re.compile(r"[A-Za-z']+")
_HEAD_RE = re.compile(
    r"^\s*(?:#{1,6}\s+)?((?:chapter|chap\.?|part|episode|ep\.?|scene)\b.*)$",
    re.IGNORECASE,
)
_HR_RE = re.compile(r"^\s*[-*=_]{3,}\s*$")
_MD_RE = re.compile(r"^\s*#{1,6}\s+(.*)$")

TWIST_CUES = (
    "but ", "however", "suddenly", "turned out", "revealed", "realized",
    "discovered", "betrayed", "twist", "little did", "unbeknownst",
    "all along", "in fact", "actually", "to her surprise", "to his surprise",
    "what he didn't know", "what she didn't know", "plot twist",
)


def _sentences(text: str):
    text = (text or "").strip()
    if not text:
        return []
    return [s.strip() for s in _SENT_RE.split(text) if s.strip()]


def _wc(text: str) -> int:
    return len(_WORD_RE.findall(text or ""))


def _trim(s: str, n: int) -> str:
    s = " ".join((s or "").split())
    if len(s) <= n:
        return s
    return s[: n - 1].rstrip() + "\u2026"


def _auto_target(text: str) -> int:
    n = _wc(text)
    return max(1, round(n / max(1, WORDS_PER_CHAPTER)))


def _detect_marker_blocks(text: str):
    lines = text.split("\n")
    blocks = []
    cur_title = None
    cur = []

    def flush():
        nonlocal cur, cur_title
        body = "\n".join(cur).strip()
        if body:
            blocks.append({"title": cur_title, "text": body})
        cur = []
        cur_title = None

    for ln in lines:
        if _HR_RE.match(ln):
            flush()
            continue
        m = _HEAD_RE.match(ln) or _MD_RE.match(ln)
        if m:
            flush()
            cur_title = (m.group(1) or ln).strip()
            continue
        cur.append(ln)
    flush()
    blocks = [b for b in blocks if b["text"]]
    return blocks if len(blocks) >= 2 else []


def _split_sentences_into(text: str, target: int):
    sents = _sentences(text)
    if len(sents) <= target or target <= 1:
        return [{"title": None, "text": text.strip()}]
    per = len(sents) / target
    blocks = []
    for k in range(target):
        start = round(k * per)
        end = round((k + 1) * per) if k < target - 1 else len(sents)
        chunk = " ".join(sents[start:end]).strip()
        if chunk:
            blocks.append({"title": None, "text": chunk})
    return blocks or [{"title": None, "text": text.strip()}]


def _split_by_target(text: str, target: int):
    paras = [p.strip() for p in re.split(r"\n\s*\n", text.strip()) if p.strip()]
    if not paras:
        paras = [text.strip()]
    if target <= 1:
        return [{"title": None, "text": text.strip()}]
    if len(paras) == 1:
        return _split_sentences_into(paras[0], target)
    if len(paras) <= target:
        return [{"title": None, "text": p} for p in paras]
    total = sum(_wc(p) for p in paras)
    per = total / target
    blocks, cur, cur_w = [], [], 0
    for p in paras:
        cur.append(p)
        cur_w += _wc(p)
        if cur_w >= per and len(blocks) < target - 1:
            blocks.append({"title": None, "text": "\n\n".join(cur)})
            cur, cur_w = [], 0
    if cur:
        blocks.append({"title": None, "text": "\n\n".join(cur)})
    return blocks


def _detect_twist(sents):
    if not sents:
        return ""
    best = None
    for i, s in enumerate(sents):
        low = s.lower()
        if any(c in low for c in TWIST_CUES):
            if best is None or i > best[0]:
                best = (i, s)
    if best:
        return _trim(best[1], 90)
    return _trim(sents[-1], 90)


def _make_title(hint, sents, index):
    if hint:
        t = hint
    elif sents:
        t = sents[0]
    else:
        t = f"Chapter {index}"
    return _trim(t, MAX_TITLE)


def _build_chapter(index, title_hint, text, wpm):
    sents = _sentences(text)
    wc = _wc(text)
    dur = round(wc / max(1.0, wpm) * 60.0, 1)
    hook = _trim(sents[0], 90) if sents else ""
    twist = _detect_twist(sents)
    summary = _trim(sents[0] if sents else text, MAX_SUMMARY)
    title = _make_title(title_hint, sents, index)
    return {
        "index": index,
        "title": title,
        "hook": hook,
        "twist": twist,
        "duration_est_s": dur,
        "summary_1_sentence": summary,
        "word_count": wc,
        "text": text,
    }


def split_chapters(story_text: str, target_chapters=None, wpm=None, **kwargs) -> dict:
    text = (story_text or "").strip()
    wpm = float(wpm or NARRATION_WPM)
    if not text:
        return {"n_chapters": 0, "total_duration_s": 0.0, "wpm": wpm, "chapters": []}
    blocks = _detect_marker_blocks(text)
    split_mode = "markers"
    if not blocks:
        tgt = target_chapters or (DEFAULT_TARGET or _auto_target(text))
        blocks = _split_by_target(text, max(1, int(tgt)))
        split_mode = "auto"
    chapters = [_build_chapter(i + 1, b["title"], b["text"], wpm)
                for i, b in enumerate(blocks)]
    total = round(sum(c["duration_est_s"] for c in chapters), 1)
    return {
        "n_chapters": len(chapters),
        "total_duration_s": total,
        "wpm": wpm,
        "split_mode": split_mode,
        "chapters": chapters,
    }
