import os
import json
import pytest
from PIL import Image
from scripts.render_twolayer_visual import calculate_dynamic_timeout, optimize_props_assets
from app.services.build_remotion_props import stage_into_public


def test_calculate_dynamic_timeout_underflow(tmp_path):
    props_file = tmp_path / "props_short.json"
    props_file.write_text(json.dumps({"durationInFrames": 1500}), encoding="utf-8")
    timeout, frames = calculate_dynamic_timeout(str(props_file), base_timeout=7200.0)
    assert frames == 1500
    # Minimum timeout floor is 36000.0s (10 hours, Rule 134)
    assert timeout == 36000.0


def test_calculate_dynamic_timeout_long_episode(tmp_path):
    props_file = tmp_path / "props_long.json"
    props_file.write_text(json.dumps({"durationInFrames": 18000}), encoding="utf-8")
    timeout, frames = calculate_dynamic_timeout(str(props_file), base_timeout=7200.0)
    assert frames == 18000
    # 18000 * 2.0 + 7200.0 = 43200.0s (12 hours, Rule 134)
    assert timeout == 43200.0


def test_stage_into_public_prescales_large_image(tmp_path):
    public_dir = tmp_path / "remotion_public"
    public_dir.mkdir()
    
    # Create 2560x1440 RGBA image
    src_img = tmp_path / "bg_2k.png"
    img = Image.new("RGBA", (2560, 1440), (20, 30, 40, 255))
    img.save(str(src_img))

    staged_rel = stage_into_public(str(src_img), str(public_dir), "TEST_EP")
    assert staged_rel == "pulled/TEST_EP/bg_2k.png"

    dest_file = public_dir / staged_rel
    assert dest_file.exists()
    
    # Verify image was pre-scaled to 1920x1080
    with Image.open(str(dest_file)) as staged_im:
        assert staged_im.size == (1920, 1080)
        assert staged_im.mode == "RGBA"


def test_stage_into_public_preserves_small_image(tmp_path):
    public_dir = tmp_path / "remotion_public"
    public_dir.mkdir()

    # Create 1280x720 RGBA image
    src_img = tmp_path / "small.png"
    img = Image.new("RGBA", (1280, 720), (10, 20, 30, 255))
    img.save(str(src_img))

    staged_rel = stage_into_public(str(src_img), str(public_dir), "TEST_EP")
    dest_file = public_dir / staged_rel

    with Image.open(str(dest_file)) as staged_im:
        assert staged_im.size == (1280, 720)


def test_optimize_props_assets_scan(tmp_path):
    remotion_dir = tmp_path / "remotion"
    pub_dir = remotion_dir / "public" / "pulled" / "TEST_EP"
    pub_dir.mkdir(parents=True)

    test_img = pub_dir / "oversized.png"
    im = Image.new("RGBA", (2560, 1440), (50, 60, 70, 255))
    im.save(str(test_img))

    props_file = tmp_path / "props.json"
    props_data = {
        "durationInFrames": 300,
        "scenes": [
            {"background": "pulled/TEST_EP/oversized.png", "foreground": None}
        ]
    }
    props_file.write_text(json.dumps(props_data), encoding="utf-8")

    optimize_props_assets(str(props_file), str(remotion_dir))

    with Image.open(str(test_img)) as res_im:
        assert res_im.size == (1920, 1080)


def test_get_beat_chunks_vox_beat_index(tmp_path):
    from scripts.render_twolayer_chunks import get_beat_chunks_from_props
    props_file = tmp_path / "vox_props.json"
    props_data = {
        "scenes": [
            {"id": "s1", "beat_index": 1, "durationInFrames": 100},
            {"id": "s2", "beat_index": 1, "durationInFrames": 120},
            {"id": "s3", "beat_index": 2, "durationInFrames": 150},
            {"id": "s4", "beat_index": 3, "durationInFrames": 130},
        ]
    }
    props_file.write_text(json.dumps(props_data), encoding="utf-8")
    chunks = get_beat_chunks_from_props(str(props_file))
    assert len(chunks) == 3
    assert chunks[0]["name"] == "BEAT 1"
    assert chunks[0]["start_frame"] == 0
    assert chunks[0]["end_frame"] == 219
    assert chunks[1]["name"] == "BEAT 2"
    assert chunks[1]["start_frame"] == 220
    assert chunks[1]["end_frame"] == 369
    assert chunks[2]["name"] == "BEAT 3"
    assert chunks[2]["start_frame"] == 370
    assert chunks[2]["end_frame"] == 499

