import sys
sys.path.insert(0, "/root/video_factory")

import pytest

from app.services.mpt_ported.subtitle_karaoke import (
    _merge_over_cap,
    resplit_for_cps,
    segments_to_karaoke_ass,
    _karaoke_text,
)


def _w(start, end, word):
    return {"start_ms": start, "end_ms": end, "word": word}


def _all_words(cues):
    out = []
    for c in cues:
        out.extend(c.get("words") or [])
    return out


def test_merge_over_cap_preserves_words_when_merging_next():
    # chunk0 is a lone over-cap singleton; merging with the next cue stays
    # under cap, so _merge_over_cap folds them. The merged cue must keep BOTH
    # words so the final karaoke can still highlight per word.
    chunks = [
        {"start_ms": 0, "end_ms": 200, "text": "fastword",
         "words": [_w(0, 200, "fastword")]},
        {"start_ms": 200, "end_ms": 2000, "text": "slow",
         "words": [_w(200, 2000, "slow")]},
    ]
    out = _merge_over_cap(chunks, cap=20.0)
    assert len(out) == 1
    words = out[0].get("words") or []
    assert [w["word"] for w in words] == ["fastword", "slow"]


def test_merge_over_cap_preserves_words_when_merging_prev():
    # Over-cap cue is LAST -> no next neighbour, so the merge-prev branch fires.
    chunks = [
        {"start_ms": 0, "end_ms": 1000, "text": "okay fine",
         "words": [_w(0, 500, "okay"), _w(500, 1000, "fine")]},
        {"start_ms": 1000, "end_ms": 1050, "text": "zip",
         "words": [_w(1000, 1050, "zip")]},
    ]
    out = _merge_over_cap(chunks, cap=20.0)
    assert len(out) == 1
    words = out[0].get("words") or []
    assert [w["word"] for w in words] == ["okay", "fine", "zip"]


def test_resplit_preserves_all_words_end_to_end():
    # A single dense segment with real word timings that must be split for CPS.
    # No word may be dropped or lose its timing across the whole resplit chain.
    words = [_w(i * 100, i * 100 + 100, "abc") for i in range(10)]
    seg = {"start_ms": 0, "end_ms": 1000,
           "text": " ".join(w["word"] for w in words), "words": words}
    out = resplit_for_cps([seg], cps_cap=20.0)
    got = _all_words(out)
    assert len(got) == 10
    assert [w["word"] for w in got] == ["abc"] * 10
    for c in out:
        if (c.get("text") or "").strip():
            assert c.get("words"), c


def test_final_ass_contains_word_level_karaoke_tags():
    # Regression guard: the FINAL burned ASS must contain \kf word tags,
    # proving karaoke rides real word timestamps, not plain text.
    words = [_w(i * 100, i * 100 + 100, "abc") for i in range(10)]
    seg = {"start_ms": 0, "end_ms": 1000,
           "text": " ".join(w["word"] for w in words), "words": words}
    cues = resplit_for_cps([seg], cps_cap=20.0)
    ass = segments_to_karaoke_ass(cues, aspect="16:9", lang_code="en")
    assert "\\kf" in ass


def test_karaoke_text_falls_back_to_plain_without_words():
    # Groq / proportional backends carry no word timings -> graceful plain
    # text, never a crash and never an empty line.
    seg = {"start_ms": 0, "end_ms": 1000, "text": "hello world"}
    txt = _karaoke_text(seg)
    assert "\\kf" not in txt
    assert "hello world" in txt
