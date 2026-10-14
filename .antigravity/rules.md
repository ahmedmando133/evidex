# Evidex Project Architectural & Methodological Rules

## 1. Phase 1 Immutability (FROZEN & SACRED)
- **Single-Study Pipeline (`data/raw/` -> `outputs/`):** Do NOT modify or refactor `src/canonical.py`, existing extraction prompts, baseline models, single-study validation rules, or the single-trial Excel export formats.
- **Single-Study UI in `app.py`:** The original single-study interface, theme, color scheme, API key bypass, and KPI summary banner must remain 100% intact and functional.

## 2. Harmonization Protocol (`src/harmonize.py`)
- Prior to pooling or comparing cross-trial data, all outcome measurements, timepoints, and units MUST be harmonized using `src/harmonize.py`.
- No raw, unharmonized metrics may be pooled together (e.g. do not mix mmol/L and mg/dL without unit transformation; do not pool weeks and months without duration conversion).

## 3. `metafor`-Grade Statistical Standards in Python
All statistical meta-analyses must adhere to Cochrane Handbook and `wviechtb/metafor` standards:
- **Effect Sizes:**
  - Continuous: Mean Difference (MD) & Standardized Mean Difference (SMD, Hedges' $g$ with exact small-sample correction $J(df) = 1 - \frac{3}{4df - 1}$).
  - Dichotomous: Odds Ratio (OR), Risk Ratio (RR), and Risk Difference (RD) with Haldane-Anscombe 0.5 zero-cell adjustment.
- **Pooling Models:**
  - Fixed-Effect Model (Inverse-Variance weights $w_i = 1 / v_i$).
  - Random-Effects Model using both DerSimonian-Laird (DL) and Restricted Maximum Likelihood (REML) estimators for between-study variance $\tau^2$.
- **Precision & Prediction Intervals:**
  - 95% Confidence Intervals for pooled effect size: $[\hat{\theta} \pm 1.96 \cdot SE]$.
  - **95% Prediction Interval (PI):** $\hat{\theta} \pm t_{k-2, 0.975} \sqrt{SE^2 + \tau^2}$ to quantify expected effect in a future or unobserved clinical trial.
- **Heterogeneity & Publication Bias:**
  - Cochran's $Q$, $p$-value, and Higgins' $I^2 = \max(0, \frac{Q - (k-1)}{Q}) \times 100\%$.
  - Egger's linear regression test for funnel plot asymmetry.
- **Multivariate Meta-Regression & Virtual Trial Prediction:**
  - Weighted meta-regression incorporating dosage, treatment duration, and baseline values.
  - Predict new trial outcomes with both confidence and prediction bands.

## 4. Active-Ingredient Directory Isolation
- Every active-ingredient cohort in `analysis/<Active_Ingredient>/` is strictly independent.
- Never mix different drug cohorts into a single analysis file. Output all results cleanly into `outputs/analysis/<Active_Ingredient>/`.
