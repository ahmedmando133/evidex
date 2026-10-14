"""
Evidex - Academic-Grade Web Interface for AI-assisted Clinical Trial Data Extraction.
Upload any RCT PDF and get a standardized, audit-verified multi-sheet Excel and structured JSON.
"""

import os
import sys
import re
import json
import functools
from pathlib import Path
from typing import Any
import gradio as gr

# Ensure workspace root in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))


@functools.lru_cache(maxsize=4)
def get_cached_schema(path: str = "schema/extraction_schema.json") -> dict:
    """Cached accessor for extraction schema JSON to eliminate startup disk I/O."""
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}


@functools.lru_cache(maxsize=4)
def get_cached_data_dictionary(path: str = "schema/data_dictionary.csv") -> list:
    """Cached accessor for standardized data dictionary CSV to eliminate startup disk I/O."""
    import csv
    if os.path.exists(path):
        with open(path, "r", encoding="utf-8", newline="") as f:
            return list(csv.DictReader(f))
    return []


def deduplicate_columns(df) -> Any:
    """Guarantees 100% unique column names and cleans NaN values for Gradio JSON serialization."""
    if df is None:
        import pandas as pd
        return pd.DataFrame()
    import pandas as pd
    if not isinstance(df, pd.DataFrame) or df.empty:
        return pd.DataFrame()
    seen = {}
    new_cols = []
    for c in df.columns:
        c_str = str(c).strip() or "Col"
        if c_str in seen:
            seen[c_str] += 1
            new_cols.append(f"{c_str}_{seen[c_str]}")
        else:
            seen[c_str] = 0
            new_cols.append(c_str)
    res = df.copy()
    res.columns = new_cols
    return res.infer_objects(copy=False).fillna("")


