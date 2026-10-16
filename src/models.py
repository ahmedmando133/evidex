"""
Data models and strict Pydantic schemas for AI-assisted clinical trial data extraction.
Designed according to the Project Concept Note (13 October 2026).
"""

from typing import List, Optional, Literal, Any, Dict
from pydantic import BaseModel, Field, field_validator


# ---------------------------------------------------------
# 1. Study Information
# ---------------------------------------------------------
class StudyMetadata(BaseModel):
    study_id: str = Field(description="Unique study identifier, e.g. RCT_ORLISTAT_2024 or RCT_METFORMIN_2012")
    title: str = Field(description="Full published title of the clinical trial")
    authors: Optional[str] = Field(default=None, description="First author et al. or key authors")
    publication_year: Optional[int] = Field(default=None, description="Year of publication")
    journal: Optional[str] = Field(default=None, description="Journal name")
    doi: Optional[str] = Field(default=None, description="DOI link or identifier")
    study_design: str = Field(
        default="Randomized Controlled Trial",
        description="e.g. Randomized, Double-blind, Placebo-controlled trial"
    )
    study_phase: Optional[str] = Field(default=None, description="e.g. Phase III, 2-year double-blind phase, follow-up")
    total_sample_size: Optional[int] = Field(default=None, description="Total number of randomized participants")
    duration_value: Optional[float] = Field(default=None, description="Overall duration numeric value")
    duration_unit: Optional[str] = Field(default=None, description="e.g. weeks, months, years")
    condition_studied: Optional[str] = Field(default=None, description="Target clinical condition, e.g. Obesity, Prediabetes")


# ---------------------------------------------------------
# 2. Treatment Arm
# ---------------------------------------------------------
class TreatmentArm(BaseModel):
    arm_id: str = Field(description="Unique arm identifier, e.g. ARM_ORLISTAT or ARM_PLACEBO")
    study_id: str = Field(description="Foreign key linking to StudyMetadata.study_id")
    arm_name: str = Field(description="Standardized name of the arm, e.g. Orlistat 120mg or Placebo")
    intervention_type: Literal["experimental", "active_comparator", "placebo", "standard_of_care", "lifestyle", "other"] = Field(
        default="experimental",
        description="Standardized classification of intervention"
    )
    drug_name: Optional[str] = Field(default=None, description="Active drug substance or intervention name")
    dose_value: Optional[float] = Field(default=None, description="Numeric dose value, e.g. 120, 850")
    dose_unit: Optional[str] = Field(default=None, description="Unit of dose, e.g. mg, g")
    frequency_number: Optional[float] = Field(default=None, description="Frequency count, e.g. 3, 2, 1")
    frequency_unit: Optional[str] = Field(default=None, description="Frequency unit, e.g. daily, twice daily, weekly")
    sample_size_allocated: Optional[int] = Field(default=None, description="Number of participants randomized to arm")
    sample_size_analyzed: Optional[int] = Field(default=None, description="Number of participants analyzed (PP or ITT)")
    route: Optional[str] = Field(default=None, description="Route of administration, e.g. oral, subcutaneous, intravenous")
    formulation: Optional[str] = Field(default=None, description="Formulation, e.g. tablet, capsule, solution, extended-release")
    titration_info: Optional[str] = Field(default=None, description="Titration or dose adjustment schedule")
    treatment_duration_value: Optional[float] = Field(default=None, description="Treatment duration value for this arm")
    treatment_duration_unit: Optional[str] = Field(default=None, description="Duration unit, e.g. weeks, months, days")
    source_page: Optional[int] = Field(default=None, description="PDF page where arm details are defined")

    @field_validator("intervention_type", mode="before")
    @classmethod
    def normalize_intervention(cls, v):
        if not v:
            return "experimental"
        v_str = str(v).lower().strip()
        if "placebo" in v_str:
            return "placebo"
        if "control" in v_str or "comparator" in v_str:
            return "active_comparator"
        if "standard" in v_str or "care" in v_str or "soc" in v_str:
            return "standard_of_care"
        if "life" in v_str or "diet" in v_str or "exercise" in v_str:
            return "lifestyle"
        if "exp" in v_str or "drug" in v_str or "active" in v_str or "treatment" in v_str:
            return "experimental"
        return "other"


