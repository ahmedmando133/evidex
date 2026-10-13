"""Validation of extracted documents against the canonical schema + cross-field rules."""
from __future__ import annotations

from typing import Any

from .canonical import ENTITIES

OPERATORS = {"=", ">", ">=", "<", "<=", "between"}
INTERVENTION_TYPES = {"experimental", "placebo", "comparator", "control"}
CRITERION_TYPES = {"inclusion", "exclusion"}
STATISTICAL_TYPES = {"continuous", "dichotomous"}
EFFECT_MEASURES = {"MD", "SMD", "RR", "OR", "HR"}


def validate_document(doc: dict[str, Any]) -> list[dict[str, str]]:
    """Return a list of validation issues (Validation_Log rows)."""
    log: list[dict[str, str]] = []

    def add(rid: str, entity: str, field: str, issue_type: str, comment: str, severity: str = "error") -> None:
        log.append(
            {
                "issue_id": f"ISS_{len(log)+1:04d}",
                "study_id": doc.get("study_id", ""),
                "target_entity": entity,
                "target_id": rid or "",
                "field_name": field,
                "issue_type": issue_type,
                "review_required": "yes" if severity == "error" else "no",
                "comment": comment,
            }
        )

    study_id = doc.get("study_id", "")

    # Studies
    for s in doc.get("Studies", []) or []:
        rid = s.get("study_id", study_id)
        if s.get("total_sample_size") is not None and (not isinstance(s["total_sample_size"], int) or s["total_sample_size"] <= 0):
            add(rid, "Studies", "total_sample_size", "type_match", f"must be positive integer, got {s['total_sample_size']!r}")
        if s.get("publication_year") is not None and not isinstance(s["publication_year"], int):
            add(rid, "Studies", "publication_year", "type_match", "must be integer or null")

    # Arms
    arm_ids = set()
    for a in doc.get("Arms", []) or []:
        rid = a.get("arm_id", "")
        arm_ids.add(rid)
        if a.get("intervention_type") not in INTERVENTION_TYPES:
            add(rid, "Arms", "intervention_type", "enum", f"not allowed: {a.get('intervention_type')!r}")
        if a.get("dose_value") is None and (a.get("dose_unit") or a.get("frequency_number")):
            add(rid, "Arms", "dose_value", "atomic", "dose_unit/frequency present without dose_value", "warning")

    # Eligibility
    for e in doc.get("Eligibility", []) or []:
        rid = e.get("criterion_id", "")
        op = e.get("operator")
        if op not in OPERATORS:
            add(rid, "Eligibility", "operator", "enum", f"not in vocabulary: {op!r}")
            continue
        if op == "between":
            if e.get("min_value") is None or e.get("max_value") is None:
                add(rid, "Eligibility", "min_value", "range", "operator='between' requires min_value and max_value")
            elif e["min_value"] > e["max_value"]:
                add(rid, "Eligibility", "min_value", "range", f"min {e['min_value']} > max {e['max_value']}")
        elif e.get("value") is None:
            add(rid, "Eligibility", "value", "value", f"operator={op!r} but no value", "warning")

    # Outcomes
    for o in doc.get("Outcomes", []) or []:
        rid = o.get("outcome_id", "")
        if o.get("statistical_type") not in STATISTICAL_TYPES:
            add(rid, "Outcomes", "statistical_type", "enum", f"not allowed: {o.get('statistical_type')!r}")
        if o.get("effect_measure") and o.get("effect_measure") not in EFFECT_MEASURES:
            add(rid, "Outcomes", "effect_measure", "enum", f"not allowed: {o.get('effect_measure')!r}")
        if o.get("events") is not None and o.get("total") is not None and o["events"] > o["total"]:
            add(rid, "Outcomes", "events", "events", f"events {o['events']} > total {o['total']}")
        if o.get("sd") is not None and o["sd"] < 0:
            add(rid, "Outcomes", "sd", "sd", "SD cannot be negative")
        if o.get("arm_id") and o["arm_id"] not in arm_ids:
            add(rid, "Outcomes", "arm_id", "reference", f"references unknown arm_id {o['arm_id']!r}")

    # Provenance
    for p in doc.get("Provenance", []) or []:
        rid = p.get("provenance_id", "")
        if not p.get("exact_source_text") or not str(p.get("exact_source_text", "")).strip():
            add(rid, "Provenance", "exact_source_text", "provenance", "missing exact_source_text", "warning")
        if p.get("source_page") is None:
            add(rid, "Provenance", "source_page", "provenance", "missing source_page", "warning")

    # Study ID consistency
    for entity in ENTITIES:
        for r in doc.get(entity, []) or []:
            if entity == "Validation_Log":
                continue
            if r.get("study_id") and r["study_id"] != study_id:
                add(r.get("study_id", ""), entity, "study_id", "reference", f"study_id mismatch: {r['study_id']!r} != {study_id!r}")
                break  # one per entity is enough

    return log


def is_clean(log: list[dict[str, str]]) -> bool:
    return not any(x["issue_type"] == "error" or x["review_required"] == "yes" for x in log)
