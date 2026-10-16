"""
Unit and Integration Tests for Extraction Guardrails, Atomic Schema Separation,
Population Stratification, and Anti-Hallucination Audits.
"""

import sys
from pathlib import Path
import pytest
import openpyxl

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.models import (
    StudyMetadata, TreatmentArm, EligibilityCriterion,
    OutcomeMeasurement, ExtractedTrialData, ProvenanceRecord, ValidationIssue
)
from src.extractor import RCTExtractor
from src.exporter import ExcelTrialExporter


def test_continuous_criteria_range_parsing():
    """Verify continuous ranges (e.g. '>= 20 and <= 74' or '7 to 10') parse into atomic min/max columns."""
    c1 = EligibilityCriterion(
        criterion_id="ELIG_001",
        study_id="TEST_001",
        criterion_type="inclusion",
        domain="demographic",
        criterion_name="Age",
        raw_source_text="Age >= 20 and <= 74 years",
        unit="years"
    )
    assert c1.min_operator == ">="
    assert c1.min_value == 20.0
    assert c1.max_operator == "<="
    assert c1.max_value == 74.0
    assert c1.unit == "years"

    c2 = EligibilityCriterion(
        criterion_id="ELIG_002",
        study_id="TEST_001",
        criterion_type="inclusion",
        domain="biomarker",
        criterion_name="HbA1c",
        raw_source_text="HbA1c between 7.0 and 10.0 %",
        unit="%"
    )
    assert c2.min_value == 7.0
    assert c2.max_value == 10.0

    c3 = EligibilityCriterion(
        criterion_id="ELIG_003",
        study_id="TEST_001",
        criterion_type="inclusion",
        domain="demographic",
        criterion_name="Age",
        greater_than=">",
        equal="=",
        value=18.0,
        raw_source_text="Age >= 18 years"
    )
    assert c3.min_operator == ">="
    assert c3.min_value == 18.0


def test_categorical_criteria_null_operators():
    """Verify categorical criteria (pregnancy, cancer, consent) have null mathematical operators."""
    c = EligibilityCriterion(
        criterion_id="ELIG_004",
        study_id="TEST_001",
        criterion_type="exclusion",
        domain="medical_history",
        criterion_name="pregnancy_or_breastfeeding",
        raw_source_text="Pregnant or nursing women",
        less_than="<",  # Erroneous input that should be cleaned
        value=1.0
    )
    # Both model_post_init and extractor rules sanitize categorical criteria
    assert c.less_than is None
    assert c.value is None
    assert c.min_value is None
    assert c.max_value is None


def test_anti_overall_race_sanitization():
    """Verify unmeasured race is never stored as 'Overall'."""
    o1 = OutcomeMeasurement(
        outcome_id="OUT_001",
        study_id="TEST_001",
        arm_id="ARM_001",
        parameter_name="Body Weight",
        race="Overall",
        mean=85.0,
        sd=12.0
    )
    assert o1.race is None

    o2 = OutcomeMeasurement(
        outcome_id="OUT_002",
        study_id="TEST_001",
        arm_id="ARM_001",
        parameter_name="Body Weight",
        race="White",
        mean=86.0,
        sd=11.5
    )
    assert o2.race == "White"


def test_gender_mathematical_reconstruction():
    """Verify mathematical calculation of opposing subgroup when only one gender is reported."""
    study_meta = StudyMetadata(
        study_id="TEST_001",
        title="Test Trial",
        total_sample_size=100
    )
    arm = TreatmentArm(
        arm_id="ARM_001",
        study_id="TEST_001",
        arm_name="Experimental 50mg",
        sample_size_analyzed=100
    )
    male_out = OutcomeMeasurement(
        outcome_id="OUT_001",
        study_id="TEST_001",
        arm_id="ARM_001",
        parameter_name="Sex: Male",
        statistical_type="dichotomous",
        events=65,
        total=100,
        percentage=65.0,
        is_baseline=True
    )

    extractor = RCTExtractor.__new__(RCTExtractor)
    extractor.pdf_path = "dummy.pdf"
    
    reconstructed = extractor._reconstruct_and_propagate_demographics(
        study_id="TEST_001",
        study_meta=study_meta,
        arms=[arm],
        outcomes=[male_out],
        sections={}
    )

    female_rec = next((o for o in reconstructed if o.gender == "Female" or "female" in o.parameter_name.lower()), None)
    assert female_rec is not None
    assert female_rec.events == 35
    assert female_rec.percentage == 35.0


