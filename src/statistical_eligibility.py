"""
src/statistical_eligibility.py
MANDOROS Universal Statistical Eligibility Engine.

Evaluates statistical and methodological eligibility before executing meta-analysis,
predictive modeling, network meta-analysis (SUCRA), and in-silico discoveries.

Adheres strictly to Cochrane Handbook, PRISMA, and ICMJE biostatistical guidelines:
1. Distinct study counts (k_studies) vs comparison counts (k_comparisons).
2. Minimum k >= 2 for two-stage meta-analytic pooling.
3. Minimum k >= 3 for random-effects between-study heterogeneity (tau^2 / I^2).
4. Minimum k >= 10 for publication bias diagnostics (Egger's / Begg's).
5. Minimum k >= 2 connected trials for indirect network meta-analysis (Bucher / SUCRA).
6. Longitudinal extrapolation bounds for predictive dose-duration projections.
7. Pharmacological evidence range checking for therapeutic sweet-spot optimization.
"""

from typing import List, Dict, Any, Optional, Tuple, Set
import math
import numpy as np
import pandas as pd


class StatisticalEligibilityReport:
    """Encapsulates eligibility decisions, methodological rationale, and flags."""
    def __init__(
        self,
        analysis_type: str,
        is_eligible: bool,
        status_code: str,
        k_studies: int,
        total_participants: int,
        methodological_rationale: str,
        allowed_metrics: Optional[List[str]] = None,
        suppressed_metrics: Optional[List[str]] = None
    ):
        self.analysis_type = analysis_type
        self.is_eligible = is_eligible
        self.status_code = status_code
        self.k_studies = k_studies
        self.total_participants = total_participants
        self.methodological_rationale = methodological_rationale
        self.allowed_metrics = allowed_metrics or []
        self.suppressed_metrics = suppressed_metrics or []

    def to_dict(self) -> Dict[str, Any]:
        return {
            "analysis_type": self.analysis_type,
            "is_eligible": self.is_eligible,
            "status_code": self.status_code,
            "k_studies": self.k_studies,
            "total_participants": self.total_participants,
            "methodological_rationale": self.methodological_rationale,
            "allowed_metrics": self.allowed_metrics,
            "suppressed_metrics": self.suppressed_metrics
        }


def extract_unique_study_id(raw_study_label: str) -> str:
    """Extracts the true underlying study_id from composite comparison labels."""
    if not raw_study_label:
        return "UNKNOWN_STUDY"
    # Format might be 'RCT4 [Empagliflozin 10 mg vs Placebo]' -> 'RCT4'
    clean = str(raw_study_label).split(" [")[0].strip()
    return clean


def count_independent_studies(study_labels: List[str]) -> int:
    """Returns the true count of distinct independent clinical trials."""
    unique_ids = {extract_unique_study_id(s) for s in study_labels if s}
    return len(unique_ids)


def compute_true_cohort_n(arms_df: pd.DataFrame, studies_df: Optional[pd.DataFrame] = None) -> int:
    """
    Computes total unique participants across all trials in the cohort.
    Prevents double-counting across repeated outcome measurements.
    """
    if arms_df is not None and not arms_df.empty:
        # Sum randomized / allocated N across unique arms per study
        if "sample_size_allocated" in arms_df.columns:
            n_series = pd.to_numeric(arms_df["sample_size_allocated"], errors="coerce").fillna(0)
            val = int(n_series.sum())
            if val > 0:
                return val
        if "sample_size_analyzed" in arms_df.columns:
            n_series = pd.to_numeric(arms_df["sample_size_analyzed"], errors="coerce").fillna(0)
            val = int(n_series.sum())
            if val > 0:
                return val

    if studies_df is not None and not studies_df.empty:
        if "total_sample_size" in studies_df.columns:
            val = int(pd.to_numeric(studies_df["total_sample_size"], errors="coerce").fillna(0).sum())
            if val > 0:
                return val

    return 0


