# Evidex Agent Skills & Architectural Blueprint

This document specifies the skills, capabilities, and data contracts for the Evidex clinical trial analysis system.

---

## Skill 1: Single-Study PDF Extraction (Phase 1 - Locked)
- **Input:** Single RCT PDF (`data/raw/<study>.pdf`).
- **Processing:**
  - Fast page extraction and layout-aware chunking (`src/pdf_parser.py`).
  - 4-pass decomposed extraction (`src/extractor.py`):
    - Pass 1: Study Protocol & Treatment Arms with exact dosages.
    - Pass 2: 4-operator atomic eligibility criteria (`<`, `=`, `>`, `between`).
    - Pass 3: Table 1 Baseline Demographics & Lab values.
    - Pass 4: Clinical Efficacy Endpoints & Safety Adverse Events.
  - Multi-level Master Extraction Sheet with merged category blocks, variable matrix, and provenance audit trail.
- **Output:** Standardized multi-sheet Excel (`outputs/<study>_structured_extracted.xlsx`) & JSON.

---

## Skill 2: Active-Ingredient Cohort Pooling & Harmonization (Phase 2)
- **Directory Structure:** `analysis/<Active_Ingredient>/` (e.g., `analysis/Metformin/`, `analysis/Dapagliflozin/`, `analysis/Orlistat/`).
- **End-to-End Ingestion:**
  - Auto-extracts any raw `.pdf` in `analysis/<Active_Ingredient>/` using Phase 1 engine into `outputs/analysis/<Active_Ingredient>/extracted_trials/`.
  - Automatically loads and harmonizes all extracted Excel workbooks via `src/harmonize.py`.
- **Harmonization Invariants:**
  - Converts timepoints to common unit (weeks/months).
  - Normalizes laboratory units (e.g., blood glucose, HbA1c %, weight kg, lipid profiles).
  - Aligns control/placebo arms with active experimental dosage arms.

---

## Skill 3: `metafor`-Grade Meta-Analysis Engine
- **Effect Size Estimation:**
  - Continuous: Mean Difference (MD) & Standardized Mean Difference (SMD, Hedges' $g$).
  - Dichotomous: Odds Ratio (OR), Risk Ratio (RR), and Risk Difference (RD) with 0.5 zero-cell correction.
- **Pooling Algorithms:**
  - Fixed-Effect (Inverse-Variance).
  - Random-Effects: DerSimonian-Laird (DL) & Restricted Maximum Likelihood (REML).
- **Heterogeneity & Reliability:**
  - Cochran's $Q$ test statistic, degrees of freedom, $p$-value.
  - Higgins' $I^2$ (%) and between-study variance $\tau^2$.
  - 95% Confidence Intervals & **95% Prediction Intervals (PI)** for future trial outcomes.
  - Leave-One-Out Sensitivity Analysis and Egger's regression test for funnel asymmetry.

---

## Skill 4: Predictive Analytics & Virtual Trial Simulator
- **Dose-Duration-Response Meta-Regression:**
  - Models relationship between active ingredient dosage ($mg$), duration ($weeks$), baseline covariates, and outcome change.
- **Virtual Trial Outcome Projection:**
  - Predicts expected outcome effect size and 95% Prediction Interval for unmeasured dosages or extended follow-up durations.
  - Estimates clinical Number Needed to Treat (NNT).
  - Generates automated Executive Clinical Verdict summarizing evidence consistency, optimal dose-duration sweet spot, and projected outcomes.

---

## Skill 5: Interactive Executive Dashboard
- **Web Interface:** Interactive Gradio dashboard integrated into `app.py` with Plotly interactive charts.
- **Export Formats:**
  - `<Drug_Name>_Master_Comparison_and_Meta_Analysis.xlsx` (6 comprehensive multi-level sheets).
  - `<Drug_Name>_Executive_Dashboard.html` (Standalone, interactive self-contained HTML report).
