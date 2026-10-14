# M Λ N D O R O S
### Meta-Analysis Network for Data, Outcomes & Research Optimization Synthesis
*— From Raw Trials to Global Clinical Verdicts. —*  
*— S M A R T E R &nbsp; E V I D E N C E . &nbsp; B E T T E R &nbsp; D E C I S I O N S . —*

---

## 🌟 Executive Overview
**MANDOROS** is a next-generation clinical trial extraction, meta-analysis, and predictive analytics engine. It transforms raw clinical trial protocols and published RCT PDFs into standardized, audit-verified evidence databases compliant with Cochrane, PRISMA, and top-tier academic biostatistical standards.

---

## 🧬 The 8-Node MANDOROS Pipeline

| Node | Acronym | Keyword | Mission |
| :---: | :---: | :--- | :--- |
| 📄 | **M** | **Meta-Analysis** | Combine evidence from multiple clinical studies using fixed and random-effects models. |
| 🧠 | **A** | **AI & Automation** | Extract, process, and structure complex protocols with multi-stage intelligence. |
| 🕸️ | **N** | **Network** | Connect trials, active ingredients, and indirect treatment comparisons (NMA). |
| 🗄️ | **D** | **Data** | From unstructured PDFs to clean, audit-traceable, tabular datasets. |
| 🎯 | **O** | **Outcomes** | Track clinical results, biomarkers, endpoints, and efficacy/safety signals. |
| 📑 | **R** | **Research** | Focus on randomized controlled trials (RCTs) and real-world evidence. |
| ⚙️ | **O** | **Optimization** | Standardize, harmonize units, and enforce zero-hallucination data quality. |
| 📈 | **S** | **Synthesis** | Build cross-trial insights, meta-regression models, and virtual trial predictions. |

---

## 🏛️ Core Architecture & Pipeline Laws

### 1. Mandatory Stage-1 Individual Excel Law
- **Unbreakable Pre-Extraction Rule:** Whenever raw RCT PDFs are added to an active-ingredient cohort folder (`analysis/<Cohort_Name>/`) or uploaded directly via the Phase-2 Web UI tab, **Stage-1 single-study extraction executes first for every PDF**.
- **Deliverables:**
  - Individual `<study_id>_structured_extracted.xlsx` (complete 7-sheet workbook) saved to `outputs/analysis/<Cohort_Name>/extracted_trials/` and copied to root `outputs/`.
  - Structured individual JSON archives.
  - Bundled `<Cohort_Name>_Individual_Stage1_Trial_Excels.zip` for instant one-click download.

### 2. Phase 2: Intelligent Adaptive Meta-Analysis & Predictive Engine
- **Cohort Mode Detection:** Automatically detects *Homogeneous Single-Drug*, *Multi-Drug Shared-Indication*, or *Heterogeneous Cross-Domain* cohorts.
- **Tiered Analytical Pooling:**
  - **Tier 1 (Exact Parameters):** Direct pooling using Inverse-Variance Fixed-Effect and DerSimonian-Laird (DL) & Restricted Maximum Likelihood (REML) Random-Effects models. Computes pooled estimates, 95% CIs, **95% Prediction Intervals (PI)**, Cochran's $Q$, $I^2$ (%), $\tau^2$, and Egger's test.
  - **Tier 2 (Clinical Domain Bridging):** Standardizes divergent outcome measures (e.g., BMI vs Body Weight vs Waist Circumference) into scale-free **Standardized Mean Differences (Hedges' $g$)** and baseline percentage change (%Δ).
  - **Tier 3 (Longitudinal Normalization):** Reconciles disparate trial durations into standardized monthly rates of change.
- **Subgroup & Network Meta-Analysis:**
  - Evaluates between-subgroup variance ($Q_{\text{between}}$, $p_{\text{between}}$) across active substances and dosage tiers.
  - Computes Bucher anchored indirect comparisons and Monte Carlo SUCRA rankings (0–100%).
- **Virtual Trial Simulator:**
  - Multivariate WLS meta-regression across dose and duration.
  - Interactive scenario forecasting with 95% Prediction Intervals, NNT, and Extrapolation Reliability Ratings.

---

## 🚀 Quick Start & Launchers

### Launching the Web Interface
Double-click `Run_MANDOROS_Web_App.bat` or run:
```bash
python app.py
```
Access the Apple-styled dark UI at: `http://localhost:7860`

### Running Batch Extraction (Stage-1)
Double-click `Run_MANDOROS_Extraction.bat` or run:
```bash
python -m src.main --all
```

### Running Cohort Meta-Analysis (Phase-2)
Double-click `Run_MANDOROS_Cohort_Analysis.bat` or run:
```bash
python run.py analyze-cohort --cohort Mixed_Metabolic_Cohort
```

---

## 📦 Deliverables Produced

1. **Master Comparison & Meta-Analysis Excel (`.xlsx`):**
   - `<Cohort_Name>_MANDOROS_Master_Report.xlsx` (8 multi-level sheets).
2. **Interactive Executive Dashboard (`.html`):**
   - `<Cohort_Name>_MANDOROS_Executive_Dashboard.html` (Standalone Plotly charts, SUCRA rankings, heatmaps).
3. **Stage-1 Individual Trial Excels Bundle (`.zip`):**
   - `<Cohort_Name>_Individual_Stage1_Trial_Excels.zip`.
4. **Individual Trial Excels (`.xlsx`):**
   - `<study_id>_structured_extracted.xlsx` (in `outputs/` and `extracted_trials/`).

---

## 🔒 Security & Data Integrity
- Single source of truth in `src/canonical.py`.
- Zero-hallucination policy (`not_reported` for unmeasured data).
- Strict separation of numeric values, operators, and units.
- Full PRISMA, Cochrane, and academic systematic review compatibility.
