"""Convert a canonical multi-sheet extraction workbook to a flat JSON document
suitable for scoring against gold standard."""
from __future__ import annotations

import argparse
from pathlib import Path

import pandas as pd

from src.io import read_json, write_json, write_workbook

ROOT = Path(__file__).parent.parent


def xlsx_to_doc(xlsx_path: str, study_id: str) -> dict:
    x = pd.ExcelFile(xlsx_path)
    doc = {}
    for sheet in x.sheet_names:
        if sheet == "Flattened_View":
            continue
        df = pd.read_excel(x, sheet_name=sheet)
        # replace NaN with None for clean JSON
        doc[sheet] = df.where(pd.notna(df), None).to_dict(orient="records")
    doc["study_id"] = study_id
    return doc


def main() -> None:
    p = argparse.ArgumentParser()
    p.add_argument("xlsx")
    p.add_argument("--study", required=True)
    args = p.parse_args()
    doc = xlsx_to_doc(args.xlsx, args.study)
    out = ROOT / "outputs" / f"{args.study}_pred.json"
    write_json(doc, out)
    n = {k: len(v) for k, v in doc.items() if k != "study_id"}
    print(f"Converted {args.xlsx} -> {out}")
    print(f"  entities: {n}")


if __name__ == "__main__":
    main()
