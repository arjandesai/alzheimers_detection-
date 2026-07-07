from alzheimers_detection.speech.acoustic_features import extract_timing_features
from alzheimers_detection.speech.schemas import Word


def _words(specs: list[tuple[str, float, float]]) -> list[Word]:
    return [Word(text=t, start=s, end=e) for t, s, e in specs]


def test_speech_rate_no_pauses():
    # 10 words evenly spoken across 10 seconds, no gaps -> ~60 wpm, phonation ratio 1.0
    words = _words([(f"w{i}", i, i + 1) for i in range(10)])
    result = extract_timing_features(words, duration=10.0, pause_threshold=0.25)
    assert result["speech_rate_wpm"] == 60.0
    assert result["total_pause_count"] == 0
    assert result["phonation_ratio"] == 1.0


def test_detects_long_pause():
    # two words with a 2s gap between them, inside a 5s clip
    words = _words([("hello", 0.0, 0.5), ("world", 2.5, 3.0)])
    result = extract_timing_features(words, duration=5.0, pause_threshold=0.25)
    # gap 0.5->2.5 = 2.0s (long pause), plus trailing 3.0->5.0 = 2.0s (also long)
    assert result["total_pause_count"] == 2
    assert result["long_pause_ratio"] == 1.0
    assert result["total_pause_duration_seconds"] == 4.0


def test_short_gaps_not_counted_as_pauses():
    words = _words([("a", 0.0, 0.5), ("b", 0.6, 1.0), ("c", 1.05, 1.5)])
    result = extract_timing_features(words, duration=1.5, pause_threshold=0.25)
    assert result["total_pause_count"] == 0


def test_empty_words_returns_zeroed_features():
    result = extract_timing_features([], duration=5.0, pause_threshold=0.25)
    assert result["speech_rate_wpm"] == 0.0
    assert result["total_pause_count"] == 0
    assert result["phonation_ratio"] == 0.0


def test_articulation_rate_exceeds_speech_rate_when_pauses_present():
    # with a real pause in the middle, articulation rate (phonation-time only)
    # should be higher than speech rate (total-duration based)
    words = _words([("a", 0.0, 0.5), ("b", 3.0, 3.5)])
    result = extract_timing_features(words, duration=5.0, pause_threshold=0.25)
    assert result["articulation_rate_wpm"] > result["speech_rate_wpm"]
