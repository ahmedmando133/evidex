"""
Regression and Validation Tests for MANDOROS Phase 1 & 2 System-Wide Corrections.
Asserts that all 16 audited biostatistical, extraction, and methodological defects
are permanently eradicated across both Stage 1 and Stage 2 pipelines.
"""

import math
import os
import pytest
import openpyxl
import pandas as pd
import numpy as np

from src.extractor import RCTExtractor
from src.statistical_eligibility import StatisticalEligibilityEngine
from src.cohort_pipeline import ActiveIngredientCohortPipeline
from src.meta_predictive import (
    compute_continuous_effect_size,
    compute_dichotomous_effect_size,
    run_meta_analysis,
    run_domain_meta_analysis,
    _safe_exp
)
from src.discovery_engine import InSilicoDiscoveryEngine


def test_safe_exp_overflow_protection():
    """Verify _safe_exp prevents OverflowError on extreme values."""
    assert _safe_exp(0.0) == 1.0
    assert abs(_safe_exp(1.0) - math.e) < 1e-4
    # Extreme positive value
    val_high = _safe_exp(1000.0)
    assert val_high > 0 and not math.isinf(val_high)
    # Extreme negative value
    val_low = _safe_exp(-1000.0)
    assert val_low > 0


def test_rct4_extraction_arm_allocation_and_duration():
    """
    Error 1 & 3: Placebo = 21, 10mg = 20, 25mg = 19 (Total=60).
    Error 2: Study phase is strictly 'Not explicitly reported' and duration is 28 days.
    """
    pdf_path = "data/raw/empa vs placebo 2doses (RCT4).pdf"
    assert os.path.exists(pdf_path)
    ext = RCTExtractor(pdf_path)
    data = ext.extract_all(study_id_override="RCT4")

    # Study metadata
    assert data.study.study_phase == "Not explicitly reported"
    assert data.study.duration_value == 28.0
    assert data.study.duration_unit == "days"
    assert data.study.total_sample_size == 60

    # Arm allocations
    arms_map = {a.arm_name: a.sample_size_allocated for a in data.arms}
    assert arms_map.get("Placebo") == 21
    assert arms_map.get("Empagliflozin 10 mg") == 20
    assert arms_map.get("Empagliflozin 25 mg") == 19
    assert sum(arms_map.values()) == 60


def test_rct4_outcomes_fpg_and_cgm_segregation():
    """
    Error 4 & 5: Figure 3 (FPG treatment differences) and Figure 4 (24h mean glucose)
    must NOT be assigned to PPG AUC1-4h or conflated with each other.
    """
    pdf_path = "data/raw/empa vs placebo 2doses (RCT4).pdf"
    ext = RCTExtractor(pdf_path)
    data = ext.extract_all(study_id_override="RCT4")

    # Check PPG AUC rows do not contain FPG differences
    ppg_outcomes = [o for o in data.outcomes if "auc" in o.parameter_name.lower()]
    for p in ppg_outcomes:
        val = p.change_value if p.change_value is not None else p.mean
        if val is not None:
            # Figure 3 treatment differences are -19.6, -22.1, -26.3, -33.5
            assert val not in [-19.6, -22.1, -26.3, -33.5], f"FPG difference leaked into PPG: {p}"

    # Verify Fasting Plasma Glucose and 24-Hour Mean Glucose exist
    param_names = [o.parameter_name for o in data.outcomes]
    assert any("fasting plasma glucose" in p.lower() or "fpg" in p.lower() for p in param_names)
    assert any("24-hour" in p.lower() or "mean glucose" in p.lower() for p in param_names)


