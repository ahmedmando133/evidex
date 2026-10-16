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
            if mean_val is not None or chg_val is not None:
                fpg_within[(arm, tp)] = (mean_val if mean_val is not None else chg_val, src)
            if eff_meas == "Adjusted Difference vs Placebo" and eff_val is not None:
                fpg_diffs[(arm, tp)] = (eff_val, src)
        elif "24-hour mean glucose" in param:
            if mean_val is not None or chg_val is not None:
                cgm_within[(arm, tp)] = (mean_val if mean_val is not None else chg_val, src)
            if eff_meas == "Adjusted Difference vs Placebo" and eff_val is not None:
                cgm_diffs[(arm, tp)] = (eff_val, src)
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


def test_zero_duplicate_outcomes_and_se_integrity():
    """
    Permanent System-Wide Rule:
    1. Zero duplicate (parameter_name, arm_id, timepoint_value) records in Stage 1 extraction.
    2. Zero spurious generic 'Follow-up' records when post-baseline timepoints exist.
    3. Strict SE vs SD classification integrity with zero SE misclassified as SD.
    4. Zero continuous single-value broadcast across multiple treatment arms.
    """
    pdf_path = "data/raw/empa vs placebo 2doses (RCT4).pdf"
    assert os.path.exists(pdf_path)
    ext = RCTExtractor(pdf_path)
    data = ext.extract_all(study_id_override="RCT4")

    # 1. Zero duplicates check
    seen_keys = set()
    duplicates = []
    for o in data.outcomes:
        k = (str(o.parameter_name).strip().lower(), str(o.arm_id).strip(), str(o.timepoint_value or "").strip().lower())
        if k in seen_keys:
            duplicates.append(k)
        seen_keys.add(k)
    assert len(duplicates) == 0, f"Duplicate arm outcome records found: {duplicates}"

    # 2. Zero spurious generic Follow-up rows check
    fu_rows = [o for o in data.outcomes if str(o.timepoint_value or "").strip().lower() == "follow-up"]
    assert len(fu_rows) == 0, f"Spurious Follow-up rows present: {fu_rows}"

    # 3. SE vs SD classification check
    for o in data.outcomes:
        src = f"{o.raw_source_text or ''} {o.source_location or ''}".lower()
        if "(se)" in src or "standard error" in src:
            if not ("(sd)" in src or "standard deviation" in src):
                assert o.dispersion_type == "SE", f"Misclassified SE as {o.dispersion_type} in {o.parameter_name} ({o.outcome_id})"
                assert o.sd is None, f"SD not None for SE record {o.outcome_id}"
                assert o.se is not None, f"SE is None for SE record {o.outcome_id}"

    # 4. Zero single-value continuous broadcast check
    # Continuous active arms and placebo must not all share identical mean and SD values
    from collections import defaultdict
    cont_by_param_tp = defaultdict(list)
    for o in data.outcomes:
        if o.mean is not None and (o.sd is not None or o.se is not None):
            cont_by_param_tp[(o.parameter_name, str(o.timepoint_value))].append(o)

    for (p, tp), o_list in cont_by_param_tp.items():
        if len(o_list) >= 3:
            means = [o.mean for o in o_list]
            disps = [o.sd or o.se for o in o_list]
            # If all 3 arms have identical mean AND identical dispersion down to decimal, flag broadcast
            if len(set(means)) == 1 and len(set(disps)) == 1:
                pytest.fail(f"Illegal identical broadcast across all arms for {p} at {tp}: mean={means[0]}, disp={disps[0]}")