def parse_clinical_range(raw_text: str, criterion_name: str = "") -> Dict[str, Any]:
    """
    Deterministic clinical range and operator parser.
    - Case A (Bounded Range): If two bounds exist (e.g. '>= 20 and <= 74 years', '20-74', '7.0 to 10.0 %',
      'aged≥20 and ≤74 years', 'HbA1c ≥7% and ≤10%'), strictly populates:
      min_operator ('>=' or '>'), min_value (float), max_operator ('<=' or '<'), max_value (float), unit (str).
    - Case B (Single Inequality): If a study only reports a single threshold (e.g. '>= 18 years', '<= 40 kg/m2',
      'eGFR below 30 ml/min/1.73m2', 'systolic blood pressure of less than 95 mm Hg'),
      populates ONLY the respective Min or Max operator and value, and leaves the opposite boundary strictly None.
    - Case C (Categorical / Qualitative): For qualitative conditions (e.g. pregnancy, written consent),
      leaves all operators and numeric values as None.
    """
    import re
    raw = str(raw_text or "").strip()
    cname = str(criterion_name or "").lower()
    raw_l = raw.lower()

    res = {
        "min_operator": None,
        "min_value": None,
        "max_operator": None,
        "max_value": None,
        "unit": None,
        "value": None,
        "is_bounded": False
    }

    # Extract unit if present
    unit_m = re.search(r'\b(years|yo|year-old|kg/m\s*2|kg/m2|mg/dl|mmol/l|umol/l|ml/min(?:/1\.73m2)?|pg/ml|%|mm\s*hg|weeks?|days?|months?)\b', raw, re.I)
    if unit_m:
        u = unit_m.group(1).strip()
        if "kg/m" in u.lower():
            u = "kg/m2"
        elif "mm" in u.lower() and "hg" in u.lower():
            u = "mmHg"
        elif u.lower() in ["yo", "year-old"]:
            u = "years"
        res["unit"] = u
    elif "%" in raw:
        res["unit"] = "%"

    # Categorical exclusions (pregnancy, consent, cancer, etc.)
    if any(k in cname or k in raw_l for k in ["pregnancy", "breastfeeding", "lactation", "consent", "malignancy", "cancer", "transplant", "contraindication"]):
        return res

    # Standardize operators in raw string: normalize unicode
    norm = raw.replace("≥", ">=").replace("≤", "<=").replace("–", "-").replace("—", "-")

    # Case A1: explicit compound range with operators: e.g. '>= 20 and <= 74', '>=7% and <=10%', '>= 7 to <= 10'
    m_bounded_op = re.search(r'([><]=?)\s*(\d+(?:\.\d+)?)\s*(?:%|\w+)?\s*(?:and|to|-)\s*([><]=?)\s*(\d+(?:\.\d+)?)', norm, re.I)
    if m_bounded_op:
        res["min_operator"] = m_bounded_op.group(1)
        res["min_value"] = float(m_bounded_op.group(2))
        res["max_operator"] = m_bounded_op.group(3)
        res["max_value"] = float(m_bounded_op.group(4))
        res["is_bounded"] = True
        return res

    # Case A2: between X and Y or X to Y or X-Y with numbers: e.g. 'between 18 and 65', '18-65', '7.0 to 10.0'
    m_between = re.search(r'(?:between\s+)?(\d+(?:\.\d+)?)\s*(?:%|\w+)?\s*(?:to|-|and)\s*(\d+(?:\.\d+)?)\s*(?:%|\w+)?', norm, re.I)
    if m_between and any(k in raw_l for k in ["between", "to", "-", "–"]):
        v1 = float(m_between.group(1))
        v2 = float(m_between.group(2))
        if v1 < v2:
            res["min_operator"] = ">="
            res["min_value"] = v1
            res["max_operator"] = "<="
            res["max_value"] = v2
            res["is_bounded"] = True
            return res

    # Case B1: Lower bound only (>= X, > X, at least X, X or older, X or greater)
    m_lower = re.search(r'(?:>=|>|\bat least\b|\babove\b)\s*(\d+(?:\.\d+)?)', norm, re.I)
    if not m_lower:
        m_lower = re.search(r'(\d+(?:\.\d+)?)\s*(?:years of age or older|or older|or greater|or more)', norm, re.I)
        if m_lower:
            res["min_operator"] = ">="
            res["min_value"] = float(m_lower.group(1))
            res["value"] = res["min_value"]
            return res
    else:
        op = ">=" if (">=" in m_lower.group(0) or "least" in m_lower.group(0)) else ">"
        res["min_operator"] = op
        res["min_value"] = float(m_lower.group(1))
        res["value"] = res["min_value"]
        return res

    # Case B2: Upper bound only (<= X, < X, at most X, X or less, below X, less than X)
    m_upper = re.search(r'(?:<=|<|\bat most\b|\bbelow\b|\bless than\b)\s*(\d+(?:\.\d+)?)', norm, re.I)
    if not m_upper:
        m_upper = re.search(r'(\d+(?:\.\d+)?)\s*(?:or less|or fewer|or below)', norm, re.I)
        if m_upper:
            res["max_operator"] = "<="
            res["max_value"] = float(m_upper.group(1))
            res["value"] = res["max_value"]
            return res
    else:
        op = "<=" if ("<=" in m_upper.group(0) or "most" in m_upper.group(0) or "less" in m_upper.group(0)) else "<"
        res["max_operator"] = op
        res["max_value"] = float(m_upper.group(1))
        res["value"] = res["max_value"]
        return res

    return res