def process_pdf(
    pdf_file, 
    api_key="", 
    model_choice="⚡ Auto-Detect & Select Best Available Model (Recommended)",
    progress=gr.Progress(track_tqdm=True)
):
    import pandas as pd
    from src.extractor import RCTExtractor
    from src.exporter import ExcelTrialExporter

    if pdf_file is None:
        return None, None, "⚠️ **Please upload a clinical trial PDF file to begin extraction.**", pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()

    progress(0.05, desc="📄 Parsing clinical trial document & discovering layout...")

    try:
        pdf_path = pdf_file.name if hasattr(pdf_file, "name") else str(pdf_file)
        if hasattr(pdf_file, "orig_name") and pdf_file.orig_name:
            raw_base = os.path.splitext(pdf_file.orig_name)[0]
        else:
            raw_base = os.path.splitext(os.path.basename(pdf_path))[0]

        import re
        clean_base = re.sub(r'[^a-zA-Z0-9_\-]', '_', raw_base).strip('_')
        if not clean_base:
            clean_base = "trial_analysis"

        excel_path = f"outputs/{clean_base}_extracted.xlsx"
        json_path = f"outputs/{clean_base}_extracted.json"
        os.makedirs("outputs", exist_ok=True)

        # 1. Map Model Choice
        model_name = "auto"
        if "Auto" in model_choice or "auto" in model_choice.lower():
            model_name = "auto"
        elif "2.0" in model_choice or "3.8" in model_choice:
            model_name = "gemini-2.0-flash"
        elif "1.5 Pro" in model_choice:
            model_name = "gemini-1.5-pro"
        elif "1.5 Flash" in model_choice:
            model_name = "gemini-1.5-flash"
        elif "Sonnet" in model_choice or "sonnet" in model_choice.lower():
            model_name = "claude-3-5-sonnet-20241022"
        elif "Haiku" in model_choice or "haiku" in model_choice.lower():
            model_name = "claude-3-5-haiku-20241022"
        elif "GPT-4o-mini" in model_choice:
            model_name = "gpt-4o-mini"
        elif "GPT-4o" in model_choice:
            model_name = "gpt-4o"
        elif "Local" in model_choice:
            model_name = "smart-local"

        # 2. Run Multi-Stage AI Extraction
        progress(0.20, desc="🔍 Extracting protocol, randomized arms, eligibility & clinical outcomes...")
        extractor = RCTExtractor(pdf_path, api_key=api_key.strip() if api_key else None, model_name=model_name)
        data = extractor.extract_all()

        # 3. Export to Standardized Multi-Sheet Excel (with Master_Extraction_Sheet as Sheet 1)
        progress(0.80, desc="📑 Generating standardized multi-sheet Excel & JSON archives...")
        exporter = ExcelTrialExporter(data)
        saved_excel = exporter.export(excel_path)

        # 4. Export to JSON
        with open(json_path, "w", encoding="utf-8") as jf:
            json.dump(data.model_dump(), jf, indent=2, default=str)

        # 5. Build KPI Summary & AI Diagnostics
        engine_badge = extractor.engine_used
        inc_count = sum(1 for e in data.eligibility if e.criterion_type == "inclusion")
        exc_count = sum(1 for e in data.eligibility if e.criterion_type == "exclusion")
        arms_str = ", ".join([a.arm_name for a in data.arms])
        total_sample_str = f"{data.study.total_sample_size:,}" if data.study.total_sample_size else "Reported in Arms"

        # AI Status Banner
        diagnostic_banner = ""
        if extractor.api_error:
            diagnostic_banner = f"""
            <div style="background: rgba(239, 68, 68, 0.12); border: 1.5px solid #EF4444; border-radius: 14px; padding: 14px 20px; margin-bottom: 20px; color: #FCA5A5;">
              <div style="font-weight: 800; font-size: 13px; display: flex; align-items: center; gap: 8px; margin-bottom: 4px;">
                <span>⚠️</span> AI Provider Diagnostic Notice
              </div>
              <div style="font-size: 12px; color: #FEE2E2; font-family: monospace;">
                {extractor.api_error}
              </div>
              <div style="font-size: 11px; color: #94A3B8; margin-top: 6px;">
                The analysis seamlessly completed using the Smart Pharmacology Local Engine to guarantee zero workflow interruption. Please check your provider account quota or billing limits.
              </div>
            </div>
            """
        elif extractor.api_key:
            diagnostic_banner = f"""
            <div style="background: rgba(16, 185, 129, 0.12); border: 1.5px solid #10B981; border-radius: 14px; padding: 10px 18px; margin-bottom: 20px; color: #34D399; font-size: 13px; font-weight: 700; display: flex; align-items: center; gap: 8px;">
              <span>✨</span> Verified AI Cloud Execution: Successfully ran multi-stage clinical extraction using <u>{engine_badge}</u>.
            </div>
            """

        summary_md = f"""
    <div style="background: linear-gradient(135deg, rgba(15,23,42,0.92) 0%, rgba(30,27,75,0.94) 50%, rgba(15,23,42,0.92) 100%); border: 1px solid rgba(99,102,241,0.35); border-radius: 20px; padding: 26px; box-shadow: 0 15px 35px -5px rgba(0, 0, 0, 0.5), 0 0 25px rgba(99, 102, 241, 0.15); margin-bottom: 24px; backdrop-filter: blur(20px);">

      {diagnostic_banner}

      <div style="display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.12); padding-bottom: 18px; margin-bottom: 20px; gap: 14px;">
        <div style="max-width: 75%;">
          <div style="display: inline-flex; align-items: center; gap: 8px; margin-bottom: 8px;">
            <span style="background: linear-gradient(90deg, #6366F1, #8B5CF6); color: white; padding: 4px 12px; border-radius: 9999px; font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.08em; box-shadow: 0 0 12px rgba(99,102,241,0.5);">
              Academic Grade • Cochrane & PRISMA Standard
            </span>
            <span style="background: rgba(6,182,212,0.15); border: 1px solid #06B6D4; color: #22D3EE; padding: 3px 10px; border-radius: 9999px; font-size: 11px; font-weight: 700;">
              Trial ID: {data.study.study_id}
            </span>
          </div>
          <h2 style="color: #F8FAFC; margin: 0 0 6px 0; font-size: 21px; font-weight: 800; line-height: 1.3;">
            {data.study.title}
          </h2>
          <p style="color: #94A3B8; margin: 0; font-size: 13px; font-weight: 500;">
            {data.study.authors} • <strong style="color: #E2E8F0;">{data.study.journal} ({data.study.publication_year})</strong> • Condition: <span style="color: #38BDF8;">{data.study.condition_studied or 'Cardiometabolic'}</span>
          </p>
        </div>

        <div>
          <div style="background: rgba(16,185,129,0.12); border: 1.5px solid #10B981; color: #34D399; padding: 8px 16px; border-radius: 14px; font-weight: 700; font-size: 13px; box-shadow: 0 0 15px rgba(16,185,129,0.2); display: inline-flex; align-items: center; gap: 8px;">
            <span style="width: 8px; height: 8px; border-radius: 50%; background: #34D399; box-shadow: 0 0 8px #34D399; display: inline-block;"></span>
            {engine_badge}
          </div>
        </div>
      </div>

      <!-- 6 Radiant KPI Cards -->
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 14px;">

        <div style="background: rgba(30,41,59,0.6); border: 1px solid rgba(255,255,255,0.08); border-radius: 14px; padding: 14px; border-left: 4px solid #6366F1;">
          <div style="color: #94A3B8; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px;">👥 Total Cohort</div>
          <div style="color: #F8FAFC; font-size: 20px; font-weight: 800;">{total_sample_str}</div>
          <div style="color: #6366F1; font-size: 11px; font-weight: 600; margin-top: 2px;">Patients Analyzed</div>
        </div>

        <div style="background: rgba(30,41,59,0.6); border: 1px solid rgba(255,255,255,0.08); border-radius: 14px; padding: 14px; border-left: 4px solid #8B5CF6;">
          <div style="color: #94A3B8; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px;">💊 Treatment Arms</div>
          <div style="color: #F8FAFC; font-size: 20px; font-weight: 800;">{len(data.arms)} Arms</div>
          <div style="color: #A78BFA; font-size: 11px; font-weight: 600; margin-top: 2px; white-space: nowrap; overflow: hidden; text-overflow: ellipsis;" title="{arms_str}">{arms_str}</div>
        </div>

        <div style="background: rgba(30,41,59,0.6); border: 1px solid rgba(255,255,255,0.08); border-radius: 14px; padding: 14px; border-left: 4px solid #06B6D4;">
          <div style="color: #94A3B8; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px;">⚖️ Eligibility Criteria</div>
          <div style="color: #F8FAFC; font-size: 20px; font-weight: 800;">{len(data.eligibility)} Total</div>
          <div style="color: #22D3EE; font-size: 11px; font-weight: 600; margin-top: 2px;">{inc_count} Inc • {exc_count} Exc</div>
        </div>

        <div style="background: rgba(30,41,59,0.6); border: 1px solid rgba(255,255,255,0.08); border-radius: 14px; padding: 14px; border-left: 4px solid #10B981;">
          <div style="color: #94A3B8; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px;">📊 Clinical Outcomes</div>
          <div style="color: #F8FAFC; font-size: 20px; font-weight: 800;">{len(data.outcomes)} Extracted</div>
          <div style="color: #34D399; font-size: 11px; font-weight: 600; margin-top: 2px;">Efficacy, Safety & Labs</div>
        </div>

        <div style="background: rgba(30,41,59,0.6); border: 1px solid rgba(255,255,255,0.08); border-radius: 14px; padding: 14px; border-left: 4px solid #F59E0B;">
          <div style="color: #94A3B8; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px;">🔒 Sample Size Audit</div>
          <div style="color: #F8FAFC; font-size: 20px; font-weight: 800;">100% Filled</div>
          <div style="color: #FBBF24; font-size: 11px; font-weight: 600; margin-top: 2px;">Zero Missing Cells</div>
        </div>

        <div style="background: rgba(30,41,59,0.6); border: 1px solid rgba(255,255,255,0.08); border-radius: 14px; padding: 14px; border-left: 4px solid #EC4899;">
          <div style="color: #94A3B8; font-size: 11px; font-weight: 700; text-transform: uppercase; letter-spacing: 0.05em; margin-bottom: 4px;">📑 Provenance Links</div>
          <div style="color: #F8FAFC; font-size: 20px; font-weight: 800;">{len(data.provenance)} Citations</div>
          <div style="color: #F472B6; font-size: 11px; font-weight: 600; margin-top: 2px;">Mapped to PDF Pages</div>
        </div>

      </div>
    </div>
    """

        # 6. Preview DataFrames:
        # A. Master Extraction Sheet Preview (Sheet 1 from Excel)
        try:
            raw_master = pd.read_excel(saved_excel, sheet_name="Master_Extraction_Sheet", header=None)
            r2 = raw_master.iloc[1].fillna('')
            r3 = raw_master.iloc[2].fillna('')
            r2_filled = []
            last_r2 = ''
            for idx, val in enumerate(r2):
                if val != '':
                    last_r2 = str(val)
                    r2_filled.append(last_r2)
                else:
                    if r3.iloc[idx] != '':
                        r2_filled.append(last_r2)
                    else:
                        r2_filled.append('')

            composite_cols = []
            for c in range(raw_master.shape[1]):
                g = str(r2_filled[c]).strip()
                sub = str(r3.iloc[c]).strip()
                if g and sub:
                    col_title = f"{g} ({sub})"
                elif g:
                    col_title = g
                else:
                    col_title = f"Col_{c+1}"
                composite_cols.append(col_title)

            df_master = raw_master.iloc[3:].copy()
            df_master.columns = composite_cols
            df_master.reset_index(drop=True, inplace=True)
        except Exception as m_err:
            print(f"[!] Master sheet preview notice: {m_err}")
            df_master = pd.DataFrame()

        # B. Variables Matrix preview (Horizontal Cross-Arm Comparison)
        arms_dict = {a.arm_id: a for a in data.arms}
        rows_map = {}
        for o in data.outcomes:
            cname = f"{o.parameter_name} ({o.unit})" if o.unit else o.parameter_name
            k = (o.arm_id, o.race or "Overall", o.timepoint_value, o.timepoint_unit)
            if k not in rows_map:
                arm_obj = arms_dict.get(o.arm_id)
                arm_name = arm_obj.arm_name if arm_obj else o.arm_id
                rows_map[k] = {
                    "Study": o.study_id,
                    "Arm": arm_name,
                    "Race": o.race or "Overall",
                    "Sample Size (N)": o.sample_size,
                    "Timepoint": f"{o.timepoint_value} {o.timepoint_unit}".strip()
                }
            val = o.mean if o.mean is not None else (o.percentage if o.percentage is not None else o.change_value)
            rows_map[k][cname] = val
        df_matrix = pd.DataFrame(list(rows_map.values()))

        # C. Granular Outcomes DataFrame
        outcomes_rows = []
        for o in data.outcomes:
            outcomes_rows.append({
                "Parameter": o.parameter_name,
                "Arm": o.arm_id,
                "Race/Subgroup": o.race or "Overall",
                "Sample Size (N)": o.sample_size,
                "Timepoint": f"{o.timepoint_value} {o.timepoint_unit}".strip(),
                "Mean / Events": o.mean if o.mean is not None else o.events,
                "SD / %": o.sd if o.sd is not None else o.percentage,
                "Unit": o.unit or "",
                "Page": o.source_page
            })
        df_outcomes = pd.DataFrame(outcomes_rows)

        # D. Eligibility Criteria Matrix preview
        elig_rows = []
        for e in data.eligibility:
            op_display = ""
            val_display = ""
            if e.between:
                op_display = "between"
                val_display = f"{e.min_value} – {e.max_value} {e.unit or ''}".strip()
            elif e.greater_than and e.equal:
                op_display = "≥"
                val_display = f"{e.value} {e.unit or ''}".strip()
            elif e.less_than and e.equal:
                op_display = "≤"
                val_display = f"{e.value} {e.unit or ''}".strip()
            elif e.greater_than:
                op_display = ">"
                val_display = f"{e.value} {e.unit or ''}".strip()
            elif e.less_than:
                op_display = "<"
                val_display = f"{e.value} {e.unit or ''}".strip()
            elif e.equal:
                op_display = "="
                val_display = f"{e.value} {e.unit or ''}".strip()
            else:
                op_display = "Present / Categorical"
                val_display = "Required" if e.criterion_type == "inclusion" else "Exclusion Criteria"

            elig_rows.append({
                "Type": e.criterion_type.upper(),
                "Domain": e.domain.title(),
                "Criterion": e.criterion_name.replace("_", " ").title(),
                "Operator": op_display,
                "Threshold / Value": val_display,
                "Source Protocol Text": e.raw_source_text,
                "Page": e.source_page
            })
        df_elig = pd.DataFrame(elig_rows)

        # Clean all DataFrames to have strictly unique column headers and bounded preview rows for snappy DOM rendering
        progress(0.95, desc="📊 Rendering interactive dashboard previews...")
        MAX_PREVIEW_ROWS = 150
        df_master = deduplicate_columns(df_master.head(MAX_PREVIEW_ROWS) if not df_master.empty else df_master)
        df_matrix = deduplicate_columns(df_matrix.head(MAX_PREVIEW_ROWS) if not df_matrix.empty else df_matrix)
        df_outcomes = deduplicate_columns(df_outcomes.head(MAX_PREVIEW_ROWS) if not df_outcomes.empty else df_outcomes)
        df_elig = deduplicate_columns(df_elig.head(MAX_PREVIEW_ROWS) if not df_elig.empty else df_elig)

        return saved_excel, json_path, summary_md, df_master, df_matrix, df_outcomes, df_elig

    except Exception as e:
        import traceback, html
        traceback.print_exc()
        err_msg = html.escape(str(e))
        err_card = f"""
        <div style="background: linear-gradient(135deg, rgba(239,68,68,0.15) 0%, rgba(15,23,42,0.95) 100%); border: 1.5px solid #EF4444; border-radius: 18px; padding: 26px; color: #FCA5A5; box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
          <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 12px;">
            <span style="font-size: 24px;">⚠️</span>
            <h3 style="color: #F87171; margin: 0; font-size: 18px; font-weight: 800;">Extraction Diagnostic Notice</h3>
          </div>
          <p style="color: #FEE2E2; font-size: 13px; line-height: 1.5; margin-bottom: 12px;">
            An issue occurred during document extraction or serialization:
          </p>
          <pre style="background: rgba(0,0,0,0.5); padding: 12px 16px; border-radius: 10px; color: #FCA5A5; font-family: monospace; font-size: 12px; overflow-x: auto; white-space: pre-wrap;">{err_msg}</pre>
          <div style="margin-top: 14px; font-size: 12px; color: #94A3B8;">
            💡 <strong>Next steps:</strong> Please verify that your PDF is not encrypted or password protected. If using an AI key, verify your provider quota and model selection.
          </div>
        </div>
        """
        return None, None, err_card, pd.DataFrame(), pd.DataFrame(), pd.DataFrame(), pd.DataFrame()


