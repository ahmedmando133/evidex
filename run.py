"""CLI entry point.

Examples:
    python run.py extract --pdf data/raw/Orlistat.pdf --study RCT_ORLISTAT --backend rules
    python run.py extract-all
    python run.py validate outputs/extraction_RCT_ORLISTAT.json
    python run.py score --gold outputs/gold.json --pred outputs/extraction_RCT_ORLISTAT.json
    python run.py flatten-pdfs
"""
from __future__ import annotations

import argparse
import json
from pathlib import Path

from src.extract import make_backend
from src.harmonize import harmonise
from src.io import read_json, to_rows, write_csv, write_json, write_workbook
from src.score import score_extraction, Timer
from src.validate import validate_document

ROOT = Path(__file__).parent
OUT = ROOT / "outputs"

DEFAULT_PDFS = [
    ("RCT_METFORMIN_DPP", "data/raw/metformin clinical trial.pdf"),
    ("RCT_ORLISTAT", "data/raw/Orlistat.pdf"),
]


def cmd_extract(args) -> None:
    backend = make_backend(args.backend)
    with Timer() as t:
        doc = backend.extract_from_pdf(args.pdf, args.study)
    doc["_meta"] = {"backend": args.backend, "elapsed_seconds": t.elapsed, "pdf": str(args.pdf)}
    raw = OUT / f"extraction_{args.study}.json"
    write_json(doc, raw)
    print(f"[{args.backend}] {args.study}: raw -> {raw}")

    rows = to_rows(doc)
    log = validate_document(doc)
    for entity, r in rows.items():
        if entity == "Outcomes":
            r = harmonise(r, name_field="parameter_name")
        elif entity == "Eligibility":
            r = harmonise(r, name_field="criterion_name")
        write_csv(r, OUT / f"{args.study}_{entity}.csv")
    # Merge validation log into doc
    doc["Validation_Log"] = log
    write_workbook(doc, OUT / f"{args.study}_structured_extracted.xlsx")
    write_json({"study_id": args.study, "log": log}, OUT / f"{args.study}_validation.json")
    n_err = sum(1 for x in log if x["review_required"] == "yes")
    print(f"  entities: " + ", ".join(f"{k}={len(v)}" for k, v in rows.items()))
    print(f"  validation: {len(log)} issue(s), {n_err} requiring review")


def cmd_extract_all(args) -> None:
    for study_id, pdf in DEFAULT_PDFS:
        cmd_extract(argparse.Namespace(pdf=ROOT / pdf, study=study_id, backend=args.backend))


def cmd_validate(args) -> None:
    doc = read_json(args.path)
    log = validate_document(doc)
    write_csv(log, OUT / "validation.csv")
    print(f"{len(log)} issue(s): " + ", ".join(f"{x['issue_type']}:{x['review_required']}" for x in log[:10]))


def cmd_score(args) -> None:
    gold = read_json(args.gold)
    pred = read_json(args.pred)
    res = score_extraction(gold, pred)
    write_json(res, OUT / "score_report.json")
    print(json.dumps(res, ensure_ascii=False, indent=2)[:4000])


def cmd_flatten_pdfs(args) -> None:
    """Flatten raw PDF text into page-delimited text files."""
    out_dir = OUT / "pdf_text"
    out_dir.mkdir(parents=True, exist_ok=True)
    for study_id, pdf in DEFAULT_PDFS:
        from src.io import read_pdf_pages
        pages = read_pdf_pages(ROOT / pdf)
        path = out_dir / f"{study_id}.txt"
        with open(path, "w", encoding="utf-8") as fh:
            for i, p in enumerate(pages, 1):
                fh.write(f"\n----- PAGE {i} -----\n{p}\n")
        print(f"{study_id}: {len(pages)} pages -> {path}")


def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(description="Evidex RCT extraction pipeline")
    sub = p.add_subparsers(dest="cmd", required=True)

    e = sub.add_parser("extract", help="extract one PDF")
    e.add_argument("--pdf", required=True)
    e.add_argument("--study", required=True)
    e.add_argument("--backend", default="rules", choices=["rules", "openai", "anthropic"])
    e.set_defaults(func=cmd_extract)

    ea = sub.add_parser("extract-all", help="extract all default PDFs")
    ea.add_argument("--backend", default="rules", choices=["rules", "openai", "anthropic"])
    ea.set_defaults(func=cmd_extract_all)

    v = sub.add_parser("validate", help="validate a raw extraction JSON")
    v.add_argument("path")
    v.set_defaults(func=cmd_validate)

    s = sub.add_parser("score", help="score against gold standard")
    s.add_argument("--gold", required=True)
    s.add_argument("--pred", required=True)
    s.set_defaults(func=cmd_score)

    fp = sub.add_parser("flatten-pdfs", help="dump PDF text to .txt files")
    fp.set_defaults(func=cmd_flatten_pdfs)

    return p


def main() -> None:
    args = build_parser().parse_args()
    OUT.mkdir(exist_ok=True)
    args.func(args)


if __name__ == "__main__":
    main()
