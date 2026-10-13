"""Single source of truth for the adopted data template.

The column names below match the structured-extraction template already in
use (Studies / Arms / Eligibility / Outcomes / Provenance / Validation_Log /
Flattened_View). `schema/data_dictionary.csv` and `schema/extraction_schema.json`
are GENERATED from this file, so the dictionary, the prompt and the validator
can never drift apart.
"""
from __future__ import annotations

# ---------------------------------------------------------------- entities
ENTITIES: dict[str, list[str]] = {
    "Studies": [
        "study_id", "title", "authors", "publication_year", "journal", "doi",
        "study_design", "study_phase", "total_sample_size", "duration_value",
        "duration_unit", "condition_studied",
    ],
    "Arms": [
        "arm_id", "study_id", "arm_name", "intervention_type", "drug_name",
        "dose_value", "dose_unit", "frequency_number", "frequency_unit",
        "sample_size_allocated", "sample_size_analyzed", "source_page",
    ],
    "Eligibility": [
        "criterion_id", "study_id", "criterion_type", "domain",
        "criterion_name", "operator", "value", "min_value", "max_value",
        "unit", "raw_source_text", "source_page",
    ],
    "Outcomes": [
        "outcome_id", "study_id", "arm_id", "domain", "parameter_name",
        "statistical_type", "timepoint", "sample_size", "mean", "sd",
        "change_value", "change_sd", "events", "total", "percentage", "unit",
        "effect_measure", "effect_value", "p_value", "source_page",
        "source_location", "raw_source_text",
    ],
    "Provenance": [
        "provenance_id", "study_id", "target_entity", "target_id",
        "field_name", "source_page", "source_location", "exact_source_text",
    ],
    "Validation_Log": [
        "issue_id", "study_id", "target_entity", "target_id", "field_name",
        "issue_type", "review_required", "comment",
    ],
    "Flattened_View": [
        "study_id", "arm_name", "intervention_type", "dose", "frequency",
        "sample_size", "timepoint", "parameter_name", "mean_or_events",
        "sd_or_pct", "change", "unit", "source_page", "source_location",
    ],
}

# ------------------------------------------------------- field metadata
# type: string | number | integer | boolean
# unit: canonical unit string or ""
# allowed: list of allowed values or []
FIELD_META: dict[str, dict] = {
    # shared
    "study_id": {"label_ar": "معرّف الدراسة", "type": "string"},
    "title": {"label_ar": "العنوان", "type": "string"},
    "authors": {"label_ar": "المؤلفون", "type": "string"},
    "publication_year": {"label_ar": "سنة النشر", "type": "integer"},
    "journal": {"label_ar": "المجلة", "type": "string"},
    "doi": {"label_ar": "المعرّف الرقمي DOI", "type": "string"},
    "study_design": {"label_ar": "تصميم الدراسة", "type": "string"},
    "study_phase": {"label_ar": "المرحلة", "type": "string"},
    "total_sample_size": {"label_ar": "الحجم الكلي للعينة", "type": "integer"},
    "duration_value": {"label_ar": "قيمة المدة", "type": "number"},
    "duration_unit": {"label_ar": "وحدة المدة", "type": "string", "unit": ""},
    "condition_studied": {"label_ar": "الحالة المدروسة", "type": "string"},
    # arms
    "arm_id": {"label_ar": "معرّف الذراع", "type": "string"},
    "arm_name": {"label_ar": "اسم الذراع", "type": "string"},
    "intervention_type": {"label_ar": "نوع التدخل", "type": "string",
 "allowed": ["experimental", "placebo", "comparator", "control"]},
    "drug_name": {"label_ar": "اسم الدواء", "type": "string"},
    "dose_value": {"label_ar": "قيمة الجرعة", "type": "number"},
    "dose_unit": {"label_ar": "وحدة الجرعة", "type": "string", "unit": ""},
    "frequency_number": {"label_ar": "عدد مرات التكرار", "type": "number"},
    "frequency_unit": {"label_ar": "وحدة التكرار", "type": "string", "unit": ""},
    "sample_size_allocated": {"label_ar": "حجم العينة الموزّع", "type": "integer"},
    "sample_size_analyzed": {"label_ar": "حجم العينة المحلّل", "type": "integer"},
    "source_page": {"label_ar": "رقم الصفحة", "type": "integer"},
    # eligibility
    "criterion_id": {"label_ar": "معرّف المعيار", "type": "string"},
    "criterion_type": {"label_ar": "نوع المعيار", "type": "string", "allowed": ["inclusion", "exclusion"]},
    "domain": {"label_ar": "النطاق", "type": "string"},
    "criterion_name": {"label_ar": "اسم المعيار", "type": "string"},
    "operator": {"label_ar": "المعامل الرياضي", "type": "string", "allowed": ["=", ">", ">=", "<", "<=", "between"]},
    "value": {"label_ar": "القيمة", "type": "number"},
    "min_value": {"label_ar": "الحد الأدنى", "type": "number"},
    "max_value": {"label_ar": "الحد الأقصى", "type": "number"},
    "unit": {"label_ar": "الوحدة", "type": "string", "unit": ""},
    "raw_source_text": {"label_ar": "النص المصدري الحرفي", "type": "string"},
    # outcomes
    "outcome_id": {"label_ar": "معرّف النتيجة", "type": "string"},
    "domain": {"label_ar": "النطاق", "type": "string"},
    "parameter_name": {"label_ar": "اسم المتغير/النتيجة", "type": "string"},
    "statistical_type": {"label_ar": "النوع الإحصائي", "type": "string", "allowed": ["continuous", "dichotomous"]},
    "timepoint": {"label_ar": "النقطة الزمنية", "type": "string"},
    "sample_size": {"label_ar": "حجم العينة", "type": "integer"},
    "mean": {"label_ar": "المتوسط", "type": "number"},
    "sd": {"label_ar": "الانحراف المعياري", "type": "number"},
    "change_value": {"label_ar": "قيمة التغيير", "type": "number"},
    "change_sd": {"label_ar": "الانحراف المعياري للتغيير", "type": "number"},
    "events": {"label_ar": "الأحداث", "type": "integer"},
    "total": {"label_ar": "الإجمالي", "type": "integer"},
    "percentage": {"label_ar": "النسبة المئوية", "type": "number"},
    "effect_measure": {"label_ar": "مقياس الأثر", "type": "string", "allowed": ["MD", "SMD", "RR", "OR", "HR"]},
    "effect_value": {"label_ar": "قيمة الأثر", "type": "number"},
    "p_value": {"label_ar": "قيمة p", "type": "string"},
    "source_location": {"label_ar": "موضع الجدول", "type": "string"},
    # provenance
    "provenance_id": {"label_ar": "معرّف الإسناد", "type": "string"},
    "target_entity": {"label_ar": "الكيان المستهدف", "type": "string", "allowed": list(ENTITIES.keys())},
    "target_id": {"label_ar": "معرّف الكيان المستهدف", "type": "string"},
    "field_name": {"label_ar": "اسم الحقل", "type": "string"},
    "exact_source_text": {"label_ar": "النص المصدري الحرفي", "type": "string"},
    # validation log
    "issue_id": {"label_ar": "معرّف الملاحظة", "type": "string"},
    "issue_type": {"label_ar": "نوع الملاحظة", "type": "string"},
    "review_required": {"label_ar": "يتطلب مراجعة بشرية", "type": "boolean"},
    "comment": {"label_ar": "التعليق", "type": "string"},
    # flattened view (derived)
    "arm_name ": {"label_ar": "اسم الذراع", "type": "string"},
    "intervention_type ": {"label_ar": "نوع التدخل", "type": "string"},
    "dose": {"label_ar": "الجرعة (قيمة + وحدة)", "type": "string"},
    "frequency": {"label_ar": "التكرار", "type": "string"},
    "timepoint ": {"label_ar": "النقطة الزمنية", "type": "string"},
    "mean_or_events": {"label_ar": "المتوسط أو الأحداث", "type": "number"},
    "sd_or_pct": {"label_ar": "الانحراف المعياري أو النسبة", "type": "number"},
    "change": {"label_ar": "التغيير", "type": "number"},
}

