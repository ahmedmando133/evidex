"""
Multi-sheet Excel exporter for extracted clinical trial data.
Generates:
1. Standard 6 relational sheets (Studies, Arms, Eligibility, Outcomes, Provenance, Validation_Log)
2. Optional 7th sheet: Flattened_View (for direct side-by-side comparison with traditional data mining sheets).
"""

from typing import List
import openpyxl
from openpyxl.styles import Font, PatternFill, Alignment, Border, Side
from openpyxl.utils import get_column_letter

from src.models import ExtractedTrialData


class ExcelTrialExporter:
    def __init__(self, data: ExtractedTrialData):
        self.data = data
        self.wb = openpyxl.Workbook()
        # Remove default empty sheet
        self.wb.remove(self.wb.active)

        # Style definitions
        self.header_font = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        self.header_fill = PatternFill(start_color="1F4E79", end_color="1F4E79", fill_type="solid")
        self.warning_fill = PatternFill(start_color="FFF2CC", end_color="FFF2CC", fill_type="solid")
        self.border_thin = Border(
            left=Side(style='thin', color='D9D9D9'),
            right=Side(style='thin', color='D9D9D9'),
            top=Side(style='thin', color='D9D9D9'),
            bottom=Side(style='thin', color='D9D9D9')
        )
        self.align_center = Alignment(horizontal="center", vertical="center")
        self.align_left = Alignment(horizontal="left", vertical="center")

    def _apply_sheet_formatting(self, ws):
        # Format header row
        for col in range(1, ws.max_column + 1):
            cell = ws.cell(row=1, column=col)
            cell.font = self.header_font
            cell.fill = self.header_fill
            cell.alignment = self.align_center

        # Apply borders and auto-fit column widths
        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                cell.border = self.border_thin
                val_str = str(cell.value or '')
                if len(val_str) > max_len:
                    max_len = len(val_str)
            ws.column_dimensions[col_letter].width = min(max(max_len + 3, 12), 45)

        ws.row_dimensions[1].height = 24

    def export(self, output_path: str) -> str:
        self._build_master_extraction_sheet()
        self._build_studies_sheet()
        self._build_arms_sheet()
        self._build_eligibility_sheet()
        self._build_outcomes_sheet()
        self._build_provenance_sheet()
        self._build_validation_log_sheet()
        self._build_flattened_view_sheet()
        self._build_variables_matrix_sheet()

        try:
            self.wb.save(output_path)
            print(f"Exported clean structured Excel workbook to: {output_path}")
            return output_path
        except PermissionError:
            import os
            base, ext = os.path.splitext(output_path)
            alt_path = f"{base}_updated{ext}"
            self.wb.save(alt_path)
            print(f"[!] Primary file '{output_path}' is currently OPEN in Excel.")
            print(f"[OK] Saved updated version to: {alt_path}")
            return alt_path

    def _build_master_extraction_sheet(self):
        """
        Builds the consolidated, multi-level Master Extraction Sheet (Sheet 1)
        faithfully replicating the benchmark layout of 'Data minimg (Metformin study).xlsx'
        and 'orlistat_manual.xlsx'.
        
        Header Structure:
        - Row 1: Merged Main Category Blocks
                 [STUDY & INTERVENTION ARMS] [ELIGIBILITY CRITERIA] [POPULATION STRATIFICATION] [CLINICAL VARIABLES & OUTCOMES]
        - Row 2: Variable & Criterion Group Headers
        - Row 3: Atomic Sub-Columns (<, =, >, Value/Range, Unit, Mean/Events, SD/%, Change, etc.)
        
        Rows:
        - One consolidated row per (Arm, Race/Subgroup, Gender, Timepoint) stratum,
          integrating protocol arms, eligibility thresholds, demographics, and clinical outcomes side-by-side.
        """
        ws = self.wb.create_sheet(title="Master_Extraction_Sheet", index=0)
        ws.views.sheetView[0].showGridLines = True

        h1_fill = PatternFill(start_color="1B365D", end_color="1B365D", fill_type="solid")
        h2_fill = PatternFill(start_color="2F5597", end_color="2F5597", fill_type="solid")
        h3_fill = PatternFill(start_color="D9E1F2", end_color="D9E1F2", fill_type="solid")
        zebra_fill = PatternFill(start_color="F8FAFC", end_color="F8FAFC", fill_type="solid")

        font_h1 = Font(name="Calibri", size=11, bold=True, color="FFFFFF")
        font_h2 = Font(name="Calibri", size=10, bold=True, color="FFFFFF")
        font_h3 = Font(name="Calibri", size=9, bold=True, color="1F1F1F")
        font_data = Font(name="Calibri", size=10)

        align_center = Alignment(horizontal="center", vertical="center", wrap_text=True)
        align_left = Alignment(horizontal="left", vertical="center", wrap_text=True)

        # 1. Collect unique Eligibility Criteria
        elig_continuous = []
        elig_categorical = []
        seen_criteria = set()
        for e in self.data.eligibility:
            c_name = e.criterion_name.replace("_", " ").title()
            if c_name in seen_criteria:
                continue
            seen_criteria.add(c_name)
            is_num = (e.less_than is not None or e.equal is not None or e.greater_than is not None 
                      or e.between is not None or e.value is not None or e.min_value is not None)
            if is_num:
                elig_continuous.append((c_name, e))
            else:
                elig_categorical.append((c_name, e))

        # 2. Collect unique Clinical Outcome Parameters
        outcome_params = []
        seen_params = set()
        for o in self.data.outcomes:
            p_name = o.parameter_name.strip()
            if p_name not in seen_params:
                seen_params.add(p_name)
                outcome_params.append(p_name)

        col_idx = 1

        # Block 1: Study & Arms (10 columns)
        arm_start_col = col_idx
        arm_end_col = col_idx + 9
        col_idx += 10

        # Block 2: Eligibility Criteria
        elig_start_col = col_idx
        elig_col_map = {}
        for c_name, e_obj in elig_continuous:
            elig_col_map[c_name] = (col_idx, True, e_obj)
            col_idx += 5
        for c_name, e_obj in elig_categorical:
            elig_col_map[c_name] = (col_idx, False, e_obj)
            col_idx += 1
        elig_end_col = col_idx - 1 if col_idx > elig_start_col else elig_start_col

        # Block 3: Population Stratification (4 columns)
        pop_start_col = col_idx
        pop_end_col = col_idx + 3
        col_idx += 4

        # Block 4: Clinical Variables & Outcomes
        out_start_col = col_idx
        out_col_map = {}
        for p_name in outcome_params:
            out_col_map[p_name] = col_idx
            col_idx += 4
        out_end_col = col_idx - 1 if col_idx > out_start_col else out_start_col

        total_cols = col_idx - 1

        ws.row_dimensions[1].height = 28
        ws.row_dimensions[2].height = 24
        ws.row_dimensions[3].height = 20

        def format_range(sheet, start_c, end_c, row, val, font, fill):
            if end_c > start_c:
                sheet.merge_cells(start_row=row, start_column=start_c, end_row=row, end_column=end_c)
            for c in range(start_c, end_c + 1):
                cell = sheet.cell(row=row, column=c)
                cell.fill = fill
                cell.font = font
                cell.alignment = align_center
                cell.border = self.border_thin
            sheet.cell(row=row, column=start_c, value=val)

        format_range(ws, arm_start_col, arm_end_col, 1, "STUDY & INTERVENTION ARMS", font_h1, h1_fill)
        if elig_end_col >= elig_start_col:
            format_range(ws, elig_start_col, elig_end_col, 1, "ELIGIBILITY CRITERIA", font_h1, h1_fill)
        format_range(ws, pop_start_col, pop_end_col, 1, "POPULATION STRATIFICATION", font_h1, h1_fill)
        if out_end_col >= out_start_col:
            format_range(ws, out_start_col, out_end_col, 1, "CLINICAL VARIABLES & OUTCOMES", font_h1, h1_fill)

        # Write Row 2 & Row 3:
        study_headers_r2 = [
            ("Study ID", 1), ("Group / Arm Name", 1), ("Intervention Type", 1),
            ("Dose", 1), ("Frequency", 1), ("Study Phase", 1),
            ("Period of Study", 2), ("Total Cohort (N)", 1), ("Arm Sample Size (N)", 1)
        ]
        curr_c = arm_start_col
        for title, span in study_headers_r2:
            format_range(ws, curr_c, curr_c + span - 1, 2, title, font_h2, h2_fill)
            if span == 2:
                ws.cell(row=3, column=curr_c, value="Number")
                ws.cell(row=3, column=curr_c + 1, value="Unit")
                for c in range(curr_c, curr_c + 2):
                    cell = ws.cell(row=3, column=c)
                    cell.fill = h3_fill
                    cell.font = font_h3
                    cell.alignment = align_center
                    cell.border = self.border_thin
            else:
                cell = ws.cell(row=3, column=curr_c, value="")
                cell.fill = h3_fill
                cell.border = self.border_thin
            curr_c += span

        for c_name, (start_c, is_num, e_obj) in elig_col_map.items():
            if is_num:
                format_range(ws, start_c, start_c + 4, 2, c_name, font_h2, h2_fill)
                sub_labels = ["<", "=", ">", "Value / Range", "Unit"]
                for i, sub_lab in enumerate(sub_labels):
                    cell = ws.cell(row=3, column=start_c + i, value=sub_lab)
                    cell.fill = h3_fill
                    cell.font = font_h3
                    cell.alignment = align_center
                    cell.border = self.border_thin
            else:
                format_range(ws, start_c, start_c, 2, c_name, font_h2, h2_fill)
                cell = ws.cell(row=3, column=start_c, value="Status / Condition")
                cell.fill = h3_fill
                cell.font = font_h3
                cell.alignment = align_center
                cell.border = self.border_thin

        format_range(ws, pop_start_col, pop_start_col, 2, "Race / Ethnicity", font_h2, h2_fill)
        cell = ws.cell(row=3, column=pop_start_col, value="")
        cell.fill = h3_fill
        cell.border = self.border_thin

        format_range(ws, pop_start_col + 1, pop_start_col + 1, 2, "Gender", font_h2, h2_fill)
        cell = ws.cell(row=3, column=pop_start_col + 1, value="")
        cell.fill = h3_fill
        cell.border = self.border_thin

        format_range(ws, pop_start_col + 2, pop_start_col + 3, 2, "Timepoint", font_h2, h2_fill)
        ws.cell(row=3, column=pop_start_col + 2, value="Value")
        ws.cell(row=3, column=pop_start_col + 3, value="Unit")
        for c in range(pop_start_col + 2, pop_start_col + 4):
            cell = ws.cell(row=3, column=c)
            cell.fill = h3_fill
            cell.font = font_h3
            cell.alignment = align_center
            cell.border = self.border_thin

        for p_name, start_c in out_col_map.items():
            format_range(ws, start_c, start_c + 3, 2, p_name, font_h2, h2_fill)
            sub_labels = ["Value / Mean / Events", "SD / %", "Change", "Unit"]
            for i, sub_lab in enumerate(sub_labels):
                cell = ws.cell(row=3, column=start_c + i, value=sub_lab)
                cell.fill = h3_fill
                cell.font = font_h3
                cell.alignment = align_center
                cell.border = self.border_thin

        s = self.data.study
        arm_strata = {a.arm_id: set() for a in self.data.arms}

        for o in self.data.outcomes:
            if o.arm_id in arm_strata:
                r = o.race or "Overall"
                g = "Overall"
                tp_v = o.timepoint_value or ("0" if s.duration_value else "")
                tp_u = o.timepoint_unit or (s.duration_unit or "")
                arm_strata[o.arm_id].add((r, g, tp_v, tp_u))

        current_row = 4
        is_even = False

        for a in self.data.arms:
            strata_list = sorted(list(arm_strata.get(a.arm_id, set())))
            if not strata_list:
                strata_list = [
                    ("Overall", "Overall", "0", s.duration_unit or "weeks"),
                    ("Overall", "Overall", str(s.duration_value or ""), s.duration_unit or "weeks")
                ]

            for (race_val, gender_val, tp_v, tp_u) in strata_list:
                is_even = not is_even
                row_fill = zebra_fill if is_even else None

                ws.cell(row=current_row, column=1, value=s.study_id)
                ws.cell(row=current_row, column=2, value=a.arm_name)
                ws.cell(row=current_row, column=3, value=a.intervention_type)
                ws.cell(row=current_row, column=4, value=f"{a.dose_value or ''} {a.dose_unit or ''}".strip())
                ws.cell(row=current_row, column=5, value=f"{a.frequency_number or ''} {a.frequency_unit or ''}".strip())
                ws.cell(row=current_row, column=6, value=s.study_phase)
                ws.cell(row=current_row, column=7, value=s.duration_value)
                ws.cell(row=current_row, column=8, value=s.duration_unit)
                ws.cell(row=current_row, column=9, value=s.total_sample_size)
                ws.cell(row=current_row, column=10, value=a.sample_size_analyzed or a.sample_size_allocated)

                for c_name, (start_c, is_num, e_obj) in elig_col_map.items():
                    if is_num:
                        ws.cell(row=current_row, column=start_c, value=e_obj.less_than)
                        ws.cell(row=current_row, column=start_c + 1, value=e_obj.equal)
                        ws.cell(row=current_row, column=start_c + 2, value=e_obj.greater_than)
                        v_str = f"{e_obj.min_value} – {e_obj.max_value}" if e_obj.between else e_obj.value
                        ws.cell(row=current_row, column=start_c + 3, value=v_str)
                        ws.cell(row=current_row, column=start_c + 4, value=e_obj.unit)
                    else:
                        cat_status = f"{e_obj.criterion_type.title()} ({'Prohibited' if e_obj.criterion_type == 'exclusion' else 'Required'})"
                        ws.cell(row=current_row, column=start_c, value=cat_status)

                ws.cell(row=current_row, column=pop_start_col, value=race_val)
                ws.cell(row=current_row, column=pop_start_col + 1, value=gender_val)
                ws.cell(row=current_row, column=pop_start_col + 2, value=tp_v)
                ws.cell(row=current_row, column=pop_start_col + 3, value=tp_u)

                for p_name, start_c in out_col_map.items():
                    matched_o = None
                    for o in self.data.outcomes:
                        if (o.arm_id == a.arm_id and 
                            o.parameter_name.strip() == p_name and
                            (o.race or "Overall") == race_val and
                            (o.timepoint_value or "") == tp_v):
                            matched_o = o
                            break

                    if matched_o:
                        m_val = matched_o.mean if matched_o.mean is not None else (matched_o.events if matched_o.events is not None else matched_o.percentage)
                        sd_val = matched_o.sd if matched_o.sd is not None else (matched_o.percentage if matched_o.mean is not None else None)
                        ws.cell(row=current_row, column=start_c, value=m_val)
                        ws.cell(row=current_row, column=start_c + 1, value=sd_val)
                        ws.cell(row=current_row, column=start_c + 2, value=matched_o.change_value)
                        ws.cell(row=current_row, column=start_c + 3, value=matched_o.unit)

                ws.row_dimensions[current_row].height = 20
                for c in range(1, total_cols + 1):
                    cell = ws.cell(row=current_row, column=c)
                    cell.font = font_data
                    cell.border = self.border_thin
                    if row_fill:
                        cell.fill = row_fill
                    if c in [1, 2, 6] or c in [sc for sc, is_n, _ in elig_col_map.values() if not is_n]:
                        cell.alignment = align_left
                    else:
                        cell.alignment = align_center

                current_row += 1

        ws.freeze_panes = "A4"

        for col in ws.columns:
            max_len = 0
            col_letter = get_column_letter(col[0].column)
            for cell in col:
                val_str = str(cell.value or "")
                if len(val_str) > max_len:
                    max_len = len(val_str)
            ws.column_dimensions[col_letter].width = min(max(max_len + 3, 10), 38)

    def _build_studies_sheet(self):
        ws = self.wb.create_sheet(title="Studies")
        headers = [
            "study_id", "title", "authors", "publication_year", "journal", "doi",
            "study_design", "study_phase", "total_sample_size", "duration_value",
            "duration_unit", "condition_studied"
        ]
        ws.append(headers)

        s = self.data.study
        row = [
            s.study_id, s.title, s.authors, s.publication_year, s.journal, s.doi,
            s.study_design, s.study_phase, s.total_sample_size, s.duration_value,
            s.duration_unit, s.condition_studied
        ]
        ws.append(row)
        self._apply_sheet_formatting(ws)

    def _build_arms_sheet(self):
        ws = self.wb.create_sheet(title="Arms")
        headers = [
            "arm_id", "study_id", "arm_name", "intervention_type", "drug_name",
            "dose_value", "dose_unit", "frequency_number", "frequency_unit",
            "sample_size_allocated", "sample_size_analyzed", "source_page"
        ]
        ws.append(headers)

        for a in self.data.arms:
            ws.append([
                a.arm_id, a.study_id, a.arm_name, a.intervention_type, a.drug_name,
                a.dose_value, a.dose_unit, a.frequency_number, a.frequency_unit,
                a.sample_size_allocated, a.sample_size_analyzed, a.source_page
            ])
        self._apply_sheet_formatting(ws)

    def _build_eligibility_sheet(self):
        ws = self.wb.create_sheet(title="Eligibility")
        headers = [
            "criterion_id", "study_id", "criterion_type", "domain", "criterion_name",
            "less_than (<)", "equal (=)", "greater_than (>)", "between",
            "value", "min_value", "max_value", "unit", "raw_source_text", "source_page"
        ]
        ws.append(headers)

        for e in self.data.eligibility:
            ws.append([
                e.criterion_id, e.study_id, e.criterion_type, e.domain, e.criterion_name,
                e.less_than, e.equal, e.greater_than, e.between,
                e.value, e.min_value, e.max_value, e.unit, e.raw_source_text, e.source_page
            ])
        self._apply_sheet_formatting(ws)

    def _build_outcomes_sheet(self):
        ws = self.wb.create_sheet(title="Outcomes")
        headers = [
            "outcome_id", "study_id", "arm_id", "race", "domain", "parameter_name", "statistical_type",
            "Timepoint (value)", "Timepoint (unit)", "sample_size", "mean", "sd", "change_value", "change_sd",
            "events", "total", "percentage", "unit", "effect_measure", "effect_value",
            "p_value", "source_page", "source_location", "raw_source_text"
        ]
        ws.append(headers)

        for o in self.data.outcomes:
            ws.append([
                o.outcome_id, o.study_id, o.arm_id, o.race or "Overall", o.domain, o.parameter_name, o.statistical_type,
                o.timepoint_value, o.timepoint_unit, o.sample_size, o.mean, o.sd, o.change_value, o.change_sd,
                o.events, o.total, o.percentage, o.unit, o.effect_measure, o.effect_value,
                o.p_value, o.source_page, o.source_location, o.raw_source_text
            ])
        self._apply_sheet_formatting(ws)

    def _build_provenance_sheet(self):
        ws = self.wb.create_sheet(title="Provenance")
        headers = [
            "provenance_id", "study_id", "target_entity", "target_id", "field_name",
            "source_page", "source_location", "exact_source_text"
        ]
        ws.append(headers)

        for p in self.data.provenance:
            ws.append([
                p.provenance_id, p.study_id, p.target_entity, p.target_id, p.field_name,
                p.source_page, p.source_location, p.exact_source_text
            ])
        self._apply_sheet_formatting(ws)

    def _build_validation_log_sheet(self):
        ws = self.wb.create_sheet(title="Validation_Log")
        headers = [
            "issue_id", "study_id", "target_entity", "target_id", "field_name",
            "issue_type", "review_required", "comment"
        ]
        ws.append(headers)

        for v in self.data.validation_log:
            ws.append([
                v.issue_id, v.study_id, v.target_entity, v.target_id, v.field_name,
                v.issue_type, v.review_required, v.comment
            ])
        self._apply_sheet_formatting(ws)

    def _build_flattened_view_sheet(self):
        """
        Creates a wide summary sheet grouping outcomes by arm and parameter,
        providing the researchers with the exact side-by-side view they are used to.
        """
        ws = self.wb.create_sheet(title="Flattened_View")
        headers = [
            "study_id", "arm_name", "race", "intervention_type", "dose", "frequency",
            "sample_size", "Timepoint (value)", "Timepoint (unit)", "parameter_name", "mean_or_events",
            "sd_or_pct", "change", "unit", "source_page", "source_location"
        ]
        ws.append(headers)

        # Map arms for fast lookup
        arms_dict = {a.arm_id: a for a in self.data.arms}

        for o in self.data.outcomes:
            arm = arms_dict.get(o.arm_id)
            arm_name = arm.arm_name if arm else o.arm_id
            dose_str = f"{arm.dose_value} {arm.dose_unit}" if arm and arm.dose_value else "N/A"
            freq_str = f"{arm.frequency_number} {arm.frequency_unit}" if arm and arm.frequency_number else "N/A"
            arm_type = arm.intervention_type if arm else "N/A"

            mean_or_events = o.mean if o.mean is not None else o.events
            sd_or_pct = o.sd if o.sd is not None else o.percentage

            ws.append([
                o.study_id, arm_name, o.race or "Overall", arm_type, dose_str, freq_str,
                o.sample_size, o.timepoint_value, o.timepoint_unit, o.parameter_name, mean_or_events,
                sd_or_pct, o.change_value, o.unit, o.source_page, o.source_location
            ])

        self._apply_sheet_formatting(ws)

    def _build_variables_matrix_sheet(self):
        """
        Creates a cross-study comparison matrix where variables are side-by-side columns along the top,
        making it trivial to compare across trials and cohorts.
        """
        ws = self.wb.create_sheet(title="Variables_Matrix")

        # Distinct variable columns
        var_columns = []
        for o in self.data.outcomes:
            col_name = f"{o.parameter_name} ({o.unit})" if o.unit else o.parameter_name
            if col_name not in var_columns:
                var_columns.append(col_name)

        headers = [
            "study_id", "arm_name", "race", "sample_size", "Timepoint (value)", "Timepoint (unit)"
        ] + var_columns
        ws.append(headers)

        arms_dict = {a.arm_id: a for a in self.data.arms}

        # Group outcomes by (arm_id, race, timepoint_value, timepoint_unit)
        rows_map = {}
        for o in self.data.outcomes:
            key = (o.arm_id, o.race or "Overall", o.timepoint_value, o.timepoint_unit)
            if key not in rows_map:
                rows_map[key] = {
                    "arm_id": o.arm_id,
                    "race": o.race or "Overall",
                    "sample_size": o.sample_size,
                    "tp_val": o.timepoint_value,
                    "tp_unit": o.timepoint_unit,
                    "values": {}
                }
            col_name = f"{o.parameter_name} ({o.unit})" if o.unit else o.parameter_name
            val = o.mean if o.mean is not None else (o.percentage if o.percentage is not None else (o.change_value if o.change_value is not None else o.events))
            rows_map[key]["values"][col_name] = val

        for row_info in rows_map.values():
            arm = arms_dict.get(row_info["arm_id"])
            arm_name = arm.arm_name if arm else row_info["arm_id"]

            row_data = [
                self.data.study.study_id,
                arm_name,
                row_info["race"],
                row_info["sample_size"],
                row_info["tp_val"],
                row_info["tp_unit"]
            ]
            for col_name in var_columns:
                row_data.append(row_info["values"].get(col_name, ""))
            ws.append(row_data)

        self._apply_sheet_formatting(ws)
