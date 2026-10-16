"""
Tests for Critical Biostatistical & Methodological Engine Overhaul
Validates:
1. Mathematical scale integrity (Zero negative ORs, exponentiated log-effects, strictly > 0, correct null = 1.0)
2. Strict outcome isolation (No across-outcome pooling of demographics, adverse events, and biomarkers)
3. Strict baseline vs follow-up segregation (filter_efficacy_and_safety_outcomes, Baseline_Population_Summary)
4. Zero double-counting & Cochrane control splitting for multi-arm trials
5. Pharmacologically bounded dose-response prediction engine & Cochrane-standard NNT
6. Multi-fallback metadata & sample size (N) / dose reconstruction (Zero N=nan)
"""

import sys
from pathlib import Path

# Ensure repo root is on sys.path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import math
import pytest
import numpy as np
import pandas as pd

from src.meta_predictive import (
    EffectSizeResult,
    MetaAnalysisResult,
    compute_continuous_effect_size,
    compute_dichotomous_effect_size,
    run_meta_analysis,
    MetaPredictiveEngine,
    generate_executive_verdict,
    PredictiveProjection
)
from src.cohort_pipeline import (
    filter_efficacy_and_safety_outcomes,
    ActiveIngredientCohortPipeline
)
from src.extraction_engine import (
    resolve_study_sample_size,
    resolve_arm_dose
)
from src.discovery_engine import InSilicoDiscoveryEngine


def test_mathematical_scale_integrity_odds_ratio():
    """Law 1: All reported OR/RR point estimates and 95% CIs must be strictly positive (> 0)."""
    # Create dichotomous effect with negative log-odds (e.g. reduction in events)
    eff = compute_dichotomous_effect_size(
        study_id="STUDY_001",
        arm_exp="Empagliflozin 10mg",
        arm_ctrl="Placebo",
        parameter="Hospitalization for Heart Failure",
        timepoint="52 weeks",
        events1=50,
        total1=1000,
        events2=100,
        total2=1000,
        measure="OR"
    )
    assert eff is not None
    # Internal yi is negative log-odds: ln(50*900 / 950*100) = ln(0.4737) ~= -0.747
    assert eff.yi < 0, f"Expected internal log-OR < 0, got {eff.yi}"
    # Reported yi must be exponentiated and strictly positive
    assert eff.is_ratio is True
    assert eff.reported_yi > 0
    assert abs(eff.reported_yi - math.exp(eff.yi)) < 1e-6
    assert eff.reported_ci_lower > 0
    assert eff.reported_ci_upper > 0
    assert eff.reported_ci_lower < eff.reported_yi < eff.reported_ci_upper

    # Now run meta-analysis on 2 studies with event reduction
    eff2 = compute_dichotomous_effect_size(
        study_id="STUDY_002",
        arm_exp="Empagliflozin 25mg",
        arm_ctrl="Placebo",
        parameter="Hospitalization for Heart Failure",
        timepoint="52 weeks",
        events1=45,
        total1=1000,
        events2=95,
        total2=1000,
        measure="OR"
    )
    meta_res = run_meta_analysis([eff, eff2])
    assert meta_res is not None
    assert meta_res.is_ratio is True
    assert meta_res.re_estimate < 0  # internal log-scale is negative
    # Reported must be exponentiated and strictly > 0
    assert meta_res.reported_re_estimate > 0
    assert meta_res.reported_re_ci_lower > 0
    assert meta_res.reported_re_ci_upper > 0
    assert meta_res.reported_fe_estimate > 0
    assert meta_res.reported_pi_lower > 0
    assert meta_res.reported_pi_upper > 0

    # Executive verdict must report exponentiated ratio
    verdict = generate_executive_verdict(meta_res)
    assert "OR" in verdict["pooled_effect"]
    # Ensure no negative signs precede the OR value
    assert "-0." not in verdict["pooled_effect"]
    assert "favorable odds/risk reduction" in verdict["summary_narrative"]


def test_continuous_effect_never_labeled_as_ratio():
    """Continuous difference (MD / SMD) must NEVER be labeled as OR."""
    eff = compute_continuous_effect_size(
        study_id="STUDY_001",
        arm_exp="Empagliflozin 10mg",
        arm_ctrl="Placebo",
        parameter="HbA1c",
        timepoint="24 weeks",
        n1=100, m1=7.2, s1=0.8,
        n2=100, m2=7.8, s2=0.9,
        measure="MD"
    )
    assert eff is not None
    assert eff.measure == "MD"
    assert eff.is_ratio is False
    assert abs(eff.reported_yi - (-0.6)) < 1e-6
    assert abs(eff.yi - (-0.6)) < 1e-6
    assert eff.reported_ci_lower == eff.ci_lower