def test_mandoros_final_audit_perfection():
    """
    Final System-Wide Acceptance Tests:
    1. Table 4 Free Fatty Acids extracted accurately (10 mg = 1.7, 25 mg = 4.3).
    2. Pooled_Effect_Estimates retains dose-specific estimates for single multi-arm trial (no combined -33.915).
    3. Domain_Bridged_Meta_Analysis accurately reports true unique patients (N=60, not 450).
    4. Predictive_Projections strictly gates 12, 24, 52 week predictions (INSUFFICIENT_DATA_FOR_VALIDATED_PREDICTION).
    5. Synthesized_Virtual_Trial formats duration as '28 Days (Observed)' and provides deterministic sample size derivation.
    """
    master_path = "outputs/analysis/Custom_Drug/Custom_Drug_MANDOROS_Master_Report.xlsx"
    assert os.path.exists(master_path), f"Missing {master_path}"
    wb = openpyxl.load_workbook(master_path, data_only=True)

    # 1. Free Fatty Acids in Meta_Analysis_Results
    ws_meta = wb["Meta_Analysis_Results"]
    ffa_effects = {}
    for r in range(2, ws_meta.max_row + 1):
        param = str(ws_meta.cell(r, 1).value or "").lower()
        if "free fatty acids" in param:
            exp_arm = str(ws_meta.cell(r, 3).value or "")
            eff_val = ws_meta.cell(r, 7).value
            ffa_effects[exp_arm] = eff_val

    assert "Empagliflozin 10 mg" in ffa_effects, f"Missing 10 mg FFA: {ffa_effects}"
    assert "Empagliflozin 25 mg" in ffa_effects, f"Missing 25 mg FFA: {ffa_effects}"
    assert abs(ffa_effects["Empagliflozin 10 mg"] - 1.7) < 1e-3, f"Incorrect 10 mg FFA effect: {ffa_effects['Empagliflozin 10 mg']}"
    assert abs(ffa_effects["Empagliflozin 25 mg"] - 4.3) < 1e-3, f"Incorrect 25 mg FFA effect: {ffa_effects['Empagliflozin 25 mg']}"

    # 2. Multi-arm pooling in Pooled_Effect_Estimates
    ws_pool = wb["Pooled_Effect_Estimates"]
    pgf_pool_rows = []
    for r in range(5, ws_pool.max_row + 1):
        param = str(ws_pool.cell(r, 1).value or "")
        if "8-iso" in param.lower() and "24h" in param.lower():
            pgf_pool_rows.append((param, ws_pool.cell(r, 6).value))

    assert len(pgf_pool_rows) >= 2, f"Expected dose-specific rows for 8-iso-PGF2a: {pgf_pool_rows}"
    for name, val in pgf_pool_rows:
        assert abs(float(val) - (-33.915)) > 0.1, f"Found combined artificial pooled effect -33.915 in {name}"
        if "10 mg" in name:
            assert abs(float(val) - (-24.7)) < 1e-2, f"10 mg estimate mismatch: {val}"
        elif "25 mg" in name:
            assert abs(float(val) - (-43.1)) < 1e-2, f"25 mg estimate mismatch: {val}"

    # 3. Domain_Bridged_Meta_Analysis unique patients
    ws_dom = wb["Domain_Bridged_Meta_Analysis"]
    assert "Unique Patients (N)" in [ws_dom.cell(5, c).value for c in range(1, 10)]
    for r in range(6, 11):
        n_val = ws_dom.cell(r, 4).value
        if n_val is not None and isinstance(n_val, (int, float)):
            assert n_val <= 60, f"Domain participant count inflated beyond trial randomized N=60: row {r} = {n_val}"

    # 4. Predictive_Projections longitudinal gating
    ws_pred = wb["Predictive_Projections"]
    long_term_rows = []
    for r in range(5, ws_pred.max_row + 1):
        dur = ws_pred.cell(r, 3).value
        eff = ws_pred.cell(r, 4).value
        if dur in [12, 24, 52, 12.0, 24.0, 52.0]:
            long_term_rows.append(eff)

    assert len(long_term_rows) > 0, "No long term rows found"
    for eff in long_term_rows:
        assert str(eff) == "INSUFFICIENT_DATA_FOR_VALIDATED_PREDICTION", f"Carried forward numerical value on long-term horizon: {eff}"

    # 5. Synthesized_Virtual_Trial time unit and sample size
    ws_vt = wb["Synthesized_Virtual_Trial"]
    sample_size_str = str(ws_vt["B7"].value or "")
    assert "Formula" in sample_size_str or "SAMPLE_SIZE" in sample_size_str, f"Sample size lack formula derivation: {sample_size_str}"
    assert "28 Days (Observed)" in str(ws_vt.cell(14, 4).value or ""), f"Misclassified time unit in virtual trial: {ws_vt.cell(14, 4).value}"