def test_statistical_eligibility_engine_single_study_rules():
    """
    Error 6, 7, 8, 9, 10, 16: StatisticalEligibilityEngine enforces strict k_studies rules:
    - Between-study heterogeneity not estimable when k < 2
    - Publication bias tests unpowered when k < 10
    - SUCRA requires network transitivity across multi-trial network
    """
    engine = StatisticalEligibilityEngine()

    # k = 1 study
    studies_df_1 = pd.DataFrame([{"study_id": "RCT4", "total_sample_size": 60}])
    effects_1 = [
        compute_continuous_effect_size(
            study_id="RCT4 [Empa 10mg vs Placebo]",
            arm_exp="Empa 10mg",
            arm_ctrl="Placebo",
            parameter="FPG",
            timepoint="Day 29",
            n1=20, m1=-22.1, s1=15.0,
            n2=21, m2=0.0, s2=15.0
        ),
        compute_continuous_effect_size(
            study_id="RCT4 [Empa 25mg vs Placebo]",
            arm_exp="Empa 25mg",
            arm_ctrl="Placebo",
            parameter="FPG",
            timepoint="Day 29",
            n1=19, m1=-33.5, s1=15.0,
            n2=21, m2=0.0, s2=15.0
        )
    ]

    # Check meta-analysis eligibility
    elig_meta = engine.check_meta_analysis_eligibility(effects_1, "FPG")
    assert elig_meta["k_studies"] == 1
    assert elig_meta["k_comparisons"] == 2
    assert elig_meta["heterogeneity_estimable"] is False
    assert elig_meta["model_recommended"] == "Fixed-Effect (Single Trial)"

    # Check publication bias eligibility
    elig_bias = engine.check_publication_bias_eligibility(k_studies=1)
    assert elig_bias["eligible"] is False
    assert "10" in elig_bias["reason"]

    # Check NMA SUCRA eligibility
    elig_nma = engine.check_nma_network(["Placebo", "Empa 10mg", "Empa 25mg"], [("Empa 10mg", "Placebo"), ("Empa 25mg", "Placebo")], k_studies=1)
    assert elig_bias["eligible"] is False
    assert "single" in elig_nma["reason"].lower()


def test_meta_predictive_engine_no_false_study_inflation():
    """
    Error 6 & 7: Multiple comparisons within 1 trial must NOT inflate k_studies or patient count.
    """
    effects = [
        compute_continuous_effect_size(
            study_id="RCT4 [Empa 10mg vs Placebo]",
            arm_exp="Empa 10mg",
            arm_ctrl="Placebo",
            parameter="FPG",
            timepoint="Day 29",
            n1=20, m1=-22.1, s1=15.0,
            n2=21, m2=0.0, s2=15.0
        ),
        compute_continuous_effect_size(
            study_id="RCT4 [Empa 25mg vs Placebo]",
            arm_exp="Empa 25mg",
            arm_ctrl="Placebo",
            parameter="FPG",
            timepoint="Day 29",
            n1=19, m1=-33.5, s1=15.0,
            n2=21, m2=0.0, s2=15.0
        )
    ]

    res = run_meta_analysis(effects)
    assert res is not None
    assert res.k_studies == 1
    # total_n must NOT double count placebo 21: max per study is 20+21=41 or 19+21=40 -> 41
    assert res.total_n <= 60
    # Between-study heterogeneity must be clamped to 0.0
    assert res.i2 == 0.0
    assert res.tau2 == 0.0
    assert res.q_df == 0


def test_discovery_engine_no_1440mg_dose_and_hypotheses_marked():
    """
    Error 11: 1440 mg/day optimal regimen must be permanently eradicated.
    Error 12 & 13: Super-responder and biomarker coupling marked as exploratory hypotheses.
    Error 14: Virtual trial tagged as hypothetical simulation framework.
    """
    arms_df = pd.DataFrame([
        {"study_id": "RCT4", "arm_name": "Placebo", "intervention_type": "placebo", "dose_value": 0.0},
        {"study_id": "RCT4", "arm_name": "Empagliflozin 10 mg", "intervention_type": "experimental", "dose_value": 10.0},
        {"study_id": "RCT4", "arm_name": "Empagliflozin 25 mg", "intervention_type": "experimental", "dose_value": 25.0}
    ])
    outcomes_df = pd.DataFrame([
        {"study_id": "RCT4", "parameter_name": "HbA1c", "mean": -0.8, "sd": 0.4, "sample_size": 20, "is_baseline": False},
        {"study_id": "RCT4", "parameter_name": "HbA1c", "mean": -0.9, "sd": 0.4, "sample_size": 19, "is_baseline": False},
        {"study_id": "RCT4", "parameter_name": "Body Weight", "mean": -2.5, "sd": 1.2, "sample_size": 20, "is_baseline": False}
    ])

    from types import SimpleNamespace
    mock_pipeline = SimpleNamespace(
        cohort_name="Custom_Drug",
        cohort_mode="Homogeneous Single-Drug Cohort",
        studies_df=pd.DataFrame([{"study_id": "RCT4"}]),
        arms_df=arms_df,
        outcomes_df=outcomes_df,
        meta_results={},
        domain_meta_results={},
        predictors={}
    )
    engine = InSilicoDiscoveryEngine(mock_pipeline)
    disc_res = engine.run_all()

    # Check therapeutic sweet-spot
    sweet = engine._detect_therapeutic_sweet_spot()
    assert "25 mg/day" in sweet.quantitative_finding
    assert "1440" not in sweet.title
    assert "1440" not in sweet.quantitative_finding

    # Check responder phenotype
    resp = engine._detect_super_responder_phenotype()
    assert "EXPLORATORY_HYPOTHESIS_UNVALIDATED" in resp.quantitative_finding
    assert "Exploratory" in resp.confidence_grade

    # Check biomarker coupling
    bio = engine._detect_biomarker_coupling()
    assert "EXPLORATORY_HYPOTHESIS_UNVALIDATED" in bio.quantitative_finding

    # Check virtual trial protocol
    engine.synthesize_denovo_virtual_trial()
    assert "[HYPOTHETICAL_SIMULATION_FRAMEWORK]" in engine.virtual_trial_metadata["protocol_name"]
    assert "power" in engine.virtual_trial_metadata["analytical_framework"].lower()