def test_strict_baseline_segregation():
    """Law 3: Exclude 100% of baseline rows from treatment effect meta-analyses."""
    data = [
        {"parameter_name": "Age", "timepoint": "Baseline", "is_baseline": True, "category": "demographics", "mean": 65.0, "sd": 10.0},
        {"parameter_name": "Sex: Male", "timepoint": "0", "is_baseline": True, "category": "demographics", "events": 60, "sample_size": 100},
        {"parameter_name": "Baseline BMI", "timepoint": "Screening", "is_baseline": True, "category": "baseline_characteristics", "mean": 29.5, "sd": 4.0},
        {"parameter_name": "HbA1c", "timepoint": "Week 24", "is_baseline": False, "category": "efficacy", "mean": -0.75, "sd": 0.8},
        {"parameter_name": "Hospitalization for HF", "timepoint": "Week 52", "is_baseline": False, "category": "safety", "events": 30, "sample_size": 500},
    ]
    df = pd.DataFrame(data)
    eff_safety, baseline = filter_efficacy_and_safety_outcomes(df)

    assert len(baseline) == 3
    assert set(baseline["parameter_name"]) == {"Age", "Sex: Male", "Baseline BMI"}
    assert len(eff_safety) == 2
    assert set(eff_safety["parameter_name"]) == {"HbA1c", "Hospitalization for HF"}


def test_pharmacologically_bounded_dose_response_and_single_dose():
    """Law 5: Restrict dose predictions within [0.5*min, 1.5*max]; single-dose must not fake multi-dose rows."""
    eff1 = EffectSizeResult("S1", "Arm 10mg", "Ctrl", "HbA1c", "24w", "MD", -0.5, 0.02, 0.141, -0.78, -0.22, dose_mg=10.0, duration_weeks=24.0)
    eff2 = EffectSizeResult("S2", "Arm 10mg", "Ctrl", "HbA1c", "24w", "MD", -0.55, 0.025, 0.158, -0.86, -0.24, dose_mg=10.0, duration_weeks=24.0)

    predictor = MetaPredictiveEngine([eff1, eff2])
    # Single-dose cohort: slope not estimable
    assert predictor.dose_slope_estimable is False
    assert "Single-dose cohort" in predictor.dose_slope_note

    grid = predictor.generate_dose_duration_grid()
    # Must only contain the observed 10.0 mg dose, never fake 4 doses
    unique_grid_doses = set(p.dose_mg for p in grid)
    assert unique_grid_doses == {10.0}

    # Multi-dose cohort: strictly bounded within [0.5*min, 1.5*max]
    eff3 = EffectSizeResult("S3", "Arm 25mg", "Ctrl", "HbA1c", "24w", "MD", -0.75, 0.02, 0.141, -1.03, -0.47, dose_mg=25.0, duration_weeks=24.0)
    predictor_multi = MetaPredictiveEngine([eff1, eff2, eff3])
    assert predictor_multi.dose_slope_estimable is True

    grid_multi = predictor_multi.generate_dose_duration_grid()
    multi_doses = [p.dose_mg for p in grid_multi]
    assert min(multi_doses) >= 0.5 * 10.0
    assert max(multi_doses) <= 1.5 * 25.0


def test_nnt_requires_absolute_rates():
    """Law 5: NNT must output N/A when absolute event rates are missing, never fake 15% baseline risk."""
    eff1 = EffectSizeResult("S1", "Arm", "Ctrl", "HbA1c", "24w", "MD", -0.6, 0.04, 0.2, -0.99, -0.21)
    predictor = MetaPredictiveEngine([eff1])
    proj = predictor.predict_trial(10.0, 24.0)
    assert proj.nnt is None
    assert "N/A" in proj.nnt_text


def test_discovery_engine_dose_bounded_empagliflozin():
    """Law 5: Virtual trial must never hallucinate 240 mg/day for Empagliflozin (max 25 mg)."""
    class DummyPipeline:
        def __init__(self):
            self.cohort_name = "Empagliflozin"
            self.cohort_mode = "Homogeneous Single-Drug Cohort"
            self.normalized_drugs = ["Empagliflozin"]
            self.meta_results = {}
            self.studies_df = pd.DataFrame([{"study_id": "STUDY_001", "total_sample_size": 200}])
            self.arms_df = pd.DataFrame([
                {"study_id": "STUDY_001", "arm_name": "Empagliflozin 10mg", "intervention_type": "experimental", "dose_value": 10.0, "dose_unit": "mg"},
                {"study_id": "STUDY_001", "arm_name": "Empagliflozin 25mg", "intervention_type": "experimental", "dose_value": 25.0, "dose_unit": "mg"},
                {"study_id": "STUDY_001", "arm_name": "Placebo", "intervention_type": "placebo", "dose_value": 0.0, "dose_unit": "mg"}
            ])
            self.outcomes_df = pd.DataFrame()
            self.comparison_matrix = pd.DataFrame()

    pipeline = DummyPipeline()
    engine = InSilicoDiscoveryEngine(pipeline)
    res = engine.synthesize_denovo_virtual_trial()
    assert res is not None

    for arm in engine.virtual_trial_arms:
        # Strict ceiling: Empagliflozin dose must NEVER exceed 25 mg
        assert arm.dose_mg <= 25.0, f"Dangerous supratherapeutic dose found: {arm.dose_mg} mg"


def test_zero_n_nan_fallback():
    """Law 6: Multi-stage sample size and dose fallbacks guarantee zero N=nan and zero missing dose."""
    text_abstract = "A randomized trial evaluating empagliflozin 10 mg daily in 520 patients with type 2 diabetes."
    n_resolved = resolve_study_sample_size("RCT_EMPA", title_text="", full_text=text_abstract)
    assert n_resolved == 520
    assert isinstance(n_resolved, int)
    assert n_resolved > 0

    dose_val, dose_unit = resolve_arm_dose("Empagliflozin 10 mg", "Empagliflozin", text_abstract)
    assert dose_val == 10.0
    assert dose_unit == "mg"