# ---------------------------------------------------------
# 3. Eligibility Criteria (Atomic decomposition)
# ---------------------------------------------------------
class EligibilityCriterion(BaseModel):
    criterion_id: str = Field(description="Unique criterion identifier, e.g. ELIG_001")
    study_id: str = Field(description="Foreign key linking to StudyMetadata.study_id")
    criterion_type: Literal["inclusion", "exclusion"] = Field(default="inclusion")
    domain: str = Field(
        default="biomarker",
        description="demographic, biomarker, diagnostic, medical_history, lifestyle, or other"
    )
    criterion_name: str = Field(
        description="Standardized name, e.g. age, bmi, fasting_plasma_glucose, impaired_glucose_tolerance, uric_acid"
    )
    less_than: Optional[str] = Field(default=None, description="'<' if less than or part of <=")
    equal: Optional[str] = Field(default=None, description="'=' if equal to or part of >= / <=")
    greater_than: Optional[str] = Field(default=None, description="'>' if greater than or part of >=")
    between: Optional[str] = Field(default=None, description="'between' if value is within a range")
    min_operator: Optional[str] = Field(default=None, description="Lower boundary operator, e.g. '>=', '>'")
    min_value: Optional[float] = Field(default=None, description="Lower limit or minimum threshold value")
    max_operator: Optional[str] = Field(default=None, description="Upper boundary operator, e.g. '<=', '<'")
    max_value: Optional[float] = Field(default=None, description="Upper limit or maximum threshold value")
    value: Optional[float] = Field(default=None, description="Single threshold value if operator is =, >=, <=, >, <")
    unit: Optional[str] = Field(default=None, description="Standardized unit, e.g. years, kg/m2, mg/dL, umol/L")
    raw_source_text: Optional[str] = Field(default=None, description="Original verbatim text snippet from paper")
    source_page: Optional[int] = Field(default=None, description="PDF page number")

    @field_validator("criterion_type", mode="before")
    @classmethod
    def normalize_criterion_type(cls, v):
        if not v:
            return "inclusion"
        return "exclusion" if "exc" in str(v).lower() else "inclusion"

    @field_validator("domain", mode="before")
    @classmethod
    def normalize_elig_domain(cls, v):
        if not v:
            return "other"
        v_low = str(v).lower().strip()
        allowed = {"demographic", "biomarker", "diagnostic", "medical_history", "lifestyle", "other"}
        if v_low in allowed:
            return v_low
        if "demo" in v_low or "age" in v_low or "sex" in v_low or "gender" in v_low:
            return "demographic"
        if "bio" in v_low or "lab" in v_low or "vital" in v_low:
            return "biomarker"
        if "diag" in v_low or "disease" in v_low or "condition" in v_low:
            return "diagnostic"
        if "med" in v_low or "history" in v_low or "prior" in v_low or "pregnan" in v_low:
            return "medical_history"
        if "life" in v_low or "diet" in v_low or "smoke" in v_low:
            return "lifestyle"
        return "other"

    def model_post_init(self, __context: Any) -> None:
        """Ensures atomic boundaries (min_operator, min_value, max_operator, max_value) are deterministically populated."""
        c_name_low = str(self.criterion_name or "").lower()
        cat_keywords = [
            "pregnan", "breastfeed", "nursing", "cancer", "malignan",
            "consent", "informed_consent", "diagnosis", "participation",
            "trial_participation", "severe_hepatic", "cardiovascular_event"
        ]
        if any(k in c_name_low for k in cat_keywords):
            self.min_operator = None
            self.min_value = None
            self.max_operator = None
            self.max_value = None
            self.less_than = None
            self.equal = None
            self.greater_than = None
            self.between = None
            self.value = None
            return

        parsed = parse_clinical_range(self.raw_source_text or "", self.criterion_name or "")

        if not self.unit and parsed["unit"]:
            self.unit = parsed["unit"]

        # Case A: Bounded range detected from text
        if parsed["is_bounded"]:
            self.min_operator = parsed["min_operator"] or ">="
            self.min_value = parsed["min_value"]
            self.max_operator = parsed["max_operator"] or "<="
            self.max_value = parsed["max_value"]
            self.between = "between"
            return

        # Explicit min_value & max_value provided on model
        if self.min_value is not None and self.max_value is not None:
            if not self.min_operator:
                self.min_operator = ">="
            if not self.max_operator:
                self.max_operator = "<="
            self.between = "between"
            return

        # Case B1: Lower bound only
        if parsed["min_value"] is not None:
            self.min_operator = parsed["min_operator"]
            self.min_value = parsed["min_value"]
            self.max_operator = None
            self.max_value = None
            self.greater_than = ">"
            if "=" in (parsed["min_operator"] or ""):
                self.equal = "="
            self.value = parsed["min_value"]
            return

        # Case B2: Upper bound only
        if parsed["max_value"] is not None:
            self.max_operator = parsed["max_operator"]
            self.max_value = parsed["max_value"]
            self.min_operator = None
            self.min_value = None
            self.less_than = "<"
            if "=" in (parsed["max_operator"] or ""):
                self.equal = "="
            self.value = parsed["max_value"]
            return

        # Align with legacy fields
        if self.between == "between" or (self.min_value is not None and self.max_value is not None):
            if not self.min_operator:
                self.min_operator = ">="
            if not self.max_operator:
                self.max_operator = "<="
        elif self.value is not None:
            if self.greater_than and self.equal:
                self.min_operator = ">="
                self.min_value = self.value
                self.max_operator = None
                self.max_value = None
            elif self.greater_than:
                self.min_operator = ">"
                self.min_value = self.value
                self.max_operator = None
                self.max_value = None
            elif self.less_than and self.equal:
                self.max_operator = "<="
                self.max_value = self.value
                self.min_operator = None
                self.min_value = None
            elif self.less_than:
                self.max_operator = "<"
                self.max_value = self.value
                self.min_operator = None
                self.min_value = None
            elif self.equal:
                self.min_operator = "="
                self.min_value = self.value
                self.max_operator = None
                self.max_value = None


