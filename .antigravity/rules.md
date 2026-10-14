# MANDOROS — Architectural, Methodological & Governance Rules
**MANDOROS**: *Meta-Analysis Network for Data, Outcomes & Research Optimization Synthesis*  
*"From Raw Trials to Global Clinical Verdicts. — Smarter Evidence. Better Decisions."*

---

## 1. Core Source of Truth & Zero Hallucination
- **Single Source of Truth (`src/canonical.py`):** `src/canonical.py` is the immutable canonical anchor for parameter naming, synonyms, units, and conversion factors.
- **Strict Data Integrity:** Zero hallucination policy. Unreported clinical metrics must be represented as `not_reported` or `None`.
- **Atomic Criterion Independence:** Strict separation of numeric `value`, comparison `operator` (`<`, `<=`, `=`, `>`, `>=`), and `unit`.

---

## 2. Phase 1 Immutability (Locked Single-Study Workflow)
- **Single-Study Pipeline (`data/raw/` -> `outputs/`):** Preserve the existing single-study extraction pipeline, validation rules, and 7-sheet individual Excel workbook structure (`Studies`, `Arms`, `Eligibility`, `Outcomes`, `Provenance`, `Validation_Log`, `Flattened_View`).
- **User Interface & API Flow:** Maintain the single-study interface, theme, model auto-detection, and BYOK (bring-your-own-key) flow without regression.

---

## 3. Strict Stage-1 Extraction Law (Phase 2 Cohort Prerequisite)
- **Mandatory Individual Extraction:** Whenever raw `.pdf` files are placed in `analysis/<Cohort_Name>/` or uploaded via the Phase-2 Cohort Web UI tab:
  1. Stage-1 extraction MUST execute first for every PDF, producing `<study_id>_structured_extracted.xlsx` (complete 7-sheet workbook) and structured JSON.
  2. Save workbooks in `outputs/analysis/<Cohort_Name>/extracted_trials/` AND copy to root `outputs/`.
  3. Package all individual workbooks into `<Cohort_Name>_Individual_Stage1_Trial_Excels.zip` for instant user download alongside the pooled Master Report.
  4. Phase 2 strictly consumes these Stage-1 Excel workbooks.

---

## 4. `metafor`-Grade Statistical Standards in Python
All statistical meta-analyses adhere to Cochrane Handbook and `wviechtb/metafor` standards:
- **Effect Sizes:**
  - Continuous: Mean Difference (MD) & Standardized Mean Difference (SMD, Hedges' $g$ with exact small-sample correction $J(df) = 1 - \frac{3}{4df - 1}$).
  - Dichotomous: Odds Ratio (OR), Risk Ratio (RR), and Risk Difference (RD) with Haldane-Anscombe 0.5 zero-cell adjustment.
- **Pooling Models:**
  - Fixed-Effect Model (Inverse-Variance weights $w_i = 1 / v_i$).
  - Random-Effects Model using DerSimonian-Laird (DL) and Restricted Maximum Likelihood (REML) estimators for $\tau^2$.
- **Precision & Prediction Intervals:**
  - 95% Confidence Intervals for pooled effect size: $[\hat{\theta} \pm 1.96 \cdot SE]$.
  - **95% Prediction Interval (PI):** $\hat{\theta} \pm t_{k-2, 0.975} \sqrt{SE^2 + \tau^2}$ to quantify expected effect in future unobserved trials.
- **Heterogeneity & Publication Bias:**
  - Cochran's $Q$, $p$-value, and Higgins' $I^2 = \max(0, \frac{Q - (k-1)}{Q}) \times 100\%$.
  - Egger's linear regression test for funnel plot asymmetry.

---

## 5. Intelligent Adaptive Multi-Drug & Heterogeneous Cohorts
- **Automatic Cohort Classification:**
  - *Mode A: Homogeneous Single-Drug Cohort*
  - *Mode B: Multi-Drug / Multi-Concentration Comparative Cohort*
  - *Mode C: Heterogeneous Exploratory Cohort*
- **Tiered Statistical Pooling:**
  - *Tier 1:* Direct harmonized parameter pooling.
  - *Tier 2:* Clinical Domain Bridging using scale-free Hedges' $g$ SMD and %Δ change.
  - *Tier 3:* Longitudinal rate normalization (change per month/week).
- **Subgroup & Network Meta-Analysis (NMA):**
  - Subgroup Meta-Analysis across active ingredients and dosage tiers with Cochran's $Q_{\text{between}}$ and $p_{\text{between}}$.
  - Bucher anchored indirect comparisons (NMA) and Monte Carlo SUCRA ranking hierarchy (0–100%).
- **Explicit Divergence Transparency:**
  - Always generate the Trial Differences Report with dosage tiers, duration horizons, eligibility discrepancy matrix (`df_eligibility`), and dynamic comparative narrative.
- **Predictive Trajectory Modeling & Virtual Trial Extrapolation:**
  - Dose-duration multivariate WLS meta-regression with confidence intervals, prediction intervals, NNT, and methodological extrapolation risk rating.