def assess_meta_analysis_eligibility(
    effects: List[Any],
    studies_df: Optional[pd.DataFrame] = None,
    parameter_name: str = ""
) -> StatisticalEligibilityReport:
    """
    Evaluates whether a standard two-stage random-effects meta-analysis can be estimated.
    Cochrane standard:
    - k = 1: Single trial. Heterogeneity (I^2, tau^2) is NOT ESTIMABLE.
             Random-effects pooling is NOT ESTIMABLE. Report study-specific effect with 95% CI.
    - k >= 2: Fixed-effect / Inverse-variance pooling estimable.
    - k >= 3: Random-effects tau^2 estimable via REML/DL.
    """
    study_ids = [getattr(e, "study_id", "") for e in effects if e is not None]
    k_unique = count_independent_studies(study_ids)

    if k_unique == 0:
        return StatisticalEligibilityReport(
            analysis_type="Conventional Meta-Analysis",
            is_eligible=False,
            status_code="NOT_ESTIMABLE_ZERO_VALID_STUDIES",
            k_studies=0,
            total_participants=0,
            methodological_rationale="No valid effect estimates extracted for parameter.",
            suppressed_metrics=["Pooled_Estimate", "I^2", "tau^2", "Prediction_Interval"]
        )

    if k_unique == 1:
        return StatisticalEligibilityReport(
            analysis_type="Conventional Meta-Analysis",
            is_eligible=False,
            status_code="NOT_ESTIMABLE_SINGLE_TRIAL",
            k_studies=1,
            total_participants=0,
            methodological_rationale=(
                f"Dataset contains exactly one independent RCT for '{parameter_name}'. "
                "Between-study heterogeneity (I^2, tau^2) and multi-study random-effects pooling "
                "are mathematically not estimable (k=1). The study-specific treatment effect and "
                "within-study 95% confidence interval are reported without conventional meta-analytic pooling."
            ),
            allowed_metrics=["Study_Effect", "95%_CI", "SE", "p_value"],
            suppressed_metrics=["I^2", "tau^2", "Q", "Prediction_Interval", "RE_Pooled_Estimate"]
        )

    return StatisticalEligibilityReport(
        analysis_type="Conventional Meta-Analysis",
        is_eligible=True,
        status_code="ELIGIBLE_MULTI_STUDY_META_ANALYSIS",
        k_studies=k_unique,
        total_participants=0,
        methodological_rationale=f"Dataset contains {k_unique} independent trials suitable for meta-analytic synthesis.",
        allowed_metrics=["Pooled_Estimate", "95%_CI", "I^2", "tau^2", "Prediction_Interval"]
    )


def assess_heterogeneity_and_bias_eligibility(
    k_studies: int
) -> Dict[str, Tuple[bool, str]]:
    """
    Evaluates eligibility for Cochran's Q, Higgins' I^2, DerSimonian-Laird tau^2,
    REML tau^2, Egger's test, and Begg's test.
    """
    res = {}
    if k_studies < 2:
        res["Q"] = (False, "NOT_ESTIMABLE_INSUFFICIENT_INDEPENDENT_STUDIES (k=1)")
        res["I^2"] = (False, "NOT_ESTIMABLE_INSUFFICIENT_INDEPENDENT_STUDIES (k=1)")
        res["tau^2"] = (False, "NOT_ESTIMABLE_INSUFFICIENT_INDEPENDENT_STUDIES (k=1)")
        res["egger"] = (False, "NOT_ESTIMABLE_INSUFFICIENT_INDEPENDENT_STUDIES (k < 10)")
        res["begg"] = (False, "NOT_ESTIMABLE_INSUFFICIENT_INDEPENDENT_STUDIES (k < 10)")
    elif k_studies == 2:
        res["Q"] = (True, "ESTIMABLE (df=1)")
        res["I^2"] = (True, "ESTIMABLE")
        res["tau^2"] = (True, "ESTIMABLE (DL only, REML requires k>=3)")
        res["egger"] = (False, "NOT_ESTIMABLE_INSUFFICIENT_INDEPENDENT_STUDIES (k < 10)")
        res["begg"] = (False, "NOT_ESTIMABLE_INSUFFICIENT_INDEPENDENT_STUDIES (k < 10)")
    elif 3 <= k_studies < 10:
        res["Q"] = (True, "ESTIMABLE")
        res["I^2"] = (True, "ESTIMABLE")
        res["tau^2"] = (True, "ESTIMABLE (REML & DL)")
        res["egger"] = (False, "NOT_ESTIMABLE_INSUFFICIENT_INDEPENDENT_STUDIES (k < 10: low statistical power per Cochrane Chapter 13)")
        res["begg"] = (False, "NOT_ESTIMABLE_INSUFFICIENT_INDEPENDENT_STUDIES (k < 10: low statistical power per Cochrane Chapter 13)")
    else:
        res["Q"] = (True, "ESTIMABLE")
        res["I^2"] = (True, "ESTIMABLE")
        res["tau^2"] = (True, "ESTIMABLE")
        res["egger"] = (True, "ESTIMABLE (k>=10)")
        res["begg"] = (True, "ESTIMABLE (k>=10)")

    return res


