# Evidex — Design Notes

AI-assisted Structured Data Extraction, Evidence Synthesis & Predictive
Analytics from Randomized Controlled Trials (RCTs).

Working language: Arabic docs, English field names / identifiers.

---

## 1. Goal

Convert facts embedded in RCT PDFs (text + tables) into a **verified,
atomic, harmonised** tabular dataset, then (if data allow) descriptive
statistics / meta-analysis feasibility / predictive modelling.

Non-goals (explicitly):

- We are **not** building a systematic review or a clinical guideline.
- We do **not** infer or invent values. Absent data are marked `not_reported`.
- A model output does **not** establish causation or diagnosis.

## 2. Record-level model (الخطوة 1)

One row = **one atomic fact** that can be traced back to a location in the PDF.
We never put an entire study into one row, and we never put an entire table
into one cell.

```
Study 1 ──── n
 ├── Arms ──────── n        (intervention / comparator, dose, n, duration)
 ├── Eligibility ─ n        (one criterion per row)
 ├── Outcomes ─── n         (arm × outcome × timepoint)
 ├── Baseline ─── n         (arm × variable)
 └── Provenance ─ n         (record → page + verbatim quote)
```

Canonical entities (single source of truth: `src/canonical.py`):

| Entity          | Sheet            | Grain (one row =)                     |
|-----------------|------------------|---------------------------------------|
| `Study`         | `Studies`        | one trial                             |
| `Arm`           | `Arms`           | one treatment arm within a trial      |
| `Eligibility`   | `Eligibility`    | one inclusion/exclusion criterion     |
| `Outcome`       | `Outcomes`       | one measurement (arm × outcome × time)|
| `Provenance`    | `Provenance`     | one extracted record → its source     |
| `Validation_Log`| `Validation_Log` | one automated/human check per record  |
| (derived)       | `Flattened_View` | one outcome joined with arm context   |

`schema/data_dictionary.csv` and `schema/extraction_schema.json` are **generated**
from `src/canonical.py`, so the dictionary, the prompt and the validator can
never drift apart. Regenerate with `python -m src.generate_schema`.

## 3. Data dictionary & atomic fields (الخطوة 2)

Rules (from the concept note):

1. **Atomic split** — a cell holds exactly one fact.
   - `65 mg` → `value=65`, `unit=mg` (never one cell "65 mg").
   - `≥ 18 years` → `operator=">="`, `value=18`, `unit="years"`.
   - `20–65 years` → `min_value=20`, `max_value=65`, `unit="years"`.
2. **Operator column** is constrained to a fixed vocabulary
   (`=`, `>`, `>=`, `<`, `<=`, `between`) instead of ad-hoc flags.
3. **Units** are canonical strings; conversions are logged, never silent.
4. **Missing** → `null` + `reported="no"` (or `not_reported`), never guessed.

See `schema/data_dictionary.csv` (machine-readable) and
`schema/extraction_schema.json` (JSON Schema handed to the model).

## 4. Extraction pipeline (الخطوة 4)

```
PDF
 → pdf_text (pypdf)  [src/pdf_text.py]
 → segment (pages / sections / tables)  [src/segment.py]
 → extract (LLM or deterministic backend)  [src/extract.py]
 → validate (JSON Schema + cross-field rules)  [src/validate.py]
 → export Excel/CSV (Studies, Arms, Outcomes, Eligibility, Provenance, Validation_Log)
 → harmonise across studies (name matching + unit unification)  [src/harmonize.py]
 → score against gold standard  [src/score.py]
```

Every extracted record carries `source_page` + `exact_source_text`
(verbatim quote) so each value is verifiable.

Backends (pluggable via `src/extract.py --backend`):

- `openai`   — OpenAI-compatible chat completions with JSON Schema / structured output.
- `anthropic` — Anthropic Messages API.
- `rules`    — deterministic, offline baseline (heuristics over extracted
  text/tables). Always available; used to build the gold standard and to smoke-test.

## 5. Prompting (الخطوة 5)

- Role: *clinical-trial data extraction assistant*.
- Extract **only explicitly reported facts** — no summarising, no interpretation.
- Always return **valid JSON** matching the supplied schema.
- Separate numeric value, operator and unit.
- Keep `study_id`, `arm_id`, outcome and timepoint context.
- Include `source_page` + `exact_source_text` per record.
- If absent/unclear → `null` + `review_required=true`.
- Never infer, calculate or invent. Never merge arms or timepoints.
- Precede with a few-shot example + the data dictionary's allowed values.
- Iterate on a **fixed test set** until accuracy is acceptable; keep prompts
  versioned under `prompts/`.

## 6. Evaluation (الخطوة 6)

Two annotators extract the same studies manually → **gold standard**
(field-level). Score the system on: per-field accuracy, unit/operator/range
match, source-backed ratio, time per study, and % records flagged for human
review. Errors are reviewed and the system improved before scaling.

## 7. Evidence synthesis (الخطوة 7-8)

- **Identification & harmonisation** — match variables across studies despite
  name drift (`BMI` vs `body mass index`), unify units/definitions/timepoints,
  while preserving true differences in populations, interventions and outcomes.
- **Descriptive** — distributions, intervention/outcome counts, gaps, heterogeneity.
- **Meta-analysis** — only if question, design and data are suitable, under an
  independent protocol. Merging tables ≠ systematic review.

## 8. Predictive analytics (الخطوة 8)

- **IPD available (with permissions)** → model an outcome from patient
  characteristics; train/test + external validation; assess bias & calibration.
- **Aggregate published results only** → do **not** claim individual risk
  prediction. Study-level analysis / meta-regression only, watching for the
  ecological fallacy.

## 9. Scope discipline

What this project **is**: structured data extraction / data curation — the
front end of a path that *may* include data mining. Analysis and prediction are
subsequent stages, and analysing published data alone proves neither causation
nor diagnosis.

## 10. Directory layout

```
D:\Evidex
├── data/
│   ├── raw/           source PDFs
│   └── manual/        manual (gold-standard) extractions
├── schema/            data_dictionary.csv, extraction_schema.json
├── prompts/           versioned prompts
├── src/               pipeline code
├── outputs/           extracted / validated / scored artefacts
├── docs/              DESIGN.md, concept note
└── config/            backend + API settings (git-ignored secrets)
```