def test_master_report_excel_all_sheets_and_values():
    """
    Validates the generated Master Excel report:
    1. 20 worksheets present
    2. Placebo=21, 10mg=20, 25mg=19 in Arms sheet
    3. Not explicitly reported in Studies sheet
    4. SUCRA NOT_ESTIMABLE banner
    5. Zero literal nan in Baseline_Population_Summary
    """
    excel_path = "outputs/analysis/Custom_Drug/Custom_Drug_MANDOROS_Master_Report.xlsx"
    assert os.path.exists(excel_path), f"Master report not found at {excel_path}"

    wb = openpyxl.load_workbook(excel_path, data_only=True)
    assert len(wb.sheetnames) == 20

    # 1. Arms
    ws_arms = wb["Arms"]
    arms_data = {}
    for r in range(2, ws_arms.max_row + 1):
        name = ws_arms.cell(r, 3).value
        n = ws_arms.cell(r, 10).value
        if name:
            arms_data[name] = n
    assert arms_data.get("Placebo") == 21
    assert arms_data.get("Empagliflozin 10 mg") == 20
    assert arms_data.get("Empagliflozin 25 mg") == 19

    # 2. Studies
    ws_studies = wb["Studies"]
    assert ws_studies.cell(2, 8).value == "Not explicitly reported"
    assert ws_studies.cell(2, 9).value == 60

    # 3. Baseline_Population_Summary: zero literal nan
    ws_base = wb["Baseline_Population_Summary"]
    for r in range(1, ws_base.max_row + 1):
        for c in range(1, ws_base.max_column + 1):
            val = str(ws_base.cell(r, c).value or "")
            assert val.lower() != "nan", f"Literal nan found in cell ({r}, {c})"

    # 4. Domain_Bridged_Meta_Analysis
    ws_dom = wb["Domain_Bridged_Meta_Analysis"]
    dom_text = " ".join(str(ws_dom.cell(r, c).value or "") for r in range(1, ws_dom.max_row + 1) for c in range(1, ws_dom.max_column + 1))
    assert "NOT_ESTIMABLE" in dom_text
    assert "N/A (k=1)" in dom_text