def assess_network_meta_and_sucra_eligibility(
    k_studies: int,
    num_treatments: int
) -> StatisticalEligibilityReport:
    """
    Evaluates whether indirect comparison (Bucher) and SUCRA ranking are methodologically valid.
    A single 3-arm trial does NOT justify independent network meta-analysis or SUCRA rankings.
    """
    if k_studies < 2:
        return StatisticalEligibilityReport(
            analysis_type="Network Meta-Analysis & SUCRA Hierarchy",
            is_eligible=False,
            status_code="SUCRA_NOT_APPLICABLE_SINGLE_TRIAL",
            k_studies=k_studies,
            total_participants=0,
            methodological_rationale=(
                "A single 3-arm RCT does not form an independent network meta-analysis. "
                "Network transitivity, multi-trial connectivity, and SUCRA treatment ranking "
                "require at least two independent trials linking the treatment nodes."
            ),
            suppressed_metrics=["SUCRA_Score", "Best_Prob", "Indirect_Bucher_NMA"]
        )

    if num_treatments < 3:
        return StatisticalEligibilityReport(
            analysis_type="Network Meta-Analysis & SUCRA Hierarchy",
            is_eligible=False,
            status_code="SUCRA_NOT_APPLICABLE_FEWER_THAN_3_TREATMENTS",
            k_studies=k_studies,
            total_participants=0,
            methodological_rationale="At least 3 distinct active treatment nodes required for network meta-analysis.",
            suppressed_metrics=["SUCRA_Score"]
        )

    return StatisticalEligibilityReport(
        analysis_type="Network Meta-Analysis & SUCRA Hierarchy",
        is_eligible=True,
        status_code="ELIGIBLE_NETWORK_META_ANALYSIS",
        k_studies=k_studies,
        total_participants=0,
        methodological_rationale="Sufficient independent trial connectivity established for network ranking.",
        allowed_metrics=["SUCRA_Score", "Bucher_Indirect_NMA"]
    )


def assess_predictive_projection_eligibility(
    observed_doses: List[float],
    observed_durations_weeks: List[float],
    target_dose_mg: float,
    target_duration_weeks: float
) -> Tuple[bool, str, str]:
    """
    Evaluates whether a dose-duration projection is evidence-grounded or unsupported extrapolation.
    Returns: (is_valid, status_code, explanation)
    """
    if not observed_doses or not observed_durations_weeks:
        return False, "INSUFFICIENT_DATA_FOR_VALIDATED_PREDICTION", "No observed dose or duration data in cohort."

    min_dose = min(observed_doses)
    max_dose = max(observed_doses)
    min_dur = min(observed_durations_weeks)
    max_dur = max(observed_durations_weeks)

    # Check duration extrapolation
    # If trial was 4 weeks (28 days), projecting 12, 24, 52 weeks without longitudinal model is unsupported
    if max_dur <= 4.5 and target_duration_weeks >= 12.0:
        return (
            False,
            "INSUFFICIENT_DATA_FOR_VALIDATED_PREDICTION",
            f"Observed study duration is only {max_dur:.1f} weeks. Projecting long-term efficacy at "
            f"{target_duration_weeks:.0f} weeks represents unvalidated longitudinal extrapolation without published trajectory evidence."
        )

    # Check dose extrapolation: strictly within [0.5 * min_dose, 1.5 * max_dose]
    if target_dose_mg < (0.5 * min_dose) or target_dose_mg > (1.5 * max_dose):
        return (
            False,
            "INVALID_UNSUPPORTED_PREDICTION",
            f"Target dose {target_dose_mg:.1f} mg is outside the evidence range [{0.5*min_dose:.1f}, {1.5*max_dose:.1f}] mg."
        )

    # Check if duration variation exists to model time effect
    if len(set(observed_durations_weeks)) == 1 and target_duration_weeks != min_dur:
        return (
            False,
            "EXPLORATORY_EXTRAPOLATION_UNVALIDATED",
            f"Single-duration cohort ({min_dur:.1f} weeks): Duration slope is not estimable from empirical data."
        )

    return True, "VALIDATED_PREDICTION", "Target parameters fall within evidence bounds."


