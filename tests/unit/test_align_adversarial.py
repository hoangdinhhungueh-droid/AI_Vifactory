#!/usr/bin/env python3
"""tests/unit/test_align_adversarial.py — Adversarial Alignment & SequenceMatcher Gate Tests (AVF-VOX-001).

Tests:
- Token alignment with SequenceMatcher opcodes
- Adversarial tests for inserted, dropped, and substituted words
- Enforcement of match_ratio >= 0.95 (raising AlignmentUnavailableError on corruption)
- allow_synthetic_alignment gating (raising in production, allowing in tests with alignment_model='synthetic')
"""

from __future__ import annotations

import sys
import types
import wave
from pathlib import Path

import pytest

from vox.align import AlignmentUnavailableError, align_script_with_audio
from vox.schemas import CameraMove, FGObject, Scene, ScenePlan


@pytest.fixture
def dummy_wav(tmp_path: Path) -> Path:
    """Creates a minimal valid 48kHz mono WAV file (1 second of silence)."""
    wav_file = tmp_path / "test_audio.wav"
    with wave.open(str(wav_file), "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(48000)
        # 48000 frames = 1.0 second
        wf.writeframes(b"\x00\x00" * 48000)
    return wav_file


@pytest.fixture
def sample_plan() -> ScenePlan:
    """Creates a standard 2-scene ScenePlan."""
    return ScenePlan(
        title="Adversarial Alignment Test",
        scenes=[
            Scene(
                idx=1,
                narration="In 2008 the financial system faced an unprecedented liquidity shock.",
                bg_prompt="A dramatic wide architectural render of Wall Street trading floor",
                fg=[
                    FGObject(
                        id="fg_01",
                        prompt="tactile paper document representing liquidity balance sheet",
                        anchor_x=0.5,
                        anchor_y=0.5,
                        scale=0.4,
                        depth=0.5,
                        enter_at=0.0,
                    )
                ],
                camera=CameraMove.PUSH_IN,
            ),
            Scene(
                idx=2,
                narration="Banks stopped lending and interbank markets completely froze overnight.",
                bg_prompt="A shadowy corporate vault with rusted iron gates and warning lights",
                fg=[
                    FGObject(
                        id="fg_02",
                        prompt="tactile paper vault key symbolizing locked interbank credit",
                        anchor_x=0.5,
                        anchor_y=0.5,
                        scale=0.4,
                        depth=0.5,
                        enter_at=0.0,
                    )
                ],
                camera=CameraMove.STATIC_BREATH,
            ),
        ],
    )


def test_align_fails_closed_without_whisper(sample_plan: ScenePlan, dummy_wav: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Asserts that align_script_with_audio raises AlignmentUnavailableError in production when Whisper is missing/fails."""
    # Hide faster_whisper to simulate runtime environment without the dependency
    monkeypatch.setitem(sys.modules, "faster_whisper", None)

    with pytest.raises(AlignmentUnavailableError, match="faster-whisper runtime alignment unavailable"):
        align_script_with_audio(sample_plan, dummy_wav, allow_synthetic_alignment=False)


def test_allow_synthetic_alignment_marks_model_synthetic(sample_plan: ScenePlan, dummy_wav: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Asserts that allow_synthetic_alignment=True works in test paths and flags alignment_model='synthetic'."""
    monkeypatch.setitem(sys.modules, "faster_whisper", None)

    timeline, updated_plan = align_script_with_audio(sample_plan, dummy_wav, allow_synthetic_alignment=True)
    assert timeline.alignment_model == "synthetic"
    assert len(timeline.words) > 0
    assert updated_plan.scenes[0].start == 0.0
    assert updated_plan.scenes[-1].end == pytest.approx(1.0, abs=0.05)


def test_adversarial_substitution_breaks_match_ratio(sample_plan: ScenePlan, dummy_wav: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Adversarial check: heavily substituted words (<0.95 ratio) must raise AlignmentUnavailableError."""
    # Mock Whisper transcribe returning corrupted tokens
    class MockSegment:
        def __init__(self, words: list[MockWord]) -> None:
            self.words = words

    class MockWord:
        def __init__(self, word: str, start: float, end: float) -> None:
            self.word = word
            self.start = start
            self.end = end
            self.probability = 0.99

    class MockWhisperModel:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def transcribe(self, *args, **kwargs) -> tuple[list[MockSegment], None]:
            # Substitute completely different random words
            corrupted_words = [
                MockWord("completely", 0.0, 0.2),
                MockWord("unrelated", 0.2, 0.4),
                MockWord("random", 0.4, 0.6),
                MockWord("garbage", 0.6, 0.8),
                MockWord("tokens", 0.8, 1.0),
            ]
            return [MockSegment(corrupted_words)], None

    mock_mod = types.ModuleType("faster_whisper")
    mock_mod.WhisperModel = MockWhisperModel  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "faster_whisper", mock_mod)

    with pytest.raises(AlignmentUnavailableError, match="below mandatory threshold 0.95"):
        align_script_with_audio(sample_plan, dummy_wav, allow_synthetic_alignment=False)


def test_adversarial_dropped_word_detected(sample_plan: ScenePlan, dummy_wav: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Adversarial check: dropping major script tokens lowers match ratio below 0.95 and raises error."""
    class MockWord:
        def __init__(self, word: str, start: float, end: float) -> None:
            self.word = word
            self.start = start
            self.end = end
            self.probability = 0.99

    class MockSegment:
        def __init__(self, words: list[MockWord]) -> None:
            self.words = words

    class MockWhisperModel:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def transcribe(self, *args, **kwargs) -> tuple[list[MockSegment], None]:
            # Emit only a fraction of words (e.g. 2 words out of 20) -> ratio << 0.95
            dropped_words = [
                MockWord("In", 0.0, 0.2),
                MockWord("2008", 0.2, 0.4),
            ]
            return [MockSegment(dropped_words)], None

    mock_mod = types.ModuleType("faster_whisper")
    mock_mod.WhisperModel = MockWhisperModel  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "faster_whisper", mock_mod)

    with pytest.raises(AlignmentUnavailableError, match="below mandatory threshold 0.95"):
        align_script_with_audio(sample_plan, dummy_wav, allow_synthetic_alignment=False)


def test_high_fidelity_alignment_succeeds(sample_plan: ScenePlan, dummy_wav: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """High-fidelity check: matching speech tokens aligns perfectly via SequenceMatcher opcodes."""
    script_words = [w for sc in sample_plan.scenes for w in sc.narration.strip().split()]

    class MockWord:
        def __init__(self, word: str, start: float, end: float) -> None:
            self.word = word
            self.start = start
            self.end = end
            self.probability = 0.98

    class MockSegment:
        def __init__(self, words: list[MockWord]) -> None:
            self.words = words

    class MockWhisperModel:
        def __init__(self, *args, **kwargs) -> None:
            pass

        def transcribe(self, *args, **kwargs) -> tuple[list[MockSegment], None]:
            whisper_words = []
            dur_per_word = 1.0 / len(script_words)
            for i, sw in enumerate(script_words):
                whisper_words.append(
                    MockWord(sw.strip(".,"), round(i * dur_per_word, 3), round((i + 1) * dur_per_word, 3))
                )
            return [MockSegment(whisper_words)], None

    mock_mod = types.ModuleType("faster_whisper")
    mock_mod.WhisperModel = MockWhisperModel  # type: ignore[attr-defined]
    monkeypatch.setitem(sys.modules, "faster_whisper", mock_mod)

    timeline, updated_plan = align_script_with_audio(sample_plan, dummy_wav, allow_synthetic_alignment=False)
    assert timeline.match_ratio >= 0.95
    assert len(timeline.words) == len(script_words)
    assert updated_plan.scenes[0].start == 0.0
    assert updated_plan.scenes[-1].end == pytest.approx(1.0, abs=0.05)