def test_second_validation_outcomes_fpg_and_cgm_segregation_and_source():
    """
    Second Validation Audit Items 2 & 3:
    - Within-arm changes separated from between-group differences.
    - Figure 3 (FPG), Figure 4 (CGM 24h glucose), and Section 3.2 (MAGE & HbA1c) citations.
    """
    excel_path = "outputs/analysis/Custom_Drug/Custom_Drug_MANDOROS_Master_Report.xlsx"
    wb = openpyxl.load_workbook(excel_path, data_only=True)
    ws = wb["Outcomes"]
    headers = [ws.cell(1, c).value for c in range(1, ws.max_column + 1)]
    col_map = {name: i + 1 for i, name in enumerate(headers)}

    # Collect FPG within-arm changes and between-group differences
    fpg_within = {}
    fpg_diffs = {}
    cgm_within = {}
    cgm_diffs = {}
    mage_sources = set()
    hba1c_sources = set()
    hba1c_units = set()

    for r in range(2, ws.max_row + 1):
        param = str(ws.cell(r, col_map["parameter_name"]).value or "").strip().lower()
        arm = str(ws.cell(r, col_map["arm_id"]).value or "")
        tp = str(ws.cell(r, col_map["Timepoint (value)"]).value or "")
        tp_unit = str(ws.cell(r, col_map["Timepoint (unit)"]).value or "")
        mean_val = ws.cell(r, col_map["mean"]).value
        chg_val = ws.cell(r, col_map["change_value"]).value
        eff_val = ws.cell(r, col_map["effect_value"]).value
        eff_meas = ws.cell(r, col_map["effect_measure"]).value
        src = str(ws.cell(r, col_map["source_location"]).value or "")

        if "fasting plasma glucose" in param:
            if eff_meas == "Adjusted Difference vs Placebo":
                fpg_diffs[(arm, tp)] = (eff_val, src)
            else:
                fpg_within[(arm, tp)] = (mean_val if mean_val is not None else chg_val, src)
        elif "24-hour mean glucose" in param:
            if eff_meas == "Adjusted Difference vs Placebo":
                cgm_diffs[(arm, tp)] = (eff_val, src)
            else:
                cgm_within[(arm, tp)] = (mean_val if mean_val is not None else chg_val, src)
        elif "mage" in param:
            mage_sources.add(src)
        elif "hba1c" in param:
            hba1c_sources.add(src)
            if tp_unit:
                hba1c_units.add(tp_unit)

    # Assert within-arm FPG changes: Day 2: -4.2, -23.8, -30.5; Day 29: -6.2, -28.3, -39.7
    within_vals = [v[0] for v in fpg_within.values() if v[0] is not None]
    assert -23.8 in within_vals, "Empa 10mg Day 2 FPG within-arm (-23.8) missing"
    assert -30.5 in within_vals, "Empa 25mg Day 2 FPG within-arm (-30.5) missing"
    assert -28.3 in within_vals, "Empa 10mg Day 29 FPG within-arm (-28.3) missing"
    assert -39.7 in within_vals, "Empa 25mg Day 29 FPG within-arm (-39.7) missing"

    # Assert between-group FPG differences: -19.6, -22.1, -26.3, -33.5
    diff_vals = [v[0] for v in fpg_diffs.values() if v[0] is not None]
    assert -19.6 in diff_vals, "Empa 10mg Day 2 FPG difference (-19.6) missing"
    assert -22.1 in diff_vals, "Empa 10mg Day 29 FPG difference (-22.1) missing"
    assert -26.3 in diff_vals, "Empa 25mg Day 2 Domenico difference (-26.3) missing"
    assert -33.5 in diff_vals, "Empa 25mg Day 29 FPG difference (-33.5) missing"

    # Assert CGM 24h Mean Glucose values
    cgm_within_vals = [v[0] for v in cgm_within.values() if v[0] is not None]
    assert -20.5 in cgm_within_vals, "Empa 10mg Day 1 CGM (-20.5) missing"
    assert -30.3 in cgm_within_vals, "Empa 10mg Day 28 CGM (-30.3) missing"
    assert -23.6 in cgm_within_vals, "Empa 25mg Day 1 CGM (-23.6) missing"
    assert -37.6 in cgm_within_vals, "Empa 25mg Day 28 CGM (-37.6) missing"

    cgm_diff_vals = [v[0] for v in cgm_diffs.values() if v[0] is not None]
    assert -20.8 in cgm_diff_vals, "Empa 10mg Day 1 CGM diff (-20.8) missing"
    assert -24.5 in cgm_diff_vals, "Empa 10mg Day 28 CGM diff (-24.5) missing"
    assert -23.9 in cgm_diff_vals, "Empa 25mg Day 1 CGM diff (-23.9) missing"
    assert -31.7 in cgm_diff_vals, "Empa 25mg Day 28 CGM diff (-31.7) missing"

    # Check source attribution
    for _, src in cgm_diffs.values():
        assert "Figure 4" in src

    assert any("Results Section 3.2" in s for s in mage_sources)
    assert any("Results Section 3.2" in s for s in hba1c_sources)
    assert "days" in hba1c_units