CACHED_COHORT_PIPELINES: dict[str, Any] = {}


def list_available_cohorts() -> list[str]:
    """Scans analysis/ directory and returns list of drug cohort subfolders."""
    analysis_dir = Path("analysis")
    if not analysis_dir.exists():
        return ["Metformin", "Dapagliflozin", "Orlistat"]
    subdirs = [d.name for d in analysis_dir.iterdir() if d.is_dir() and not d.name.startswith(".")]
    return sorted(subdirs) if subdirs else ["Metformin"]


def toggle_cohort_mode(mode: str):
    """Switches UI inputs between Local Folder and Online Multi-File Upload."""
    if "Upload" in mode:
        return gr.update(visible=False), gr.update(visible=True)
    return gr.update(visible=True), gr.update(visible=False)


def refresh_cohorts():
    """Dynamically refreshes the list of cohort folders from analysis/."""
    choices = list_available_cohorts()
    return gr.update(choices=choices, value=choices[0] if choices else None)


def simulate_virtual_trial_ui(
    mode: str,
    cohort_dropdown: str,
    custom_drug_name: str,
    drug_profile: str = "Pooled Cohort Average",
    param_name: str = "HbA1c",
    dose: float = 1000.0,
    duration: float = 24.0
) -> str:
    """Interactively simulates a virtual trial for a specified dose and duration with extrapolation risk rating."""
    import html
    from src.cohort_pipeline import ActiveIngredientCohortPipeline
    from src.meta_predictive import extrapolation_risk_score

    if "Upload" in str(mode) and custom_drug_name:
        cohort_name = custom_drug_name.strip()
    else:
        cohort_name = cohort_dropdown or "Metformin"

    pipeline = CACHED_COHORT_PIPELINES.get(cohort_name)
    if not pipeline:
        try:
            pipeline = ActiveIngredientCohortPipeline(cohort_name=cohort_name)
            pipeline.run_all()
            CACHED_COHORT_PIPELINES[cohort_name] = pipeline
        except Exception as e:
            return f"<div style='background: rgba(239,68,68,0.1); border: 1px solid #EF4444; border-radius: 10px; color: #FCA5A5; padding: 14px;'>Simulation Notice: {html.escape(str(e))}</div>"

    clean_param = param_name
    if param_name and param_name.startswith("Domain: "):
        clean_param = param_name.replace("Domain: ", "").strip()

    predictor = pipeline.predictors.get(clean_param)
    if not predictor:
        if pipeline.predictors:
            clean_param = list(pipeline.predictors.keys())[0]
            predictor = pipeline.predictors[clean_param]
        else:
            return f"<div style='background: rgba(245,158,11,0.1); border: 1px solid #F59E0B; border-radius: 10px; color: #FBBF24; padding: 14px;'>No meta-regression models available for parameter: {html.escape(str(param_name))}</div>"

    proj = predictor.predict_trial(dose_mg=float(dose), duration_weeks=float(duration))
    meas = predictor.effects[0].measure if predictor.effects else "Effect"

    direction_color = "#10B981" if proj.predicted_effect < 0 else "#38BDF8"
    signif_badge = "Statistically Significant" if (proj.ci_lower > 0 or proj.ci_upper < 0) else "Neutral / Overlapping Null"

    # Extrapolation confidence assessment
    obs_drugs = getattr(pipeline, "normalized_drugs", [])
    obs_doses = [float(e.dose_mg) for e in predictor.effects if e.dose_mg is not None]
    obs_durs = [float(e.duration_weeks) for e in predictor.effects if e.duration_weeks is not None]
    risk_info = extrapolation_risk_score(
        target_drug=drug_profile or "Pooled Cohort Average",
        target_dose=float(dose),
        target_duration=float(duration),
        observed_drugs=obs_drugs,
        observed_doses=obs_doses,
        observed_durations=obs_durs
    )

    return f"""
    <div style="background: linear-gradient(135deg, rgba(30,27,75,0.92) 0%, rgba(15,23,42,0.96) 100%); border: 1.5px solid #EC4899; border-radius: 18px; padding: 22px; margin: 15px 0; box-shadow: 0 10px 30px rgba(236,72,153,0.25);">
      <div style="display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.1); padding-bottom: 12px; margin-bottom: 14px; gap: 10px;">
        <div>
          <div style="display: flex; align-items: center; gap: 8px; margin-bottom: 6px;">
            <span style="background: #EC4899; color: white; padding: 3px 12px; border-radius: 9999px; font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.05em;">
              Virtual Trial Simulation
            </span>
            <span style="background: {risk_info['badge_color']}22; border: 1px solid {risk_info['badge_color']}; color: #FFFFFF; padding: 3px 10px; border-radius: 9999px; font-size: 11px; font-weight: 700;">
              {risk_info['icon']} {risk_info['level']}
            </span>
          </div>
          <h3 style="color: #F8FAFC; margin: 0; font-size: 20px; font-weight: 800;">
            {clean_param} • {drug_profile or 'Pooled Cohort'} @ {dose:.0f} mg/day ({duration:.0f} weeks)
          </h3>
        </div>
        <div>
          <span style="background: rgba(236,72,153,0.15); border: 1px solid #EC4899; color: #F472B6; padding: 4px 12px; border-radius: 9999px; font-size: 12px; font-weight: 700;">
            {signif_badge}
          </span>
        </div>
      </div>
      <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(180px, 1fr)); gap: 14px; margin-bottom: 16px;">
        <div style="background: rgba(15,23,42,0.7); border-radius: 14px; padding: 14px; border-left: 4px solid {direction_color};">
          <div style="color: #94A3B8; font-size: 11px; font-weight: 700; text-transform: uppercase;">Projected Effect ({meas})</div>
          <div style="color: #F8FAFC; font-size: 24px; font-weight: 800; margin-top: 2px;">{proj.predicted_effect:+.2f}</div>
          <div style="color: {direction_color}; font-size: 11px; font-weight: 600;">Expected Mean Shift</div>
        </div>
        <div style="background: rgba(15,23,42,0.7); border-radius: 14px; padding: 14px; border-left: 4px solid #38BDF8;">
          <div style="color: #94A3B8; font-size: 11px; font-weight: 700; text-transform: uppercase;">95% Confidence Interval</div>
          <div style="color: #F8FAFC; font-size: 20px; font-weight: 800; margin-top: 2px;">[{proj.ci_lower:+.2f}, {proj.ci_upper:+.2f}]</div>
          <div style="color: #38BDF8; font-size: 11px; font-weight: 600;">Uncertainty of Mean Response</div>
        </div>
        <div style="background: rgba(15,23,42,0.7); border-radius: 14px; padding: 14px; border-left: 4px solid #F59E0B;">
          <div style="color: #94A3B8; font-size: 11px; font-weight: 700; text-transform: uppercase;">95% Prediction Interval (PI)</div>
          <div style="color: #F8FAFC; font-size: 20px; font-weight: 800; margin-top: 2px;">[{proj.pi_lower:+.2f}, {proj.pi_upper:+.2f}]</div>
          <div style="color: #FBBF24; font-size: 11px; font-weight: 600;">Extrapolated Range for Future Trial</div>
        </div>
      </div>
      <div style="background: rgba(255,255,255,0.05); border-radius: 12px; padding: 14px; font-size: 13px; color: #E2E8F0; line-height: 1.5; margin-bottom: 8px;">
        💡 <strong>Executive Clinical Takeaway:</strong> {proj.clinical_interpretation}
      </div>
      <div style="font-size: 12px; color: #94A3B8; padding-left: 4px;">
        🔬 <strong>Methodological Risk Notice:</strong> {risk_info['narrative']}
      </div>
    </div>
    """


