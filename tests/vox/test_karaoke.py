#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/vox/test_karaoke.py — Tests for ASS Karaoke Generator and Timing Parity (AVF-VOX-001)."""

import pytest
from vox.schemas import Word, WordTimeline
from vox.karaoke import generate_ass_subtitles, parse_words_from_ass


def test_ass_karaoke_generation_and_reverse_timing_parity(tmp_path):
    words = [
        Word(text="Global", start=0.00, end=0.35, scene_idx=1),
        Word(text="liquidity", start=0.35, end=0.85, scene_idx=1),
        Word(text="shock", start=0.85, end=1.20, scene_idx=1),
        Word(text="triggered", start=1.20, end=1.65, scene_idx=1),
        Word(text="an", start=1.65, end=1.85, scene_idx=1),
        Word(text="unprecedented", start=1.85, end=2.50, scene_idx=1),
        Word(text="cascade.", start=2.50, end=3.00, scene_idx=1),
    ]
    tl = WordTimeline(words=words, audio_duration=3.10, match_ratio=1.0)

    ass_path = tmp_path / "test.ass"
    generate_ass_subtitles(tl, ass_path)
    assert ass_path.exists()

    # Reverse parse and verify timing drift <= 10ms (centisecond precision)
    reconstructed = parse_words_from_ass(ass_path)
    assert len(reconstructed) == len(words)

    for orig, parsed in zip(words, reconstructed):
        # Strip punctuation for textual comparison
        orig_clean = orig.text.strip(".,!?:;\"'()[]{}")
        parsed_clean = parsed["text"].strip(".,!?:;\"'()[]{}")
        assert orig_clean == parsed_clean

        # Timing difference must be <= 0.015s (1.5 cs)
        drift_start = abs(orig.start - parsed["start"])
        assert drift_start <= 0.02, f"Word {orig.text} start drift {drift_start:.3f}s exceeds 20ms"
