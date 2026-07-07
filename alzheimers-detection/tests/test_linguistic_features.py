from alzheimers_detection.speech.linguistic_features import extract_linguistic_features


def test_basic_counts():
    text = "The cat sat on the mat"
    f = extract_linguistic_features(text)
    assert f.word_count == 6
    assert f.unique_word_count == 5  # "the" repeated
    assert round(f.type_token_ratio, 4) == round(5 / 6, 4)


def test_filler_word_detection():
    text = "um so I was uh going to the um store"
    f = extract_linguistic_features(text)
    # "so" is also in FILLER_WORDS, so matches are: um, so, uh, um = 4
    assert f.filler_word_count == 4


def test_filler_word_ratio_zero_for_clean_text():
    text = "The quick brown fox jumps over the lazy dog"
    f = extract_linguistic_features(text)
    assert f.filler_word_count == 0
    assert f.filler_word_ratio == 0.0


def test_repetition_detection():
    text = "I I was going going to the store"
    f = extract_linguistic_features(text)
    assert f.repetition_count == 2


def test_empty_text_does_not_crash():
    f = extract_linguistic_features("")
    assert f.word_count == 0
    assert f.type_token_ratio == 0.0
    assert f.filler_word_ratio == 0.0


def test_moving_average_ttr_none_for_short_text():
    f = extract_linguistic_features("short text here")
    assert f.moving_average_ttr is None  # below default window of 25 tokens


def test_moving_average_ttr_computed_for_long_text():
    import itertools
    import string

    # NOTE: the tokenizer only matches alphabetic runs ([a-zA-Z']+), so
    # numeric suffixes like "word0".."word39" would all collapse to the
    # single token "word". Use distinct two-letter alphabetic tokens instead.
    words = ["".join(p) for p in itertools.islice(itertools.product(string.ascii_lowercase, repeat=2), 40)]
    text = " ".join(words)
    f = extract_linguistic_features(text)
    assert f.moving_average_ttr is not None
    assert 0.0 < f.moving_average_ttr <= 1.0
    assert f.moving_average_ttr == 1.0  # all 40 tokens are distinct
