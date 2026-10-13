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
