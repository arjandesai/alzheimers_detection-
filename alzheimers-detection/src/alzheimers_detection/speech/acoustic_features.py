"""Signal-level (acoustic) biomarker extraction.

Two families of features here, deliberately separated by dependency:

1. Timing features (pauses, speech rate, articulation rate) are derived
   purely from ASR word timestamps + audio duration -- no extra library
   needed beyond numpy.
2. Voice-quality features (pitch, jitter, shimmer) require
   period-synchronous analysis that numpy/scipy don't provide out of the
   box; we use parselmouth (a Python binding to Praat), which is the
   standard tool in the speech-pathology literature these features come
   from. If parselmouth isn't installed, those fields come back as None
   rather than the whole pipeline failing -- see AcousticFeatures fields
   being Optional in schemas.py.
"""

from __future__ import annotations

from pathlib import Path

import numpy as np

from alzheimers_detection.core.config import get_settings
from alzheimers_detection.speech.schemas import AcousticFeatures, Word


def _compute_pauses(words: list[Word], duration: float, pause_threshold: float) -> tuple[list[float], float]:
    """Return (pause_durations, phonation_time_seconds).

    Pauses are gaps between consecutive words, plus the lead-in before the
    first word and the trailing silence after the last word, matching how
    pause/silence ratio is typically defined in the dementia speech
    literature (time not spent producing the utterance).
    """
    pauses: list[float] = []
    if not words:
        return pauses, 0.0

    ordered = sorted(words, key=lambda w: w.start)

    lead_in = ordered[0].start
    if lead_in >= pause_threshold:
        pauses.append(lead_in)

    for prev, cur in zip(ordered, ordered[1:]):
        gap = cur.start - prev.end
        if gap >= pause_threshold:
            pauses.append(gap)

    trailing = duration - ordered[-1].end
    if trailing >= pause_threshold:
        pauses.append(trailing)

    total_pause_time = sum(pauses)
    phonation_time = max(duration - total_pause_time, 0.0)
    return pauses, phonation_time


def extract_timing_features(words: list[Word], duration: float, pause_threshold: float | None = None) -> dict:
    """Compute speech-rate and pause statistics. Pure function, easy to
    unit test with synthetic Word lists (see tests/test_acoustic_features.py).
    """
    if pause_threshold is None:
        pause_threshold = get_settings().pause_threshold_seconds

    word_count = len(words)
    pauses, phonation_time = _compute_pauses(words, duration, pause_threshold)

    speech_rate_wpm = (word_count / duration) * 60 if duration > 0 else 0.0
    articulation_rate_wpm = (word_count / phonation_time) * 60 if phonation_time > 0 else 0.0

    long_pauses = [p for p in pauses if p > 1.0]
    long_pause_ratio = (len(long_pauses) / len(pauses)) if pauses else 0.0

    return {
        "speech_rate_wpm": round(speech_rate_wpm, 2),
        "articulation_rate_wpm": round(articulation_rate_wpm, 2),
        "total_pause_count": len(pauses),
        "total_pause_duration_seconds": round(sum(pauses), 3),
        "mean_pause_duration_seconds": round(float(np.mean(pauses)), 3) if pauses else 0.0,
        "long_pause_ratio": round(long_pause_ratio, 3),
        "phonation_ratio": round(phonation_time / duration, 3) if duration > 0 else 0.0,
    }


def extract_voice_quality_features(audio_path: Path) -> dict:
    """Pitch mean/std, jitter, shimmer, voiced fraction via Praat/parselmouth.

    Returns a dict of Nones (not an exception) if parselmouth is
    unavailable, so callers can merge this straight into AcousticFeatures
    without special-casing a missing optional dependency.
    """
    empty = {
        "pitch_mean_hz": None,
        "pitch_std_hz": None,
        "jitter_local_percent": None,
        "shimmer_local_percent": None,
        "voiced_fraction": None,
    }
    try:
        import parselmouth
        from parselmouth.praat import call
    except ImportError:
        return empty

    try:
        sound = parselmouth.Sound(str(audio_path))
        pitch = sound.to_pitch()
        pitch_values = pitch.selected_array["frequency"]
        voiced = pitch_values[pitch_values > 0]
        voiced_fraction = float(len(voiced) / len(pitch_values)) if len(pitch_values) else None
        pitch_mean = float(np.mean(voiced)) if len(voiced) else None
        pitch_std = float(np.std(voiced)) if len(voiced) else None

        point_process = call(sound, "To PointProcess (periodic, cc)", 75, 500)
        jitter_local = call(point_process, "Get jitter (local)", 0, 0, 0.0001, 0.02, 1.3) * 100
        shimmer_local = (
            call([sound, point_process], "Get shimmer (local)", 0, 0, 0.0001, 0.02, 1.3, 1.6) * 100
        )

        return {
            "pitch_mean_hz": round(pitch_mean, 2) if pitch_mean is not None else None,
            "pitch_std_hz": round(pitch_std, 2) if pitch_std is not None else None,
            "jitter_local_percent": round(jitter_local, 3) if jitter_local == jitter_local else None,  # NaN check
            "shimmer_local_percent": round(shimmer_local, 3) if shimmer_local == shimmer_local else None,
            "voiced_fraction": round(voiced_fraction, 3) if voiced_fraction is not None else None,
        }
    except Exception:  # noqa: BLE001 - Praat calls can fail on short/noisy audio; degrade gracefully
        return empty


def extract_acoustic_features(audio_path: Path, words: list[Word], duration: float) -> AcousticFeatures:
    """Full acoustic feature extraction combining timing + voice quality."""
    timing = extract_timing_features(words, duration)
    voice_quality = extract_voice_quality_features(audio_path)
    return AcousticFeatures(**timing, **voice_quality)
