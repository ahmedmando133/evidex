"""IO helpers: read PDF text, read/write extraction artefacts."""
from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Any, Iterable

ENTITY_SHEET_ORDER = ["Studies", "Arms", "Eligibility", "Outcomes", "Provenance", "Validation_Log"]
ENTITY_JSON_KEY = {e: e.lower() for e in ENTITY_SHEET_ORDER}


def read_pdf_pages(path: str | Path) -> list[str]:
    """Return one string per page using pypdf (pure-python, always available)."""
    from pypdf import PdfReader

    reader = PdfReader(str(path))
    pages: list[str] = []
    for page in reader.pages:
        pages.append(page.extract_text() or "")
    return pages


def read_data_dictionary(path: str | Path) -> list[dict[str, str]]:
    with open(path, encoding="utf-8", newline="") as fh:
        return list(csv.DictReader(fh))


def write_json(data: Any, path: str | Path) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def read_json(path: str | Path) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def write_csv(rows: Iterable[dict[str, Any]], path: str | Path, fieldnames=None) -> None:
    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    rows = list(rows)
    if not rows:
        p.write_text("", encoding="utf-8")
        return
    if fieldnames is None:
        fieldnames = list(rows[0].keys())
    with open(p, "w", encoding="utf-8", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=fieldnames, extrasaction="ignore")
        w.writeheader()
        for r in rows:
            w.writerow({k: _cell(v) for k, v in r.items()})


def _cell(v: Any) -> Any:
    if v is None:
        return ""
    if isinstance(v, bool):
        return "yes" if v else "no"
    if isinstance(v, (int, float)):
        return v
    return str(v)


def write_workbook(doc: dict[str, Any], path: str | Path) -> None:
    """Write the canonical multi-sheet workbook (Studies..Flattened_View)."""
    import pandas as pd

    p = Path(path)
    p.parent.mkdir(parents=True, exist_ok=True)
    with pd.ExcelWriter(p, engine="openpyxl") as writer:
        for entity in ENTITY_SHEET_ORDER:
            rows = doc.get(entity) or doc.get(entity.lower()) or []
            df = pd.DataFrame(rows)
            df.to_excel(writer, sheet_name=entity, index=False)
        flat = build_flattened_view(doc)
        pd.DataFrame(flat).to_excel(writer, sheet_name="Flattened_View", index=False)


def build_flattened_view(doc: dict[str, Any]) -> list[dict[str, Any]]:
    """Derived human-readable view: one row per outcome, joined with arm info."""
    arms = {a.get("arm_id"): a for a in (doc.get("Arms") or doc.get("arms") or [])}
    rows = []
    for o in doc.get("Outcomes") or doc.get("outcomes") or []:
        a = arms.get(o.get("arm_id"), {})
        rows.append(
            {
                "study_id": o.get("study_id"),
                "arm_name": a.get("arm_name"),
                "intervention_type": a.get("intervention_type"),
                "dose": _join([a.get("dose_value"), a.get("dose_unit")]),
                "frequency": _join([a.get("frequency_number"), a.get("frequency_unit")]),
                "sample_size": o.get("sample_size"),
                "timepoint": o.get("timepoint"),
                "parameter_name": o.get("parameter_name"),
                "mean_or_events": o.get("mean") if o.get("statistical_type", "continuous") != "dichotomous" else o.get("events"),
                "sd_or_pct": o.get("sd") if o.get("statistical_type", "continuous") != "dichotomous" else o.get("percentage"),
                "change": o.get("change_value"),
                "unit": o.get("unit"),
                "source_page": o.get("source_page"),
                "source_location": o.get("source_location"),
            }
        )
    return rows


def _join(parts):
    vals = [str(p) for p in parts if p is not None]
    return " ".join(vals) if vals else None


def to_rows(doc: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    """Split an extraction document into per-entity row lists (canonical names)."""
    out: dict[str, list[dict[str, Any]]] = {}
    for entity in ENTITY_SHEET_ORDER:
        out[entity] = [dict(r) for r in (doc.get(entity) or doc.get(entity.lower()) or [])]
    return out
