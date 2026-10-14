#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""tests/vox/test_schemas.py — Tests for vox/schemas.py (AVF-VOX-001)."""

import pytest
from pydantic import ValidationError
from vox.schemas import CameraMove, FGObject, Scene, ScenePlan, Word, WordTimeline


def test_valid_scene_plan():
    fg1 = FGObject(id="obj_1", prompt="vintage retro typewriter on mahogany wood desk", anchor_x=0.5, anchor_y=0.5, scale=0.4, depth=0.5, enter_at=0.5)
    fg2 = FGObject(id="obj_2", prompt="stack of confidential financial documents with red stamp", anchor_x=0.3, anchor_y=0.6, scale=0.3, depth=0.8, enter_at=1.0)
    
    scene1 = Scene(idx=1, narration="First scene narration.", bg_prompt="dimly lit 1970s investigative archives room", fg=[fg1], camera=CameraMove.PUSH_IN)
    scene2 = Scene(idx=2, narration="Second scene narration.", bg_prompt="modern wall street trading floor with monitors", fg=[fg2], camera=CameraMove.PAN_LEFT)
    
    plan = ScenePlan(title="The Paper Trail", scenes=[scene1, scene2])
    assert len(plan.scenes) == 2
    assert plan.scenes[0].camera == CameraMove.PUSH_IN
    assert plan.scenes[1].camera == CameraMove.PAN_LEFT


def test_duplicate_consecutive_camera_rejected():
    fg = FGObject(id="obj_1", prompt="vintage retro typewriter on mahogany wood desk", anchor_x=0.5, anchor_y=0.5, scale=0.4, depth=0.5, enter_at=0.0)
    scene1 = Scene(idx=1, narration="Scene 1", bg_prompt="investigative newsroom archives background", fg=[fg], camera=CameraMove.PUSH_IN)
    scene2 = Scene(idx=2, narration="Scene 2", bg_prompt="corporate skyscraper boardroom background", fg=[fg], camera=CameraMove.PUSH_IN)
    
    with pytest.raises(ValidationError) as exc:
        ScenePlan(title="Bad Camera Variety", scenes=[scene1, scene2])
    assert "duplicate camera move" in str(exc.value)


def test_fg_limits_rejected():
    fg = FGObject(id="obj_1", prompt="vintage retro typewriter on mahogany wood desk", anchor_x=0.5, anchor_y=0.5, scale=0.4, depth=0.5, enter_at=0.0)
    
    # 0 FG objects should fail
    with pytest.raises(ValidationError):
        Scene(idx=1, narration="Scene 1", bg_prompt="investigative newsroom archives background", fg=[], camera=CameraMove.PUSH_IN)

    # 4 FG objects should fail (max is 3)
    with pytest.raises(ValidationError):
        Scene(idx=1, narration="Scene 1", bg_prompt="investigative newsroom archives background", fg=[fg, fg, fg, fg], camera=CameraMove.PUSH_IN)


def test_fg_anchor_bounds():
    # anchor_x > 1.0 should fail
    with pytest.raises(ValidationError):
        FGObject(id="obj_1", prompt="vintage retro typewriter on mahogany wood desk", anchor_x=1.5, anchor_y=0.5, scale=0.4, depth=0.5, enter_at=0.0)

    # scale < 0.1 should fail
    with pytest.raises(ValidationError):
        FGObject(id="obj_1", prompt="vintage retro typewriter on mahogany wood desk", anchor_x=0.5, anchor_y=0.5, scale=0.05, depth=0.5, enter_at=0.0)


def test_word_timeline():
    w1 = Word(text="Hello", start=0.0, end=0.3, scene_idx=1)
    w2 = Word(text="World", start=0.35, end=0.7, scene_idx=1)
    tl = WordTimeline(words=[w1, w2], audio_duration=0.75, match_ratio=1.0)
    assert len(tl.words) == 2
    assert tl.match_ratio == 1.0