# ---------------------------------------------------------
# 4. Clinical Outcomes & Laboratory Measures
# ---------------------------------------------------------
class OutcomeMeasurement(BaseModel):
    outcome_id: str = Field(description="Unique outcome record ID, e.g. OUT_001")
    study_id: str = Field(description="Foreign key linking to StudyMetadata.study_id")
    arm_id: str = Field(description="Foreign key linking to TreatmentArm.arm_id")
    domain: str = Field(
        default="anthropometric",
        description="Clinical domain: anthropometric, glycemic, lipid, renal, liver, inflammatory, cardiac, vital_signs, respiratory, safety_adverse_events, other"
    )
    race: Optional[str] = Field(
        default=None,
        description="Race, ethnicity, or demographic subgroup if explicitly reported (leave None/blank if not reported)"
    )
    gender: Optional[str] = Field(
        default=None,
        description="Gender or sex: Male, Female, or None if not reported"
    )
    is_baseline: Optional[bool] = Field(
        default=None,
        description="True if baseline characteristic (timepoint 0), False if follow-up endpoint"
    )
    metric_type: Optional[str] = Field(
        default=None,
        description="Explicit metric type: 'mean_sd', 'median_iqr', 'events_percentage', 'effect_size'"
    )
    parameter_name: str = Field(
        description="Standardized parameter name, e.g. BMI, Body Weight, WC, TC, HDL, LDL, TG, Glucose, HbA1c, FINS, ALT, AST, High Adherence"
    )
    statistical_type: Literal["continuous", "dichotomous", "categorical"] = Field(default="continuous")
    timepoint_value: Optional[str] = Field(
        default=None,
        description="Numeric or label value of the timepoint, e.g. 0, 12, 2"
    )
    timepoint_unit: Optional[str] = Field(
        default=None,
        description="Measurement unit of timepoint, e.g. weeks, years, months, days"
    )

    @field_validator("domain", mode="before")
    @classmethod
    def normalize_domain(cls, v):
        if not v:
            return "other"
        v_low = str(v).lower().strip()
        allowed = {
            "anthropometric", "glycemic", "lipid", "renal", "liver",
            "inflammatory", "safety_adverse_events", "cardiac", "cardiovascular",
            "vital_signs", "demographic", "respiratory", "pulmonary", "other"
        }
        if v_low in allowed:
            return v_low
        if "safe" in v_low or "adverse" in v_low or "ae" in v_low:
            return "safety_adverse_events"
        if "vital" in v_low or "bp" in v_low or "pressure" in v_low:
            return "vital_signs"
        if "cardio" in v_low or "heart" in v_low:
            return "cardiac"
        if "lung" in v_low or "breath" in v_low or "asthma" in v_low or "pulmon" in v_low:
            return "respiratory"
        if "anthro" in v_low or "weight" in v_low or "bmi" in v_low:
            return "anthropometric"
        if "glyc" in v_low or "diabet" in v_low or "glucose" in v_low or "hba1c" in v_low:
            return "glycemic"
        if "lipid" in v_low or "cholest" in v_low:
            return "lipid"
        if "renal" in v_low or "kidney" in v_low or "egfr" in v_low:
            return "renal"
        if "liver" in v_low or "hepat" in v_low:
            return "liver"
        if "inflam" in v_low or "crp" in v_low:
            return "inflammatory"
        if "demo" in v_low or "age" in v_low or "sex" in v_low:
            return "demographic"
        return "other"

    @field_validator("statistical_type", mode="before")
    @classmethod
    def normalize_stat_type(cls, v):
        if not v:
            return "continuous"
        v_str = str(v).lower().strip()
        if "dichot" in v_str or "binary" in v_str or "event" in v_str or "count" in v_str:
            return "dichotomous"
        if "categ" in v_str:
            return "categorical"
        return "continuous"

    timepoint: Optional[str] = Field(
        default=None,
        description="Optional full timepoint string, e.g. Baseline, 12 weeks"
    )
    
    # Continuous measures
    sample_size: Optional[int] = Field(default=None, description="Number of subjects measured for this parameter")
    mean: Optional[float] = Field(default=None, description="Mean value")
    sd: Optional[float] = Field(default=None, description="Standard deviation")
    se: Optional[float] = Field(default=None, description="Standard error of the mean")
    median: Optional[float] = Field(default=None, description="Median value if non-parametric")
    iqr_lower: Optional[float] = Field(default=None, description="IQR 25th percentile or lower range")
    iqr_upper: Optional[float] = Field(default=None, description="IQR 75th percentile or upper range")
    min_value: Optional[float] = Field(default=None, description="Minimum reported continuous value")
    max_value: Optional[float] = Field(default=None, description="Maximum reported continuous value")
    
    # Reported change from baseline
    change_value: Optional[float] = Field(default=None, description="Reported mean change from baseline")
    change_sd: Optional[float] = Field(default=None, description="SD of change from baseline")
    change_percentage: Optional[float] = Field(default=None, description="Percentage change from baseline")
    is_between_group_diff: Optional[bool] = Field(default=False, description="True if between-group treatment difference, False if within-arm measurement")
    
    # Dichotomous measures (e.g. events, flares)
    events: Optional[int] = Field(default=None, description="Number of events/patients experiencing outcome")
    total: Optional[int] = Field(default=None, description="Denominator total count")
    percentage: Optional[float] = Field(default=None, description="Percentage of events")
    
    # Units and statistical effect
    unit: Optional[str] = Field(default=None, description="Standardized measurement unit, e.g. kg, kg/m2, mg/dL, %")
    effect_measure: Optional[str] = Field(default=None, description="e.g. Mean Difference, Hazard Ratio, Odds Ratio")
    effect_value: Optional[float] = Field(default=None, description="Calculated or reported effect estimate")
    ci_lower: Optional[float] = Field(default=None, description="95% CI lower limit")
    ci_upper: Optional[float] = Field(default=None, description="95% CI upper limit")
    p_value: Optional[str] = Field(default=None, description="Reported p-value string, e.g. '<0.001', '0.023', 'NS'")
    dispersion_type: Optional[str] = Field(default=None, description="Dispersion type: SD, SE, gCV, IQR, 95% CI")
    is_primary: Optional[bool] = Field(default=False, description="True if primary clinical trial endpoint")
    analysis_population: Optional[str] = Field(default=None, description="e.g. FAS (n=20 at Day 28), Full Analysis Set, Treated")
    ratio: Optional[float] = Field(default=None, description="Multiplicative effect or geometric mean ratio")
    ratio_ci_lower: Optional[float] = Field(default=None, description="Ratio 95% CI lower")
    ratio_ci_upper: Optional[float] = Field(default=None, description="Ratio 95% CI upper")
    
    # Derivation & Traceability
    derivation_type: Optional[str] = Field(default="directly_reported", description="directly_reported, mathematically_derived, converted, graph_annotated, digitized")
    digitization_uncertainty: Optional[str] = Field(default=None, description="Precision or uncertainty comment for figure-derived numbers")
    source_page: Optional[int] = Field(default=None, description="PDF page where this data is located")
    source_location: Optional[str] = Field(default=None, description="e.g. Table 1, Table 2, Results text")
    raw_source_text: Optional[str] = Field(default=None, description="Exact text or cell excerpt supporting this fact")

    def model_post_init(self, __context: Any) -> None:
        """Autodetects baseline status, metric type, and demographic stratum."""
        tp_v_str = str(self.timepoint_value or "").strip()
        tp_str = str(self.timepoint or "").lower()
        param_low = str(self.parameter_name or "").lower()

        # 1. Baseline determination
        if self.is_baseline is None:
            if tp_v_str in ["0", "0.0", "baseline"] or "baseline" in tp_str or "day 1" in tp_str or "day 0" in tp_str or "pre" in tp_str:
                self.is_baseline = True
            elif self.change_value is not None or any(k in tp_str for k in ["change", "week", "month", "year", "endpoint", "follow"]):
                self.is_baseline = False
            else:
                self.is_baseline = True if tp_v_str == "" else False

        # 2. Metric type typing
        if self.metric_type is None:
            if self.ratio is not None:
                self.metric_type = "geometric_mean_ratio"
            elif self.dispersion_type in ["gCV", "gcv"] or "geometric" in str(self.dispersion_type or "").lower():
                self.metric_type = "geometric_mean_gcv"
            elif self.se is not None and self.sd is None:
                self.metric_type = "mean_se"
            elif self.events is not None or self.statistical_type == "dichotomous":
                self.metric_type = "events_percentage"
            elif self.median is not None or self.iqr_lower is not None:
                self.metric_type = "median_iqr"
            elif self.effect_value is not None:
                self.metric_type = "effect_size"
            else:
                self.metric_type = "mean_sd"

        # 3. Detect gender from parameter name if not explicitly set
        if not self.gender:
            if "female" in param_low or "women" in param_low:
                self.gender = "Female"
            elif "male" in param_low or " men" in param_low or param_low.startswith("men"):
                self.gender = "Male"

        # 4. Strictly remove fake 'Overall' race fallbacks
        if self.race and str(self.race).strip().lower() in ["overall", "all", "total", "n/a", "none"]:
            self.race = None


