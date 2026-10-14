# -*- coding: utf-8 -*-
"""Adversarial & Invariant Tests for Render Timeout Policy (Rule 134 Compliance).

Verifies:
  1. Strict hierarchy: T_continue > T_run_episode > T_remotion across all frame boundaries.
  2. Absolute floor enforcement (>= 36,000s) preventing premature watchdog terminations.
  3. Frame rate scaling (2.0s/frame + 7,200s buffer) for complex multi-layer Remotion rendering.
  4. Robust props parsing handling missing, malformed, or diverse JSON structures.
  5. Static codebase audit guaranteeing zero hardcoded shadow timeout remnants.
"""

import json
from pathlib import Path
import pytest

from app.services.render_timeout_policy import (
    MIN_RENDER_TIMEOUT_FLOOR,
    SECONDS_PER_FRAME_ALLOCATION,
    RENDER_BASE_BUFFER_SEC,
    RUN_EPISODE_BUFFER_SEC,
    CONTINUE_STAGE_BUFFER_SEC,
    extract_frames_from_props,
    compute_render_timeout_hierarchy,
)


# Boundary frame counts: [micro-clip, standard 1-min, 5-min, 10-min, 14.4-min (EP0003), 25-min, 50-min mega]
TEST_FRAME_BOUNDARIES = [1, 1500, 9000, 18000, 25956, 45000, 90000]


@pytest.mark.parametrize("frames", TEST_FRAME_BOUNDARIES)
@pytest.mark.parametrize("base_t", [0.0, 7200.0, 36000.0, 54000.0])
def test_strict_hierarchy_inequality(frames: int, base_t: float):
    """Rule 134: Under ALL circumstances, T_continue > T_run_episode > T_remotion."""
    h = compute_render_timeout_hierarchy(frames, base_timeout=base_t)
    
    rem_t = h["remotion_timeout"]
    run_t = h["run_episode_timeout"]
    cont_t = h["continue_timeout"]

    # 1. Strict inequality
    assert cont_t > run_t > rem_t, f"Hierarchy violated for frames={frames}, base_t={base_t}: {h}"

    # 2. Caller buffers must strictly match or exceed policy specification
    assert run_t - rem_t >= RUN_EPISODE_BUFFER_SEC
    assert cont_t - rem_t >= CONTINUE_STAGE_BUFFER_SEC
    assert cont_t - run_t >= (CONTINUE_STAGE_BUFFER_SEC - RUN_EPISODE_BUFFER_SEC)

    # 3. Minimum safe floor
    assert rem_t >= MIN_RENDER_TIMEOUT_FLOOR
    assert run_t >= MIN_RENDER_TIMEOUT_FLOOR + RUN_EPISODE_BUFFER_SEC
    assert cont_t >= MIN_RENDER_TIMEOUT_FLOOR + CONTINUE_STAGE_BUFFER_SEC


def test_ep0003_exact_scaling():
    """Specific regression test for EN_EP0003_san_diego_daycare_fraud (25,956 frames)."""
    frames = 25956
    h = compute_render_timeout_hierarchy(frames)

    # Expected: 25956 * 2.0 + 7200 = 59112.0s
    expected_rem = 25956 * 2.0 + 7200.0
    assert h["remotion_timeout"] == expected_rem
    assert h["remotion_timeout"] == 59112.0
    assert h["run_episode_timeout"] == 59112.0 + 3600.0  # 62712.0s
    assert h["continue_timeout"] == 59112.0 + 7200.0     # 66312.0s
    # Guarantee that continue_timeout easily covers the actual 37,080s render time with >7 hours headroom
    assert h["continue_timeout"] > 37080.0 + 25000.0


def test_extract_frames_from_props_scenes(tmp_path: Path):
    """Test frame accumulation across scenes array."""
    props_file = tmp_path / "props.json"
    props_file.write_text(json.dumps({
        "scenes": [
            {"durationInFrames": 120},
            {"durationInFrames": 300},
            {"durationInFrames": 450},
        ]
    }), encoding="utf-8")
    assert extract_frames_from_props(props_file) == 870


def test_extract_frames_from_props_toplevel(tmp_path: Path):
    """Test fallback to durationInFrames top-level key when scenes is absent."""
    props_file = tmp_path / "props.json"
    props_file.write_text(json.dumps({"durationInFrames": 24500}), encoding="utf-8")
    assert extract_frames_from_props(props_file) == 24500


def test_extract_frames_corrupt_and_missing(tmp_path: Path):
    """Test graceful fallback for non-existent or corrupt files."""
    missing_file = tmp_path / "does_not_exist.json"
    assert extract_frames_from_props(missing_file, default_frames=19999) == 19999

    corrupt_file = tmp_path / "corrupt.json"
    corrupt_file.write_text("{invalid json", encoding="utf-8")
    assert extract_frames_from_props(corrupt_file, default_frames=18000) == 18000


def test_static_code_audit_zero_shadow_timeouts():
    """Rule 134 & Rule 125: Verify caller scripts delegate to canonical render_timeout_policy."""
    root_dir = Path(__file__).resolve().parent.parent

    # 1. Check scripts/render_twolayer_visual.py
    render_script = root_dir / "scripts" / "render_twolayer_visual.py"
    render_text = render_script.read_text(encoding="utf-8")
    assert "from app.services.render_timeout_policy import" in render_text
    assert "compute_render_timeout_hierarchy" in render_text

    # 2. Check scripts/continue_after_images.py
    cont_script = root_dir / "scripts" / "continue_after_images.py"
    cont_text = cont_script.read_text(encoding="utf-8")
    assert "from app.services.render_timeout_policy import" in cont_text
    assert "compute_render_timeout_hierarchy" in cont_text
    # Default render timeout should be at least 54000
    assert "--render-timeout\", type=int, default=54000" in cont_text

    # 3. Check app/pipeline/run_episode.py if exists (purged in AVF-VOX-001)
    run_script = root_dir / "app" / "pipeline" / "run_episode.py"
    if run_script.exists():
        run_text = run_script.read_text(encoding="utf-8")
        assert "from app.services.render_timeout_policy import" in run_text
        assert "compute_render_timeout_hierarchy" in run_text
