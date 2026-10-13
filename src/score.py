"""Field-level scoring of system output against a manual gold standard (الخطوة 6)."""
from __future__ import annotations

import re
import time
from typing import Any, Iterable

from .canonical import IDENTITY_FIELD

# Fields excluded from field-by-field comparison (provenance/audit only)
EXCLUDE_FIELDS = {
    "source_page", "source_location", "raw_source_text", "exact_source_text",
    "provenance_id", "issue_id", "review_required", "comment", "table_caption",
}

# Composite keys used when the id field alone is unstable across annotators.
# Each entry: entity -> tuple of fields that jointly identify a record.
COMPOSITE_KEY = {
    "Outcomes": ("arm_id", "parameter_name", "timepoint", "statistical_type"),
    "Arms": ("study_id", "arm_name"),
    "Eligibility": ("study_id", "criterion_name", "operator"),
    "Provenance": ("target_id", "field_name", "exact_source_text"),
}


def _norm(v: Any) -> Any:
    if v is None:
        return None
    if isinstance(v, str):
        v = v.strip()
        return v if v else None
    if isinstance(v, float):
        return round(v, 4)
    return v


def _canon_name(v: Any) -> Any:
    """Normalise parameter/criterion names for comparison (case, spaces, underscores)."""
    if v is None:
        return None
    s = str(v).strip().lower()
    s = s.replace(" ", "_").replace("-", "_")
    s = re.sub(r"_+", "_", s)
    return s


def _key(record: dict, entity: str) -> tuple:
    ck = COMPOSITE_KEY.get(entity)
    if ck:
        return tuple(_canon_name(record.get(f)) if f in ("parameter_name", "criterion_name", "arm_name") else _norm(record.get(f)) for f in ck)
    idf = IDENTITY_FIELD.get(entity, "study_id")
    return (_norm(record.get(idf)),)


def score_entity(
    gold: Iterable[dict[str, Any]],
    pred: Iterable[dict[str, Any]],
    *,
    entity: str,
) -> dict[str, Any]:
    gold = { _key(r, entity): r for r in gold }
    pred = { _key(r, entity): r for r in pred }

    compare_fields = [
        f for f in (list(next(iter(gold.values())).keys()) if gold else [])
        if f not in EXCLUDE_FIELDS and f not in set(COMPOSITE_KEY.get(entity, ())) | {IDENTITY_FIELD.get(entity, "study_id")}
    ]

    tp = fp = fn = 0
    field_correct = {f: 0 for f in compare_fields}
    field_total = {f: 0 for f in compare_fields}
    missing, extra = [], []

    for key, g in gold.items():
        p = pred.get(key)
        if p is None:
            missing.append(key)
            fn += 1
            continue
        for f in compare_fields:
            field_total[f] += 1
            if _norm(g.get(f)) == _norm(p.get(f)):
                field_correct[f] += 1
                tp += 1
            else:
                fp += 1

    for key in pred:
        if key not in gold:
            extra.append(key)

    precision = tp / (tp + fp) if (tp + fp) else 0.0
    recall = tp / (tp + fn) if (tp + fn) else 0.0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) else 0.0

    return {
        "entity": entity,
        "key_fields": list(COMPOSITE_KEY.get(entity, (IDENTITY_FIELD.get(entity, "study_id"),))),
        "n_gold": len(gold),
        "n_pred": len(pred),
        "precision": round(precision, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
        "missing_records": [list(k) for k in missing[:10]],
        "extra_records": [list(k) for k in extra[:10]],
        "field_accuracy": {
            f: round(field_correct[f] / field_total[f], 4) if field_total[f] else None
            for f in compare_fields
        },
    }


def score_extraction(gold_doc: dict, pred_doc: dict) -> dict[str, Any]:
    results = {}
    for entity in IDENTITY_FIELD:
        g = gold_doc.get(entity) or gold_doc.get(entity.lower()) or []
        p = pred_doc.get(entity) or pred_doc.get(entity.lower()) or []
        if not g:
            continue
        results[entity] = score_entity(g, p, entity=entity)
    return results


class Timer:
    def __enter__(self):
        self.t0 = time.perf_counter()
        return self

    def __exit__(self, *a):
        self.elapsed = round(time.perf_counter() - self.t0, 3)
