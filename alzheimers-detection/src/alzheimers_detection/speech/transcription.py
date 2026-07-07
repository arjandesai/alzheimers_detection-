"""Speech-to-text with word-level timestamps.

Why an abstract engine instead of calling faster-whisper directly from the
pipeline: pause detection and speech-rate features both depend entirely on
word-level timing, so the ASR engine is a hard dependency of the acoustic
feature stage, not just the linguistic stage. Making it swappable also
means a contributor can drop in wav2vec2-based CTC alignment or the
OpenAI Whisper API without touching pipeline.py -- they implement
ASREngine and register it.

Model choice: faster-whisper (CTranslate2 reimplementation of Whisper) is
the default because it gives word-level timestamps, runs well on CPU
(important for a local-inference-first, privacy-conscious tool per the
project's privacy goals), and is MIT licensed. Plain openai-whisper is
kept as a fallback since it has no extra system dependencies.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Callable

from alzheimers_detection.speech.schemas import Transcript, Word


class TranscriptionError(RuntimeError):
    """Raised when ASR fails or produces unusable output (e.g. no speech detected)."""


class ASREngine(ABC):
    """Interface every ASR backend must implement."""

    name: str = "base"

    @abstractmethod
    def transcribe(self, audio_path: Path) -> Transcript:
        """Transcribe audio at `audio_path` and return word-aligned text.

        Implementations must raise TranscriptionError (not a bare
        exception) on failure so the API layer can return a clean 4xx
        instead of a 500.
        """
        raise NotImplementedError


class FasterWhisperEngine(ASREngine):
    """Wraps faster-whisper. Lazily imports the library so the rest of the
    package can be imported/tested without the (large) model dependency
    installed -- useful in lightweight CI jobs and for contributors who
    only touch, say, the linguistic-features code.
    """

    name = "faster_whisper"

    def __init__(self, model_size: str = "base", device: str = "cpu", compute_type: str = "int8"):
        self.model_size = model_size
        self.device = device
        self.compute_type = compute_type
        self._model = None  # loaded lazily on first transcribe() call

    def _load_model(self):
        if self._model is None:
            try:
                from faster_whisper import WhisperModel
            except ImportError as e:  # pragma: no cover - exercised only without the optional dep
                raise TranscriptionError(
                    "faster-whisper is not installed. Install the 'speech' extra: "
                    "pip install 'alzheimers-detection[speech]'"
                ) from e
            self._model = WhisperModel(self.model_size, device=self.device, compute_type=self.compute_type)
        return self._model

    def transcribe(self, audio_path: Path) -> Transcript:
        import soundfile as sf

        model = self._load_model()
        try:
            segments, info = model.transcribe(str(audio_path), word_timestamps=True)
        except Exception as e:  # noqa: BLE001 - library raises varied errors, normalize them
            raise TranscriptionError(f"faster-whisper transcription failed: {e}") from e

        words: list[Word] = []
        text_parts: list[str] = []
        for segment in segments:
            text_parts.append(segment.text.strip())
            for w in segment.words or []:
                words.append(Word(text=w.word.strip(), start=w.start, end=w.end, confidence=w.probability))

        if not words:
            raise TranscriptionError("No speech detected in audio.")

        try:
            duration = sf.info(str(audio_path)).duration
        except Exception:  # noqa: BLE001 - duration fallback is best-effort
            duration = words[-1].end

        return Transcript(
            text=" ".join(text_parts).strip(),
            words=words,
            language=info.language or "en",
            audio_duration_seconds=duration,
            asr_backend=self.name,
            asr_model=self.model_size,
        )


class OpenAIWhisperEngine(ASREngine):
    """Fallback using the original openai-whisper package. Slower and has
    no int8 CPU quantization, but has fewer system-level dependencies
    (no need for the CTranslate2 runtime), which is useful on platforms
    where faster-whisper's wheels are unavailable.
    """

    name = "openai_whisper"

    def __init__(self, model_size: str = "base"):
        self.model_size = model_size
        self._model = None

    def _load_model(self):
        if self._model is None:
            try:
                import whisper
            except ImportError as e:  # pragma: no cover
                raise TranscriptionError(
                    "openai-whisper is not installed. Install the 'speech' extra: "
                    "pip install 'alzheimers-detection[speech]'"
                ) from e
            self._model = whisper.load_model(self.model_size)
        return self._model

    def transcribe(self, audio_path: Path) -> Transcript:
        model = self._load_model()
        try:
            result = model.transcribe(str(audio_path), word_timestamps=True)
        except Exception as e:  # noqa: BLE001
            raise TranscriptionError(f"whisper transcription failed: {e}") from e

        words: list[Word] = []
        for segment in result.get("segments", []):
            for w in segment.get("words", []):
                words.append(Word(text=w["word"].strip(), start=w["start"], end=w["end"], confidence=w.get("probability")))

        if not words:
            raise TranscriptionError("No speech detected in audio.")

        duration = words[-1].end
        return Transcript(
            text=result.get("text", "").strip(),
            words=words,
            language=result.get("language", "en"),
            audio_duration_seconds=duration,
            asr_backend=self.name,
            asr_model=self.model_size,
        )


_ENGINE_REGISTRY: dict[str, Callable[..., ASREngine]] = {
    "faster_whisper": FasterWhisperEngine,
    "openai_whisper": OpenAIWhisperEngine,
}


def get_asr_engine(backend: str, model_size: str = "base") -> ASREngine:
    """Factory used by the pipeline/API layer. Raises a clear error for
    unknown backend names instead of an obscure KeyError downstream.
    """
    if backend not in _ENGINE_REGISTRY:
        valid = ", ".join(sorted(_ENGINE_REGISTRY))
        raise ValueError(f"Unknown ASR backend '{backend}'. Valid options: {valid}")
    return _ENGINE_REGISTRY[backend](model_size=model_size)


def register_engine(name: str, factory: Callable[..., ASREngine]) -> None:
    """Allow external plugins/tests to register a custom engine (e.g. a
    deterministic fake for unit tests) without modifying this file."""
    _ENGINE_REGISTRY[name] = factory