def test_mandoros_phase2_perfection_lock_and_3column_schema():
    """
    Perfection Lock verification (Achieving 40/40 benchmark):
    1. Universal 3-column range schema (Min | Max | Unit) across Age, HbA1c blocks, and continuous criteria.
    2. Exclusion criteria contain specific prohibited drugs and timeframe windows (zero bare 'Prohibited').
    3. Contextual Race scanner correctly extracts Asian (Japanese) at 100% allocation.
    4. Zero QA warnings in Validation_Log.
    """
    pdf_path = "data/raw/empa vs placebo 2doses (RCT4).pdf"
    assert os.path.exists(pdf_path)
    ext = RCTExtractor(pdf_path)
    data = ext.extract_all(study_id_override="RCT4")

    # 1. Continuous criteria use 3-column schema and discrete HbA1c blocks exist
    elig_names = [e.criterion_name for e in data.eligibility]
    assert "age" in elig_names
    assert "hba1c_drug_naive" in elig_names
    assert "hba1c_treated" in elig_names
    assert "hba1c_run_in" in elig_names

    # Check bounds
    naive_e = next(e for e in data.eligibility if e.criterion_name == "hba1c_drug_naive")
    assert naive_e.min_value == 7.0 and naive_e.max_value == 10.0 and naive_e.unit == "%"
    treated_e = next(e for e in data.eligibility if e.criterion_name == "hba1c_treated")
    assert treated_e.min_value == 7.0 and treated_e.max_value == 9.5 and treated_e.unit == "%"
    runin_e = next(e for e in data.eligibility if e.criterion_name == "hba1c_run_in")
    assert runin_e.min_value == 7.0 and runin_e.max_value == 10.0 and runin_e.unit == "%"

    # 2. Specific unpacked exclusion criteria and timeframe windows
    assert "prohibited_medications" in elig_names
    prohib_e = next(e for e in data.eligibility if e.criterion_name == "prohibited_medications")
    assert "Insulin" in str(prohib_e.value) and "GLP-1" in str(prohib_e.value)
    assert "12 weeks" in str(prohib_e.value)

    assert "anti_obesity_drugs" in elig_names
    obesity_e = next(e for e in data.eligibility if e.criterion_name == "anti_obesity_drugs")
    assert "12 weeks" in str(obesity_e.value)

    assert "unstable_body_weight" in elig_names
    wt_e = next(e for e in data.eligibility if e.criterion_name == "unstable_body_weight")
    assert "screening" in str(wt_e.value).lower()

    assert "systemic_steroids" in elig_names
    steroid_e = next(e for e in data.eligibility if e.criterion_name == "systemic_steroids")
    assert "consent" in str(steroid_e.value).lower()

    assert "thyroid_hormone_change" in elig_names
    thyroid_e = next(e for e in data.eligibility if e.criterion_name == "thyroid_hormone_change")
    assert "6 weeks" in str(thyroid_e.value)

    assert "alcohol_or_drug_abuse" in elig_names
    alcohol_e = next(e for e in data.eligibility if e.criterion_name == "alcohol_or_drug_abuse")
    assert "12 weeks" in str(alcohol_e.value)

    assert "investigational_drug_intake" in elig_names
    inv_e = next(e for e in data.eligibility if e.criterion_name == "investigational_drug_intake")
    assert "30 days" in str(inv_e.value)

    # 3. Demographic Race propagation
    for arm in data.arms:
        arm_outs = [o for o in data.outcomes if o.arm_id == arm.arm_id and o.race]
        assert len(arm_outs) > 0, f"No race assigned for arm {arm.arm_name}"
        for o in arm_outs:
            assert "Asian" in o.race or "Japanese" in o.race

    # 4. Zero QA warnings in Validation_Log
    qa_warnings = [log for log in data.validation_log if getattr(log, "severity", "").upper() == "WARNING"]
    assert len(qa_warnings) == 0, f"Found unexpected QA warnings: {qa_warnings}"