# ---------------------------------------------------------
# 5. Provenance & Audit Trail
# ---------------------------------------------------------
class ProvenanceRecord(BaseModel):
    provenance_id: str = Field(description="Unique provenance identifier, e.g. PROV_001")
    study_id: str = Field(description="Foreign key to study_id")
    target_entity: str = Field(description="Entity type: study, arm, eligibility, outcome")
    target_id: str = Field(description="ID of target entity")
    field_name: str = Field(description="Specific field being cited, e.g. mean, dose_value, operator")
    source_page: int = Field(description="PDF page number (1-indexed)")
    source_location: str = Field(description="e.g. Table 1, Paragraph 2 under Methods")
    exact_source_text: str = Field(description="Verbatim text quote from the paper")


# ---------------------------------------------------------
# 6. Validation & Quality Log
# ---------------------------------------------------------
class ValidationIssue(BaseModel):
    issue_id: str = Field(description="Unique issue identifier, e.g. VAL_001")
    study_id: str = Field(description="Foreign key to study_id")
    target_entity: str = Field(description="Entity type: study, arm, eligibility, outcome")
    target_id: str = Field(description="ID of target entity")
    field_name: str = Field(description="Specific field with issue")
    issue_type: str = Field(
        default="warning",
        description="Standardized issue category: not_reported, unit_mismatch, value_out_of_range, unclear_text, calculation_needed, warning, error, info"
    )
    review_required: bool = Field(default=True, description="Flag indicating human clinical review is required")
    comment: str = Field(description="Human-readable explanation of why review is needed")
    rule_id: Optional[str] = Field(default=None, description="Standardized QA rule identifier, e.g. QA_ARM_RECON_001")
    severity: Literal["ERROR", "WARNING", "INFORMATION"] = Field(default="WARNING", description="Severity level")
    source_reference: Optional[str] = Field(default=None, description="Page / table / figure reference")
    expected_condition: Optional[str] = Field(default=None, description="What the clinical schema or inventory expected")
    observed_condition: Optional[str] = Field(default=None, description="What was observed in extracted data")
    recommended_resolution: Optional[str] = Field(default=None, description="Actionable recommendation")
    resolution_status: str = Field(default="OPEN", description="OPEN, RESOLVED, or ACCEPTED_EXCEPTION")


