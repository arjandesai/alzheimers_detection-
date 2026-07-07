from pathlib import Path

import pytest

from alzheimers_detection.speech.pipeline import analyze_audio_bytes, analyze_audio_file
from alzheimers_detection.speech.schemas import RiskBand, Transcript, Word
from alzheimers_detection.speech.transcription import TranscriptionError


def test_analyze_audio_file_end_to_end(fake_asr_engine, tmp_path):
    audio_path = tmp_path / "sample.wav"
    audio_path.write_bytes(b"\x00" * 100)  # content irrelevant, fake engine ignores it

    result = analyze_audio_file(audio_path, asr_engine=fake_asr_engine)

    assert result.transcript.asr_backend == "fake"
    assert result.acoustic_features.speech_rate_wpm > 0
    assert result.linguistic_features.word_count > 0
    assert result.disclaimer  # non-empty disclaimer always present
    assert len(result.limitations) > 0


def test_analyze_propagates_transcription_error(failing_asr_engine, tmp_path):
    audio_path = tmp_path / "sample.wav"
    audio_path.write_bytes(b"\x00" * 100)

    with pytest.raises(TranscriptionError):
        analyze_audio_file(audio_path, asr_engine=failing_asr_engine)


def test_insufficient_data_band_for_very_short_transcript(fake_asr_engine, tmp_path):
    short_transcript = Transcript(
        text="yes okay",
        words=[Word(text="yes", start=0.0, end=0.3), Word(text="okay", start=0.4, end=0.7)],
        language="en",
        audio_duration_seconds=1.0,
        asr_backend="fake",
        asr_model="fake-v1",
    )
    fake_asr_engine._transcript = short_transcript
    audio_path = tmp_path / "short.wav"
    audio_path.write_bytes(b"\x00" * 10)

    result = analyze_audio_file(audio_path, asr_engine=fake_asr_engine)
    assert result.risk_band == RiskBand.INSUFFICIENT_DATA


def test_analyze_audio_bytes_wraps_file_analysis(fake_asr_engine, tiny_wav_bytes):
    result = analyze_audio_bytes(tiny_wav_bytes, filename_hint="clip.wav", asr_engine=fake_asr_engine)
    assert result.transcript.asr_backend == "fake"