def test_biomarker_domain_and_zero_contamination_audit():
    """Verify biomarker domain integrity: FPG is glycemic (not liver), AST/ALT is liver (not glycemic)."""
    extractor = RCTExtractor.__new__(RCTExtractor)

    # 1. Glucose wrongly assigned to liver
    o1 = OutcomeMeasurement(
        outcome_id="OUT_001",
        study_id="TEST_001",
        arm_id="ARM_001",
        parameter_name="Fasting Plasma Glucose",
        domain="liver",
        mean=110.0,
        sd=15.0
    )
    # 2. Glucose misattributed as AST
    o2 = OutcomeMeasurement(
        outcome_id="OUT_002",
        study_id="TEST_001",
        arm_id="ARM_001",
        parameter_name="AST (FPG)",
        raw_source_text="Fasting plasma glucose was 110 mg/dL",
        domain="liver",
        mean=110.0,
        sd=15.0
    )
    # 3. Contaminated fake liver enzyme when text was actually about glucose
    o3 = OutcomeMeasurement(
        outcome_id="OUT_003",
        study_id="TEST_001",
        arm_id="ARM_001",
        parameter_name="ALT",
        raw_source_text="glucose levels decreased significantly",
        domain="liver",
        mean=25.0
    )

    sanitized = extractor._audit_and_sanitize_biomarkers([o1, o2, o3])
    
    # o1 domain corrected to glycemic
    assert sanitized[0].domain == "glycemic"
    assert sanitized[0].parameter_name == "Fasting Plasma Glucose"
    
    # o2 parameter corrected to Fasting Plasma Glucose and domain glycemic
    assert sanitized[1].domain == "glycemic"
    assert "Glucose" in sanitized[1].parameter_name

    # o3 should have been discarded due to cross-contamination
    assert len(sanitized) == 2