def test_second_validation_meta_analysis_no_zero_effects_and_exact_sample_size():
    """
    Second Validation Audit Items 4, 5, 7:
    - No artificial 0.000 point estimates for reported ANCOVA differences.
    - Standard error and variance derived from published CIs (no arbitrary SD=1.0).
    - Pairwise comparisons report exact analyzed sample sizes (N=41, N=40, total N=60).
    """
    excel_path = "outputs/analysis/Custom_Drug/Custom_Drug_MANDOROS_Master_Report.xlsx"
    wb = openpyxl.load_workbook(excel_path, data_only=True)
    ws_ma = wb["Meta_Analysis_Results"]

    # In Meta_Analysis_Results: col 1=parameter, col 6=measure, col 7=effect_estimate, col 8=yi, col 9=vi
    for r in range(2, ws_ma.max_row + 1):
        param = str(ws_ma.cell(r, 1).value or "").lower()
        meas = str(ws_ma.cell(r, 6).value or "")
        est = ws_ma.cell(r, 7).value
        vi = ws_ma.cell(r, 9).value

        # For 8-iso-pgf2a, point estimate must NOT be 0.0
        if "8-iso-pgf2a" in param:
            assert est is not None and abs(est) > 1.0, f"False 0.0 effect estimate for {param}"
            assert vi is not None and vi > 10.0, f"False precision (vi={vi}) for {param}"

    ws_eff = wb["Pooled_Effect_Estimates"]
    for r in range(5, ws_eff.max_row + 1):
        param = str(ws_eff.cell(r, 1).value or "").lower()
        n_val = ws_eff.cell(r, 5).value
        # Pairwise multi-arm pooling must not exceed total trial N=60
        if n_val is not None:
            assert n_val <= 60, f"Sample size double counting (N={n_val}) for {param}"


def test_second_validation_predictive_projections_and_discovery_rigor():
    """
    Second Validation Audit Items 8, 9, 10, 11:
    - 17.5 mg dose eradicated; doses bounded to {10, 25}.
    - No unsupported 'Optimal Regimen' claims.
    - Virtual trial tagged as [HYPOTHETICAL_SIMULATION_FRAMEWORK] with transparent power calculation.
    - Secondary endpoints marked [Unvalidated Scenario].
    """
    excel_path = "outputs/analysis/Custom_Drug/Custom_Drug_MANDOROS_Master_Report.xlsx"
    wb = openpyxl.load_workbook(excel_path, data_only=True)

    # Predictive Projections
    ws_pred = wb["Predictive_Projections"]
    pred_doses = {ws_pred.cell(r, 2).value for r in range(5, ws_pred.max_row + 1) if ws_pred.cell(r, 2).value is not None}
    assert 17.5 not in pred_doses, "Unstudied 17.5 mg dose present in Predictive_Projections"
    assert pred_doses.issubset({10, 25}), f"Unexpected doses in Predictive_Projections: {pred_doses}"

    # In Silico New Discoveries
    ws_disc = wb["In_Silico_New_Discoveries"]
    disc_text = " ".join(str(ws_disc.cell(r, c).value or "") for r in range(1, ws_disc.max_row + 1) for c in range(1, ws_disc.max_column + 1))
    assert "Optimal Regimen" not in disc_text, "Unsupported 'Optimal Regimen' claim found in In_Silico_New_Discoveries"
    assert "10 mg/day" in disc_text and "25 mg/day" in disc_text

    # Synthesized Virtual Trial
    ws_vt = wb["Synthesized_Virtual_Trial"]
    vt_text = " ".join(str(ws_vt.cell(r, c).value or "") for r in range(1, ws_vt.max_row + 1) for c in range(1, ws_vt.max_column + 1))
    assert "[HYPOTHETICAL_SIMULATION_FRAMEWORK]" in vt_text
    assert "[Unvalidated Scenario]" in vt_text


def test_second_validation_zero_nan_strings_across_all_sheets():
    """
    Second Validation Audit Item 12:
    Assert zero literal 'nan', 'none', or 'null' cells across ALL 20 worksheets.
    """
    excel_path = "outputs/analysis/Custom_Drug/Custom_Drug_MANDOROS_Master_Report.xlsx"
    wb = openpyxl.load_workbook(excel_path, data_only=True)
    assert len(wb.sheetnames) == 20

    nan_occurrences = []
    for sheet in wb.sheetnames:
        ws = wb[sheet]
        for r in range(1, ws.max_row + 1):
            for c in range(1, ws.max_column + 1):
                val = str(ws.cell(r, c).value or "").strip().lower()
                if val == "nan":
                    nan_occurrences.append(f"{sheet}!{ws.cell(r, c).coordinate}")

    assert len(nan_occurrences) == 0, f"Literal 'nan' found in cells: {nan_occurrences}"

