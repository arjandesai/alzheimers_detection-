# alzheimers-detection

An open-source digital biomarker platform for **research and screening
support** around early cognitive decline — not a diagnostic tool. See
[docs/DISCLAIMER.md](docs/DISCLAIMER.md) before using or contributing.

> **Status: Milestone 1 (speech pipeline).** This is an early-stage project.
> One modality (speech) is implemented end-to-end and tested. Other
> modalities described in the long-term roadmap (handwriting, drawing,
> facial, typing, full cognitive test battery) are **not yet built** — see
> [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#roadmap-not-yet-built) rather
> than assuming they exist.

## What's implemented right now

- Audio → transcription (pluggable ASR: faster-whisper by default, OpenAI
  Whisper as fallback) with word-level timestamps
- Acoustic biomarker extraction: speech rate, articulation rate, pause
  statistics, and (if `parselmouth` is installed) pitch, jitter, shimmer
- Linguistic biomarker extraction: lexical diversity (TTR/MATTR), filler
  word rate, repetition detection, and (if `spacy`'s English model is
  installed) pronoun-to-noun ratio and sentence length
- A transparent, rule-based (not black-box ML) explainability report:
  which features deviate from reference patterns and in which direction
- A FastAPI service (`POST /api/v1/speech/analyze`) wrapping the pipeline
- A DementiaBank CHAT-format parser for contributors with their own
  **approved** TalkBank access (no data is bundled — see below)
- CI: lint (ruff), type check (mypy), tests (pytest), Docker build

## Why so much of the original scope isn't here yet

The starting brief for this project asked for 15 cognitive test instruments,
five sensing modalities, multimodal fusion, and FDA-readiness. Building
shallow stubs for all of that at once would produce code that reads as
comprehensive but is untested everywhere. Instead this repo builds one
modality for real, with real tests and honest documentation of its limits,
and expands modality-by-modality from there. See
[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) for the reasoning and the
roadmap.

**On "FDA-ready":** that's a regulatory and clinical-validation process
(predicate device comparison, clinical trials, quality management system,
FDA submission pathway), not something achieved through code alone. This
project does not claim FDA-readiness at any milestone unless that process
has actually happened.

## Datasets

This project uses **only real, documented datasets** — see
[docs/DATASETS.md](docs/DATASETS.md) for exactly what's available, what
license/access terms apply, and how to integrate them. Short version: the
most relevant speech corpora (DementiaBank/Pitt Corpus, ADReSS) are
access-controlled by TalkBank and are **not included in this repository**.
You'll need your own approved access to use the DementiaBank loader.

## Quickstart

```bash
git clone https://github.com/arjandesai/alzheimers_detection- alzheimers-detection
cd alzheimers-detection
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev,speech]"
cp .env.example .env

# Run tests (no gated data or model downloads required)
pytest -m "not slow"

# Run the API locally
uvicorn alzheimers_detection.api.main:app --reload
# then POST an audio file to http://localhost:8000/api/v1/speech/analyze
# interactive docs at http://localhost:8000/docs
```

Or with Docker:

```bash
docker compose up --build
```

## Project layout

See [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md#repository-layout).

## Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md). Highlights:
- No `.cha`/audio files from gated corpora get committed — `.gitignore`
  blocks the obvious cases, but review your diffs.
- New features need tests that run without gated data (use the fake ASR
  engine in `tests/conftest.py` as a pattern).
- Any new user-facing text goes through `core/disclaimers.py`, not inline
  strings — see `tests/test_no_diagnostic_language.py`.

## License

MIT for the code in this repository (see [LICENSE](LICENSE)) — chosen
because it's permissive enough for both academic and commercial reuse while
requiring attribution, which fits an open research tool intended to be
built on. This license does **not** extend to third-party datasets
referenced in docs/DATASETS.md, which have their own separate terms.
