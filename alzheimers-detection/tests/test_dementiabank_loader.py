"""Tests use a tiny, hand-written CHAT-format snippet -- NOT real
DementiaBank data (which this repo never includes; see
data/loaders/dementiabank.py docstring). It just mimics the syntax
closely enough to exercise the parser.
"""

import pytest

from alzheimers_detection.data.loaders.dementiabank import (
    DementiaBankParseError,
    chat_utterances_to_transcript,
    parse_chat_file,
)

SAMPLE_CHAT = (
    "@Begin\n"
    "@Participants:\tPAR Participant, INV Investigator\n"
    "*INV:\tcan you tell me what you see in this picture ?\n"
    "*PAR:\tthe boy is climbing on the stool \x15500_2300\x15\n"
    "*PAR:\tand the water is running over \x152400_4100\x15\n"
    "*INV:\tanything else ?\n"
    "*PAR:\tthe mother is drying dishes \x154200_5900\x15\n"
    "@End\n"
)


@pytest.fixture
def sample_chat_file(tmp_path):
    path = tmp_path / "sample001.cha"
    path.write_text(SAMPLE_CHAT, encoding="utf-8")
    return path


def test_parse_chat_file_extracts_all_speaker_turns(sample_chat_file):
    utterances = parse_chat_file(sample_chat_file)
    # 2 INV turns + 3 PAR turns in the fixture
    assert len(utterances) == 5
    speakers = {u.speaker for u in utterances}
    assert speakers == {"PAR", "INV"}


def test_missing_file_raises():
    with pytest.raises(DementiaBankParseError):
        parse_chat_file("/nonexistent/path.cha")


def test_transcript_excludes_investigator_turns(sample_chat_file):
    utterances = parse_chat_file(sample_chat_file)
    transcript = chat_utterances_to_transcript(utterances)
    assert "boy" in transcript.text
    assert "anything else" not in transcript.text  # INV turn excluded


def test_transcript_word_timing_within_utterance_bounds(sample_chat_file):
    utterances = parse_chat_file(sample_chat_file)
    transcript = chat_utterances_to_transcript(utterances)
    first_par_words = [w for w in transcript.words if w.start >= 0.5 and w.end <= 2.3]
    assert len(first_par_words) > 0


def test_unknown_speaker_code_raises(sample_chat_file):
    utterances = parse_chat_file(sample_chat_file)
    with pytest.raises(DementiaBankParseError):
        chat_utterances_to_transcript(utterances, participant_speaker_code="XXX")
