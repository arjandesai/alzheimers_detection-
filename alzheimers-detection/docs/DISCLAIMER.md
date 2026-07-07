# Medical Disclaimer

**This software is not a medical device.** It has not been evaluated,
cleared, or approved by the FDA or any other regulatory body for the
diagnosis, treatment, cure, or prevention of any disease, including
Alzheimer's disease or any other form of dementia or cognitive impairment.

## What this project is

A research and engineering platform for exploring digital biomarkers
(speech, and eventually other modalities) that have been studied in
peer-reviewed literature as correlating with cognitive aging patterns. It
extracts transparent, individually-inspectable features and reports how they
compare to broad reference patterns from published research.

## What this project is not

- It is **not** a diagnostic tool. It cannot and does not determine whether
  any individual has Alzheimer's disease, MCI, or any other condition.
- It is **not** a substitute for evaluation by a qualified clinician,
  neurologist, or neuropsychologist.
- Results ("risk bands," feature deviations) reflect statistical pattern
  comparison against group-level published reference ranges — not a
  probability of disease for any individual.
- A "low" risk band does **not** mean a person does not have cognitive
  impairment, and an "elevated" band does **not** mean they do. Many
  non-disease factors (fatigue, non-native language, hearing difficulty,
  anxiety, recording quality, unrelated speech or motor conditions) can move
  these features.

## If you are concerned about cognitive changes

Please speak with a doctor. Early evaluation by a qualified professional is
the right path for a concern about memory or thinking changes — not a
self-administered digital tool. If you are in the US, your primary care
provider can refer you to a neurologist or memory clinic; the Alzheimer's
Association operates a 24/7 helpline at 1-800-272-3900 for information and
support.

## For contributors

Every user-facing surface (API responses, any future UI) must include the
disclaimer text centralized in `src/alzheimers_detection/core/disclaimers.py`.
Do not write new disclaimer copy inline — import from that module so legal/
clinical review stays centralized. `tests/test_no_diagnostic_language.py`
enforces a baseline guardrail against banned diagnostic phrasing in CI, but
passing that test is a minimum bar, not a substitute for careful review of
any new user-facing copy.
