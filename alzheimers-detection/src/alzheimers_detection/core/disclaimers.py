"""Centralized medical-safety language.

Every API response and report in this project must surface these strings
rather than re-authoring disclaimer text ad hoc. Keeping this in one module
means a legal/clinical reviewer only has to sign off on one place, and a
grep for `disclaimers.py` finds every surface that needs updating if the
language changes.

Hard rule enforced across this codebase: nothing in this project may emit
the words "diagnose", "diagnosis", or "you have Alzheimer's" in a
prediction context. See tests/test_no_diagnostic_language.py, which greps
the source tree for banned phrasing as a CI guardrail.
"""

from __future__ import annotations

GENERAL_DISCLAIMER = (
    "This tool estimates digital biomarker patterns associated with cognitive "
    "aging in published research. It is a research and screening-support tool, "
    "not a medical device, and it does not diagnose Alzheimer's disease, "
    "dementia, or any other condition. Only a qualified clinician can evaluate "
    "cognitive health. If you or someone you know is concerned about memory or "
    "thinking changes, please talk to a doctor."
)

RESULT_FOOTER = (
    "This result is a screening-support estimate based on limited digital "
    "biomarkers. It is not a diagnosis and should not be used to rule in or "
    "rule out any medical condition. Please discuss any concerns with a "
    "licensed healthcare provider."
)

LOW_DATA_WARNING = (
    "This result is based on a short or partial sample and has lower "
    "reliability than a full assessment. Treat it as provisional."
)

RESEARCH_USE_ONLY = (
    "Research/screening-support use only. Not evaluated or cleared by the "
    "FDA or any regulatory body as a diagnostic device."
)


def risk_band_language(band: str) -> str:
    """Map an internal risk band to clinician-safe, non-alarmist phrasing.

    We deliberately avoid words like "positive", "negative", "high risk of
    Alzheimer's" -- those imply diagnostic certainty this system cannot
    provide. Bands describe *pattern consistency with published biomarker
    ranges*, not disease probability.
    """
    mapping = {
        "low": (
            "Patterns observed are broadly consistent with samples from "
            "cognitively unimpaired reference groups in the literature this "
            "tool draws on."
        ),
        "moderate": (
            "Some patterns observed fall outside the typical reference range "
            "seen in cognitively unimpaired groups in the literature. This is "
            "common and does not by itself indicate impairment."
        ),
        "elevated": (
            "Several patterns observed fall outside the typical reference "
            "range seen in cognitively unimpaired groups in the literature. "
            "Consider discussing a full cognitive evaluation with a doctor."
        ),
        "insufficient_data": (
            "Not enough usable signal was extracted from the input to "
            "produce a reliable estimate."
        ),
    }
    if band not in mapping:
        raise ValueError(f"Unknown risk band: {band!r}")
    return mapping[band]
