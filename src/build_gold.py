"""Convert the manual (hand-extracted) Excel sheets into the canonical
gold-standard format used for scoring.

Manual sources:
  data/manual/metformin_manual.xlsx  (long/arm-level, DPP adherence table)
  data/manual/orlistat_manual.xlsx   (wide, blood-chemistry table)
"""
from __future__ import annotations

from pathlib import Path

import pandas as pd

from src.io import write_json
from src.canonical import ENTITIES

ROOT = Path(__file__).parent.parent


def _empty_doc(study_id: str) -> dict:
    return {e: [] for e in ENTITIES}


def build_metformin() -> dict:
    f = ROOT / "data/manual/metformin_manual.xlsx"
    raw = pd.read_excel(f, header=None)
    # header rows 0-2; data from row 3
    data = raw.iloc[3:].reset_index(drop=True)
    data.columns = [
        "drug", "phase", "period_n", "period_u", "n_total",
        "bmi_lt", "bmi_eq", "bmi_gt", "bmi_v", "bmi_u",
        "age_lt", "age_eq", "age_gt", "age_v", "age_u",
        "fg_min", "fg_max", "fg_u", "igt_min", "igt_max", "igt_u",
        "race", "gender", "adh_low", "adh_lt50", "adh_gt50", "adh_high",
        "wl_lt", "wl_eq", "wl_gt", "wl_v", "wl_u",
        "p_low", "p_lt50", "p_gt50", "p_high",
    ]
    doc = _empty_doc("RCT_METFORMIN_2012")
    doc["Studies"].append({
        "study_id": "RCT_METFORMIN_2012",
        "title": "Long-Term Safety, Tolerability, and Weight Loss Associated With Metformin in the Diabetes Prevention Program Outcomes Study",
        "authors": "DPP Research Group",
        "publication_year": 2012,
        "journal": "Diabetes Care",
        "doi": "10.2337/dc11-1299",
        "study_design": "Multicenter randomized placebo-controlled clinical trial",
        "study_phase": "DPP 2-year double-blind phase + DPPOS follow-up",
        "total_sample_size": 2155,
        "duration_value": 2,
        "duration_unit": "years",
        "condition_studied": "Prediabetes / Impaired Glucose Tolerance",
    })

    arms = {}
    for i, r in data.iterrows():
        drug = str(r["drug"]).strip().lower()
        if not drug or drug == "nan":
            continue
        arm_id = "ARM_MET_850" if "metformin" in drug else "ARM_MET_PLA"
        if arm_id not in arms:
            arms[arm_id] = {
                "arm_id": arm_id,
                "study_id": "RCT_METFORMIN_2012",
                "arm_name": "Metformin 850mg" if arm_id == "ARM_MET_850" else "Placebo",
                "intervention_type": "experimental" if arm_id == "ARM_MET_850" else "placebo",
                "drug_name": "Metformin" if arm_id == "ARM_MET_850" else "Placebo",
                "dose_value": 850.0 if arm_id == "ARM_MET_850" else None,
                "dose_unit": "mg" if arm_id == "ARM_MET_850" else None,
                "frequency_number": 2.0,
                "frequency_unit": "twice daily",
                "sample_size_allocated": int(r["n_total"]) if pd.notna(r["n_total"]) else None,
                "sample_size_analyzed": None,
                "source_page": 2,
            }
        # Eligibility (once)
        if not doc["Eligibility"]:
            doc["Eligibility"].extend([
                {"criterion_id": "ELIG_001", "study_id": "RCT_METFORMIN_2012", "criterion_type": "inclusion", "domain": "demographic", "criterion_name": "age", "operator": ">=", "value": 25.0, "min_value": None, "max_value": None, "unit": "years", "raw_source_text": "age >= 25 years", "source_page": 2},
                {"criterion_id": "ELIG_002", "study_id": "RCT_METFORMIN_2012", "criterion_type": "inclusion", "domain": "demographic", "criterion_name": "bmi", "operator": ">=", "value": 24.0, "min_value": None, "max_value": None, "unit": "kg/m2", "raw_source_text": "BMI >= 24 kg/m2", "source_page": 2},
                {"criterion_id": "ELIG_003", "study_id": "RCT_METFORMIN_2012", "criterion_type": "inclusion", "domain": "biomarker", "criterion_name": "baseline_fasting_glucose", "operator": "between", "value": None, "min_value": 95.0, "max_value": 125.0, "unit": "mg/dL", "raw_source_text": "fasting plasma glucose 95-125 mg/dL", "source_page": 2},
                {"criterion_id": "ELIG_004", "study_id": "RCT_METFORMIN_2012", "criterion_type": "inclusion", "domain": "biomarker", "criterion_name": "baseline_impaired_glucose_tolerance", "operator": "between", "value": None, "min_value": 140.0, "max_value": 199.0, "unit": "mg/dL", "raw_source_text": "impaired glucose tolerance 140-199 mg/dL", "source_page": 2},
            ])

        # Outcomes: adherence categories + weight loss percent
        base = int(r["adh_low"]) if pd.notna(r["adh_low"]) else None
        lt50 = int(r["adh_lt50"]) if pd.notna(r["adh_lt50"]) else None
        gt50 = int(r["adh_gt50"]) if pd.notna(r["adh_gt50"]) else None
        high = int(r["adh_high"]) if pd.notna(r["adh_high"]) else None
        wl = r["wl_v"] if pd.notna(r["wl_v"]) else None
        tp = str(r["phase"])

        if base is not None:
            doc["Outcomes"].append(_out("RCT_METFORMIN_2012", arm_id, "adherence", "dichotomous", tp, percentage=base))
        if lt50 is not None:
            doc["Outcomes"].append(_out("RCT_METFORMIN_2012", arm_id, "adherence_lt50", "dichotomous", tp, percentage=lt50))
        if gt50 is not None:
            doc["Outcomes"].append(_out("RCT_METFORMIN_2012", arm_id, "adherence_gt50", "dichotomous", tp, percentage=gt50))
        if high is not None:
            doc["Outcomes"].append(_out("RCT_METFORMIN_2012", arm_id, "adherence_high", "dichotomous", tp, percentage=high))
        if wl is not None:
            doc["Outcomes"].append(_out("RCT_METFORMIN_2012", arm_id, "weight_loss_percent", "dichotomous", tp, percentage=float(wl)))

    doc["Arms"] = list(arms.values())
    return doc