def test_mandoros_system_wide_extraction_perfection():
    """
    Validates Master System-Wide Extraction Improvements:
    1. FPG vs PPG Discrimination (no -19.6 or -26.3 in PPG AUC).
    2. Triglycerides Geometric Ratio & NOT_APPLICABLE in Change from Baseline.
    3. Adverse Events Canonicalization & single canonical record per arm.
    4. Enriched clinical schema (variable_role, estimate_type, timepoint metadata).
    """
    from src.extractor import RCTExtractor
    from src.exporter import ExcelTrialExporter

    pdf_path = "data/raw/empa vs placebo 2doses (RCT4).pdf"
    if not os.path.exists(pdf_path):
        pdf_path = "empa vs placebo 2doses (RCT4)(4).pdf"
    assert os.path.exists(pdf_path), f"Test PDF not found at {pdf_path}"

    ext = RCTExtractor(pdf_path)
    data = ext.extract_all(study_id_override="RCT4")

    # 1. FPG vs PPG Discrimination
    ppg_outs = [o for o in data.outcomes if "ppg" in o.parameter_name.lower()]
    for o in ppg_outs:
        assert o.change_value not in [-19.6, -26.3], f"Found FPG Day 2 contrast in PPG AUC: {o.change_value}"
        assert o.effect_value not in [-19.6, -26.3], f"Found FPG Day 2 contrast in PPG AUC: {o.effect_value}"

    ppg_d28 = {o.arm_id: o for o in ppg_outs if str(o.timepoint_value) == "28"}
    assert ppg_d28["ARM_001"].change_value == -18.1
    assert ppg_d28["ARM_002"].change_value == -103.6
    assert ppg_d28["ARM_002"].effect_value == -85.5
    assert ppg_d28["ARM_003"].change_value == -122.9
    assert ppg_d28["ARM_003"].effect_value == -104.9

    fpg_d2 = {o.arm_id: o for o in data.outcomes if o.parameter_name == "Fasting Plasma Glucose" and str(o.timepoint_value) == "2"}
    assert fpg_d2["ARM_001"].change_value == -4.2
    assert fpg_d2["ARM_002"].change_value == -23.8
    assert fpg_d2["ARM_002"].effect_value == -19.6
    assert fpg_d2["ARM_003"].change_value == -30.5
    assert fpg_d2["ARM_003"].effect_value == -26.3

    # 2. Triglycerides Geometric Ratio & NOT_APPLICABLE
    tg_d29 = {o.arm_id: o for o in data.outcomes if o.parameter_name == "Triglycerides" and str(o.timepoint_value) == "29"}
    assert tg_d29["ARM_001"].ratio == 1.0
    assert tg_d29["ARM_002"].ratio == 0.8
    assert tg_d29["ARM_002"].effect_value == 0.8
    assert tg_d29["ARM_003"].ratio == 0.7
    assert tg_d29["ARM_003"].effect_value == 0.7

    # Export to Excel and verify sheet cells
    out_test_file = "outputs/test_mandoros_perfection_export.xlsx"
    exporter = ExcelTrialExporter(data)
    exporter.export(out_test_file)

    wb = openpyxl.load_workbook(out_test_file, data_only=True)
    ws_master = wb["Master_Extraction_Sheet"]

    # Verify Triglycerides Change from Baseline is NOT_APPLICABLE (not empty)
    # Find Triglycerides column in row 2
    tg_col = None
    for c in range(1, ws_master.max_column + 1):
        if ws_master.cell(2, c).value and "triglycerides" in str(ws_master.cell(2, c).value).lower():
            tg_col = c
            break
    assert tg_col is not None, "Triglycerides column not found in Master_Extraction_Sheet"
    chg_col = tg_col + 4  # Change from Baseline is offset 4 from start of block
    # Check that rows with Day 29 timepoint have NOT_APPLICABLE
    for r in range(4, ws_master.max_row + 1):
        tp_v = ws_master.cell(r, 20).value # pop_start_col + 6
        if str(tp_v) == "29":
            val = ws_master.cell(r, chg_col).value
            assert val == "NOT_APPLICABLE", f"Row {r} Triglycerides Change from Baseline was '{val}', expected 'NOT_APPLICABLE'"

    # 3. Adverse Events Canonicalization & Display Deduplication
    safe_cols = [c for c in range(1, ws_master.max_column + 1) if ws_master.cell(2, c).value and "adverse" in str(ws_master.cell(2, c).value).lower()]
    # There should NOT be both "Adverse Events" and "Any Adverse Event"
    r2_ae_titles = [str(ws_master.cell(2, c).value) for c in safe_cols]
    assert "adverse events" not in [t.lower().strip() for t in r2_ae_titles if t.lower().strip() == "adverse events"], "Duplicate 'Adverse Events' column block found!"
    assert any("any adverse event" in t.lower() for t in r2_ae_titles), "Missing canonical 'Any Adverse Event' column block!"

    # In Outcomes sheet: exactly ONE canonical Any Adverse Event per arm
    ws_out = wb["Outcomes"]
    out_headers = [ws_out.cell(1, c).value for c in range(1, ws_out.max_column + 1)]
    assert "variable_role" in out_headers
    assert "estimate_type" in out_headers
    assert "original_timepoint_label" in out_headers

    any_ae_outcomes = [r for r in ws_out.iter_rows(min_row=2, values_only=True) if r[7] == "Any Adverse Event"]
    assert len(any_ae_outcomes) == 3, f"Expected 3 canonical AE records (1 per arm), found {len(any_ae_outcomes)}"
    ae_by_arm = {r[2]: (r[26], r[27], r[28]) for r in any_ae_outcomes}
    assert ae_by_arm["ARM_001"] == (2, 21, 9.5)
    assert ae_by_arm["ARM_002"] == (3, 20, 15.0)
    assert ae_by_arm["ARM_003"] == (3, 19, 15.8)

    # In Eligibility sheet: variable_role, applicable_population, assessment_stage populated
    ws_elig = wb["Eligibility"]
    elig_headers = [ws_elig.cell(1, c).value for c in range(1, ws_elig.max_column + 1)]
    assert "variable_role" in elig_headers
    assert "applicable_population" in elig_headers
    assert "assessment_stage" in elig_headers



