"""Transcript-level (linguistic) biomarker extraction.

Split the same way as acoustic_features.py: features computable with pure
Python/regex (word count, TTR, fillers, repetition) are always available;
features that need part-of-speech tagging (pronoun-to-noun ratio, empty
word ratio, sentence length via clause boundaries) use spaCy if it's
installed and degrade to None otherwise, so the pipeline never hard-fails
for lack of an NLP model.
"""

from __future__ import annotations

import re

from alzheimers_detection.speech.schemas import LinguisticFeatures

# Common disfluency/filler tokens in English spontaneous speech transcripts.
# Not exhaustive -- extend via a config file rather than hardcoding more
# here if you need locale/dialect-specific fillers.
FILLER_WORDS = {"um", "uh", "erm", "er", "hm", "hmm", "like", "you know", "well", "so"}

# "Empty" / low-content words that AD speech literature associates with
# word-finding difficulty (used as filler nouns when a specific word can't
# be retrieved).
EMPTY_WORDS = {"thing", "things", "stuff", "something", "someone", "somewhere", "it", "that"}

_WORD_RE = re.compile(r"[a-zA-Z']+")


def _tokenize(text: str) -> list[str]:
    return [w.lower() for w in _WORD_RE.findall(text)]


def _moving_average_ttr(tokens: list[str], window: int = 25) -> float | None:
    """MATTR: average TTR over sliding windows of `window` tokens.

    Raw type-token ratio is biased by transcript length (longer transcripts
    mechanically have lower TTR), which makes it a poor comparator across
    samples of different length. MATTR corrects for this and is the metric
    generally preferred in the AD lexical-diversity literature.
    """
    if len(tokens) < window:
        return None
    ratios = []
    for i in range(len(tokens) - window + 1):
        chunk = tokens[i : i + window]
        ratios.append(len(set(chunk)) / window)
    return round(sum(ratios) / len(ratios), 4)


def _count_repetitions(tokens: list[str]) -> int:
    """Count immediate repeated tokens/bigrams (e.g. "the the", "I was I was").

    This is a coarse proxy for disfluent repetition, not a full repair/
    revision detector -- a proper CHAT-format analysis (as used with real
    DementiaBank transcripts) captures far more nuance. Documented as a
    limitation in the API response (see pipeline.py LIMITATIONS list).
    """
    count = 0
    for i in range(1, len(tokens)):
        if tokens[i] == tokens[i - 1]:
            count += 1
    return count


def _pos_based_features(text: str) -> dict:
    """Pronoun/noun ratio, empty-word ratio (noun-normalized), mean sentence
    length -- all need POS tags or sentence boundaries better than regex
    can reliably give. Uses spaCy's small English model if available.
    """
    empty = {
        "pronoun_to_noun_ratio": None,
        "mean_sentence_length_words": None,
        "empty_word_ratio": None,
    }
    try:
        import spacy
    except ImportError:
        return empty

    try:
        nlp = spacy.load("en_core_web_sm")
    except OSError:
        # Model not downloaded (`python -m spacy download en_core_web_sm`).
        # Fail soft rather than crashing the pipeline.
        return empty

    doc = nlp(text)
    pronouns = sum(1 for t in doc if t.pos_ == "PRON")
    nouns = sum(1 for t in doc if t.pos_ in ("NOUN", "PROPN"))
    sentences = list(doc.sents)
    sentence_lengths = [len([t for t in s if t.is_alpha]) for s in sentences]

    return {
        "pronoun_to_noun_ratio": round(pronouns / nouns, 3) if nouns > 0 else None,
        "mean_sentence_length_words": round(sum(sentence_lengths) / len(sentence_lengths), 2)
        if sentence_lengths
        else None,
        "empty_word_ratio": round(sum(1 for t in doc if t.lemma_.lower() in EMPTY_WORDS) / nouns, 3)
        if nouns > 0
        else None,
    }


def extract_linguistic_features(text: str) -> LinguisticFeatures:
    tokens = _tokenize(text)
    word_count = len(tokens)
    unique_count = len(set(tokens))

    filler_count = sum(1 for t in tokens if t in FILLER_WORDS)
    repetition_count = _count_repetitions(tokens)
    pos_features = _pos_based_features(text)

    return LinguisticFeatures(
        word_count=word_count,
        unique_word_count=unique_count,
        type_token_ratio=round(unique_count / word_count, 4) if word_count else 0.0,
        moving_average_ttr=_moving_average_ttr(tokens),
        filler_word_count=filler_count,
        filler_word_ratio=round(filler_count / word_count, 4) if word_count else 0.0,
        repetition_count=repetition_count,
        **pos_features,
    )
