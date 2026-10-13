"""
Data models and strict Pydantic schemas for AI-assisted clinical trial data extraction.
Designed according to the Project Concept Note (13 October 2026).
"""

from typing import List, Optional, Literal
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
    source_page: Optional[int] = Field(default=None, description="PDF page where arm details are defined")


# ---------------------------------------------------------
# 3. Eligibility Criteria (Atomic decomposition)
# ---------------------------------------------------------
class EligibilityCriterion(BaseModel):
    criterion_id: str = Field(description="Unique criterion identifier, e.g. ELIG_001")
    study_id: str = Field(description="Foreign key linking to StudyMetadata.study_id")
    criterion_type: Literal["inclusion", "exclusion"] = Field(default="inclusion")
    domain: Literal["demographic", "biomarker", "diagnostic", "medical_history", "lifestyle", "other"] = Field(
        default="biomarker"
    )
    criterion_name: str = Field(
        description="Standardized name, e.g. age, bmi, fasting_plasma_glucose, impaired_glucose_tolerance, uric_acid"
    )
    less_than: Optional[str] = Field(default=None, description="'<' if less than or part of <=")
    equal: Optional[str] = Field(default=None, description="'=' if equal to or part of >= / <=")
    greater_than: Optional[str] = Field(default=None, description="'>' if greater than or part of >=")
    between: Optional[str] = Field(default=None, description="'between' if value is within a range")
    value: Optional[float] = Field(default=None, description="Single threshold value if operator is =, >=, <=, >, <")
    min_value: Optional[float] = Field(default=None, description="Lower limit if operator is 'between'")
    max_value: Optional[float] = Field(default=None, description="Upper limit if operator is 'between'")
    unit: Optional[str] = Field(default=None, description="Standardized unit, e.g. years, kg/m2, mg/dL, umol/L")
    raw_source_text: Optional[str] = Field(default=None, description="Original verbatim text snippet from paper")
    source_page: Optional[int] = Field(default=None, description="PDF page number")


# ---------------------------------------------------------
# 4. Clinical Outcomes & Laboratory Measures
# ---------------------------------------------------------
class OutcomeMeasurement(BaseModel):
    outcome_id: str = Field(description="Unique outcome record ID, e.g. OUT_001")
    study_id: str = Field(description="Foreign key linking to StudyMetadata.study_id")
    arm_id: str = Field(description="Foreign key linking to TreatmentArm.arm_id")
    domain: Literal[
        "anthropometric", "glycemic", "lipid", "renal", "liver", "inflammatory", "safety_adverse_events", "other"
    ] = Field(default="anthropometric")
    race: Optional[str] = Field(
        default="Overall",
        description="Race, ethnicity, or demographic subgroup, e.g. Caucasian, African American, Hispanic, Asian, Native American, Overall"
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
    timepoint: Optional[str] = Field(
        default=None,
        description="Optional full timepoint string, e.g. Baseline, 12 weeks"
    )
    
    # Continuous measures
    sample_size: Optional[int] = Field(default=None, description="Number of subjects measured for this parameter")
    mean: Optional[float] = Field(default=None, description="Mean value")
    sd: Optional[float] = Field(default=None, description="Standard deviation")
    median: Optional[float] = Field(default=None, description="Median value if non-parametric")
    iqr_lower: Optional[float] = Field(default=None, description="IQR 25th percentile or lower range")
    iqr_upper: Optional[float] = Field(default=None, description="IQR 75th percentile or upper range")
    
    # Reported change from baseline
    change_value: Optional[float] = Field(default=None, description="Reported mean change from baseline")
    change_sd: Optional[float] = Field(default=None, description="SD of change from baseline")
    change_percentage: Optional[float] = Field(default=None, description="Percentage change from baseline")
    
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
    
    # Traceability
    source_page: Optional[int] = Field(default=None, description="PDF page where this data is located")
    source_location: Optional[str] = Field(default=None, description="e.g. Table 1, Table 2, Results text")
    raw_source_text: Optional[str] = Field(default=None, description="Exact text or cell excerpt supporting this fact")


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
    issue_type: Literal[
        "not_reported", "unit_mismatch", "value_out_of_range", "unclear_text", "calculation_needed", "warning"
    ] = Field(description="Standardized issue category")
    review_required: bool = Field(default=True, description="Flag indicating human clinical review is required")
    comment: str = Field(description="Human-readable explanation of why review is needed")


# ---------------------------------------------------------
# 7. Complete Study Extraction Container
# ---------------------------------------------------------
class ExtractedTrialData(BaseModel):
    study: StudyMetadata
    arms: List[TreatmentArm] = Field(default_factory=list)
    eligibility: List[EligibilityCriterion] = Field(default_factory=list)
    outcomes: List[OutcomeMeasurement] = Field(default_factory=list)
    provenance: List[ProvenanceRecord] = Field(default_factory=list)
    validation_log: List[ValidationIssue] = Field(default_factory=list)
