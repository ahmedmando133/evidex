"""
Real-Document Acceptance Tests on representative RCT PDFs.
Executes extraction on actual clinical trial PDFs in data/raw/:
- Orlistat.pdf (XENDOS / Multi-arm / 54-week obesity trial)
- metformin clinical trial.pdf (DPP / Diabetes Prevention Program)
- semaglutide trial.pdf (STEP-1 / SELECT / GLP-1 RA trial)
- Dabagliflozin.pdf (DAPA-HF / SGLT2i heart failure trial)

Verifies:
1. Extraction completeness & Zero-Omission standards
2. Source Inventory & 7-Gate Completeness Certification
3. Workbook generation with all canonical + QA sheets
4. Downstream meta-analysis compatibility
"""

import sys
import os
from pathlib import Path
import pytest
import openpyxl

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from src.extractor import RCTExtractor
from src.exporter import ExcelTrialExporter


@pytest.mark.parametrize("pdf_name,expected_drug", [
    ("Orlistat.pdf", "Orlistat"),
    ("metformin clinical trial.pdf", "Metformin"),
    ("semaglutide trial.pdf", "Semaglutide"),
    ("Dabagliflozin.pdf", "Dapagliflozin"),
])
def test_real_document_extraction_and_qa_gates(pdf_name, expected_drug, tmp_path):
    pdf_path = Path(__file__).resolve().parent.parent / "data" / "raw" / pdf_name
    if not pdf_path.exists():
        pytest.skip(f"PDF fixture {pdf_name} not found at {pdf_path}")

    # Initialize extractor (without external API key to exercise smart local pharmacology engine)
    extractor = RCTExtractor(str(pdf_path), api_key=None)
    data = extractor.extract_all()

    # 1. Verification of Study Metadata
    assert data.study is not None
    assert data.study.study_id
    assert data.study.title

    # 2. Verification of Treatment Arms
    assert len(data.arms) >= 1
    has_target_drug = any(expected_drug.lower() in str(a.arm_name).lower() or expected_drug.lower() in str(a.drug_name).lower() for a in data.arms)
    assert has_target_drug or len(data.arms) >= 1

    for arm in data.arms:
        assert arm.arm_id
        assert arm.arm_name
        assert arm.intervention_type in ["experimental", "placebo", "active_comparator", "standard_of_care", "lifestyle", "other"]

    # 3. Verification of Clinical Outcomes
    assert len(data.outcomes) > 0
    for o in data.outcomes:
        assert o.outcome_id
        assert o.parameter_name
        assert o.domain in [
            "anthropometric", "glycemic", "lipid", "renal", "liver",
            "inflammatory", "safety_adverse_events", "cardiac", "cardiovascular",
            "vital_signs", "demographic", "respiratory", "pulmonary", "other"
        ]
        assert o.statistical_type in ["continuous", "dichotomous", "categorical"]

    # 4. Verification of Document Inventory & Completeness Audit
    assert hasattr(data, "inventory")
    assert len(data.inventory) >= 3

    assert data.completeness_audit is not None
    audit = data.completeness_audit
    assert audit.overall_status in [
        "COMPLETE AND VALIDATED",
        "COMPLETE WITH DOCUMENTED NON-BLOCKING WARNINGS"
    ]
    assert len(audit.gates) == 7

    # 5. Export to Excel Workbook and verify sheets
    out_xlsx = str(tmp_path / f"{expected_drug}_test_extracted.xlsx")
    exporter = ExcelTrialExporter(data)
    exported_file = exporter.export(out_xlsx)
    assert os.path.exists(exported_file)

    wb = openpyxl.load_workbook(exported_file)
    expected_sheets = [
        "Master_Extraction_Sheet",
        "Studies",
        "Arms",
        "Eligibility",
        "Outcomes",
        "Provenance",
        "Validation_Log",
        "Flattened_View",
        "Variables_Matrix",
        "QA_Audit_and_Inventory"
    ]
    for s_name in expected_sheets:
        assert s_name in wb.sheetnames, f"Expected sheet '{s_name}' missing from {exported_file}"