# Fields shared between entities -> we keep them explicit above but map the
# flattened-view / duplicate names to their canonical meta via _ALIAS_META.
FIELD_META.update({
    "arm_name": FIELD_META.get("arm_name", {"label_ar": "اسم الذراع", "type": "string"}),
})

REQUIRED = {
    "Studies": ["study_id", "title", "study_design", "total_sample_size"],
    "Arms": ["arm_id", "study_id", "arm_name", "intervention_type"],
    "Eligibility": ["criterion_id", "study_id", "criterion_name", "operator"],
    "Outcomes": ["outcome_id", "study_id", "arm_id", "parameter_name", "timepoint"],
    "Provenance": ["provenance_id", "study_id", "target_entity", "field_name", "source_page", "exact_source_text"],
    "Validation_Log": ["issue_id", "study_id", "target_entity", "field_name", "issue_type"],
}

# Identity field used to match records when scoring against gold standard.
IDENTITY_FIELD = {
    "Studies": "study_id",
    "Arms": "arm_id",
    "Eligibility": "criterion_id",
    "Outcomes": "outcome_id",
    "Provenance": "provenance_id",
    "Validation_Log": "issue_id",
}


def data_dictionary_rows() -> list[dict]:
    rows = []
    for entity, fields in ENTITIES.items():
        for f in fields:
            meta = FIELD_META.get(f, {"label_ar": f, "type": "string"})
            rows.append(
                {
                    "entity": entity,
                    "field": f,
                    "label_en": f,
                    "label_ar": meta["label_ar"],
                    "data_type": meta["type"],
                    "unit": meta.get("unit", ""),
                    "allowed_values": "; ".join(str(a) for a in meta.get("allowed", [])),
                    "operator": "yes" if f == "operator" else "",
                    "required": "yes" if f in REQUIRED.get(entity, []) else "",
                    "description": meta.get("label_ar", ""),
                    "example": "",
                }
            )
    return rows


def json_schema() -> dict:
    type_map = {"string": {"type": ["string", "null"]},
                "number": {"type": ["number", "null"]},
                "integer": {"type": ["integer", "null"]},
                "boolean": {"type": ["boolean", "null"]}}
    props = {}
    for entity, fields in ENTITIES.items():
        p = {}
        for f in fields:
            if f in ("Flattened_View",):
                continue
            meta = FIELD_META.get(f, {"type": "string"})
            d = dict(type_map.get(meta["type"], type_map["string"]))
            allowed = meta.get("allowed")
            if allowed:
                d["enum"] = allowed + [None]
            p[f] = d
        req = [r for r in REQUIRED.get(entity, []) if r in p]
        obj = {"type": "object", "properties": p}
        if req:
            obj["required"] = req
        props[entity.lower()] = {"type": "array", "items": obj}
    return {
        "$schema": "https://json-schema.org/draft/2020-12/schema",
        "title": "RCT structured extraction",
        "description": "Output schema for AI-assisted extraction of facts from one RCT. Return ONLY this JSON, no prose.",
        "type": "object",
        "required": ["studies", "arms", "eligibility", "outcomes", "provenance"],
        "properties": props,
    }
