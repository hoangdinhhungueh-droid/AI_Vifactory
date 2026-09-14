# tests/test_beat_bgm_engine.py
"""Unit tests for Beat-Adaptive BGM Engine (beat_bgm_engine.py)."""
import os
import sys
import json
import shutil
import pytest
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(REPO_ROOT))

from app.services.beat_bgm_engine import (
    load_bgm_catalog,
    get_beat_durations,
    select_5_beat_tracks,
    generate_beat_adaptive_bgm,
    _probe_duration,
    CATALOG_PATH
)


def test_catalog_integrity():
    """Verify catalog covers all 5 beats with valid licensing metadata."""
    catalog = load_bgm_catalog()
    assert len(catalog) >= 5, f"Expected at least 5 tracks, got {len(catalog)}"
    
    beats_present = set(t["beat_index"] for t in catalog)
    assert beats_present == {1, 2, 3, 4, 5}, f"Missing beats in catalog: {beats_present}"
    
    for t in catalog:
        assert t.get("license"), f"Missing license for track: {t.get('title')}"
        assert t.get("beat_index") in (1, 2, 3, 4, 5)
        # If physical audio files are installed on disk, verify their existence
        if os.path.exists(t.get("file_path", "")):
            assert t["duration_s"] > 5.0, f"Track duration too short: {t['duration_s']}s"


def test_select_5_beat_tracks():
    """Verify selection deterministically produces 5 tracks for beats 1..5."""
    tracks_a = select_5_beat_tracks("EN_EP0001_test_topic")
    tracks_b = select_5_beat_tracks("EN_EP0001_test_topic")
    tracks_c = select_5_beat_tracks("KR_EP0002_other_topic")
    
    assert len(tracks_a) == 5
    for idx, t in enumerate(tracks_a, start=1):
        assert t["beat_index"] == idx
    
    # Determinism check
    assert [t["track_id"] for t in tracks_a] == [t["track_id"] for t in tracks_b]
    assert len(tracks_c) == 5


def test_get_beat_durations_fallback():
    """Verify fallback duration partitioning for standard 5-Act ratios."""
    durs = get_beat_durations("NON_EXISTENT_EP", out_dir="/tmp/non_existent_dir", total_dur=500.0)
    assert len(durs) == 5
    assert sum(durs) == pytest.approx(500.0, rel=1e-3)
    assert durs[0] == pytest.approx(75.0, rel=1e-3)   # 15%
    assert durs[1] == pytest.approx(125.0, rel=1e-3)  # 25%
    assert durs[2] == pytest.approx(125.0, rel=1e-3)  # 25%
    assert durs[3] == pytest.approx(100.0, rel=1e-3)  # 20%
    assert durs[4] == pytest.approx(75.0, rel=1e-3)   # 15%


@pytest.mark.integration
def test_generate_beat_adaptive_bgm_smoke():
    """Integration test generating a test adaptive BGM output with crossfade (requires ffmpeg)."""
    if shutil.which("ffmpeg") is None:
        pytest.skip("ffmpeg not installed in this environment")
        
    test_out_dir = "/tmp/test_bgm_run"
    os.makedirs(test_out_dir, exist_ok=True)
    
    dummy_audio = f"{test_out_dir}/audio_norm.mp3"
    import subprocess
    subprocess.run(
        f"ffmpeg -y -f lavfi -i anullsrc=r=24000:cl=mono -t 20.0 -q:a 9 -acodec libmp3lame '{dummy_audio}'",
        shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
    )
    
    try:
        res = generate_beat_adaptive_bgm(
            episode_id="TEST_EP0001_bgm_smoke",
            out_dir=test_out_dir,
            audio_path=dummy_audio,
            crossfade_s=1.0,
            force=True
        )
        
        assert os.path.exists(res["bgm_path"])
        assert os.path.getsize(res["bgm_path"]) > 10000
        assert len(res["tracks"]) == 5
        assert "Music Credits:" in res["attribution_text"]
        
        dur = _probe_duration(res["bgm_path"])
        assert dur == pytest.approx(20.0, abs=1.5)
    finally:
        # Cleanup
        try:
            if os.path.exists(dummy_audio):
                os.remove(dummy_audio)
            if os.path.exists(f"{test_out_dir}/bgm_master.mp3"):
                os.remove(f"{test_out_dir}/bgm_master.mp3")
        except Exception:
            pass
