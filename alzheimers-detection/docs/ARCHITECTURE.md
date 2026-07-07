# Architecture (Milestone 1 — speech pipeline)

## Why speech-first, not "all modalities at once"

The original project scope spans speech, handwriting, drawing, facial video,
typing dynamics, and 15 cognitive test instruments. Building thin stubs for
all of those at once would produce a lot of code that *looks* comprehensive
but is untested and unvalidated everywhere. Speech was chosen to go first
because:
1. It has the deepest peer-reviewed literature base of any digital biomarker
   here (DementiaBank/Pitt Corpus work goes back decades).
2. Open tooling (Whisper-family ASR, Praat/parselmouth) is mature enough to
   build a real pipeline today, not a mocked one.
3. It cleanly demonstrates the pattern (ASR → signal features → linguistic
   features → explainable fusion) that later modalities (handwriting,
   drawing) will reuse structurally, even though their feature extractors
   will differ.

## Data flow

```
 audio file/bytes
        |
        v
 ASREngine.transcribe()          (speech/transcription.py)
        |
        v
   Transcript (text + word-level timestamps)
        |
        +----------------------------+
        v                            v
 extract_acoustic_features()   extract_linguistic_features()
 (speech/acoustic_features.py)  (speech/linguistic_features.py)
        |                            |
        +-------------+--------------+
                       v
              _compute_risk_band()
              (speech/pipeline.py)
                       |
                       v
             SpeechAnalysisResult
        (transcript + features + risk band +
         contributing features + limitations +
         disclaimer -- speech/schemas.py)
                       |
                       v
              FastAPI route returns JSON
              (api/routes/speech.py)
```

## Key design decisions

- **ASR is an abstract interface (`ASREngine`), not a hardcoded call.**
  Pause/speech-rate features depend on word-level timestamps, which makes
  ASR a hard dependency of feature extraction, not an optional add-on. A
  swappable interface lets a contributor plug in wav2vec2-CTC alignment,
  the Whisper API, or a test double without touching the pipeline.
- **Every ML/audio dependency is imported lazily and fails soft.**
  `faster-whisper`, `parselmouth`, and `spacy` are all optional extras.
  Their absence degrades individual feature fields to `None` rather than
  crashing the whole pipeline — important because this repo will be run by
  contributors who may only want to touch, say, the linguistic-feature code
  and shouldn't need a GPU or a Praat install just to run the test suite.
- **No black-box diagnostic classifier yet.** The current "risk band" is a
  transparent, rule-based comparison against explicitly-labeled
  *unvalidated placeholder* reference ranges (see docs/BIOMARKERS.md). A
  learned fusion model is a later milestone, gated on having real labeled
  data (DementiaBank/ADReSS) and a validation methodology — not something
  to fake with synthetic data and call production-ready.
- **Privacy-by-default.** `analyze_audio_bytes()` writes to a temp file that
  is deleted immediately after processing unless `ALZDX_KEEP_UPLOADED_AUDIO`
  is explicitly set. No audio or transcript is persisted to a database in
  this milestone — there isn't one yet (see Roadmap).

## Repository layout

```
src/alzheimers_detection/
  core/            # config, centralized medical-safety disclaimer text
  speech/          # transcription, acoustic + linguistic feature extraction,
                    # pipeline orchestration, pydantic schemas
  data/loaders/     # parsers for external corpora (DementiaBank CHAT format)
                    # -- parses locally-held, user-provided approved data only
  api/             # FastAPI app + routes
tests/             # unit + API tests, all runnable without gated data or
                    # real model downloads (see tests/conftest.py FakeASREngine)
docs/              # this file, DATASETS.md, BIOMARKERS.md, DISCLAIMER.md
```

## Roadmap (not yet built)

- **Milestone 2:** Literature-backed, cited reference ranges replacing the
  current placeholder thresholds; expand test coverage against real
  (locally-held, approved) DementiaBank samples.
- **Milestone 3:** Persistence layer (PostgreSQL) + auth, so results can be
  saved across sessions; audit logging for HIPAA/GDPR-conscious design.
- **Milestone 4:** Second modality (likely Clock Drawing Test via CV, given
  literature depth second only to speech).
- **Milestone 5+:** Multi-modal fusion scoring, once ≥2 modalities exist for
  real — fusing one real modality with four stubs would be fake precision.
