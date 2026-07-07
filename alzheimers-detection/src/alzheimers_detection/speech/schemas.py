"""Data contracts for the speech biomarker pipeline.

Keeping these as explicit Pydantic models (rather than passing dicts
around) means the FastAPI layer gets free request/response validation and
OpenAPI docs, and every downstream consumer knows exactly what shape of
data to expect.
"""

from __future__ import annotations

from enum import Enum

from pydantic import BaseModel, Field


class Word(BaseModel):
    """A single word with alignment timing from the ASR engine."""

    text: str
    start: float = Field(description="Start time in seconds from audio start")
    end: float = Field(description="End time in seconds from audio start")
    confidence: float | None = Field(
        default=None, description="ASR-reported confidence for this token, if available"
    )


class Transcript(BaseModel):
    """Output of the ASR stage. Intentionally engine-agnostic."""

    text: str
    words: list[Word]
    language: str = "en"
    audio_duration_seconds: float
    asr_backend: str
    asr_model: str


class AcousticFeatures(BaseModel):
    """Signal-level biomarkers, computed directly from the waveform.

    Field-level docstrings summarize the direction reported in AD/MCI
    literature; see docs/DATASETS.md and docs/BIOMARKERS.md for citations.
    This model does NOT claim these directions hold for any individual --
    only that they are the population-level trends the feature is chosen
    to measure.
    """

    speech_rate_wpm: float = Field(description="Words per minute over total duration")
    articulation_rate_wpm: float = Field(
        description="Words per minute over phonation time only (excludes pauses); "
        "AD-associated speech often shows articulation rate closer to overall "
        "speech rate than controls, because pause time dominates more"
    )
    total_pause_count: int
    total_pause_duration_seconds: float
    mean_pause_duration_seconds: float
    long_pause_ratio: float = Field(
        description="Fraction of pauses exceeding 1s -- associated with word-finding difficulty"
    )
    phonation_ratio: float = Field(
        description="Fraction of audio duration that is speech (not pause/silence)"
    )
    pitch_mean_hz: float | None = None
    pitch_std_hz: float | None = Field(
        default=None, description="Pitch variation; reduced prosodic variation is reported in AD speech"
    )
    jitter_local_percent: float | None = Field(
        default=None, description="Cycle-to-cycle pitch perturbation from Praat-style analysis"
    )
    shimmer_local_percent: float | None = Field(
        default=None, description="Cycle-to-cycle amplitude perturbation"
    )
    voiced_fraction: float | None = Field(
        default=None, description="Fraction of phonation time that is voiced (has detectable pitch)"
    )


class LinguisticFeatures(BaseModel):
    """Transcript-level biomarkers, computed from ASR text output."""

    word_count: int
    unique_word_count: int
    type_token_ratio: float = Field(
        description="unique_word_count / word_count; lower values are associated "
        "with reduced lexical diversity reported in early AD"
    )
    moving_average_ttr: float | None = Field(
        default=None,
        description="TTR computed over a sliding window and averaged, which is "
        "less sensitive to transcript length than raw TTR",
    )
    filler_word_count: int = Field(description="Count of um/uh/er/like-as-filler etc.")
    filler_word_ratio: float
    repetition_count: int = Field(
        description="Immediate word/phrase repetitions, a proxy for word-retrieval struggle"
    )
    pronoun_to_noun_ratio: float | None = Field(
        default=None,
        description="Elevated pronoun use relative to nouns is reported as a marker "
        "of word-finding difficulty (semantic emptying of language)",
    )
    mean_sentence_length_words: float | None = None
    empty_word_ratio: float | None = Field(
        default=None,
        description="Ratio of low-content words (thing, stuff, something) to total "
        "content words -- another word-finding proxy",
    )


class RiskBand(str, Enum):
    LOW = "low"
    MODERATE = "moderate"
    ELEVATED = "elevated"
    INSUFFICIENT_DATA = "insufficient_data"


class FeatureContribution(BaseModel):
    """One line of the explainability report: which feature, how far from
    reference range, and in which direction."""

    feature_name: str
    observed_value: float
    reference_note: str
    deviation_direction: str = Field(description="'higher_than_typical', 'lower_than_typical', or 'typical'")


class SpeechAnalysisResult(BaseModel):
    """Top-level response for a single speech sample analysis."""

    transcript: Transcript
    acoustic_features: AcousticFeatures
    linguistic_features: LinguisticFeatures
    risk_band: RiskBand
    risk_band_explanation: str
    contributing_features: list[FeatureContribution]
    limitations: list[str]
    disclaimer: str