# ---------------------------------------------------------
# 7. Document Component Inventory
# ---------------------------------------------------------
class InventoryItem(BaseModel):
    item_id: str = Field(description="Unique inventory item ID, e.g. INV_TAB_001")
    study_id: str = Field(description="Foreign key to study_id")
    item_type: Literal[
        "table", "continued_table", "figure", "figure_panel", "appendix",
        "narrative_section", "treatment_arm", "timepoint", "primary_endpoint",
        "secondary_endpoint", "safety_endpoint"
    ] = Field(default="table")
    item_label: str = Field(description="Human readable label, e.g. Table 1: Baseline Demographics")
    source_page: Optional[int] = Field(default=None, description="PDF page where component appears")
    extraction_status: Literal[
        "extracted_and_validated",
        "extracted_requires_verification",
        "not_applicable",
        "unavailable_unreadable",
        "expected_not_found",
        "not_reported"
    ] = Field(default="extracted_and_validated")
    status_justification: Optional[str] = Field(default=None, description="Clinical justification for status")
    recovered_record_count: int = Field(default=0, description="Number of atomic extracted records derived")
    notes: Optional[str] = Field(default=None, description="Additional context or notes")


# ---------------------------------------------------------
# 8. Extraction Completeness Gates
# ---------------------------------------------------------
class CompletenessGate(BaseModel):
    gate_name: str = Field(description="Gate A through Gate G name")
    passed: bool = Field(description="True if gate criteria met")
    score: float = Field(default=100.0, description="Completion score 0.0 to 100.0")
    error_count: int = Field(default=0, description="Number of blocking errors")
    warning_count: int = Field(default=0, description="Number of non-blocking warnings")
    details: str = Field(default="", description="Gate evaluation summary")


