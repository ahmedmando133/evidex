import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

def build_audit_excel():
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Error_Audit_Log"

    # Palette
    navy_fill = PatternFill(start_color="1E3A8A", end_color="1E3A8A", fill_type="solid")
    header_fill = PatternFill(start_color="2563EB", end_color="2563EB", fill_type="solid")
    zebra_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")
    title_font = Font(name="Calibri", size=14, bold=True, color="FFFFFF")
    header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
    body_font = Font(name="Calibri", size=10)
    bold_font = Font(name="Calibri", size=10, bold=True)
    thin_side = Side(border_style="thin", color="CBD5E1")
    thin_border = Border(left=thin_side, right=thin_side, top=thin_side, bottom=thin_side)

    # Title Block
    ws.merge_cells("A1:H1")
    ws["A1"] = "MANDOROS Phase 1 & 2 Comprehensive Error & Correction Audit Log"
    ws["A1"].font = title_font
    ws["A1"].fill = navy_fill
    ws["A1"].alignment = Alignment(horizontal="center", vertical="center")

    ws.merge_cells("A2:H2")
    ws["A2"] = "Academic Biostatistical System-Wide Audit - Universal Source-Code & Pipeline Correction Tracking"
    ws["A2"].font = Font(name="Calibri", size=10, italic=True, color="555555")
    ws["A2"].alignment = Alignment(horizontal="center", vertical="center")

    headers = [
        "Defect ID",
        "Category / Sheet",
        "Cell / Location",
        "Original Value / Finding",
        "Corrected Value / Status",
        "PDF Source of Truth",
        "Root Cause & Methodological Rationale",
        "Modified System Component"
    ]

    for col_idx, h in enumerate(headers, 1):
        c = ws.cell(row=4, column=col_idx, value=h)
        c.font = header_font
        c.fill = header_fill
        c.alignment = Alignment(horizontal="center", vertical="center", wrap_text=True)

    audit_data = [
        (
            "DEF-01",
            "Arms / Denominators",
            "Arms!C2:C4; Master_Extraction_Sheet!C4:C6",
            "Empa 10mg: 21, Empa 25mg: 20, Placebo: 19",
            "Empa 10mg: 20, Empa 25mg: 19, Placebo: 21",
            "PDF Table 1 (page 4), Abstract (page 1)",
            "Treatment arms were inverted during table column mapping. Corrected arm mapping binds authoritative randomized N and segregates analyzed N.",
            "src/extractor.py (Table 1 extraction & baseline arm binding)"
        ),
        (
            "DEF-02",
            "Studies / Phase Classification",
            "Studies!H2; Master_Extraction_Sheet!H4",
            "Phase III",
            "Not explicitly reported",
            "Full PDF text (Nishimura et al., 2015)",
            "Trial phase was not explicitly stated in the publication text. Enforced strict rule that prevents hallucinating or inferring phase without explicit source confirmation.",
            "src/extractor.py (Strict study phase extraction pattern)"
        ),
        (
            "DEF-03",
            "Outcomes / FPG Contrast Mapping",
            "Outcomes!O33:O37",
            "O33: -19.6, O34: -22.1, O36: -26.3, O37: -33.5",
            "O33: -23.8, O34: -30.5, O36: -28.3, O37: -39.7",
            "PDF Figure 3 (page 6)",
            "Extracted within-arm changes were confounded with between-group ANCOVA differences. Unified within-arm changes and ANCOVA contrasts onto correct arm rows.",
            "src/extractor.py (Figure 3 FPG extraction & contrast binding)"
        ),
        (
            "DEF-04",
            "Outcomes / Statistical Uncertainty",
            "Outcomes!AM39:AM43",
            "Between-group CIs incorrectly attached to within-arm adjusted means",
            "Within-arm SEs and between-group CIs strictly segregated",
            "PDF Figure 4 (page 6)",
            "Prevented cross-pollination of between-group confidence intervals onto within-arm continuous measurements.",
            "src/extractor.py (Figure 4 CGM extraction block)"
        ),
        (
            "DEF-05",
            "Meta-Analysis / Table 4 Mapping",
            "Meta_Analysis_Results!G10",
            "Empa 10 mg vs Placebo: 4.3 mg/dL",
            "Empa 10 mg vs Placebo: 1.7 mg/dL [-0.6, 4.1], p=0.149; Empa 25 mg vs Placebo: 4.3 mg/dL [2.0, 6.7], p<0.001",
            "PDF Table 4 (page 10)",
            "Regex failed on unicode minus and space inside parentheses in '1.7 ( -0.6, 4.1)', causing 25 mg effect to shift to 10 mg. Normalized unicode dashes and robustified whitespace regex.",
            "src/extractor.py (Table 4 diff_matches regex & unicode normalization)"
        ),
        (
            "DEF-06",
            "Meta-Analysis / Zero Effects",
            "Meta_Analysis_Results!G14:G15",
            "Spurious 0.0 effects generated for HbA1c comparisons",
            "Zero artificial 0.0 effects. Day 29 HbA1c: 10 mg = -0.35 [-0.52, -0.19]; 25 mg = -0.52 [-0.68, -0.35]",
            "PDF page 7 (HbA1c results text)",
            "Spurious duplicate follow-up rows created placeholder 0.0 values. Eradicated duplicate rows and enforced referee checks prohibiting numerical 0.0 for missing estimates.",
            "src/extractor.py, src/scientific_referee.py (REF-14-NO-DUPLICATE-OUTCOMES)"
        ),
        (
            "DEF-07",
            "Meta-Analysis / Single Multi-Arm Pooling",
            "Pooled_Effect_Estimates!F5; Executive_Summary!E5",
            "Combined 8-iso-PGF2a effect -33.915 pooling two active arms sharing a placebo",
            "Suppressed naive pooling; retained dose-specific comparisons (10 mg: -24.7 [-54.5, 5.2]; 25 mg: -43.1 [-72.9, -13.3])",
            "PDF Table 3 (page 9); Cochrane Handbook Section 23.3",
            "Combining correlated active arms sharing a control group from a single trial (k=1) violates Cochrane Handbook Section 23.3. Retained dose-specific estimates without artificial pooling.",
            "src/cohort_pipeline.py (Dose-specific retention for single multi-arm trials)"
        ),
        (
            "DEF-08",
            "Domain Synthesis / Patient Inflation",
            "Domain_Bridged_Meta_Analysis!D6:D10",
            "Domain total N accumulated to ~450 patients for single trial",
            "Unique Randomized Patients (N) capped at true study N=60; distinguished comparisons (m)",
            "PDF Table 1 (Randomized N=60)",
            "Summing n_exp + n_ctrl across repeated domain parameters inflated patient count. Replaced with study-level unique randomized participant tracking across unique arms.",
            "src/meta_predictive.py, src/cohort_pipeline.py (DomainMetaAnalysisResult.total_n)"
        ),
        (
            "DEF-09",
            "Predictive Projections / Extrapolation Bounds",
            "Predictive_Projections!D6:D8",
            "Carried forward 28-day effects to 12, 24, and 52 weeks without model",
            "4-week observed horizon validly projected; 12, 24, 52 weeks return INSUFFICIENT_DATA_FOR_VALIDATED_PREDICTION and NOT_ESTIMABLE",
            "Study Duration = 28 days (4 weeks)",
            "Longitudinal extrapolation beyond 2x observed study duration without multi-timepoint kinetic modeling lacks identifiable parameters. Enforced strict longitudinal eligibility gate.",
            "src/meta_predictive.py (predict_trial longitudinal eligibility gate)"
        ),
        (
            "DEF-10",
            "Virtual Trial / Time-Unit Conversion",
            "Synthesized_Virtual_Trial!D12:D14",
            "'28 Wks (Observed)'",
            "'28 Days (Observed)'",
            "PDF Study Design (28 days treatment period)",
            "Study duration value was extracted as 28, but duration_unit = days was not converted to weeks in calculations and was mislabeled as weeks in text formatting.",
            "src/cohort_pipeline.py (duration_unit day conversion), src/discovery_engine.py"
        ),
        (
            "DEF-11",
            "Virtual Trial / Sample Size Derivation",
            "Synthesized_Virtual_Trial!B7:B9",
            "Arbitrary recommended N=393 without formula or assumptions",
            "Deterministic Machin-Campbell power derivation: N=440 (132/arm, delta=6.65, sigma=16.63, alpha=0.05, 90% power, 1:1:1 allocation, 10% attrition)",
            "Biostatistical sample size formulas (Machin et al., 2018)",
            "AI-generated sample sizes lack transparent auditable derivation. Implemented deterministic formula documenting primary endpoint, delta, sigma, alpha, power, and attrition.",
            "src/discovery_engine.py, src/cohort_pipeline.py (Deterministic sample size model)"
        ),
        (
            "DEF-12",
            "Dispersion Type / SE vs SD Integrity",
            "Outcomes!Q2:Q150",
            "Classified SEs as SDs in continuous outcomes",
            "Preserved dispersion_type = SE, metric_type = mean_se, prevented artificial variance contraction",
            "PDF Table 1 footnote ('Data are mean (SE)')",
            "Misclassifying SE as SD severely underestimates true sample variance by factor of sqrt(N). Implemented referee rule REF-13-SE-SD-INTEGRITY.",
            "src/extractor.py, src/scientific_referee.py (REF-13-SE-SD-INTEGRITY)"
        )
    ]

    for row_idx, row_vals in enumerate(audit_data, 5):
        bg_fill = zebra_fill if row_idx % 2 == 0 else PatternFill(fill_type=None)
        for col_idx, val in enumerate(row_vals, 1):
            c = ws.cell(row=row_idx, column=col_idx, value=val)
            c.font = bold_font if col_idx in [1, 5] else body_font
            if bg_fill.fill_type:
                c.fill = bg_fill
            c.border = thin_border
            c.alignment = Alignment(horizontal="center" if col_idx in [1, 3] else "left", vertical="center", wrap_text=True)

    # Column widths
    col_widths = {1: 12, 2: 24, 3: 28, 4: 38, 5: 42, 6: 30, 7: 48, 8: 36}
    for col_idx, w in col_widths.items():
        ws.column_dimensions[get_column_letter(col_idx)].width = w

    ws.row_dimensions[1].height = 28
    ws.row_dimensions[2].height = 18
    ws.row_dimensions[4].height = 26
    for r in range(5, len(audit_data) + 5):
        ws.row_dimensions[r].height = 42

    wb.save("MANDOROS_Phase2_Error_Audit.xlsx")
    print("Successfully built MANDOROS_Phase2_Error_Audit.xlsx")

if __name__ == "__main__":
    build_audit_excel()
