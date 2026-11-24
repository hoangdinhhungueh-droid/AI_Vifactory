#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/unit/test_s10_render.py — Fail-closed unit tests for Stage S10 (Boss Item 3)."""

import json
from pathlib import Path

import pytest

from core.config import RunContext, load_profile
from core.contracts.stages import StageID
from core.paths import resolve_run_paths
from core.run_manifest import RunManifest
from stages.s10_render import MissingClipsError
from stages.s10_render import run as run_s10_render


def test_s10_render_fails_closed_on_partial_clip_loss(tmp_path: Path) -> None:
    """Verifies that if ANY declared S8 clip is missing, S10 raises MissingClipsError listing offending indices."""
    run_id = "test_s10_partial_loss"
    paths = resolve_run_paths(run_id, repo_root=tmp_path)
    paths.final_render_dir.mkdir(parents=True, exist_ok=True)

    # Valid clip 0 and 2, but missing clip 1
    clip0 = tmp_path / "clip0.mp4"
    clip0.write_bytes(b"A" * 200)
    clip1_missing = tmp_path / "clip1_missing.mp4"
    clip2 = tmp_path / "clip2.mp4"
    clip2.write_bytes(b"B" * 200)

    s8_artifact = {
        "run_id": run_id,
        "stage": StageID.S8_VIDEO_GEN.value,
        "status": "ok",
        "payload": {
            "clips": [
                {"scene_id": "SCENE_01", "file_path": str(clip0), "duration_sec": 2.0},
                {"scene_id": "SCENE_02", "file_path": str(clip1_missing), "duration_sec": 2.0},
                {"scene_id": "SCENE_03", "file_path": str(clip2), "duration_sec": 2.0},
            ]
        },
        "provenance": {"generator": "stages.s8_video_gen"},
    }
    s8_file = paths.artifact_file(StageID.S8_VIDEO_GEN.value)
    s8_file.parent.mkdir(parents=True, exist_ok=True)
    s8_file.write_text(json.dumps(s8_artifact), encoding="utf-8")

    audio_file = tmp_path / "narration.wav"
    audio_file.write_bytes(b"C" * 500)
    sub_file = tmp_path / "custom_subtitles.ass"
    sub_file.write_text("[Script Info]\nTitle: Test", encoding="utf-8")

    s9_artifact = {
        "run_id": run_id,
        "stage": StageID.S9_VOICE_TTS.value,
        "status": "ok",
        "payload": {
            "audio_file": str(audio_file),
            "subtitles_file": str(sub_file),
            "subtitles": []
        },
        "provenance": {"generator": "stages.s9_voice_tts"},
    }
    s9_file = paths.artifact_file(StageID.S9_VOICE_TTS.value)
    s9_file.parent.mkdir(parents=True, exist_ok=True)
    s9_file.write_text(json.dumps(s9_artifact), encoding="utf-8")

    cfg = load_profile("e2e_min")
    manifest = RunManifest.create_new(run_id, profile="e2e_min")
    ctx = RunContext(
        run_id=run_id,
        paths=paths,
        manifest=manifest,
        config=cfg,
        force=True,
        dry_run=False,
    )

    with pytest.raises(MissingClipsError, match="Found 1 invalid clip\\(s\\) at index/indices \\[1\\]"):
        run_s10_render(ctx)


