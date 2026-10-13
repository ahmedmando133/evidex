"""
Evidex - Web Interface for AI-assisted Clinical Trial Data Extraction.
Upload any RCT PDF and get a standardized multi-sheet Excel file.
"""

import os
import sys
import pandas as pd
import gradio as gr

# Ensure workspace root in path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from src.extractor import RCTExtractor
from src.exporter import ExcelTrialExporter


def process_pdf(pdf_file, api_key=""):
    if pdf_file is None:
        return None, "⚠️ Please upload a clinical trial PDF file.", None, None

    pdf_path = pdf_file.name if hasattr(pdf_file, "name") else str(pdf_file)
    base_name = os.path.splitext(os.path.basename(pdf_path))[0]
    output_filename = f"outputs/{base_name}_extracted.xlsx"
    os.makedirs("outputs", exist_ok=True)

    # 1. Run extraction (Deep AI if api_key provided, else Smart Local Engine)
    extractor = RCTExtractor(pdf_path, api_key=api_key.strip() if api_key else None)
    data = extractor.extract_all()

    # 2. Export to Excel
    exporter = ExcelTrialExporter(data)
    saved_path = exporter.export(output_filename)

    # 3. Create summary markdown
    summary_md = f"""
### ✅ Extraction Completed Successfully!
- **Study Identifier:** `{data.study.study_id}`
- **Title:** {data.study.title}
- **Authors & Year:** {data.study.authors} ({data.study.publication_year})
- **Journal:** {data.study.journal}
- **Total Sample Size:** {data.study.total_sample_size or 'Not reported'}
- **Arms Extracted:** {len(data.arms)}
- **Eligibility Criteria:** {len(data.eligibility)}
- **Clinical Outcomes Extracted:** {len(data.outcomes)}
- **Provenance Audit Links:** {len(data.provenance)}
"""

    # 4. Preview DataFrames
    outcomes_rows = []
    for o in data.outcomes:
        outcomes_rows.append({
            "Parameter": o.parameter_name,
            "Arm": o.arm_id,
            "Race/Subgroup": o.race or "Overall",
            "Sample Size": o.sample_size,
            "Timepoint": f"{o.timepoint_value} {o.timepoint_unit}",
            "Mean / Events": o.mean if o.mean is not None else o.events,
            "SD / %": o.sd if o.sd is not None else o.percentage,
            "Unit": o.unit or "",
            "Page": o.source_page
        })
    df_outcomes = pd.DataFrame(outcomes_rows)

    # Variables Matrix preview
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
                "Sample Size": o.sample_size,
                "Timepoint": f"{o.timepoint_value} {o.timepoint_unit}"
            }
        val = o.mean if o.mean is not None else (o.percentage if o.percentage is not None else o.change_value)
        rows_map[k][cname] = val

    df_matrix = pd.DataFrame(list(rows_map.values()))

    return saved_path, summary_md, df_matrix, df_outcomes


def build_app():
    custom_css = """
    .gradio-container { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; }
    #header { text-align: center; margin-bottom: 20px; }
    """
    with gr.Blocks(title="Evidex - Clinical Trial AI Extractor") as demo:
        gr.Markdown(
            """
            # 🩺 Evidex: Clinical Trial AI Data Extraction Engine
            ### Verifiable, Multi-Sheet Clinical Trial Extraction Platform
            Upload any RCT paper PDF to automatically extract **Study Metadata, Arms, Eligibility (with 4 operators), Clinical Outcomes (with separate Race & Timepoint columns)**, and generate a dynamic **Variables Matrix**.
            """,
            elem_id="header"
        )

        with gr.Row():
            with gr.Column(scale=1):
                pdf_input = gr.File(
                    label="📄 Upload Clinical Trial PDF",
                    file_types=[".pdf"],
                    type="filepath"
                )
                api_key_input = gr.Textbox(
                    label="🔑 AI API Key (Optional: Google Gemini or OpenAI)",
                    type="password",
                    placeholder="Enter GEMINI_API_KEY or OPENAI_API_KEY (Leave blank for Smart Local Engine)"
                )
                extract_btn = gr.Button("🚀 Extract Trial Data", variant="primary")
                
                gr.Markdown("### 📥 Download Output")
                excel_output = gr.File(label="Standardized Multi-Sheet Excel (.xlsx)")

            with gr.Column(scale=2):
                summary_output = gr.Markdown("### 📊 Extraction Status: Awaiting upload...")
                
                with gr.Tabs():
                    with gr.TabItem("📊 Variables Matrix (Horizontal Comparison)"):
                        matrix_table = gr.DataFrame(label="Cross-Trial Variable Matrix", interactive=False)
                    with gr.TabItem("📋 Outcomes Table"):
                        outcomes_table = gr.DataFrame(label="Normalized Outcomes", interactive=False)

        extract_btn.click(
            fn=process_pdf,
            inputs=[pdf_input, api_key_input],
            outputs=[excel_output, summary_output, matrix_table, outcomes_table]
        )

        gr.Markdown(
            """
            ---
            **Evidex Extraction Architecture Rules Enforced:**
            - **Eligibility Operators:** Split into `<, =, >, between`
            - **Timepoint Separation:** Side-by-side `Timepoint (value)` & `Timepoint (unit)`
            - **Subgroup / Race Separation:** Pure `parameter_name` with dedicated `race` column
            - **100% Sample Size Fill:** Mandatory `sample_size` across all outcome rows
            - **Verifiable Audit:** Full provenance citation mapping to source PDF pages
            """
        )
    return demo


if __name__ == "__main__":
    demo = build_app()
    port = int(os.environ.get("PORT", 7860))
    demo.launch(server_name="0.0.0.0", server_port=port)
