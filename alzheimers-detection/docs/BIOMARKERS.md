# Speech Biomarkers: What's Established vs. What's Exploratory

This tracks the evidence basis for each feature implemented in
`src/alzheimers_detection/speech/`. "Confidence" is a qualitative summary of
how consistently a direction of effect has been reported, not a formal
meta-analytic estimate — treat it as a starting point for literature review,
not a substitute for it.

| Feature | Direction reported in AD/MCI literature | Confidence | Notes |
|---|---|---|---|
| Speech rate (wpm) | Reduced vs. healthy controls | Established | One of the most replicated findings in spontaneous-speech AD studies |
| Pause frequency / long-pause ratio | Increased | Established | Associated with word-finding difficulty and reduced fluency |
| Articulation rate vs. speech rate gap | Widens (more pause-dominated) | Moderate | Less consistently isolated from overall speech rate across studies |
| Lexical diversity (TTR / MATTR) | Reduced | Established | Confounded by transcript length if raw TTR is used — MATTR preferred |
| Filler word rate | Increased | Moderate | Also affected by individual speaking style, not disease-specific alone |
| Pronoun-to-noun ratio | Increased | Moderate | Reflects "semantic emptying" of language; effect sizes vary across studies |
| Pitch variation (F0 std) | Reduced (flatter prosody) | Exploratory | Reported in some studies; less consistently replicated than timing features |
| Jitter / shimmer | Mixed findings | Exploratory | Primarily voice-quality/dysarthria markers; AD-specific signal is weaker and less established than in e.g. Parkinsonian speech |
| Repetition rate | Increased | Moderate | Requires careful distinction from normal disfluency; our regex-based detector is a coarse proxy (see Limitations) |

## How this maps to code

Each field in `speech/schemas.py::AcousticFeatures` and `::LinguisticFeatures`
carries a docstring summarizing the *direction* reported in the literature.
None of these are wired to a validated per-feature clinical threshold yet —
the `_REFERENCE_RANGES` dict in `speech/pipeline.py` is explicitly marked as
an **unvalidated placeholder** pending either (a) published reference ranges
with proper citations, or (b) a validation pass against approved
DementiaBank/ADReSS data once access is available. Do not treat the current
ranges as clinically meaningful — they exist so the explainability plumbing
(risk bands, contributing-feature reports) has something to compute over
during early development.

## Regulatory framing

This document is a literature summary for engineering purposes, not a
clinical evidence dossier. An actual regulatory submission would need a
systematic literature review, formal effect-size/meta-analysis, and
validation on held-out clinical data — well beyond what a codebase README
can establish.
