"""
Test suite for B3.5 -> B4 Bridge, Thumbnail Synthesis, and B5 Forensic Audit.
Enforces Rule 118 (Zero-Mock Data), Rule 122 (Visual Audit Gate), Rule 125 (Single Truth), and Rule 128 (Zero Semantic Bias).
"""
import os
import json
import pytest
from unittest.mock import MagicMock, patch

from app.services.prompt_forge import (
    _sanitize_thumbnail_prompt,
    _synthesize_thumbnail_prompts,
    generate_scene_prompts
)
from scripts.gemini_browser_gen import (
    audit_single_image,
    create_images_ready_marker
)


def test_sanitize_thumbnail_prompt():
    """Kiểm tra sanitize thumbnail prompt đảm bảo tỷ lệ 16:9, độ phân giải 2560x1440 2K DCI và safe-zone."""
    raw = "Cinematic dramatic portrait of an ancient warrior looking at a burning temple."
    sanitized = _sanitize_thumbnail_prompt(raw, "thumbnail_a")
    
    assert "2560x1440" in sanitized
    assert "16:9" in sanitized
    assert "typography" in sanitized.lower()
    assert "ancient warrior" in sanitized
    # Cấm lặp trùng technical instruction
    assert sanitized.count("2560x1440") == 1


def test_synthesize_thumbnail_prompts_generic():
    """Kiểm tra sinh Thumbnail A/B từ SEO package tổng quát (Rule 128 - Zero Semantic Bias)."""
    seo_package = {
        "title_a": "Why Rome Fell In 24 Hours",
        "title_b": "The Shocking Secret That Broke An Empire",
        "hook_3s": "Nobody saw the betrayal coming until it was too late.",
        "specific_viral_angle": "Focus on the silent economic collapse before the invasion",
        "key_characters": ["Emperor Aurelius", "General Marcus"]
    }
    
    result = _synthesize_thumbnail_prompts("Why Rome Fell In 24 Hours", seo_data=seo_package)
    
    assert "thumbnail_a" in result
    assert "thumbnail_b" in result
    assert "2560x1440" in result["thumbnail_a"]
    assert "2560x1440" in result["thumbnail_b"]
    assert "Rome" in result["thumbnail_a"] or "economic collapse" in result["thumbnail_a"]


def test_generate_scene_prompts_includes_thumbnails():
    """Kiểm tra generate_scene_prompts tự động nạp và sinh trường thumbnails."""
    bg_dict = {"bg_1": "Sunset over a desolate wasteland"}
    fg_dict = {"fg_1": "A lone traveler with a walking staff"}
    story_title = "The Last Journey Across The Border"
    
    with patch("app.services.prompt_forge.call_gpt6_astra") as mock_astra:
        mock_astra.return_value = json.dumps({
            "backgrounds": {"bg_1": "Detailed prompt for bg_1 with 16:9 2560x1440"},
            "foregrounds": {"fg_1": "Detailed prompt for fg_1 with #FF00FF"}
        })
        res = generate_scene_prompts(
            bg_dict=bg_dict,
            fg_dict=fg_dict,
            story_title=story_title
        )
    
    assert "thumbnails" in res
    assert "thumbnail_a" in res["thumbnails"]
    assert "thumbnail_b" in res["thumbnails"]
    assert "bg_1" in res["backgrounds"]


def test_b5_audit_single_image_metrics(tmp_path):
    """Kiểm tra B5 audit tính toán metric vật lý thật, không dùng mock score 98 (Rule 118 & 122)."""
    try:
        from PIL import Image
    except ImportError:
        pytest.skip("PIL not available in environment")
        
    # Tạo ảnh test background 2560x1440
    bg_path = tmp_path / "test_bg.png"
    img = Image.new("RGB", (2560, 1440), color=(100, 150, 200))
    img.save(bg_path, format="PNG")
    
    is_pass, metrics = audit_single_image(str(bg_path), "Background")
    assert is_pass is True
    assert metrics["dimensions"] == "2560x1440"
    assert metrics["format"] == "PNG"
    assert metrics["dim_pass"] is True
    assert metrics["black_pixel_pct"] == 0.0
    assert "mock" not in str(metrics).lower()
    
    # Tạo ảnh foreground có kênh Alpha
    fg_path = tmp_path / "test_fg.png"
    fg_img = Image.new("RGBA", (2048, 2048), color=(0, 0, 0, 0))
    # Vẽ 1 vùng opaque (50% diện tích)
    for x in range(1024):
        for y in range(2048):
            fg_img.putpixel((x, y), (200, 50, 50, 255))
    fg_img.save(fg_path, format="PNG")
    
    is_pass_fg, metrics_fg = audit_single_image(str(fg_path), "Foreground")
    assert is_pass_fg is True
    assert metrics_fg["transparency_pct"] is not None
    assert 40.0 <= metrics_fg["transparency_pct"] <= 60.0
    assert metrics_fg["magenta_leak_pct"] == 0.0


def test_images_ready_marker_generation():
    """Kiểm tra tạo khế ước marker images_ready.json cho watcher."""
    mock_client = MagicMock()
    with patch("scripts.gemini_browser_gen.client", mock_client):
        create_images_ready_marker("TEST_EP001", total_count=10, pass_count=10)
        
        mock_client.call_tool.assert_called_once()
        call_args = mock_client.call_tool.call_args[0]
        assert call_args[0] == "write_file"
        payload = call_args[1]
        assert payload["path"] == "/var/vf/episodes/TEST_EP001/images_ready.json"
        marker_data = json.loads(payload["content"])
        assert marker_data["episode_id"] == "TEST_EP001"
        assert marker_data["approved_count"] == 10
        assert marker_data["status"] == "ready_for_render"
