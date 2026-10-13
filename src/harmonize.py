"""Harmonisation: name matching + unit unification across studies (الخطوة 7)."""
from __future__ import annotations

import re
from typing import Any, Iterable

NAME_ALIASES = {
    "bmi": "bmi",
    "body mass index": "bmi",
    "body mass index (bmi)": "bmi",
    "age": "age",
    "mean age": "age",
    "body weight": "body_weight",
    "weight": "body_weight",
    "weight loss": "weight_loss",
    "waist circumference": "waist_circumference",
    "waist circumference reduction": "waist_circumference",
    "wc": "waist_circumference",
    "hba1c": "hba1c",
    "glycated hemoglobin": "hba1c",
    "fasting glucose": "fasting_glucose",
    "fbg": "fasting_glucose",
    "fasting insulin": "fasting_insulin",
    "fins": "fasting_insulin",
    "total cholesterol": "total_cholesterol",
    "tc": "total_cholesterol",
}

UNIT_MAP = {
    "kg/m2": ("kg/m2", 1.0),
    "kg/m^2": ("kg/m2", 1.0),
    "mg/dl": ("mg/dL", 1.0),
    "mmol/l": ("mmol/L", 1.0),
    "umol/l": ("µmol/L", 1.0),
    "µmol/l": ("µmol/L", 1.0),
    "ml/min/1.73m2": ("mL/min/1.73m2", 1.0),
    "uu/ml": ("µU/mL", 1.0),
    "ng/ml": ("ng/mL", 1.0),
    "years": ("years", 1.0),
    "year": ("years", 1.0),
    "months": ("months", 1.0),
    "weeks": ("weeks", 1.0),
    "cm": ("cm", 1.0),
    "kpa": ("kPa", 1.0),
    "u/l": ("U/L", 1.0),
    "db/m": ("dB/m", 1.0),
    "%": ("%", 1.0),
    "kg": ("kg", 1.0),
}


def canonical_name(name: str) -> str:
    if name is None:
        return ""
    n = re.sub(r"\s+", " ", str(name).strip().lower()).rstrip(" .;,")
    return NAME_ALIASES.get(n, n)


def canonical_unit(unit: str) -> tuple[str, float]:
    if unit is None:
        return ("", 1.0)
    key = re.sub(r"\s+", "", str(unit)).strip().lower()
    for alias, (canon, factor) in UNIT_MAP.items():
        if re.sub(r"\s+", "", alias.lower()) == key:
            return (canon, factor)
    return (str(unit), 1.0)


def harmonise(rows: Iterable[dict[str, Any]], *, name_field: str = "parameter_name") -> list[dict[str, Any]]:
    """Return new rows with canonical names/units; log conversions."""
    out = []
    for r in rows:
        r = dict(r)
        if name_field in r and r[name_field] is not None:
            r[f"{name_field}_reported"] = r[name_field]
            r[name_field] = canonical_name(r[name_field])
        if r.get("unit"):
            canon, factor = canonical_unit(r["unit"])
            if canon != r["unit"]:
                r["unit_reported"] = r["unit"]
                r["unit"] = canon
                r["unit_conversion"] = f"standardised to {canon}"
            if factor != 1.0:
                for f in ("value", "mean", "sd", "min_value", "max_value", "effect_value"):
                    if isinstance(r.get(f), (int, float)):
                        r[f] = round(r[f] * factor, 6)
        out.append(r)
    return out
