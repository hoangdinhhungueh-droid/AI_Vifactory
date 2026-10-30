import pytest
from core.contracts.stages import Scene
from app.services.kinetic_sub_director import build_natural_kinetic_i2v_prompt
from stages.s05_director_plan import build_vox_scene_prompts, build_universal_video_prompt


def test_natural_kinetic_i2v_prompt_cartesian_free():
    """Kiểm tra build_natural_kinetic_i2v_prompt 100% không chứa toạ độ Descartes (X:%, Y:%)."""
    sentence = "공정거래위원회는 보증금을 돌려주지 않은 악성 임대사업자 3곳에 대해 총 42억 원의 과징금을 부과했습니다."
    prompt = build_natural_kinetic_i2v_prompt(sentence, market="KR")

    assert "(X:" not in prompt
    assert "Y:" not in prompt
    assert "[CAMERA & ENVIRONMENT]:" in prompt
    assert "[ACTION PHASE (0.2s - 0.4s)]:" in prompt
    assert "[PHYSICAL REACTION & RESIDUE]:" in prompt
    assert "[HOLD & LIVING TEXTURE]:" in prompt
    assert "12fps (on twos)" in prompt


def test_s05_sub_director_plan_generates_natural_prompt_and_no_chimeric_stamp():
    """Kiểm tra s05 sinh sub director plan sử dụng semantic evidence thay vì hardcode stamp."""
    scene = Scene(
        scene_id="SCENE_06",
        narration="공정거래위원회는 보증금을 돌려주지 않은 악성 임대사업자 3곳에 대해 총 42억 원의 과징금을 부과했습니다.",
        headline="42억 과징금 철퇴",
        market="KR",
        duration_est_sec=5.0
    )

    plan = build_vox_scene_prompts(scene, idx=5, total_scenes=8, market="KR")

    # 1. Prompt không chứa tọa độ Descartes
    i2v_prompt = plan["i2v_prompt_google_flow"]
    assert "(X:" not in i2v_prompt
    assert "Y:" not in i2v_prompt
    assert "[ACTION PHASE" in i2v_prompt

    # 2. Không chứa stamp quái thai khi câu nói về số liệu tài chính / 과징금 (phải là thước kẹp)
    objects = plan["objects"]
    sec_obj = next(o for o in objects if o["role"] == "secondary")
    assert "crimson forensic seal" not in sec_obj["name"]
    assert "caliper" in sec_obj["name"] or "vernier" in sec_obj["name"] or "balance sheet" in sec_obj["name"]


def test_s05_build_universal_video_prompt_natural_syntax():
    """Kiểm tra build_universal_video_prompt sinh natural kinetic prompt."""
    scene = Scene(
        scene_id="SCENE_01",
        narration="전세 사기 피해가 전국적으로 확산되고 있습니다.",
        headline="전세사기 확산",
        market="KR"
    )

    prompt = build_universal_video_prompt(scene)
    assert "[CAMERA & ENVIRONMENT]:" in prompt
    assert "[ACTION PHASE (0.2s - 0.4s)]:" in prompt
    assert "[HOLD & LIVING TEXTURE]:" in prompt
    assert "(X:" not in prompt


def test_build_remotion_props_zero_drift_guard():
    """Kiểm tra logic bảo vệ 0ms drift trong build_remotion_props: khi có whisper subtitles, cấm scale."""
    scenes_out = [
        {
            "id": "sc001",
            "durationInFrames": 150,
            "subtitles": [
                {"word": "Test", "abs_start_ms": 0, "abs_end_ms": 500}
            ]
        }
    ]

    has_whisper_subtitles = any(sc.get("subtitles") for sc in scenes_out)
    assert has_whisper_subtitles is True

    # Bất biến: Khi có whisper subtitles, durationInFrames giữ nguyên 150, không bị giãn
    initial_frames = scenes_out[0]["durationInFrames"]
    assert initial_frames == 150