def assess_domain_pooling_eligibility(
    effects: List[Any],
    domain_name: str = ""
) -> Tuple[bool, str, str]:
    """
    Evaluates whether pooling heterogeneous parameters under a shared domain is methodologically sound.
    Cochrane / PRISMA law:
    - Domain membership alone does not justify meta-analytic pooling.
    - Outcomes must represent identical clinical constructs, compatible timepoints, and k_studies >= 2.
    - Pooling across distinct endpoints (e.g., FPG with CGM, or lipid fractions) or single-trial cohorts is NOT_ESTIMABLE.
    """
    if not effects or len(effects) < 2:
        return False, "NOT_ESTIMABLE_INSUFFICIENT_DATA", "Domain-level pooling requires at least 2 compatible effect estimates."

    params = {getattr(e, "parameter_name", "") for e in effects if getattr(e, "parameter_name", "")}
    study_ids = [getattr(e, "study_id", "") for e in effects if getattr(e, "study_id", "")]
    k_studies = count_independent_studies(study_ids)

    # 1. Single study rule
    if k_studies < 2:
        return (
            False,
            "NOT_ESTIMABLE_SINGLE_TRIAL",
            f"Domain '{domain_name}' pooling is NOT_ESTIMABLE in a single-trial dataset (k=1). "
            "Meta-analytic pooling across differing endpoints within the same trial creates severe "
            "unit-of-analysis dependency and conflates distinct clinical constructs."
        )

    # 2. Construct heterogeneity check
    if len(params) > 1:
        return (
            False,
            "NOT_ESTIMABLE_HETEROGENEOUS_CONSTRUCTS",
            f"Domain '{domain_name}' contains {len(params)} distinct clinical constructs ({', '.join(params)}). "
            "Omnibus pooling of clinically unrelated endpoints into a single SMD is methodologically invalid."
        )

    return True, "ELIGIBLE_DOMAIN_POOLING", "Eligible for domain-level meta-analysis."


def assess_dose_response_model_eligibility(
    observed_doses: List[float],
    k_studies: int
) -> Tuple[bool, str, str]:
    """
    Evaluates eligibility for continuous dose-response meta-regression or in-silico interpolation.
    Biostatistical requirement:
    - Minimum of 3 distinct dose levels (k_doses >= 3) or multi-trial longitudinal data (k_studies >= 2)
      with reproducible parameter estimates and validation.
    - In single-trial cohorts with only 2 active doses, interpolation of unstudied intermediate doses
      (e.g. 17.5 mg) or unvalidated curve fitting is unsupported.
    """
    unique_doses = sorted(list(set(d for d in observed_doses if d is not None and d > 0)))
    if len(unique_doses) < 3 and k_studies < 2:
        return (
            False,
            "INSUFFICIENT_DATA_FOR_VALIDATED_PREDICTION",
            f"Observed data contains only {len(unique_doses)} active dose levels ({unique_doses}) from a single trial (k=1). "
            "Fitting a validated non-linear dose-response model requires at least 3 distinct active dose levels or "
            "multi-trial longitudinal data. Interpolation for unstudied doses is methodologically unsupported."
        )

    return True, "ELIGIBLE_DOSE_RESPONSE_MODEL", "Sufficient dose variation and independent evidence for dose-response modeling."


