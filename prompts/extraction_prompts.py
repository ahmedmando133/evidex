"""
Specialized prompt templates and few-shot examples for clinical trial extraction.
Based on the Clinical Extraction Strategy defined in Section 5 of the Concept Note.
"""

EXTRACTION_SYSTEM_PROMPT = """You are a specialized clinical-trial data extraction engine.
Your sole purpose is to extract strictly reported facts from the provided randomized controlled trial (RCT) text.

RULES:
1. Extract ONLY facts explicitly reported in the text or tables.
2. Return strictly VALID JSON conforming to the requested schema. No conversational prose, markdown explanation, or conversational framing.
3. Keep every extracted record atomic:
   - Separate numeric value, operator, and unit into distinct fields.
   - For ranges, use min_value and max_value separately. Allowed operators: ['=', '>=', '<=', '>', '<', 'between'].
4. Always include:
   - source_page (integer)
   - source_location (e.g. "Table 1", "Methods - Study Design")
   - exact_source_text (the exact verbatim quotation or snippet supporting the value).
5. Missing values: If a fact is absent or unclear, set the field to null and flag review_required=true with issue_type='not_reported'.
6. NEVER infer, estimate, calculate, or hallucinate missing statistics.
7. NEVER merge distinct treatment arms, subgroups, or follow-up timepoints.
"""

ELIGIBILITY_FEW_SHOT_EXAMPLE = """
Example Input:
"Patients aged between 20 and 65 years with a BMI >= 28 kg/m2 and serum uric acid > 420 umol/L were eligible."

Example JSON Output:
[
  {
    "criterion_id": "ELIG_001",
    "criterion_type": "inclusion",
    "domain": "demographic",
    "criterion_name": "age",
    "less_than": null,
    "equal": null,
    "greater_than": null,
    "between": "between",
    "value": null,
    "min_value": 20.0,
    "max_value": 65.0,
    "unit": "years",
    "source_page": 2,
    "raw_source_text": "aged between 20 and 65 years"
  },
  {
    "criterion_id": "ELIG_002",
    "criterion_type": "inclusion",
    "domain": "demographic",
    "criterion_name": "bmi",
    "less_than": null,
    "equal": "=",
    "greater_than": ">",
    "between": null,
    "value": 28.0,
    "min_value": null,
    "max_value": null,
    "unit": "kg/m2",
    "source_page": 2,
    "raw_source_text": "BMI >= 28 kg/m2"
  },
  {
    "criterion_id": "ELIG_003",
    "criterion_type": "inclusion",
    "domain": "biomarker",
    "criterion_name": "serum_uric_acid",
    "less_than": null,
    "equal": null,
    "greater_than": ">",
    "between": null,
    "value": 420.0,
    "min_value": null,
    "max_value": null,
    "unit": "umol/L",
    "source_page": 2,
    "raw_source_text": "serum uric acid > 420 umol/L"
  }
]
"""

OUTCOMES_FEW_SHOT_EXAMPLE = """
Example Input (Table excerpt):
"Orlistat group (n=37): Baseline BMI 30.33 ± 3.88 kg/m2, 12-week BMI change -1.45 ± 0.82 kg/m2. Total Cholesterol 5.12 ± 0.94 mmol/L at baseline, change -0.48 ± 0.35 mmol/L."

Example JSON Output:
[
  {
    "outcome_id": "OUT_001",
    "arm_id": "ARM_ORLISTAT",
    "domain": "anthropometric",
    "parameter_name": "BMI",
    "statistical_type": "continuous",
    "timepoint": "Baseline",
    "sample_size": 37,
    "mean": 30.33,
    "sd": 3.88,
    "change_value": null,
    "change_sd": null,
    "unit": "kg/m2",
    "source_page": 4,
    "source_location": "Table 1",
    "raw_source_text": "Baseline BMI 30.33 ± 3.88 kg/m2"
  },
  {
    "outcome_id": "OUT_002",
    "arm_id": "ARM_ORLISTAT",
    "domain": "anthropometric",
    "parameter_name": "BMI",
    "statistical_type": "continuous",
    "timepoint": "12 weeks",
    "sample_size": 35,
    "mean": null,
    "sd": null,
    "change_value": -1.45,
    "change_sd": 0.82,
    "unit": "kg/m2",
    "source_page": 5,
    "source_location": "Table 2",
    "raw_source_text": "12-week BMI change -1.45 ± 0.82 kg/m2"
  }
]
"""