def test_s10_render_reverifies_stale_mp4(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that existing final.mp4 < 1000B is considered corrupt/stale and triggers assembly."""
    run_id = "test_s10_stale_mp4"
    paths = resolve_run_paths(run_id, repo_root=tmp_path)
    paths.final_render_dir.mkdir(parents=True, exist_ok=True)

    # Corrupt tiny MP4 (50 bytes)
    stale_mp4 = paths.final_render_dir / "final.mp4"
    stale_mp4.write_bytes(b"tiny_corrupt_mp4")

    clip0 = tmp_path / "clip0.mp4"
    clip0.write_bytes(b"A" * 200)

    s8_artifact = {
        "run_id": run_id,
        "stage": StageID.S8_VIDEO_GEN.value,
        "status": "ok",
        "payload": {
            "clips": [
                {"scene_id": "SCENE_01", "file_path": str(clip0), "duration_sec": 2.0},
            ]
        },
        "provenance": {"generator": "stages.s8_video_gen"},
    }
    s8_file = paths.artifact_file(StageID.S8_VIDEO_GEN.value)
    s8_file.parent.mkdir(parents=True, exist_ok=True)
    s8_file.write_text(json.dumps(s8_artifact), encoding="utf-8")

    audio_file = tmp_path / "narration.wav"
    audio_file.write_bytes(b"C" * 500)
    sub_file = tmp_path / "subtitles.ass"
    sub_file.write_text("[Script Info]\nTitle: Test", encoding="utf-8")

    s9_artifact = {
        "run_id": run_id,
        "stage": StageID.S9_VOICE_TTS.value,
        "status": "ok",
        "payload": {
            "audio_file": str(audio_file),
            "subtitles_file": str(sub_file),
            "subtitles": []
        },
        "provenance": {"generator": "stages.s9_voice_tts"},
    }
    s9_file = paths.artifact_file(StageID.S9_VOICE_TTS.value)
    s9_file.parent.mkdir(parents=True, exist_ok=True)
    s9_file.write_text(json.dumps(s9_artifact), encoding="utf-8")

    cfg = load_profile("e2e_min")
    manifest = RunManifest.create_new(run_id, profile="e2e_min")
    ctx = RunContext(
        run_id=run_id,
        paths=paths,
        manifest=manifest,
        config=cfg,
        force=False,
        dry_run=False,
    )

    assembly_called = False

    def fake_assemble(clips, audio, sub, target):
        nonlocal assembly_called
        assembly_called = True
        target.write_bytes(b"X" * 1500)

    monkeypatch.setattr("stages.s10_render.assemble_final_video", fake_assemble)
    monkeypatch.setattr("vox.qa.gates.probe_media_file", lambda p: {
        "streams": [{"codec_type": "video", "codec_name": "h264", "nb_frames": 60, "nb_read_packets": "60", "r_frame_rate": "30/1", "duration": "2.0"}],
        "format": {"duration": "2.0"}
    })

    art = run_s10_render(ctx)
    assert assembly_called is True
    assert art.status == "ok"
    assert stale_mp4.stat().st_size >= 1000


def test_s10_render_fails_closed_when_subtitles_file_key_missing(tmp_path: Path) -> None:
    """Verifies that S10 raises MissingSubtitlesError when S9 lacks the canonical 'subtitles_file' key."""
    from stages.s10_render import MissingSubtitlesError

    run_id = "test_s10_missing_sub_key"
    paths = resolve_run_paths(run_id, repo_root=tmp_path)
    paths.final_render_dir.mkdir(parents=True, exist_ok=True)

    clip0 = tmp_path / "clip0.mp4"
    clip0.write_bytes(b"A" * 200)

    s8_artifact = {
        "run_id": run_id,
        "stage": StageID.S8_VIDEO_GEN.value,
        "status": "ok",
        "payload": {
            "clips": [{"scene_id": "SCENE_01", "file_path": str(clip0), "duration_sec": 2.0}]
        },
        "provenance": {"generator": "stages.s8_video_gen"},
    }
    s8_file = paths.artifact_file(StageID.S8_VIDEO_GEN.value)
    s8_file.parent.mkdir(parents=True, exist_ok=True)
    s8_file.write_text(json.dumps(s8_artifact), encoding="utf-8")

    audio_file = tmp_path / "narration.wav"
    audio_file.write_bytes(b"C" * 500)

    # S9 payload intentionally omitting 'subtitles_file'
    s9_artifact = {
        "run_id": run_id,
        "stage": StageID.S9_VOICE_TTS.value,
        "status": "ok",
        "payload": {
            "audio_file": str(audio_file),
            "subtitles": []
        },
        "provenance": {"generator": "stages.s9_voice_tts"},
    }
    s9_file = paths.artifact_file(StageID.S9_VOICE_TTS.value)
    s9_file.parent.mkdir(parents=True, exist_ok=True)
    s9_file.write_text(json.dumps(s9_artifact), encoding="utf-8")

    cfg = load_profile("e2e_min")
    manifest = RunManifest.create_new(run_id, profile="e2e_min")
    ctx = RunContext(
        run_id=run_id,
        paths=paths,
        manifest=manifest,
        config=cfg,
        force=True,
        dry_run=False,
    )

    with pytest.raises(MissingSubtitlesError, match="canonical 'subtitles_file' key in S9 payload contract"):
        run_s10_render(ctx)


def test_s10_render_vox_native_parallax_motion_graphics(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Verifies that Stage S10 successfully renders 2.5D CSS parallax motion graphics when clips is empty."""
    run_id = "test_s10_vox_native"
    paths = resolve_run_paths(run_id, repo_root=tmp_path)
    paths.final_render_dir.mkdir(parents=True, exist_ok=True)

    # Empty clips list in S8 (representing Vox motion graphics mode without fragmented I2V clips)
    s8_artifact = {
        "run_id": run_id,
        "stage": StageID.S8_VIDEO_GEN.value,
        "status": "ok",
        "payload": {"clips": []},
        "provenance": {"generator": "stages.s8_video_gen"},
    }
    s8_file = paths.artifact_file(StageID.S8_VIDEO_GEN.value)
    s8_file.parent.mkdir(parents=True, exist_ok=True)
    s8_file.write_text(json.dumps(s8_artifact), encoding="utf-8")

    # S5 Director Plan with scene narration
    s5_artifact = {
        "run_id": run_id,
        "stage": StageID.S5_DIRECTOR_PLAN.value,
        "status": "ok",
        "payload": {
            "scenes": [
                {
                    "scene_id": "SCENE_01",
                    "headline": "FORENSIC DISCLOSURE",
                    "narration": "Archival ledger entries exposed the diversion of funds.",
                    "duration_est_sec": 3.0,
                }
            ]
        },
        "provenance": {"generator": "stages.s5_director_plan"},
    }
    s5_file = paths.artifact_file(StageID.S5_DIRECTOR_PLAN.value)
    s5_file.parent.mkdir(parents=True, exist_ok=True)
    s5_file.write_text(json.dumps(s5_artifact), encoding="utf-8")

    # Valid narration WAV and ASS subtitles
    audio_file = tmp_path / "narration.wav"
    audio_file.write_bytes(b"RIFF" + b"\x00" * 400)
    sub_file = tmp_path / "subtitles.ass"
    sub_file.write_text("[Script Info]\nTitle: Test Subtitles\n", encoding="utf-8")

    s9_artifact = {
        "run_id": run_id,
        "stage": StageID.S9_VOICE_TTS.value,
        "status": "ok",
        "payload": {
            "audio_file": str(audio_file),
            "subtitles_file": str(sub_file),
            "total_duration_sec": 3.0,
            "subtitles": [
                {"word": "Archival", "start": 0.0, "end": 0.5},
                {"word": "ledger", "start": 0.5, "end": 1.0},
            ]
        },
        "provenance": {"generator": "stages.s9_voice_tts"},
    }
    s9_file = paths.artifact_file(StageID.S9_VOICE_TTS.value)
    s9_file.parent.mkdir(parents=True, exist_ok=True)
    s9_file.write_text(json.dumps(s9_artifact), encoding="utf-8")

    cfg = load_profile("e2e_min")
    manifest = RunManifest.create_new(run_id, profile="e2e_min")
    ctx = RunContext(
        run_id=run_id,
        paths=paths,
        manifest=manifest,
        config=cfg,
        force=True,
        dry_run=False,
    )

    # Monkeypatch render_scene_clip and assemble_final_video to isolate unit test
    vox_rendered = []
    captured_manifests = []
    captured_fg_maps = []
    def fake_render_scene_clip(scene, bg_path, fg_map, out_clip, **kwargs):
        Path(out_clip).parent.mkdir(parents=True, exist_ok=True)
        Path(out_clip).write_bytes(b"fake_vox_mp4" + b"\x00" * 1200)
        vox_rendered.append(out_clip)
        if "master_manifest" in kwargs and kwargs["master_manifest"]:
            captured_manifests.append(kwargs["master_manifest"])
        captured_fg_maps.append(fg_map)
        return out_clip

    def fake_assemble(clip_paths, audio_file, ass_file, final_mp4, **kwargs):
        Path(final_mp4).parent.mkdir(parents=True, exist_ok=True)
        Path(final_mp4).write_bytes(b"master_video_data" + b"\x00" * 2000)
        return final_mp4

    monkeypatch.setattr("vox.compositor.render_scene_clip", fake_render_scene_clip)
    monkeypatch.setattr("stages.s10_render.assemble_final_video", fake_assemble)
    monkeypatch.setattr("vox.qa.gates.probe_media_file", lambda p: {
        "streams": [
            {"codec_type": "video", "r_frame_rate": "30/1", "avg_frame_rate": "30/1", "duration": "3.0", "nb_frames": "90", "nb_read_packets": "90"},
            {"codec_type": "audio", "duration": "3.0"}
        ],
        "format": {"duration": "3.0"}
    })

    art = run_s10_render(ctx)
    assert art.status == "ok"
    assert len(vox_rendered) == 1
    assert Path(art.payload["final_video_path"]).exists()
    assert art.payload["total_scenes_rendered"] == 1

    # Verify 3-layer manifests and modular cutouts were resolved and passed to master compositor
    assert len(captured_manifests) == 1
    m = captured_manifests[0]
    assert "layer_1_background" in m
    assert m["layer_1_background"]["background_color"] == "#F4F1EA"
    assert "layer_2_midground" in m
    assert "layer_3_foreground" in m
    assert "camera_cue_sheet" in m
    assert "hero" in captured_fg_maps[0]
    assert "tool" in captured_fg_maps[0]
    assert "supp" in captured_fg_maps[0]


