"""End-to-end speech biomarker pipeline: audio file -> explainable result.

Deliberately NOT a diagnostic classifier. This milestone produces
transparent, individually-interpretable features and a coarse, clearly
caveated "how much does this deviate from published reference patterns"
band -- not a black-box AD/non-AD prediction. A learned fusion model
(Milestone 3+, once real labeled data via DementiaBank/ADReSS access is
in place) will sit on top of these same features later; keeping the
feature extraction and any eventual classifier as separate stages means
we can validate/audit feature quality independently of model performance.
"""

from __future__ import annotations

import tempfile
from pathlib import Path

from alzheimers_detection.core import disclaimers
from alzheimers_detection.core.config import get_settings
from alzheimers_detection.speech.acoustic_features import extract_acoustic_features
from alzheimers_detection.speech.linguistic_features import extract_linguistic_features
from alzheimers_detection.speech.schemas import (
    AcousticFeatures,
    FeatureContribution,
    LinguisticFeatures,
    RiskBand,
    SpeechAnalysisResult,
)
from alzheimers_detection.speech.transcription import ASREngine, TranscriptionError, get_asr_engine

LIMITATIONS = [
    "Reference ranges are drawn from published group-level studies (typically "
    "older adults, English speakers, picture-description tasks) and may not "
    "generalize to this speaker's age, accent, language, or recording context.",
    "This pipeline evaluates a single speech sample. Published biomarker "
    "studies generally compare groups across many samples; single-sample "
    "estimates have much higher variance.",
    "Repetition detection is a coarse immediate-token heuristic, not a full "
    "disfluency/repair analysis as used in CHAT-coded corpora like DementiaBank.",
    "Voice-quality features (pitch, jitter, shimmer) require the optional "
    "'parselmouth' dependency and a clean recording; noisy audio or a missing "
    "dependency will leave these fields empty rather than estimated.",
    "No classifier trained on labeled clinical outcomes is used in this "
    "milestone -- the risk band reflects feature deviation from reference "
    "ranges, not a model prediction of diagnosis.",
]

# Rough reference ranges synthesized from the speech-biomarker literature
# summarized in docs/DATASETS.md and docs/BIOMARKERS.md. These are
# intentionally wide and are placeholders for the real, cited per-feature
# ranges to be filled in once literature review (Milestone 2) is complete
# and validated against actual reference data (DementiaBank/ADReSS, once
# access is granted) rather than shipped as unsourced numbers.
_REFERENCE_RANGES: dict[str, tuple[float, float]] = {
    "speech_rate_wpm": (100, 160),
    "long_pause_ratio": (0.0, 0.25),
    "type_token_ratio": (0.4, 1.0),
    "filler_word_ratio": (0.0, 0.06),
}


def _score_feature(name: str, value: float | None) -> FeatureContribution | None:
    if value is None or name not in _REFERENCE_RANGES:
        return None
    low, high = _REFERENCE_RANGES[name]
    if value < low:
        direction = "lower_than_typical"
    elif value > high:
        direction = "higher_than_typical"
    else:
        direction = "typical"
    return FeatureContribution(
        feature_name=name,
        observed_value=value,
        reference_note=f"reference range (unvalidated placeholder): {low}-{high}",
        deviation_direction=direction,
    )


def _compute_risk_band(
    acoustic: AcousticFeatures, linguistic: LinguisticFeatures, duration: float
) -> tuple[RiskBand, str, list[FeatureContribution]]:
    settings = get_settings()
    if duration < settings.min_audio_duration_seconds or linguistic.word_count < 10:
        return (
            RiskBand.INSUFFICIENT_DATA,
            disclaimers.risk_band_language("insufficient_data"),
            [],
        )

    candidates = {
        "speech_rate_wpm": acoustic.speech_rate_wpm,
        "long_pause_ratio": acoustic.long_pause_ratio,
        "type_token_ratio": linguistic.type_token_ratio,
        "filler_word_ratio": linguistic.filler_word_ratio,
    }
    contributions = [c for c in (_score_feature(k, v) for k, v in candidates.items()) if c is not None]
    deviations = sum(1 for c in contributions if c.deviation_direction != "typical")

    if deviations == 0:
        band = RiskBand.LOW
    elif deviations <= 1:
        band = RiskBand.MODERATE
    else:
        band = RiskBand.ELEVATED

    return band, disclaimers.risk_band_language(band.value), contributions


def analyze_audio_file(
    audio_path: Path,
    asr_engine: ASREngine | None = None,
) -> SpeechAnalysisResult:
    """Main entry point: run ASR, extract features, assemble explainable result.

    `asr_engine` is injectable so tests (and API request handling, if a
    request wants a non-default backend) don't have to go through the
    settings-driven factory every time.
    """
    settings = get_settings()

    if asr_engine is None:
        asr_engine = get_asr_engine(settings.asr_backend, settings.asr_model_size)

    try:
        transcript = asr_engine.transcribe(audio_path)
    except TranscriptionError:
        raise

    if transcript.audio_duration_seconds > settings.max_audio_duration_seconds:
        raise ValueError(
            f"Audio duration {transcript.audio_duration_seconds:.0f}s exceeds "
            f"max_audio_duration_seconds ({settings.max_audio_duration_seconds}s)."
        )

    acoustic = extract_acoustic_features(audio_path, transcript.words, transcript.audio_duration_seconds)
    linguistic = extract_linguistic_features(transcript.text)

    risk_band, explanation, contributions = _compute_risk_band(
        acoustic, linguistic, transcript.audio_duration_seconds
    )

    return SpeechAnalysisResult(
        transcript=transcript,
        acoustic_features=acoustic,
        linguistic_features=linguistic,
        risk_band=risk_band,
        risk_band_explanation=explanation,
        contributing_features=contributions,
        limitations=LIMITATIONS,
        disclaimer=disclaimers.RESULT_FOOTER,
    )


def analyze_audio_bytes(
    audio_bytes: bytes,
    filename_hint: str = "upload.wav",
    asr_engine: ASREngine | None = None,
) -> SpeechAnalysisResult:
    """Convenience wrapper for the API layer, which receives raw bytes from
    an upload rather than a filesystem path. Honors keep_uploaded_audio so
    the privacy-by-default posture (delete after processing) is enforced
    in one place rather than left to callers to remember.
    """
    settings = get_settings()
    suffix = Path(filename_hint).suffix or ".wav"
    with tempfile.NamedTemporaryFile(suffix=suffix, delete=not settings.keep_uploaded_audio) as tmp:
        tmp.write(audio_bytes)
        tmp.flush()
        result = analyze_audio_file(Path(tmp.name), asr_engine=asr_engine)
    return result