def test_master_extraction_sheet_and_row_continuity(tmp_path):
    """Verify Master_Extraction_Sheet builds with atomic columns, split criteria, and row continuity."""
    study = StudyMetadata(
        study_id="TEST_RCT",
        title="Sample Double-Blind Trial",
        publication_year=2024,
        total_sample_size=100
    )
    arm1 = TreatmentArm(
        arm_id="ARM_01",
        study_id="TEST_RCT",
        arm_name="Active 25mg",
        drug_name="ActiveDrug",
        dose_value=25.0,
        dose_unit="mg",
        frequency_number=1.0,
        frequency_unit="daily",
        sample_size_allocated=50,
        sample_size_analyzed=50
    )
    arm2 = TreatmentArm(
        arm_id="ARM_02",
        study_id="TEST_RCT",
        arm_name="Placebo",
        drug_name="Placebo",
        dose_value=0.0,
        dose_unit="mg",
        frequency_number=1.0,
        frequency_unit="daily",
        sample_size_allocated=50,
        sample_size_analyzed=50
    )
    elig1 = EligibilityCriterion(
        criterion_id="E01",
        study_id="TEST_RCT",
        criterion_type="inclusion",
        domain="demographic",
        criterion_name="Age",
        min_operator=">=",
        min_value=20.0,
        max_operator="<=",
        max_value=74.0,
        unit="years",
        raw_source_text="Age >= 20 and <= 74 years"
    )
    elig2 = EligibilityCriterion(
        criterion_id="E02",
        study_id="TEST_RCT",
        criterion_type="exclusion",
        domain="medical_history",
        criterion_name="Pregnancy",
        raw_source_text="Pregnant patients"
    )
    out_base_age = OutcomeMeasurement(
        outcome_id="O01",
        study_id="TEST_RCT",
        arm_id="ARM_01",
        domain="demographic",
        parameter_name="Age",
        timepoint="Baseline",
        timepoint_value="0",
        timepoint_unit="weeks",
        is_baseline=True,
        metric_type="mean_sd",
        mean=55.0,
        sd=8.0,
        unit="years"
    )
    out_male = OutcomeMeasurement(
        outcome_id="O02",
        study_id="TEST_RCT",
        arm_id="ARM_01",
        domain="demographic",
        parameter_name="Sex: Male",
        gender="Male",
        timepoint="Baseline",
        is_baseline=True,
        metric_type="events_percentage",
        events=30,
        percentage=60.0
    )
    out_female = OutcomeMeasurement(
        outcome_id="O03",
        study_id="TEST_RCT",
        arm_id="ARM_01",
        domain="demographic",
        parameter_name="Sex: Female",
        gender="Female",
        timepoint="Baseline",
        is_baseline=True,
        metric_type="events_percentage",
        events=20,
        percentage=40.0
    )
    # Efficacy endpoint at Week 12
    out_eff_w12 = OutcomeMeasurement(
        outcome_id="O04",
        study_id="TEST_RCT",
        arm_id="ARM_01",
        domain="glycemic",
        parameter_name="HbA1c",
        timepoint="Week 12",
        timepoint_value="12",
        timepoint_unit="weeks",
        is_baseline=False,
        metric_type="mean_sd",
        mean=6.5,
        sd=0.6,
        change_value=-0.8,
        unit="%"
    )
    # Efficacy endpoint at Week 24
    out_eff_w24 = OutcomeMeasurement(
        outcome_id="O05",
        study_id="TEST_RCT",
        arm_id="ARM_01",
        domain="glycemic",
        parameter_name="HbA1c",
        timepoint="Week 24",
        timepoint_value="24",
        timepoint_unit="weeks",
        is_baseline=False,
        metric_type="mean_sd",
        mean=6.3,
        sd=0.5,
        change_value=-1.0,
        unit="%"
    )

    data = ExtractedTrialData(
        study=study,
        arms=[arm1, arm2],
        eligibility=[elig1, elig2],
        outcomes=[out_base_age, out_male, out_female, out_eff_w12, out_eff_w24],
        provenance=[],
        validation_log=[]
    )

    out_file = str(tmp_path / "test_trial_extracted.xlsx")
    exporter = ExcelTrialExporter(data)
    exporter.export(out_file)

    # Load workbook and inspect Master_Extraction_Sheet
    wb = openpyxl.load_workbook(out_file)
    assert "Master_Extraction_Sheet" in wb.sheetnames
    assert "Eligibility" in wb.sheetnames
    assert "Outcomes" in wb.sheetnames
    assert "Flattened_View" in wb.sheetnames
    assert "Variables_Matrix" in wb.sheetnames

    ws = wb["Master_Extraction_Sheet"]

    # Read row 1 (Categories), row 2 (Major variables), row 3 (Atomic sub-headers)
    r1_cats = [cell.value for cell in ws[1]]
    r2_vars = [cell.value for cell in ws[2]]
    r3_subheaders = [cell.value for cell in ws[3]]

    # 1. Section Categories in Row 1
    assert "STUDY & INTERVENTION ARMS" in r1_cats
    assert "INCLUSION CRITERIA" in r1_cats
    assert "EXCLUSION CRITERIA" in r1_cats
    assert "POPULATION STRATIFICATION" in r1_cats
    assert "BASELINE CHARACTERISTICS & LABS (TIME 0)" in r1_cats
    assert "LONGITUDINAL EFFICACY & ENDPOINTS (FOLLOW-UP)" in r1_cats

    # 2. Major Variables in Row 2
    assert "Dose" in r2_vars
    assert "Frequency" in r2_vars
    assert "Age" in r2_vars
    assert "Pregnancy" in r2_vars
    assert "Male Stratum" in r2_vars
    assert "Female Stratum" in r2_vars

    # 3. Atomic sub-headers in Row 3
    assert "Dose Value" in r3_subheaders
    assert "Dose Unit" in r3_subheaders
    assert "Frequency Value" in r3_subheaders
    assert "Frequency Unit" in r3_subheaders
    assert "Min" in r3_subheaders
    assert "Max" in r3_subheaders
    assert "Unit" in r3_subheaders
    assert "Count (n)" in r3_subheaders
    assert "Percentage (%)" in r3_subheaders
    assert "Change from Baseline" in r3_subheaders

    # 4. Verify arm-level continuity (row propagation) across timepoint rows
    # Row 4 is Week 12, Row 5 is Week 24 for ARM_01
    row4_vals = [cell.value for cell in ws[4]]
    row5_vals = [cell.value for cell in ws[5]]

    # Dose Value is col 4 (0-indexed 3), Dose Unit is col 5 (0-indexed 4)
    assert row4_vals[3] == 25.0
    assert row4_vals[4] == "mg"
    assert row5_vals[3] == 25.0
    assert row5_vals[4] == "mg"

    # Frequency Value is col 6 (0-indexed 5), Frequency Unit is col 7 (0-indexed 6)
    assert row4_vals[5] == 1.0
    assert row4_vals[6] == "daily"
    assert row5_vals[5] == 1.0
    assert row5_vals[6] == "daily"

    # Demographics and baseline characteristics are fully propagated to subsequent rows
    # Male % is col pop_start_col + 3, Female % is pop_start_col + 5
    male_pct_idx = r3_subheaders.index("Percentage (%)")
    # Both rows 4 and 5 must have male and female percentages populated!
    assert row4_vals[male_pct_idx] == 60.0
    assert row5_vals[male_pct_idx] == 60.0
