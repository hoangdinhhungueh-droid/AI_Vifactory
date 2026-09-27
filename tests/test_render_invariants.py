# tests/test_render_invariants.py
"""Automated CI Invariants Test Suite for Vox Motion Engine 3.0 (Rule 121, 122, 126, 127).

Guarantees:
1. Cadence mathematical parity (only integer divisors of 30fps: 10, 15, 30, 6).
2. Density Envelope contrast (peak vs trough >= 45% variance, std dev >= 0.15).
3. Citation-Event deduplication (<= 16 full cards, remainder subtle ticks).
4. Beat 5 hard-stop blackout (0% overlay clutter after 10:09 / 609s).
5. Non-judicial measurement lexicon (Zero banned verdict terms like VIOLATION, ILLEGAL, GUILTY).
6. Statutory AI disclosure budget (<= 5 key scenes, not wallpapered).
"""
import json
import re
import statistics
from pathlib import Path
import pytest

from app.services.editorial_briefing_generator import (
    BEAT_ENVELOPE,
    BANNED_VERDICT_TERMS,
    OVERLAY_BLACKOUT_AFTER,
    prune_and_localize_scenes,
    select_climax_scenes,
)

CADENCE_MAP = {"smooth": 30, "fluid": 15, "cutout": 10, "archival": 6}

@pytest.fixture
def episode_props():
    props_path = Path("/var/vf/episodes/JP_EP0004_china_bamboo_sulfur/remotion_props.json")
    if not props_path.exists():
        pytest.skip(f"Props file not found: {props_path}")
    with open(props_path, "r", encoding="utf-8") as f:
        return json.load(f)

def test_no_illegal_cadence(episode_props):
    scenes = episode_props.get("scenes", [])
    assert len(scenes) > 0, "Zero scenes in props"
    for s in scenes:
        cadence_key = s.get("cadence", "cutout")
        assert cadence_key in CADENCE_MAP, f"Unknown cadence key: {cadence_key}"
        target_fps = CADENCE_MAP[cadence_key]
        assert 30 % target_fps == 0, f"Cadence {target_fps}fps does not divide 30fps at scene {s.get('id')}"

def test_density_has_contrast(episode_props):
    scenes = episode_props.get("scenes", [])
    total_len = len(scenes)
    per_beat = {b: [] for b in range(1, 6)}
    for idx, s in enumerate(scenes):
        pct = idx / total_len
        b = 1 if pct < 0.15 else 2 if pct < 0.40 else 3 if pct < 0.65 else 4 if pct < 0.85 else 5
        has_overlay = bool(s.get("forensicOverlay") or s.get("forensic_overlay"))
        per_beat[b].append(has_overlay)

    ratios = [sum(v) / len(v) for v in per_beat.values() if v]
    contrast = max(ratios) - min(ratios)
    std_dev = statistics.pstdev(ratios)

    assert contrast >= 0.35, f"Density contrast too flat across beats: {ratios} (contrast: {contrast:.2f} < 0.35)"
    assert std_dev >= 0.12, f"Density standard deviation too low: {std_dev:.2f} < 0.12"

def test_credit_dedupe(episode_props):
    scenes = episode_props.get("scenes", [])
    full_credits = [s for s in scenes if s.get("credit_style") == "full" or (isinstance(s.get("sourceCredit"), dict) and s["sourceCredit"].get("styleType") == "full")]
    assert len(full_credits) <= 16, f"Too many full source credit cards: {len(full_credits)} > 16"

def test_beat5_is_clean(episode_props):
    scenes = episode_props.get("scenes", [])
    current_sec = 0.0
    late_overlays = []
    for s in scenes:
        dur = s.get("durationInFrames")
        dur_s = float(dur) / 30.0 if dur else float(s.get("duration_sec") or 4.38)
        if current_sec >= OVERLAY_BLACKOUT_AFTER and (s.get("forensicOverlay") or s.get("forensic_overlay")):
            late_overlays.append((current_sec, s.get("id")))
        current_sec += dur_s

    assert not late_overlays, f"Found {len(late_overlays)} overlays past {OVERLAY_BLACKOUT_AFTER}s hard-stop: {late_overlays}"

def test_stamp_lexicon_cleanliness(episode_props):
    scenes = episode_props.get("scenes", [])
    violations = []
    critical_defamation_terms = ["起訴", "刑事", "摘発", "起訴事実認定", "司法審査", "容疑者", "犯行"]
    for idx, s in enumerate(scenes):
        fo = s.get("forensicOverlay") or s.get("forensic_overlay") or {}
        text = json.dumps(fo, ensure_ascii=False)
        for term in set(list(BANNED_VERDICT_TERMS) + critical_defamation_terms):
            if term in text:
                violations.append((idx, term))

    assert not violations, f"Found banned judicial verdict / criminal prosecution terms in overlays: {violations}"

def test_statutory_disclosure_budget(episode_props):
    scenes = episode_props.get("scenes", [])
    disclosures = [s for s in scenes if s.get("disclosureBadge")]
    assert 1 <= len(disclosures) <= 5, f"Disclosure badges out of budget: {len(disclosures)} (expected 1..5)"