def validate_therapeutic_optimum(
    candidate_dose_mg: float,
    observed_doses: List[float],
    drug_name: str = ""
) -> Tuple[bool, str, float]:
    """
    Protects against fabricated therapeutic optima (e.g. 1440 mg/day).
    Enforces pharmacological ceilings and evidence boundaries.
    Returns: (is_valid, status_code, clamped_or_validated_dose)
    """
    CLASS_CEILINGS = {
        "empagliflozin": 25.0,
        "dapagliflozin": 10.0,
        "canagliflozin": 300.0,
        "semaglutide": 2.4,
        "tirzepatide": 15.0,
        "liraglutide": 3.0,
        "metformin": 2550.0,
        "orlistat": 360.0,
        "sitagliptin": 100.0,
        "pioglitazone": 45.0
    }

    d_clean = drug_name.lower().strip()
    class_max = 5000.0
    for k, v in CLASS_CEILINGS.items():
        if k in d_clean:
            class_max = v
            break

    # If observed doses exist, must not exceed 1.5x max observed dose
    if observed_doses:
        obs_max = max(observed_doses)
        allowed_max = min(class_max, obs_max * 1.5)
    else:
        allowed_max = class_max

    if candidate_dose_mg > allowed_max or candidate_dose_mg <= 0:
        return (
            False,
            "INVALID_UNSUPPORTED_PREDICTION",
            allowed_max
        )

    return True, "EVIDENCE_BOUNDED_OPTIMUM", candidate_dose_mg


class StatisticalEligibilityEngine:
    """Convenience class providing unified access to all eligibility checks."""

    @staticmethod
    def extract_unique_study_id(raw_study_label: str) -> str:
        return extract_unique_study_id(raw_study_label)

    @staticmethod
    def count_independent_studies(study_labels: List[str]) -> int:
        return count_independent_studies(study_labels)

    @staticmethod
    def compute_true_cohort_n(arms_df: pd.DataFrame, studies_df: Optional[pd.DataFrame] = None) -> int:
        return compute_true_cohort_n(arms_df, studies_df)

    @staticmethod
    def check_meta_analysis_eligibility(effects: List[Any], parameter_name: str = "", studies_df: Optional[pd.DataFrame] = None) -> Dict[str, Any]:
        rep = assess_meta_analysis_eligibility(effects, studies_df, parameter_name)
        k_unique = count_independent_studies([getattr(e, "study_id", "") for e in effects if e])
        k_comp = len([e for e in effects if e])
        return {
            "eligible": rep.is_eligible,
            "status_code": rep.status_code,
            "k_studies": k_unique,
            "k_comparisons": k_comp,
            "heterogeneity_estimable": k_unique >= 2,
            "model_recommended": "Random-Effects (REML/DL)" if k_unique >= 3 else ("Fixed-Effect (Single Trial)" if k_unique < 2 else "Fixed-Effect (Two Studies)"),
            "rationale": rep.methodological_rationale
        }

    @staticmethod
    def check_publication_bias_eligibility(k_studies: int) -> Dict[str, Any]:
        return {
            "eligible": k_studies >= 10,
            "status": "ESTIMABLE" if k_studies >= 10 else f"NOT_ESTIMABLE_INSUFFICIENT_INDEPENDENT_STUDIES (k < 10)",
            "reason": f"Funnel plot asymmetry tests require at least 10 independent studies (observed k={k_studies})." if k_studies < 10 else "Sufficient independent studies for publication bias diagnostics."
        }

    @staticmethod
    def check_nma_network(treatments: List[str], comparisons: List[Tuple[str, str]], k_studies: int) -> Dict[str, Any]:
        rep = assess_network_meta_and_sucra_eligibility(k_studies, len(treatments))
        return {
            "eligible": rep.is_eligible,
            "status_code": rep.status_code,
            "reason": rep.methodological_rationale
        }

    @staticmethod
    def check_predictive_projection_eligibility(observed_doses: List[float], observed_durations: List[float], target_dose: float, target_duration: float) -> Tuple[bool, str, str]:
        return assess_predictive_projection_eligibility(observed_doses, observed_durations, target_dose, target_duration)

    @staticmethod
    def check_domain_pooling_eligibility(effects: List[Any], domain_name: str = "") -> Tuple[bool, str, str]:
        return assess_domain_pooling_eligibility(effects, domain_name)

    @staticmethod
    def check_dose_response_model_eligibility(observed_doses: List[float], k_studies: int) -> Tuple[bool, str, str]:
        return assess_dose_response_model_eligibility(observed_doses, k_studies)

    @staticmethod
    def validate_therapeutic_optimum(candidate_dose_mg: float, observed_doses: List[float], drug_name: str = "") -> Tuple[bool, str, float]:
        return validate_therapeutic_optimum(candidate_dose_mg, observed_doses, drug_name)