class CompletenessAudit(BaseModel):
    study_id: str = Field(description="Foreign key to study_id")
    overall_status: Literal[
        "COMPLETE AND VALIDATED",
        "COMPLETE WITH DOCUMENTED NON-BLOCKING WARNINGS",
        "INCOMPLETE — REVIEW REQUIRED",
        "BLOCKED BY SOURCE OR TECHNICAL LIMITATION",
        "FAILED VALIDATION"
    ] = Field(default="COMPLETE AND VALIDATED")
    gates: List[CompletenessGate] = Field(default_factory=list)
    summary: str = Field(default="Extraction completed successfully")
    total_inventory_items: int = Field(default=0)
    validated_items: int = Field(default=0)
    omission_count: int = Field(default=0)


# ---------------------------------------------------------
# 9. Complete Study Extraction Container
# ---------------------------------------------------------
class ExtractedTrialData(BaseModel):
    study: StudyMetadata
    arms: List[TreatmentArm] = Field(default_factory=list)
    eligibility: List[EligibilityCriterion] = Field(default_factory=list)
    outcomes: List[OutcomeMeasurement] = Field(default_factory=list)
    provenance: List[ProvenanceRecord] = Field(default_factory=list)
    validation_log: List[ValidationIssue] = Field(default_factory=list)
    inventory: List[InventoryItem] = Field(default_factory=list)
    completeness_audit: Optional[CompletenessAudit] = Field(default=None)
