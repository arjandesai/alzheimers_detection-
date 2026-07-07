"""Medical-safety guardrail, enforced in CI, not just at review time.

This project must never claim to diagnose Alzheimer's disease (see
core/disclaimers.py module docstring and docs/DISCLAIMER.md). This test
greps user-facing source files for banned phrasing so a regression is
caught automatically rather than relying on every contributor remembering
the rule.

Deliberately scoped to src/ (shipped code), not tests/ or docs/, since
docs legitimately need to talk *about* diagnosis in the "we do not
diagnose" sense, and this file itself needs to say the banned words to
define them.
"""

from pathlib import Path

BANNED_PHRASES = [
    "you have alzheimer's",
    "you have dementia",
    "this diagnoses",
    "diagnosis: positive",
    "diagnosis: negative",
]

SRC_ROOT = Path(__file__).resolve().parent.parent / "src"


def _all_source_files():
    return list(SRC_ROOT.rglob("*.py"))


def test_no_banned_diagnostic_phrases_in_source():
    violations = []
    for path in _all_source_files():
        content = path.read_text(encoding="utf-8").lower()
        for phrase in BANNED_PHRASES:
            if phrase in content:
                violations.append((str(path), phrase))
    assert not violations, f"Banned diagnostic language found: {violations}"


def test_disclaimer_module_defines_required_constants():
    from alzheimers_detection.core import disclaimers

    for name in ("GENERAL_DISCLAIMER", "RESULT_FOOTER", "RESEARCH_USE_ONLY"):
        assert hasattr(disclaimers, name)
        assert len(getattr(disclaimers, name)) > 20


def test_speech_result_schema_requires_disclaimer_field():
    from alzheimers_detection.speech.schemas import SpeechAnalysisResult

    assert "disclaimer" in SpeechAnalysisResult.model_fields
    assert "limitations" in SpeechAnalysisResult.model_fields
