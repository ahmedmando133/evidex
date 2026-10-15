"""
Unit tests for MANDOROS In-Silico Discovery & Emergent Synthesis Engine.
"""

import pytest
import openpyxl
from pathlib import Path
from src.cohort_pipeline import ActiveIngredientCohortPipeline
from src.discovery_engine import InSilicoDiscoveryEngine


@pytest.fixture(scope="module")
def mixed_pipeline():
    pipeline = ActiveIngredientCohortPipeline(cohort_name="Mixed_Metabolic_Cohort")
    pipeline.run_all()
    return pipeline


def test_reconstruct_missing_matrix(mixed_pipeline):
    engine = InSilicoDiscoveryEngine(mixed_pipeline)
    cells = engine.reconstruct_missing_matrix()
    assert len(cells) > 0, "Expected missing cells to be reconstructed"
    for c in cells:
        assert c.study_id != ""
        assert c.missing_parameter != ""
        assert c.ci_lower <= c.inferred_value <= c.ci_upper or c.ci_lower <= c.ci_upper
        assert 60.0 <= c.confidence_score <= 100.0
        assert len(c.surrogate_basis) > 0


def test_emergent_discoveries(mixed_pipeline):
    engine = InSilicoDiscoveryEngine(mixed_pipeline)
    discoveries = engine.discover_emergent_phenotypes()
    assert len(discoveries) >= 3, "Expected at least 3 emergent discoveries"
    disc_types = [d.discovery_type for d in discoveries]
    assert "Therapeutic Sweet-Spot" in disc_types
    assert "Hidden Super-Responder" in disc_types
    assert "Latent Biomarker Coupling" in disc_types


def test_synthesize_denovo_virtual_trial(mixed_pipeline):
    engine = InSilicoDiscoveryEngine(mixed_pipeline)
    engine.reconstruct_missing_matrix()
    engine.discover_emergent_phenotypes()
    vt_res = engine.synthesize_denovo_virtual_trial()
    assert "metadata" in vt_res
    assert "arms" in vt_res
    arms = vt_res["arms"]
    assert len(arms) == 3, "Expected 3 virtual trial arms"
    opt_arm = arms[0]
    assert opt_arm.recommended_sample_size >= 100
    assert opt_arm.projected_nnt > 0
    assert 50.0 <= opt_arm.superiority_probability <= 100.0


def test_master_excel_all_10_sheets(mixed_pipeline):
    excel_path = mixed_pipeline.output_dir / f"{mixed_pipeline.cohort_name}_MANDOROS_Master_Report.xlsx"
    assert excel_path.exists(), f"Excel file {excel_path} should exist"
    wb = openpyxl.load_workbook(excel_path)
    expected_sheets = [
        "Executive_Summary",
        "Cross_Trial_Comparison",
        "Harmonized_Outcomes",
        "Meta_Analysis_Results",
        "Predictive_Projections",
        "Heterogeneity_and_Bias",
        "Trial_Differences_Report",
        "Domain_Bridged_Meta_Analysis",
        "In_Silico_New_Discoveries",
        "Synthesized_Virtual_Trial"
    ]
    for s in expected_sheets:
        assert s in wb.sheetnames, f"Expected sheet {s} in Master Excel"
