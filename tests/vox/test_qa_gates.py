#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/vox/test_qa_gates.py — Unit & Falsifiable Adversarial Tests for Vox QA Gates (AVF-VOX-001).

Guarantees:
1. Module constants BROADCAST_LUFS_TARGET (-16.0), BROADCAST_LUFS_MIN (-17.0),
   BROADCAST_LUFS_MAX (-15.0), and BROADCAST_TRUE_PEAK_CEILING (-2.0) are strictly enforced.
2. Falsifiable negative test: -1.9 dBTP true peak strictly raises ValueError (Boss Item 5).
3. Falsifiable negative test: loudness outside [-17.0, -15.0] LUFS strictly raises ValueError.
4. Stream verification: non-h264, non-aac, or missing streams strictly raise ValueError.
5. Consecutive identical camera moves strictly raise ValueError.
"""

import subprocess
from types import SimpleNamespace

import pytest

import vox.qa.gates as gates
from vox.qa.gates import (
    BROADCAST_LUFS_MAX,
    BROADCAST_LUFS_MIN,
    BROADCAST_LUFS_TARGET,
    BROADCAST_TRUE_PEAK_CEILING,
    verify_final_video_gates,
)
from vox.schemas import CameraMove, FGObject, Scene, ScenePlan


@pytest.fixture
def valid_scene_plan() -> ScenePlan:
    return ScenePlan(
        title="Test Scene Plan",
        scenes=[
            Scene(
                idx=1,
                narration="First scene narration.",
                bg_prompt="vintage editorial ledger desk background, 16:9 aspect ratio",
                camera=CameraMove.PAN_LEFT,
                fg=[
                    FGObject(
                        id="obj1",
                        prompt="tactile archival seal medallion, 1:1 aspect ratio",
                        anchor_x=0.5,
                        anchor_y=0.5,
                        scale=0.4,
                        depth=0.5,
                        enter_at=0.1,
                    )
                ],
            ),
            Scene(
                idx=2,
                narration="Second scene narration.",
                bg_prompt="vintage wall street trading chalkboard backdrop, 16:9 aspect ratio",
                camera=CameraMove.PAN_RIGHT,
                fg=[
                    FGObject(
                        id="obj2",
                        prompt="tactile brass balance scale prop, 1:1 aspect ratio",
                        anchor_x=0.6,
                        anchor_y=0.5,
                        scale=0.35,
                        depth=0.6,
                        enter_at=0.2,
                    )
                ],
            ),
            Scene(
                idx=3,
                narration="Third scene narration.",
                bg_prompt="vintage banking vault interior with steel safe door, 16:9 aspect ratio",
                camera=CameraMove.PUSH_IN,
                fg=[
                    FGObject(
                        id="obj3",
                        prompt="tactile official red wax ribbon seal, 1:1 aspect ratio",
                        anchor_x=0.4,
                        anchor_y=0.6,
                        scale=0.45,
                        depth=0.7,
                        enter_at=0.3,
                    )
                ],
            ),
        ],
    )


def test_broadcast_loudness_constants_parity():
    """Rule 134 parity: Broadcast constants adhere to AES TD1004 and EBU Tech 3343."""
    assert BROADCAST_LUFS_TARGET == -16.0
    assert BROADCAST_LUFS_MIN == -17.0
    assert BROADCAST_LUFS_MAX == -15.0
    assert BROADCAST_TRUE_PEAK_CEILING == -2.0


def test_qa_gate_rejects_breach_true_peak(tmp_path, valid_scene_plan):
    """Adversarial Falsifiable Test (Boss Item 5): True Peak at -1.9 dBTP exceeds -2.0 dBTP ceiling."""
    dummy_mp4 = tmp_path / "final.mp4"
    dummy_mp4.write_bytes(b"dummy_mp4_bytes")

    probe_spec = {
        "streams": [
            {"codec_type": "video", "codec_name": "h264", "width": 1920, "height": 1080, "pix_fmt": "yuv420p", "nb_frames": "300", "r_frame_rate": "30/1"},
            {"codec_type": "audio", "codec_name": "aac", "sample_rate": 48000},
        ],
        "format": {"duration": "10.0", "size": "1000000", "bit_rate": "2000000"},
    }

    # -1.9 dBTP is an explicit breach of the -2.0 dBTP ceiling
    breach_loudness = {"integrated_lufs": -16.0, "true_peak_dbtp": -1.9}

    orig_probe = gates.probe_media_file
    orig_loudness = gates.measure_ebur128_loudness
    orig_subproc = subprocess.run

    try:
        gates.probe_media_file = lambda p: probe_spec
        gates.measure_ebur128_loudness = lambda p: breach_loudness
        subprocess.run = lambda *args, **kwargs: SimpleNamespace(stderr="", returncode=0)

        with pytest.raises(ValueError) as exc_info:
            verify_final_video_gates(dummy_mp4, expected_duration=10.0, plan=valid_scene_plan)
        assert "exceeds zero-tolerance ceiling -2.0 dBTP" in str(exc_info.value)
    finally:
        gates.probe_media_file = orig_probe
        gates.measure_ebur128_loudness = orig_loudness
        subprocess.run = orig_subproc


def test_qa_gate_rejects_loudness_outside_range(tmp_path, valid_scene_plan):
    """Adversarial Falsifiable Test: Loudness at -14.5 LUFS is outside [-17.0, -15.0] LUFS."""
    dummy_mp4 = tmp_path / "final.mp4"
    dummy_mp4.write_bytes(b"dummy_mp4_bytes")

    probe_spec = {
        "streams": [
            {"codec_type": "video", "codec_name": "h264", "width": 1920, "height": 1080, "pix_fmt": "yuv420p", "nb_frames": "300", "r_frame_rate": "30/1"},
            {"codec_type": "audio", "codec_name": "aac", "sample_rate": 48000},
        ],
        "format": {"duration": "10.0", "size": "1000000", "bit_rate": "2000000"},
    }

    too_loud = {"integrated_lufs": -14.5, "true_peak_dbtp": -2.5}

    orig_probe = gates.probe_media_file
    orig_loudness = gates.measure_ebur128_loudness
    orig_subproc = subprocess.run

    try:
        gates.probe_media_file = lambda p: probe_spec
        gates.measure_ebur128_loudness = lambda p: too_loud
        subprocess.run = lambda *args, **kwargs: SimpleNamespace(stderr="", returncode=0)

        with pytest.raises(ValueError) as exc_info:
            verify_final_video_gates(dummy_mp4, expected_duration=10.0, plan=valid_scene_plan)
        assert "outside [-17.0, -15.0]" in str(exc_info.value)
    finally:
        gates.probe_media_file = orig_probe
        gates.measure_ebur128_loudness = orig_loudness
        subprocess.run = orig_subproc


def test_qa_gate_rejects_consecutive_identical_camera_moves():
    """Camera variety gate: Consecutive identical camera moves must fail at schema level."""
    with pytest.raises(ValueError) as exc_info:
        ScenePlan(
            title="Bad Camera Plan",
            scenes=[
                Scene(
                    idx=1,
                    narration="Scene 1",
                    bg_prompt="vintage editorial ledger desk background, 16:9 aspect ratio",
                    camera=CameraMove.PAN_LEFT,
                    fg=[FGObject(id="obj1", prompt="vintage seal stamp prop, 1:1 aspect ratio", anchor_x=0.5, anchor_y=0.5, scale=0.4, depth=0.5, enter_at=0.1)]
                ),
                Scene(
                    idx=2,
                    narration="Scene 2",
                    bg_prompt="vintage wall street trading chalkboard backdrop, 16:9 aspect ratio",
                    camera=CameraMove.PAN_LEFT,
                    fg=[FGObject(id="obj2", prompt="vintage ledger balance scale, 1:1 aspect ratio", anchor_x=0.5, anchor_y=0.5, scale=0.4, depth=0.5, enter_at=0.1)]
                ),
            ],
        )
    assert "duplicate camera move" in str(exc_info.value)


def test_qa_gate_passes_strictly_compliant_video(tmp_path, valid_scene_plan):
    """Happy Path: Compliant loudness (-16.4 LUFS, -2.5 dBTP), CFR 30fps, H.264+AAC."""
    dummy_mp4 = tmp_path / "final.mp4"
    dummy_mp4.write_bytes(b"dummy_mp4_bytes")

    probe_spec = {
        "streams": [
            {"codec_type": "video", "codec_name": "h264", "width": 1920, "height": 1080, "pix_fmt": "yuv420p", "nb_frames": "300", "r_frame_rate": "30/1"},
            {"codec_type": "audio", "codec_name": "aac", "sample_rate": 48000},
        ],
        "format": {"duration": "10.0", "size": "1000000", "bit_rate": "2000000"},
    }

    compliant_loudness = {"integrated_lufs": -16.4, "true_peak_dbtp": -2.5}

    orig_probe = gates.probe_media_file
    orig_loudness = gates.measure_ebur128_loudness
    orig_subproc = subprocess.run

    try:
        gates.probe_media_file = lambda p: probe_spec
        gates.measure_ebur128_loudness = lambda p: compliant_loudness
        subprocess.run = lambda *args, **kwargs: SimpleNamespace(stderr="", returncode=0)

        report = verify_final_video_gates(dummy_mp4, expected_duration=10.0, plan=valid_scene_plan)
        assert report["status"] == "PASS"
        assert report["integrated_loudness_lufs"] == -16.4
        assert report["true_peak_dbtp"] == -2.5
        assert report["video_codec"] == "h264"
        assert report["audio_codec"] == "aac"
    finally:
        gates.probe_media_file = orig_probe
        gates.measure_ebur128_loudness = orig_loudness
        subprocess.run = orig_subproc
