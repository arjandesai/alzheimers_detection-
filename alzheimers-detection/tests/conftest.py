"""Shared fixtures.

Real ASR (faster-whisper/openai-whisper) needs multi-hundred-MB model
downloads, which we don't want as a hard requirement for running the unit
test suite (including in this sandbox, and in fast CI jobs). FakeASREngine
implements the same ASREngine interface with deterministic, hand-authored
output so pipeline/API tests can exercise the full flow without network
access or GPU/CPU-heavy inference.

Tests that need to validate real ASR accuracy belong in a separate,
explicitly-marked integration suite (see pyproject.toml `slow` marker)
that CI can skip by default and run nightly instead.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from alzheimers_detection.speech.schemas import Transcript, Word
from alzheimers_detection.speech.transcription import ASREngine, TranscriptionError


class FakeASREngine(ASREngine):
    name = "fake"

    def __init__(self, transcript: Transcript | None = None, raise_error: bool = False):
        self._transcript = transcript
        self._raise_error = raise_error

    def transcribe(self, audio_path: Path) -> Transcript:
        if self._raise_error:
            raise TranscriptionError("simulated ASR failure")
        if self._transcript is not None:
            return self._transcript
        # Default: a plausible short utterance, evenly timed.
        text = "the boy is climbing on the stool and the water is running over"
        tokens = text.split()
        words = [Word(text=t, start=i * 0.4, end=i * 0.4 + 0.35) for i, t in enumerate(tokens)]
        return Transcript(
            text=text,
            words=words,
            language="en",
            audio_duration_seconds=words[-1].end + 0.5,
            asr_backend=self.name,
            asr_model="fake-v1",
        )


@pytest.fixture
def fake_asr_engine():
    return FakeASREngine()


@pytest.fixture
def failing_asr_engine():
    return FakeASREngine(raise_error=True)


@pytest.fixture
def tiny_wav_bytes():
    """A minimal valid WAV file (silence, ~1s) for tests that need real
    bytes to upload, without depending on any external audio asset."""
    import io
    import wave

    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(16000)
        wf.writeframes(b"\x00\x00" * 16000)  # 1 second of silence
    return buf.getvalue()