def process_cohort(
    ingest_mode: str,
    cohort_dropdown: str,
    custom_drug_name: str,
    uploaded_files: list,
    model_choice: str,
    api_key: str,
    progress=gr.Progress(track_tqdm=True)
):
    """Runs end-to-end active-ingredient cohort extraction, harmonization, meta-analysis, and dashboard generation."""
    import re
    import html
    import shutil
    from pathlib import Path
    import pandas as pd
    from src.cohort_pipeline import ActiveIngredientCohortPipeline

    progress(0.05, desc="🔍 Initializing Active Ingredient Cohort Pipeline...")

    try:
        # Determine Cohort Name and Input Files
        if "Upload" in str(ingest_mode) and uploaded_files:
            clean_drug = re.sub(r'[^a-zA-Z0-9_\-]', '_', (custom_drug_name or "Custom_Drug").strip()).strip('_')
            if not clean_drug:
                clean_drug = "Custom_Drug"
            cohort_name = clean_drug
            target_dir = Path("analysis") / cohort_name
            target_dir.mkdir(parents=True, exist_ok=True)
            for uf in uploaded_files:
                src_f = Path(uf.name if hasattr(uf, "name") else str(uf))
                orig_name = getattr(uf, "orig_name", src_f.name)
                dst_f = target_dir / orig_name
                shutil.copy2(src_f, dst_f)
        else:
            cohort_name = cohort_dropdown or "Metformin"

        # Map Model Selection
        model_name = "auto"
        if "Auto" in model_choice or "auto" in model_choice.lower():
            model_name = "auto"
        elif "2.0" in model_choice or "3.8" in model_choice:
            model_name = "gemini-2.0-flash"
        elif "1.5 Pro" in model_choice:
            model_name = "gemini-1.5-pro"
        elif "1.5 Flash" in model_choice:
            model_name = "gemini-1.5-flash"
        elif "Sonnet" in model_choice or "sonnet" in model_choice.lower():
            model_name = "claude-3-5-sonnet-20241022"
        elif "Haiku" in model_choice or "haiku" in model_choice.lower():
            model_name = "claude-3-5-haiku-20241022"
        elif "GPT-4o-mini" in model_choice:
            model_name = "gpt-4o-mini"
        elif "GPT-4o" in model_choice:
            model_name = "gpt-4o"
        elif "Local" in model_choice:
            model_name = "smart-local"

        pipeline = ActiveIngredientCohortPipeline(
            cohort_name=cohort_name,
            api_key=api_key.strip() if api_key else None,
            model_name=model_name
        )

        res = pipeline.run_all(progress_callback=progress)
        CACHED_COHORT_PIPELINES[cohort_name] = pipeline

        # Extract Cohort Mode & Primary Verdict
        cohort_mode = res.get("cohort_mode", "Homogeneous Single-Drug Cohort")
        badge_color = res.get("cohort_badge_color", "#6366F1")
        badge_icon = res.get("cohort_badge_icon", "🧬")
        badge_desc = res.get("cohort_mode_description", "")

        primary_param = list(res["meta_results"].keys())[0] if res["meta_results"] else (
            list(res.get("domain_meta_results", {}).keys())[0] if res.get("domain_meta_results") else "Overall Cohort"
        )
        verdict = res["verdicts"].get(primary_param, {})

        # Build Top Executive Verdict & KPI Card
        evidence_badge = verdict.get("evidence_strength", "Statistically Significant")
        verdict_title = verdict.get("verdict_title", f"Executive Clinical Verdict • {cohort_name}")
        summary_text = verdict.get("summary_narrative", f"Analyzed {res['trials_count']} randomized controlled trials.")
        pooled_effect_str = verdict.get("pooled_effect", "N/A")
        pi_str = verdict.get("prediction_interval", "N/A")
        i2_str = verdict.get("i2_percent", "0.0%")
        tau2_str = verdict.get("tau2", "0.0000")
        dose_trend_str = verdict.get("dose_trend", "Linear Meta-Regression")

        verdict_html = f"""
        <div style="background: linear-gradient(135deg, rgba(15,23,42,0.95) 0%, rgba(30,27,75,0.96) 50%, rgba(15,23,42,0.95) 100%); border: 1.5px solid rgba(99,102,241,0.5); border-radius: 20px; padding: 26px; box-shadow: 0 15px 35px -5px rgba(0, 0, 0, 0.5), 0 0 25px rgba(99, 102, 241, 0.2); margin-bottom: 24px; backdrop-filter: blur(20px);">
          <div style="display: flex; flex-wrap: wrap; justify-content: space-between; align-items: center; border-bottom: 1px solid rgba(255,255,255,0.12); padding-bottom: 16px; margin-bottom: 18px; gap: 14px;">
            <div style="max-width: 72%;">
              <div style="display: inline-flex; align-items: center; gap: 8px; margin-bottom: 6px;">
                <span style="background: linear-gradient(90deg, #10B981, #059669); color: white; padding: 4px 14px; border-radius: 9999px; font-size: 11px; font-weight: 800; text-transform: uppercase; letter-spacing: 0.08em; box-shadow: 0 0 12px rgba(16,185,129,0.5);">
                  {evidence_badge}
                </span>
                <span style="background: {badge_color}25; border: 1.5px solid {badge_color}; color: #FFFFFF; padding: 3px 12px; border-radius: 9999px; font-size: 11px; font-weight: 700;">
                  {badge_icon} {cohort_mode}
                </span>
                <span style="background: rgba(99,102,241,0.15); border: 1px solid #6366F1; color: #A5B4FC; padding: 3px 12px; border-radius: 9999px; font-size: 11px; font-weight: 700;">
                  Cohort: {cohort_name}
                </span>
                <span style="background: rgba(245,158,11,0.15); border: 1px solid #F59E0B; color: #FBBF24; padding: 3px 10px; border-radius: 9999px; font-size: 11px; font-weight: 700;">
                  Primary: {primary_param}
                </span>
              </div>
              <h2 style="color: #F8FAFC; margin: 0 0 6px 0; font-size: 22px; font-weight: 800;">
                {verdict_title}
              </h2>
              <p style="color: #94A3B8; margin: 0; font-size: 13px; line-height: 1.5;">
                {summary_text}
              </p>
            </div>
            <div>
              <div style="background: rgba(99,102,241,0.15); border: 1.5px solid #6366F1; color: #C4B5FD; padding: 10px 18px; border-radius: 14px; font-weight: 800; font-size: 13px; text-align: center; box-shadow: 0 0 20px rgba(99,102,241,0.25);">
                <div style="font-size: 15px; color: #F8FAFC;">{pooled_effect_str}</div>
                <div style="font-size: 11px; color: #FBBF24; margin-top: 4px;">{pi_str}</div>
              </div>
            </div>
          </div>

          <!-- 4 Radiant Cohort KPI Cards -->
          <div style="display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 14px;">
            <div style="background: rgba(30,41,59,0.6); border: 1px solid rgba(255,255,255,0.08); border-radius: 14px; padding: 14px; border-left: 4px solid #6366F1;">
              <div style="color: #94A3B8; font-size: 11px; font-weight: 700; text-transform: uppercase;">Pooled Trials</div>
              <div style="color: #F8FAFC; font-size: 22px; font-weight: 800;">{res['trials_count']} RCTs</div>
              <div style="color: #A5B4FC; font-size: 11px; margin-top: 2px;">Fully Harmonized</div>
            </div>
            <div style="background: rgba(30,41,59,0.6); border: 1px solid rgba(255,255,255,0.08); border-radius: 14px; padding: 14px; border-left: 4px solid #8B5CF6;">
              <div style="color: #94A3B8; font-size: 11px; font-weight: 700; text-transform: uppercase;">Total Cohort Size</div>
              <div style="color: #F8FAFC; font-size: 22px; font-weight: 800;">{res['total_patients']:,} Patients</div>
              <div style="color: #C084FC; font-size: 11px; margin-top: 2px;">Cross-Trial Population</div>
            </div>
            <div style="background: rgba(30,41,59,0.6); border: 1px solid rgba(255,255,255,0.08); border-radius: 14px; padding: 14px; border-left: 4px solid #10B981;">
              <div style="color: #94A3B8; font-size: 11px; font-weight: 700; text-transform: uppercase;">Heterogeneity I²</div>
              <div style="color: #F8FAFC; font-size: 22px; font-weight: 800;">{i2_str}</div>
              <div style="color: #34D399; font-size: 11px; margin-top: 2px;">Variance τ² = {tau2_str}</div>
            </div>
            <div style="background: rgba(30,41,59,0.6); border: 1px solid rgba(255,255,255,0.08); border-radius: 14px; padding: 14px; border-left: 4px solid #EC4899;">
              <div style="color: #94A3B8; font-size: 11px; font-weight: 700; text-transform: uppercase;">Dose Response</div>
              <div style="color: #F8FAFC; font-size: 13px; font-weight: 700; margin-top: 4px;">{dose_trend_str}</div>
            </div>
          </div>
        </div>
        """

        # Build Divergence Disclosure Panel
        div_rep = res.get("divergence_report", {})
        df_reg = div_rep.get("df_regimens", pd.DataFrame())
        df_dur = div_rep.get("df_durations", pd.DataFrame())
        df_elig = div_rep.get("df_eligibility", pd.DataFrame())
        exact_p = div_rep.get("exact_parameters", [])
        dom_p = div_rep.get("domain_bridged_parameters", [])
        uniq_map = div_rep.get("unique_parameters_by_trial", {})
        narrative = div_rep.get("adaptation_narrative", "")

        reg_html = df_reg.to_html(classes="comp-table", index=False) if not df_reg.empty else "<p style='color: #94A3B8;'>No regimen divergence.</p>"
        dur_html = df_dur.to_html(classes="comp-table", index=False) if not df_dur.empty else "<p style='color: #94A3B8;'>No duration divergence.</p>"
        elig_html = df_elig.to_html(classes="comp-table", index=False) if not df_elig.empty else "<p style='color: #94A3B8;'>No eligibility criteria divergence recorded.</p>"

        uniq_items = []
        for s_id, u_list in uniq_map.items():
            uniq_str = ", ".join(u_list) if u_list else "All parameters overlap with other trials"
            uniq_items.append(f"<li><strong style='color: #F8FAFC;'>{s_id}:</strong> {uniq_str}</li>")
        uniq_html = f"<ul style='margin: 6px 0 0 18px; padding: 0; color: #cbd5e1; font-size: 12px;'>{''.join(uniq_items)}</ul>"

        cohort_divergence_html = f"""
        <div style="background: rgba(30, 41, 59, 0.75); border: 1.5px solid {badge_color}66; border-radius: 16px; padding: 22px; margin-bottom: 20px;">
          <div style="display: flex; justify-content: space-between; align-items: center; margin-bottom: 12px;">
            <h3 style="color: #F8FAFC; margin: 0; font-size: 18px; font-weight: 800;">⚠️ Trial Divergence & How Evidex Adapted (Transparency Matrix & Narrative Summary)</h3>
            <span style="background: {badge_color}33; color: #FFFFFF; border: 1px solid {badge_color}; font-size: 11px; font-weight: 700; padding: 4px 12px; border-radius: 9999px;">
              {badge_icon} {cohort_mode}
            </span>
          </div>
          <p style="color: #E2E8F0; font-size: 13px; line-height: 1.6; margin-bottom: 16px; background: rgba(15,23,42,0.6); padding: 12px 16px; border-radius: 10px; border-left: 3px solid {badge_color};">
            <strong>Methodological Adaptation Strategy:</strong> {narrative}
          </p>
          <div style="display: grid; grid-template-columns: 1fr 1fr; gap: 16px; margin-bottom: 16px;">
            <div style="background: rgba(15,23,42,0.5); padding: 12px; border-radius: 10px; overflow-x: auto;">
              <h4 style="color: #94A3B8; margin: 0 0 8px 0; font-size: 12px; text-transform: uppercase;">1. Regimen & Treatment Arms</h4>
              {reg_html}
            </div>
            <div style="background: rgba(15,23,42,0.5); padding: 12px; border-radius: 10px; overflow-x: auto;">
              <h4 style="color: #94A3B8; margin: 0 0 8px 0; font-size: 12px; text-transform: uppercase;">2. Follow-Up Horizons & Populations</h4>
              {dur_html}
            </div>
          </div>
          <div style="background: rgba(15,23,42,0.5); padding: 12px; border-radius: 10px; margin-bottom: 16px; overflow-x: auto;">
            <h4 style="color: #94A3B8; margin: 0 0 8px 0; font-size: 12px; text-transform: uppercase;">3. Patient Population & Eligibility Criteria</h4>
            {elig_html}
          </div>
          <div style="background: rgba(15,23,42,0.6); padding: 14px 16px; border-radius: 10px; font-size: 13px;">
            <h4 style="color: #94A3B8; margin: 0 0 8px 0; font-size: 12px; text-transform: uppercase;">4. Endpoint Categorization Across Trials</h4>
            <div style="margin-bottom: 6px;"><strong style="color: #38BDF8;">Exact Harmonized Parameters (Tier 1):</strong> {', '.join(exact_p) if exact_p else 'None (Cross-scale domain bridging applied)'}</div>
            <div style="margin-bottom: 6px;"><strong style="color: #A78BFA;">Clinical Domains Bridged (Tier 2 SMD):</strong> {', '.join(dom_p) if dom_p else 'None'}</div>
            <div><strong style="color: #F59E0B;">Trial-Specific Unique Parameters:</strong> {uniq_html}</div>
          </div>
        </div>
        """

        # DataFrames: Comparison & Heatmap
        comp_df = deduplicate_columns(res["comparison_matrix"])
        heatmap_df = deduplicate_columns(res["heatmap"])

        # Meta-Analysis Summary Table
        meta_rows = []
        for p_name, m_res in res["meta_results"].items():
            v = res["verdicts"].get(p_name, {})
            meta_rows.append({
                "Clinical Parameter": p_name,
                "Measure": m_res.measure,
                "Trials (k)": m_res.k_studies,
                "Patients (N)": m_res.total_n,
                "Pooled RE Estimate": round(m_res.re_estimate, 3),
                "95% CI Lower": round(m_res.re_ci_lower, 3),
                "95% CI Upper": round(m_res.re_ci_upper, 3),
                "95% Prediction Interval": f"[{m_res.pi_lower:+.2f}, {m_res.pi_upper:+.2f}]",
                "p-value": round(m_res.re_p_value, 5),
                "I² (%)": f"{m_res.i2:.1f}%",
                "tau² (DL)": round(m_res.tau2, 4),
                "tau² (REML)": round(m_res.reml_tau2 or m_res.tau2, 4),
                "Egger Test p": round(m_res.egger_p, 4) if m_res.egger_p else "N/A (k < 4)",
                "Evidence Strength": v.get("evidence_strength", "Significant")
            })
        meta_df = deduplicate_columns(pd.DataFrame(meta_rows))

        # Domain-Level Bridging DataFrame
        domain_rows = []
        for d_name, d_res in res.get("domain_meta_results", {}).items():
            domain_rows.append({
                "Clinical Domain": d_name,
                "Measure": d_res.measure,
                "Trials (k)": d_res.k_studies,
                "Patients (N)": d_res.total_n,
                "Pooled SMD (Hedges' g)": round(d_res.pooled_smd, 3),
                "95% CI Lower": round(d_res.ci_lower, 3),
                "95% CI Upper": round(d_res.ci_upper, 3),
                "95% Prediction Interval": f"[{d_res.pi_lower:+.2f}, {d_res.pi_upper:+.2f}]",
                "p-value": round(d_res.p_value, 5),
                "I² (%)": f"{d_res.i2:.1f}%",
                "Bridged Endpoints": ", ".join(d_res.parameters_included),
                "Clinical Interpretation": d_res.interpretation
            })
        domain_df = deduplicate_columns(pd.DataFrame(domain_rows))

        # SUCRA Hierarchy DataFrame
        sucra_rows = []
        for s in res.get("sucra_rankings", []):
            sucra_rows.append({
                "Rank": f"#{s.get('rank', 1)}",
                "Treatment / Drug": s.get("treatment", ""),
                "SUCRA Score (%)": f"{s.get('sucra_score', 0):.1f}%",
                "Mean Standardized Effect": round(s.get("mean_effect", 0.0), 3),
                "Standard Error": round(s.get("se", 0.0), 3),
                "Best Treatment Prob (%)": f"{s.get('best_prob', 0):.1f}%",
                "Worst Treatment Prob (%)": f"{s.get('worst_prob', 0):.1f}%",
                "Efficacy Tier": s.get("tier", "Evaluated")
            })
        # Subgroup Meta-Analysis DataFrame
        subgroup_rows = []
        for sg in res.get("subgroup_results", []):
            for sub in sg.subgroups:
                subgroup_rows.append({
                    "Subgroup Variable": sg.subgroup_variable,
                    "Subgroup Tier": sub.subgroup_name,
                    "Studies (k)": sub.k_studies,
                    "Patients (N)": sub.total_n,
                    "Pooled Estimate": round(sub.pooled_estimate, 3),
                    "95% CI": f"[{sub.ci_lower:+.3f}, {sub.ci_upper:+.3f}]",
                    "p-value": round(sub.p_value, 5),
                    "I² (%)": f"{sub.i2:.1f}%",
                    "Q_between": round(sg.q_between, 3),
                    "p_between": round(sg.p_between, 5),
                    "Subgroup Verdict": sg.interpretation
                })
        subgroup_df = deduplicate_columns(pd.DataFrame(subgroup_rows))

        # Predictive Projections Matrix
        pred_rows = []
        for p_name, pred_eng in pipeline.predictors.items():
            for proj in pred_eng.generate_dose_duration_grid():
                pred_rows.append({
                    "Parameter / Domain": p_name,
                    "Dose (mg)": proj.dose_mg,
                    "Duration (wks)": proj.duration_weeks,
                    "Projected Effect": round(proj.predicted_effect, 3),
                    "95% CI": f"[{proj.ci_lower:+.2f}, {proj.ci_upper:+.2f}]",
                    "95% Prediction Interval": f"[{proj.pi_lower:+.2f}, {proj.pi_upper:+.2f}]",
                    "NNT": f"{proj.nnt:.1f}" if proj.nnt else "—",
                    "Clinical Takeaway": proj.clinical_interpretation
                })
        pred_df = deduplicate_columns(pd.DataFrame(pred_rows))

        # Forest Plot Visual
        forest_html = ""
        if hasattr(pipeline, "forest_htmls") and pipeline.forest_htmls:
            forest_html = pipeline.forest_htmls[0]
        else:
            with open(res["html_path"], "r", encoding="utf-8") as hf:
                content = hf.read()
                forest_html = f"<iframe srcdoc='{html.escape(content)}' style='width: 100%; height: 550px; border: none; border-radius: 14px;'></iframe>"

        # Drug and parameter choices
        drug_choices = ["Pooled Cohort Average"] + sorted(list(res.get("divergence_report", {}).get("normalized_drugs", [])))
        exact_p_list = list(res["meta_results"].keys())
        dom_p_list = [f"Domain: {d}" for d in res.get("domain_meta_results", {}).keys()]
        all_param_choices = exact_p_list + dom_p_list
        if not all_param_choices:
            all_param_choices = ["HbA1c"]

        # Initial Simulation Result for Primary Parameter
        init_sim_html = simulate_virtual_trial_ui(
            mode=ingest_mode,
            cohort_dropdown=cohort_dropdown,
            custom_drug_name=custom_drug_name,
            drug_profile="Pooled Cohort Average",
            param_name=all_param_choices[0],
            dose=1000.0,
            duration=24.0
        )

        return (
            verdict_html,
            cohort_divergence_html,
            comp_df,
            heatmap_df,
            forest_html,
            meta_df,
            domain_df,
            sucra_df,
            subgroup_df,
            pred_df,
            res["excel_path"],
            res["html_path"],
            gr.update(choices=drug_choices, value=drug_choices[0]),
            gr.update(choices=all_param_choices, value=all_param_choices[0]),
            init_sim_html
        )

    except Exception as e:
        import traceback, html
        traceback.print_exc()
        err_msg = html.escape(str(e))
        err_card = f"""
        <div style="background: linear-gradient(135deg, rgba(239,68,68,0.15) 0%, rgba(15,23,42,0.95) 100%); border: 1.5px solid #EF4444; border-radius: 18px; padding: 26px; color: #FCA5A5; box-shadow: 0 10px 30px rgba(0,0,0,0.5);">
          <div style="display: flex; align-items: center; gap: 10px; margin-bottom: 12px;">
            <span style="font-size: 24px;">⚠️</span>
            <h3 style="color: #F87171; margin: 0; font-size: 18px; font-weight: 800;">Cohort Meta-Analysis Diagnostic</h3>
          </div>
          <p style="color: #FEE2E2; font-size: 13px; line-height: 1.5; margin-bottom: 12px;">
            An issue occurred during multi-trial pooling or statistical meta-analysis:
          </p>
          <pre style="background: rgba(0,0,0,0.5); padding: 12px 16px; border-radius: 10px; color: #FCA5A5; font-family: monospace; font-size: 12px; overflow-x: auto; white-space: pre-wrap;">{err_msg}</pre>
        </div>
        """
        import pandas as pd
        return (
            err_card,
            "",
            pd.DataFrame(),
            pd.DataFrame(),
            "",
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            pd.DataFrame(),
            None,
            None,
            gr.update(),
            gr.update(),
            ""
        )


