# MANDOROS — Agent Skills & Architectural Blueprint
**MANDOROS**: *Meta-Analysis Network for Data, Outcomes & Research Optimization Synthesis*  
*"From Raw Trials to Global Clinical Verdicts. — Smarter Evidence. Better Decisions."*

This document defines the skills, capabilities, and data contracts for MANDOROS.

---

## Skill 1: Single-Study PDF Extraction (Phase 1 - Locked)
- **Input:** Single RCT PDF (`data/raw/<study>.pdf` or web upload).
- **Processing:**
  - Layout-aware PDF decomposition and table extraction (`src/pdf_parser.py`).
  - 4-pass multi-stage extraction (`src/extractor.py`):
    - Pass 1: Study Protocol & Treatment Arms with exact dosages and regimens.
    - Pass 2: 4-operator atomic eligibility criteria (`<`, `<=`, `=`, `>`, `>=`, `between`).
    - Pass 3: Baseline Demographics & Laboratory values.
    - Pass 4: Clinical Efficacy Endpoints & Safety Adverse Events.
  - Verification & provenance cross-referencing.
- **Output:** Standardized 7-sheet individual Excel workbook (`outputs/<study>_structured_extracted.xlsx`) & JSON.

---

## Skill 2: Mandatory Stage-1 Pre-Extraction Law
- Whenever raw `.pdf` files exist in `analysis/<Cohort_Name>/` or are uploaded in the Phase-2 Cohort UI tab:
  - Skill 1 runs automatically on each PDF first.
  - Individual `<study_id>_structured_extracted.xlsx` workbooks are saved in `outputs/analysis/<Cohort_Name>/extracted_trials/` and copied to root `outputs/`.
  - All individual Excels are packaged into `<Cohort_Name>_Individual_Stage1_Trial_Excels.zip`.
  - Phase 2 exclusively consumes these structured Stage-1 Excels.

---

## Skill 3: Intelligent Adaptive Cohort Pooling & Harmonization
- **Cohort Mode Detection:** Classifies cohorts into *Homogeneous Single-Drug*, *Multi-Drug Shared-Indication*, or *Heterogeneous Exploratory* modes.
- **Drug & Regimen Normalization:** Extracts `Active_Ingredient`, `Dose_Value`, `Dose_Unit`, and `Regimen_Frequency`.
- **Harmonization (`src/harmonize.py`):** Canonical unit transformation, duration conversion, and alias reconciliation against `src/canonical.py`.

---

## Skill 4: `metafor`-Grade Meta-Analysis & Domain Bridging
- **Tier 1 (Exact Parameters):**
  - Continuous: Mean Difference (MD) with 95% CI and 95% Prediction Interval.
  - Dichotomous: Odds Ratio (OR), Risk Ratio (RR), Risk Difference (RD).
  - Inverse-variance fixed-effect, DerSimonian-Laird (DL) and REML random-effects models.
  - Cochran's $Q$, $I^2$ (%), $\tau^2$, and Egger's funnel asymmetry test.
- **Tier 2 (Clinical Domain Bridging):**
  - Unifies non-identical outcomes into Clinical Domains (*Anthropometric & Weight*, *Glycemic & Metabolic*, *Cardiovascular/Lipid*, *Adherence & Safety*).
  - Computes scale-free Standardized Mean Difference (Hedges' $g$) and baseline-adjusted percentage change (%Δ).
- **Tier 3 (Longitudinal Normalization):**
  - Reconciles disparate follow-up horizons via monthly rate-of-change meta-regression.
- **Subgroup & Network Meta-Analysis:**
  - Subgroup Meta-Analysis across active ingredients and dosage tiers ($Q_{\text{between}}$, $p_{\text{between}}$).
  - Bucher anchored indirect comparisons and Monte Carlo SUCRA ranking hierarchy (0–100%).

---

## Skill 5: Divergence Transparency & Adaptation Reporting
- Explicit disclosure of:
  1. Active ingredient and dosage regimens.
  2. Follow-up horizons and durations.
  3. Patient population eligibility criteria discrepancy matrix (`df_eligibility`).
  4. Endpoint categorization (Exact Tier 1 vs Domain Tier 2 vs Unique).
  5. Plain-language comparative adaptation narrative (*"Specifically, because Study A measured [X] over [dur1]..."*).

---

## Skill 6: Predictive Analytics & Virtual Trial Simulator
- Multivariate WLS meta-regression across dose and duration.
- Real-time simulation of hypothetical/future trials with 95% Confidence and Prediction Intervals, NNT, and Extrapolation Reliability Rating.

---

## Skill 7: Apple Flagship UI & Multi-Format Reporting
- **Web App (`app.py`):** Dark Apple.com frosted glass bento layout, 3D ribbon emblem, 8-node pipeline strip (`M-A-N-D-O-R-O-S`), Apple Studio & GitHub Primer glowing upload dropzones, responsive tabs.
- **Live Cloud Deployment:** Continuous deployment on Render: [https://mandoros.onrender.com](https://mandoros.onrender.com).
- **Deliverables:**
  - `<Cohort_Name>_MANDOROS_Master_Report.xlsx` (10 biotechnology-styled sheets).
  - `<Cohort_Name>_MANDOROS_Executive_Dashboard.html` (Standalone interactive Plotly report).
  - `<Cohort_Name>_Individual_Stage1_Trial_Excels.zip` & multi-file individual Excel downloads.

---

## Skill 8: In-Silico Discovery & Emergent Synthesis Engine (`src/discovery_engine.py`)
- **Missing-Data Reconstruction & Matrix Completion:** Scans across pooled trials to identify unmeasured endpoints or missing timepoints and reconstructs them using cross-trial surrogate regressions, multivariate covariance imputation, and longitudinal trajectory models with 95% CIs and confidence scores.
- **Emergent Cross-Trial Hypotheses:**
  - *Therapeutic Sweet-Spot:* Inflection point of diminishing marginal efficacy and safety escalation.
  - *Hidden Super-Responder Phenotype:* Baseline severity and demographic predictors of amplified treatment response.
  - *Latent Biomarker Coupling:* Cross-trial covariance cascades between primary and secondary clinical outcomes.
- **De-Novo Virtual Clinical Trial Synthesis:**
  - Pharmacological Bliss independence / additive synergy modeling for novel multi-agent combination regimens or precision titration protocols.
  - Calculates required sample size $N$ for 90% power, predicted primary/secondary deltas, 95% Prediction Intervals, NNT, and Monte Carlo superiority probability vs existing trials.
- **Exported Deliverables:**
  - Master Excel Sheet 9: `In_Silico_New_Discoveries`.
  - Master Excel Sheet 10: `Synthesized_Virtual_Trial`.
  - Interactive Web UI Sub-Tab & Standalone HTML Dashboard comparison charts.