def _out(study_id, arm_id, param, stype, tp, mean=None, sd=None, change=None, percentage=None, unit="%"):
    return {
        "outcome_id": f"OUT_{len([1]):04d}",
        "study_id": study_id, "arm_id": arm_id, "domain": "metabolic",
        "parameter_name": param, "statistical_type": stype, "timepoint": tp,
        "sample_size": None, "mean": mean, "sd": sd, "change_value": change,
        "change_sd": None, "events": None, "total": None,
        "percentage": percentage, "unit": unit,
        "effect_measure": None, "effect_value": None, "p_value": None,
        "source_page": 2, "source_location": "Results", "raw_source_text": "",
    }


def build_orlistat() -> dict:
    f = ROOT / "data/manual/orlistat_manual.xlsx"
    raw = pd.read_excel(f, header=None)
    # headers rows 0-3; data rows 4-7 (baseline + followup for 2 arms)
    data = raw.iloc[4:8].reset_index(drop=True)
    doc = _empty_doc("RCT_ORLISTAT_2024")
    doc["Studies"].append({
        "study_id": "RCT_ORLISTAT_2024",
        "title": "Effects of orlistat on serum uric acid levels and gout flares in overweight and obese patients with hyperuricemia: a randomized controlled trial",
        "authors": "Liu et al.", "publication_year": 2024,
        "journal": "Lipids in Health and Disease",
        "doi": "10.1186/s12944-024-02047-7",
        "study_design": "Randomized, double-blind, placebo-controlled trial",
        "study_phase": "12-week intervention phase",
        "total_sample_size": 72, "duration_value": 12, "duration_unit": "weeks",
        "condition_studied": "Overweight and obesity with hyperuricemia (HUA)",
    })

    # The wide manual sheet has: col0=Group, col1=dose value, col2=dose unit,
    # col3=frequency number, col4=frequency unit, col5=design, col6=phase,
    # col7=duration value, col8=duration unit, col9=sample size, col10=gender,
    # then biomarker triplets (value, change, unit).
    # We reconstruct arm-level baseline + change rows.
    cols = list(raw.iloc[1].values)  # row 1 holds parameter names
    biomarkers = [
        (14, "bmi", "kg/m2"), (17, "waist_circumference", "cm"),
        (20, "body_fat", "kg"), (23, "body_muscle", "kg"),
        (26, "total_cholesterol", "mmol/L"), (29, "hdl", "mmol/L"),
        (32, "ldl", "mmol/L"), (35, "triglycerides", "mmol/L"),
        (38, "glucose", "mmol/L"), (41, "hba1c", "%"),
        (44, "fasting_insulin", "uU/ml"), (47, "fasting_c_peptide", "ng/ml"),
        (50, "egfr", "ml/min/1.73m2"), (53, "creatinine", "µmol/L"),
        (56, "urea", "mmol/L"), (59, "alt", "U/L"),
        (62, "ast", "U/L"),
    ]
    arms = {}
    for i, r in data.iterrows():
        group = str(r.iloc[0]).strip()
        if not group or group == "nan":
            continue
        is_orl = "orlistat" in group.lower()
        arm_id = "ARM_ORL_120" if is_orl else "ARM_ORL_PLA"
        if arm_id not in arms:
            arms[arm_id] = {
                "arm_id": arm_id, "study_id": "RCT_ORLISTAT_2024",
                "arm_name": "Orlistat 120mg" if is_orl else "Placebo",
                "intervention_type": "experimental" if is_orl else "placebo",
                "drug_name": "Orlistat" if is_orl else "Placebo",
                "dose_value": float(r.iloc[1]) if pd.notna(r.iloc[1]) else None,
                "dose_unit": str(r.iloc[2]) if pd.notna(r.iloc[2]) else None,
                "frequency_number": float(r.iloc[3]) if pd.notna(r.iloc[3]) else None,
                "frequency_unit": str(r.iloc[4]) if pd.notna(r.iloc[4]) else None,
                "sample_size_allocated": int(r.iloc[9]) if pd.notna(r.iloc[9]) else None,
                "sample_size_analyzed": None,
                "source_page": 3,
            }

        phase = str(r.iloc[6]) if pd.notna(r.iloc[6]) else ""
        tp = "Baseline" if "baseline" in phase.lower() else "12 weeks (Change)"
        for col, name, unit in biomarkers:
            val = r.iloc[col] if col < len(r) else None
            chg = r.iloc[col + 1] if col + 1 < len(r) else None
            u = r.iloc[col + 2] if col + 2 < len(r) else None
            if pd.notna(val):
                doc["Outcomes"].append({
                    "outcome_id": f"OUT_{len(doc['Outcomes'])+1:04d}",
                    "study_id": "RCT_ORLISTAT_2024", "arm_id": arm_id,
                    "domain": "blood_chemistry", "parameter_name": name,
                    "statistical_type": "continuous", "timepoint": tp,
                    "sample_size": int(r.iloc[9]) if pd.notna(r.iloc[9]) else None,
                    "mean": float(val) if pd.notna(val) else None,
                    "sd": None, "change_value": float(chg) if pd.notna(chg) else None,
                    "change_sd": None, "events": None, "total": None,
                    "percentage": None, "unit": str(u) if pd.notna(u) else unit,
                    "effect_measure": None, "effect_value": None, "p_value": None,
                    "source_page": 5 if tp == "Baseline" else 6,
                    "source_location": "Table 1" if tp == "Baseline" else "Table 2",
                    "raw_source_text": "",
                })

    doc["Arms"] = list(arms.values())
    return doc


def main():
    out = ROOT / "outputs/gold"
    out.mkdir(parents=True, exist_ok=True)
    for name, fn in [("RCT_METFORMIN_2012", build_metformin), ("RCT_ORLISTAT_2024", build_orlistat)]:
        doc = fn()
        # assign sequential outcome ids
        for i, o in enumerate(doc["Outcomes"], 1):
            o["outcome_id"] = f"OUT_{i:04d}"
        write_json(doc, out / f"{name}_gold.json")
        n = {e: len(doc[e]) for e in ENTITIES}
        print(name, "->", n)


if __name__ == "__main__":
    main()