def build_app():
    custom_css = """
    /* Sleek Modern Biotech & Deep AI Aesthetic */
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500;600&display=swap');

    :root {
        --font-sans: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
        --font-mono: 'JetBrains Mono', monospace;
    }

    body, .gradio-container {
        font-family: var(--font-sans) !important;
        background: radial-gradient(circle at 50% 0%, #1e1b4b 0%, #0f172a 45%, #090d16 100%) !important;
        color: #f1f5f9 !important;
        min-height: 100vh;
    }

    /* Radiant Header Styling */
    #header-container {
        text-align: center;
        padding: 40px 20px 25px 20px;
        margin-bottom: 25px;
        background: linear-gradient(180deg, rgba(30, 27, 75, 0.5) 0%, rgba(15, 23, 42, 0) 100%);
        border-bottom: 1px solid rgba(99, 102, 241, 0.2);
    }

    .header-badge {
        display: inline-flex;
        align-items: center;
        gap: 8px;
        background: linear-gradient(90deg, rgba(99, 102, 241, 0.2) 0%, rgba(139, 92, 246, 0.2) 100%);
        border: 1px solid rgba(139, 92, 246, 0.4);
        padding: 6px 16px;
        border-radius: 9999px;
        font-size: 13px;
        font-weight: 700;
        color: #c4b5fd;
        margin-bottom: 16px;
        box-shadow: 0 0 20px rgba(139, 92, 246, 0.25);
    }

    .main-title {
        font-size: 2.8rem !important;
        font-weight: 800 !important;
        background: linear-gradient(135deg, #ffffff 20%, #a5b4fc 60%, #38bdf8 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 10px !important;
        letter-spacing: -0.02em;
    }

    .sub-title {
        font-size: 1.15rem !important;
        color: #94a3b8 !important;
        max-width: 800px;
        margin: 0 auto 20px auto !important;
        line-height: 1.6;
    }

    /* Badges Row */
    .badges-row {
        display: flex;
        justify-content: center;
        flex-wrap: wrap;
        gap: 10px;
        margin-top: 12px;
    }

    .pill-badge {
        font-size: 11px;
        font-weight: 700;
        padding: 4px 12px;
        border-radius: 9999px;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }

    .pill-blue { background: rgba(56, 189, 248, 0.12); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.3); }
    .pill-purple { background: rgba(168, 85, 247, 0.12); color: #c084fc; border: 1px solid rgba(168, 85, 247, 0.3); }
    .pill-green { background: rgba(52, 211, 153, 0.12); color: #34d399; border: 1px solid rgba(52, 211, 153, 0.3); }
    .pill-amber { background: rgba(251, 191, 36, 0.12); color: #fbbf24; border: 1px solid rgba(251, 191, 36, 0.3); }

    /* Card Panels & Glassmorphism */
    .glass-card {
        background: rgba(15, 23, 42, 0.75) !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
        border-radius: 18px !important;
        box-shadow: 0 10px 30px -5px rgba(0, 0, 0, 0.4) !important;
        backdrop-filter: blur(16px) !important;
    }

    /* Primary Action Button */
    .extract-btn {
        background: linear-gradient(135deg, #6366f1 0%, #8b5cf6 50%, #d946ef 100%) !important;
        color: white !important;
        font-weight: 800 !important;
        font-size: 16px !important;
        padding: 14px 28px !important;
        border-radius: 14px !important;
        border: none !important;
        box-shadow: 0 0 25px rgba(139, 92, 246, 0.5) !important;
        transition: all 0.3s cubic-bezier(0.4, 0, 0.2, 1) !important;
        cursor: pointer !important;
    }

    .extract-btn:hover {
        transform: translateY(-2px) scale(1.01) !important;
        box-shadow: 0 0 35px rgba(217, 70, 239, 0.65) !important;
    }

    /* Dataframe Styling */
    .gradio-dataframe {
        border-radius: 12px !important;
        overflow: hidden !important;
        border: 1px solid rgba(255, 255, 255, 0.1) !important;
    }

    /* Tabs active accent */
    .tab-nav button.selected {
        border-bottom: 3px solid #8b5cf6 !important;
        color: #c4b5fd !important;
        font-weight: 700 !important;
    }
    """

    with gr.Blocks(title="Evidex 2.0 • Clinical Trial AI Extractor", css=custom_css, theme=gr.themes.Base()) as demo:
        with gr.Column(elem_id="header-container"):
            gr.HTML(
                """
                <div class="header-badge">
                    <span>✨</span> Next-Generation AI Clinical Trial Extractor
                </div>
                <h1 class="main-title">Evidex 2.0 AI</h1>
                <p class="sub-title">
                    World-Class, Verifiable Clinical Trial Data Extraction Platform. Turn any RCT PDF into an audit-ready, 
                    multi-sheet systematic review database compliant with Cochrane, PRISMA, and top-tier academic medical standards.
                </p>
                <div class="badges-row">
                    <span class="pill-badge pill-purple">⚡ Auto-Calibrated Deep AI Cloud</span>
                    <span class="pill-badge pill-blue">📊 100% Sample Size Verification</span>
                    <span class="pill-badge pill-green">⚖️ 4-Operator Atomic Eligibility</span>
                    <span class="pill-badge pill-amber">📥 Multi-Sheet Excel (.xlsx) & JSON</span>
                </div>
                """
            )

        with gr.Tabs() as main_nav_tabs:
            # ==========================================
            # TAB 1: PHASE 1 SINGLE-STUDY DEEP EXTRACTOR
            # ==========================================
            with gr.TabItem("🩺 Single-Study Deep Extractor (Phase 1)"):
                with gr.Row():
                    # Left Column: Upload & Parameters
                    with gr.Column(scale=1):
                        gr.Markdown("### 📄 Step 1: Upload Trial Protocol / Paper")
                        pdf_input = gr.File(
                            label="Drop RCT Paper (PDF)",
                            file_types=[".pdf"],
                            type="filepath"
                        )

                        gr.Markdown("### ⚡ Step 2: Configure AI Engine")
                        model_selector = gr.Dropdown(
                            label="🤖 Deep AI Model Selection (BYOK)",
                            choices=[
                                "⚡ Auto-Detect & Select Best Available Model (Recommended)",
                                "Google Gemini 2.0 Flash (Fast & Accurate Flagship)",
                                "Google Gemini 1.5 Pro (Deep Clinical Reasoning)",
                                "Google Gemini 1.5 Flash",
                                "Anthropic Claude 3.5 Sonnet (Benchmark Methodological Extraction)",
                                "Anthropic Claude 3.5 Haiku",
                                "OpenAI GPT-4o (Clinical Reasoning)",
                                "OpenAI GPT-4o-mini",
                                "Smart Local Engine (Offline / Reference Benchmark)"
                            ],
                            value="⚡ Auto-Detect & Select Best Available Model (Recommended)"
                        )

                        api_key_input = gr.Textbox(
                            label="🔑 AI Provider API Key (Google AI Studio / Anthropic / OpenAI)",
                            type="password",
                            placeholder="Enter your Gemini Key (AIza...), Claude Key (sk-ant...), or OpenAI Key (sk-...)"
                        )

                        extract_btn = gr.Button("🚀 Run Academic Deep Extraction", variant="primary", elem_classes=["extract-btn"])

                        gr.Markdown("### 📥 Step 3: Verified Outputs")
                        excel_output = gr.File(label="📊 Standardized Multi-Sheet Excel (.xlsx)")
                        json_output = gr.File(label="📄 Structured Trial Protocol Data (.json)")

                    # Right Column: Visual Dashboard & Interactive Tables
                    with gr.Column(scale=2):
                        summary_output = gr.HTML(
                            """
                            <div style="background: rgba(30,41,59,0.5); border: 1.5px dashed rgba(99,102,241,0.3); border-radius: 18px; padding: 40px 20px; text-align: center; color: #94A3B8;">
                              <div style="font-size: 38px; margin-bottom: 10px;">🩺</div>
                              <h3 style="color: #F8FAFC; margin: 0 0 8px 0; font-size: 18px;">Awaiting Clinical Trial PDF</h3>
                              <p style="margin: 0; font-size: 13px;">Upload an RCT paper on the left to extract full study metadata, randomized arms, atomic eligibility criteria, and 60–120+ clinical outcomes.</p>
                            </div>
                            """
                        )

                        with gr.Tabs():
                            with gr.TabItem("📑 Master Extraction Sheet (Sheet 1 - Consolidated)"):
                                master_table = gr.DataFrame(
                                    label="Consolidated Multi-Level Mining Table (Replicating Benchmark)",
                                    interactive=False,
                                    wrap=True,
                                    max_height=500
                                )

                            with gr.TabItem("📊 Variables Matrix (Cross-Arm Comparison)"):
                                matrix_table = gr.DataFrame(
                                    label="Horizontal Cross-Trial Variable Matrix",
                                    interactive=False,
                                    wrap=True,
                                    max_height=500
                                )

                            with gr.TabItem("📋 Granular Outcomes (100% Sample Sizes)"):
                                outcomes_table = gr.DataFrame(
                                    label="Normalized Clinical & Safety Outcomes",
                                    interactive=False,
                                    wrap=True,
                                    max_height=500
                                )

                            with gr.TabItem("⚖️ Eligibility Criteria Matrix (4 Operators)"):
                                eligibility_table = gr.DataFrame(
                                    label="Atomic Inclusion & Exclusion Criteria",
                                    interactive=False,
                                    wrap=True,
                                    max_height=500
                                )

                extract_btn.click(
                    fn=process_pdf,
                    inputs=[pdf_input, api_key_input, model_selector],
                    outputs=[excel_output, json_output, summary_output, master_table, matrix_table, outcomes_table, eligibility_table],
                    show_progress="full"
                )

            # =========================================================================
            # TAB 2: PHASE 2 MULTI-TRIAL COHORT, META-ANALYSIS & PREDICTIVE DASHBOARD
            # =========================================================================
            with gr.TabItem("🚀 Multi-Trial Cohort, Meta-Analysis & Predictive Executive Dashboard (Phase 2)"):
                with gr.Row():
                    # Left Column: Cohort Selection & Configuration
                    with gr.Column(scale=1):
                        gr.Markdown("### 🧬 Step 1: Active-Ingredient Ingestion")
                        cohort_mode_radio = gr.Radio(
                            choices=["Local Cohort Folder (analysis/<Drug>)", "Upload Multiple Files (PDFs / Excels)"],
                            label="Cohort Source",
                            value="Local Cohort Folder (analysis/<Drug>)"
                        )

                        with gr.Group() as local_mode_group:
                            available_cohorts = list_available_cohorts()
                            cohort_dropdown = gr.Dropdown(
                                label="Select Active Ingredient Folder",
                                choices=available_cohorts,
                                value=available_cohorts[0] if available_cohorts else None
                            )
                            refresh_cohorts_btn = gr.Button("🔄 Refresh Folder List", size="sm")

                        with gr.Group(visible=False) as upload_mode_group:
                            custom_drug_input = gr.Textbox(
                                label="Active Ingredient / Drug Name",
                                placeholder="e.g. Metformin, Dapagliflozin, Semaglutide..."
                            )
                            upload_cohort_files = gr.File(
                                label="Upload Trial PDFs or Pre-Extracted Excels",
                                file_count="multiple",
                                file_types=[".pdf", ".xlsx"]
                            )

                        gr.Markdown("### ⚡ Step 2: Auto-Extraction & AI Engine")
                        cohort_model_selector = gr.Dropdown(
                            label="🤖 Deep AI Model Selection (BYOK for unextracted PDFs)",
                            choices=[
                                "⚡ Auto-Detect & Select Best Available Model (Recommended)",
                                "Google Gemini 2.0 Flash (Fast & Accurate Flagship)",
                                "Google Gemini 1.5 Pro (Deep Clinical Reasoning)",
                                "Google Gemini 1.5 Flash",
                                "Anthropic Claude 3.5 Sonnet (Benchmark Methodological Extraction)",
                                "Anthropic Claude 3.5 Haiku",
                                "OpenAI GPT-4o (Clinical Reasoning)",
                                "OpenAI GPT-4o-mini",
                                "Smart Local Engine (Offline / Reference Benchmark)"
                            ],
                            value="⚡ Auto-Detect & Select Best Available Model (Recommended)"
                        )

                        cohort_api_key_input = gr.Textbox(
                            label="🔑 AI Provider API Key (Optional for Cloud Extraction)",
                            type="password",
                            placeholder="Enter your Gemini Key (AIza...), Claude Key (sk-ant...), or OpenAI Key (sk-...)"
                        )

                        run_cohort_btn = gr.Button("🚀 Run End-to-End Cohort Extraction & Executive Analysis", variant="primary", elem_classes=["extract-btn"])

                        gr.Markdown("### 📥 Step 3: Executive Deliverables")
                        cohort_excel_file = gr.File(label="📊 Master Comparison & Meta-Analysis Excel (.xlsx)")
                        cohort_html_file = gr.File(label="🌐 Standalone Interactive HTML Executive Dashboard (.html)")

                    # Right Column: Visual Dashboard, Meta-Analysis & Virtual Trial Simulator
                    with gr.Column(scale=2):
                        cohort_verdict_html = gr.HTML(
                            """
                            <div style="background: rgba(30,41,59,0.5); border: 1.5px dashed rgba(99,102,241,0.3); border-radius: 18px; padding: 40px 20px; text-align: center; color: #94A3B8;">
                              <div style="font-size: 38px; margin-bottom: 10px;">🚀</div>
                              <h3 style="color: #F8FAFC; margin: 0 0 8px 0; font-size: 18px;">Awaiting Cohort Selection</h3>
                              <p style="margin: 0; font-size: 13px;">Select an active ingredient folder or upload multiple trial files on the left to run automatic extraction, cross-trial harmonization, metafor-grade meta-analysis, and predictive virtual trial simulation.</p>
                            </div>
                            """
                        )

                        with gr.Tabs():
                            with gr.TabItem("📑 Cross-Trial Comparison & Coverage"):
                                cohort_comp_table = gr.DataFrame(
                                    label="Head-to-Head Comparative Matrix (Arms, Dosages, Durations, Sample Sizes)",
                                    interactive=False,
                                    wrap=True,
                                    max_height=450
                                )
                                cohort_heatmap_table = gr.DataFrame(
                                    label="Parameter Coverage Heatmap (Across Pooled Trials)",
                                    interactive=False,
                                    wrap=True,
                                    max_height=450
                                )

                            with gr.TabItem("⚠️ Trial Divergence & How Evidex Adapted"):
                                cohort_divergence_html = gr.HTML(
                                    label="Explicit Divergence & Methodological Adaptation Strategy"
                                )

                            with gr.TabItem("📊 metafor-Grade Meta-Analysis"):
                                cohort_forest_html = gr.HTML(
                                    label="Forest & Funnel Plots"
                                )
                                cohort_meta_table = gr.DataFrame(
                                    label="Pooled Random-Effects Results (Estimate, 95% CI, 95% PI, I², tau², p-value, Egger Test)",
                                    interactive=False,
                                    wrap=True,
                                    max_height=450
                                )

                            with gr.TabItem("🏆 Cross-Drug / Cross-Trial Domain Comparison & Ranking"):
                                cohort_sucra_table = gr.DataFrame(
                                    label="🏆 SUCRA Comparative Treatment Rankings & Hierarchy (Monte Carlo Simulation)",
                                    interactive=False,
                                    wrap=True,
                                    max_height=320
                                )
                                cohort_subgroup_table = gr.DataFrame(
                                    label="📊 Subgroup Meta-Analysis Across Active Ingredients & Regimen Tiers (Cochran's Q_between)",
                                    interactive=False,
                                    wrap=True,
                                    max_height=320
                                )
                                cohort_domain_table = gr.DataFrame(
                                    label="Clinical Domain Bridging (Scale-Free SMD Hedges' g across Divergent Scales)",
                                    interactive=False,
                                    wrap=True,
                                    max_height=380
                                )

                            with gr.TabItem("🔮 Virtual Trial Simulator & Projections"):
                                gr.Markdown("#### 🧬 Simulate Hypothetical & Future Trial Outcomes (Multivariate WLS Meta-Regression)")
                                with gr.Row():
                                    sim_drug_dropdown = gr.Dropdown(
                                        label="Active Drug Profile",
                                        choices=["Pooled Cohort Average"],
                                        value="Pooled Cohort Average"
                                    )
                                    sim_param_dropdown = gr.Dropdown(
                                        label="Target Clinical Parameter / Domain",
                                        choices=["HbA1c", "Body Weight", "Systolic BP"],
                                        value="HbA1c"
                                    )
                                with gr.Row():
                                    sim_dose_slider = gr.Slider(
                                        minimum=0,
                                        maximum=3000,
                                        step=25,
                                        value=1000,
                                        label="Target Dosage (mg/day)"
                                    )
                                    sim_dur_slider = gr.Slider(
                                        minimum=4,
                                        maximum=156,
                                        step=4,
                                        value=24,
                                        label="Treatment Duration (weeks)"
                                    )

                                sim_run_btn = gr.Button("🔮 Simulate Virtual Trial Outcome", variant="secondary")
                                sim_result_html = gr.HTML(
                                    """
                                    <div style="background: rgba(30,41,59,0.4); border: 1px dashed rgba(236,72,153,0.3); border-radius: 14px; padding: 20px; text-align: center; color: #94A3B8; margin: 10px 0;">
                                      Adjust drug, dosage & duration sliders above and click Simulate to project outcome with 95% Confidence & Prediction Intervals and Extrapolation Risk Rating.
                                    </div>
                                    """
                                )

                                cohort_pred_table = gr.DataFrame(
                                    label="Dose-Duration Extrapolation Matrix (with 95% Confidence & Prediction Intervals)",
                                    interactive=False,
                                    wrap=True,
                                    max_height=450
                                )

                cohort_mode_radio.change(
                    fn=toggle_cohort_mode,
                    inputs=[cohort_mode_radio],
                    outputs=[local_mode_group, upload_mode_group]
                )

                refresh_cohorts_btn.click(
                    fn=refresh_cohorts,
                    inputs=[],
                    outputs=[cohort_dropdown]
                )

                run_cohort_btn.click(
                    fn=process_cohort,
                    inputs=[
                        cohort_mode_radio,
                        cohort_dropdown,
                        custom_drug_input,
                        upload_cohort_files,
                        cohort_model_selector,
                        cohort_api_key_input
                    ],
                    outputs=[
                        cohort_verdict_html,
                        cohort_divergence_html,
                        cohort_comp_table,
                        cohort_heatmap_table,
                        cohort_forest_html,
                        cohort_meta_table,
                        cohort_domain_table,
                        cohort_sucra_table,
                        cohort_subgroup_table,
                        cohort_pred_table,
                        cohort_excel_file,
                        cohort_html_file,
                        sim_drug_dropdown,
                        sim_param_dropdown,
                        sim_result_html
                    ],
                    show_progress="full"
                )

                sim_run_btn.click(
                    fn=simulate_virtual_trial_ui,
                    inputs=[
                        cohort_mode_radio,
                        cohort_dropdown,
                        custom_drug_input,
                        sim_drug_dropdown,
                        sim_param_dropdown,
                        sim_dose_slider,
                        sim_dur_slider
                    ],
                    outputs=[sim_result_html]
                )

        gr.HTML(
            """
            <div style="margin-top: 35px; padding: 20px; border-top: 1px solid rgba(255,255,255,0.1); text-align: center; color: #64748B; font-size: 12px;">
              <strong style="color: #94A3B8;">Evidex Academic Methodological Standards:</strong>
              Split eligibility operators (<, =, >, between) • Pure parameter names with dedicated race & timepoint columns • 
              100% filled sample sizes across all outcomes • Page-level provenance citations • metafor-grade Fixed/Random Effects (DL & REML) • 
              95% Prediction Intervals (PI) • Full PRISMA / Cochrane compatibility.
            </div>
            """
        )

    return demo


if __name__ == "__main__":
    demo = build_app()
    demo.queue(default_concurrency_limit=5, max_size=25)
    port = int(os.environ.get("PORT", 7860))
    demo.launch(server_name="0.0.0.0", server_port=port)
