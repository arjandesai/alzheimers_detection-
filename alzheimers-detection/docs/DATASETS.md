# Datasets

This project uses only real, publicly documented research datasets. Nothing
here is invented, and **no dataset is bundled with this repository** — several
of the most relevant ones are access-controlled by their maintainers and
redistributing them would violate their terms. This document exists so
contributors know exactly what to apply for and what to expect.

## Speech / language

### DementiaBank — Pitt Corpus
- **What it is:** Longitudinal spontaneous-speech corpus collected 1983–1988.
  A commonly analyzed subset is 101 cognitively healthy controls and 181
  patients with Alzheimer's disease describing the "Cookie Theft" picture
  from the Boston Diagnostic Aphasia Examination. Audio plus CHAT-format
  transcripts (pauses, repetitions, errors annotated).
- **Access:** Managed by the TalkBank project (Carnegie Mellon University).
  Requires registration and approval; rules published at
  https://talkbank.org/share/rules.html. No co-authorship or DementiaBank
  affiliation is required to use approved data, but a sponsoring
  institution/PI is typically expected.
- **License:** Not redistributable. You may publish derived, non-identifying
  results (features, aggregate statistics, model weights trained on it) per
  TalkBank's citation rules, but not the raw corpus itself.
- **Integration point in this repo:**
  `src/alzheimers_detection/data/loaders/dementiabank.py` — a CHAT-format
  parser you point at your own locally-approved copy via `ALZDX_DATA_DIR`.
  This repo's `.gitignore` excludes `data/` and `*.cha` so approved data
  never accidentally gets committed.
- **Limitations:** Not age/gender balanced; 1980s recording equipment;
  English only; small by modern ML standards (~280 participants).

### ADReSS / ADReSSo Challenge
- **What it is:** A balanced (age, gender) subset derived from Pitt Corpus,
  purpose-built as an ML benchmark with matched train/test splits.
- **Access:** Same TalkBank gate as Pitt Corpus.
- **License:** Same redistribution restriction as Pitt Corpus.
- **Why it matters for this project:** Because it's demographically
  balanced, it's a better benchmark for isolating disease-related signal
  from confounds like age and gender than the raw Pitt Corpus is.

## Neuroimaging

### OASIS (Open Access Series of Imaging Studies)
- **What it is:** Structural MRI across normal aging and AD, some releases
  paired with clinical/cognitive scores (CDR, MMSE).
- **Access:** Free registration at oasis-brains.org. No institutional review
  process — the lowest-friction dataset on this list.
- **License:** Open for research use with attribution per OASIS's data use
  terms.
- **Status in this project:** Not yet integrated (Milestone 1 is speech-only).
  Natural candidate for a future imaging-based biomarker milestone.

### ADNI (Alzheimer's Disease Neuroimaging Initiative)
- **What it is:** Large multimodal longitudinal dataset — MRI, PET, CSF
  biomarkers, genetics, cognitive/clinical scores.
- **Access:** Requires accepting a Data Use Agreement and submitting an
  online application stating institutional affiliation and proposed use,
  reviewed by ADNI's Data Sharing and Publications Committee (typically
  ~2 weeks). Approved accounts get LONI IDA login access. **Access expires
  annually unless you submit a progress-report renewal** — this is not a
  one-time download, and needs to be budgeted for as ongoing maintenance,
  not a setup step.
- **License:** Per ADNI Data Use Agreement; publications must follow ADNI's
  acknowledgement/authorship policy.
- **Status in this project:** Not yet integrated.

## Other

### PhysioNet
- **What it is:** Umbrella repository for many physiological datasets;
  access level varies per dataset (some fully open, some require PhysioNet
  Credentialing / CITI training).
- **Status:** Not currently used; would need a dataset-by-dataset evaluation
  if a specific PhysioNet corpus (e.g. gait or EEG data relevant to
  cognitive decline) becomes relevant to a future milestone.

### OpenNeuro
- **What it is:** Fully open neuroimaging data repository (BIDS format), no
  access gate.
- **Status:** Good for prototyping data pipelines without waiting on
  approval, but has no dataset curated specifically for AD/MCI screening —
  would need manual identification of relevant studies.

## What this means for contributors

If you fork this repo, you will **not** get working models out of the box for
anything trained on DementiaBank/ADReSS/ADNI, because none of that data ships
here and none of it can be auto-downloaded. What you do get:
- A fully working, testable feature-extraction pipeline that runs on any
  audio you provide (e.g. your own recordings).
- A parser ready to consume DementiaBank CHAT files the moment *you* have
  your own approved access.
- Synthetic/fixture-based tests that don't require any gated dataset, so CI
  is fully green without anyone needing special access.
