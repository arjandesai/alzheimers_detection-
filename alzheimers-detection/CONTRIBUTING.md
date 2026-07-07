# Contributing

Thanks for considering contributing. A few things specific to this project,
on top of normal good-PR practice:

## Data safety (read this first)

- **Never commit files from gated corpora** (DementiaBank, ADReSS, ADNI,
  etc.), even small samples "just for a test fixture." Use hand-written
  synthetic fixtures instead (see `tests/test_dementiabank_loader.py` for
  the pattern — a few lines of CHAT-like syntax, not real transcripts).
- If you're testing against your own approved DementiaBank access locally,
  keep it under `data/` (gitignored) and double-check `git status` before
  committing.

## Medical-safety language

- All user-facing disclaimer/result text lives in
  `src/alzheimers_detection/core/disclaimers.py`. Don't write new
  disclaimer copy inline in a route or pipeline function.
- Don't introduce language implying diagnosis ("this patient has...",
  "positive for Alzheimer's", etc.). `tests/test_no_diagnostic_language.py`
  greps for a baseline list of banned phrases in CI — treat a passing test
  as a floor, not a ceiling; use judgment for anything not on that list.
- If a new feature or model output could plausibly be read as diagnostic
  by a non-expert user, it needs an explicit limitations entry (see
  `speech/pipeline.py::LIMITATIONS`) and reviewer sign-off before merging.

## Code standards

- Type hints on new public functions; `mypy` runs in CI.
- `ruff check` must pass.
- New logic needs tests that run in the default (`not slow`) test suite —
  i.e. without downloading real ASR models or needing gated data. See
  `tests/conftest.py::FakeASREngine` for the pattern of testing pipeline
  logic without a real model.
- Optional heavy dependencies (new ASR backends, CV models, etc.) should be
  imported lazily inside the function/class that needs them, with a clear
  ImportError message pointing at which extra to install — follow the
  pattern in `speech/transcription.py` and `speech/acoustic_features.py`.

## Adding a new biomarker feature

1. Add the field to the relevant Pydantic model in `speech/schemas.py` with
   a docstring summarizing what it measures and, if applicable, the
   direction reported in the literature.
2. Implement extraction in the relevant module (`acoustic_features.py` /
   `linguistic_features.py`), as a pure function where possible for
   testability.
3. Add an entry to `docs/BIOMARKERS.md` with an honest confidence level
   (Established / Moderate / Exploratory) and a note on why.
4. Write unit tests with synthetic inputs covering at least: a typical case,
   an edge case (empty/very short input), and the documented direction of
   effect.

## Adding a new modality (handwriting, drawing, etc.)

Follow the structural pattern established by `speech/`: schemas.py (data
contracts) → feature extraction module(s) → pipeline.py (orchestration,
explainability, limitations) → api/routes/. Don't skip the limitations list
or the disclaimer wiring just because it's "obviously the same as speech" —
copy the pattern explicitly so it's easy to audit.

## Pull requests

- Keep PRs scoped to one milestone/feature area where possible.
- Update `docs/ARCHITECTURE.md`'s roadmap section if you complete or start a
  roadmap item.
- CI must be green (lint, type check, tests, Docker build) before review.
