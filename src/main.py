"""
Main execution CLI for the RCT Data Extraction Pipeline.
Usage:
    python src/main.py --input data/raw/Orlistat.pdf --output outputs/orlistat_extracted.xlsx
    python src/main.py --all
"""

import os
import sys
import argparse

# Ensure safe console output on Windows
if sys.stdout.encoding != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Add workspace to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.extractor import RCTExtractor
from src.exporter import ExcelTrialExporter


def process_single_trial(pdf_path: str, output_path: str):
    print(f"\n=======================================================")
    print(f"[*] Processing Clinical Trial PDF: {pdf_path}")
    print(f"=======================================================")
    
    if not os.path.exists(pdf_path):
        print(f"[-] Error: File not found: {pdf_path}")
        return

    # 1. Extraction
    extractor = RCTExtractor(pdf_path)
    data = extractor.extract_all()
    
    print(f"[+] Extraction complete for Study ID: {data.study.study_id}")
    print(f"    - Title: {data.study.title[:60]}...")
    print(f"    - Treatment Arms: {len(data.arms)}")
    print(f"    - Eligibility Criteria: {len(data.eligibility)}")
    print(f"    - Clinical Outcomes: {len(data.outcomes)}")
    print(f"    - Provenance Citations: {len(data.provenance)}")
    print(f"    - Validation Issues Flagged: {len(data.validation_log)}")

    # 2. Export
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    exporter = ExcelTrialExporter(data)
    saved_path = exporter.export(output_path)
    print(f"[OK] Saved formatted Excel to: {saved_path}")
    return data


def main():
    parser = argparse.ArgumentParser(description="AI-assisted Structured RCT Extraction Pipeline")
    parser.add_argument("--input", type=str, help="Path to input trial PDF")
    parser.add_argument("--output", type=str, help="Path to output Excel file")
    parser.add_argument("--all", action="store_true", help="Process all PDFs in data/raw/")
    args = parser.parse_args()

    if args.all or (not args.input and not args.output):
        trials = [
            ("data/raw/Orlistat.pdf", "outputs/orlistat_structured_extracted.xlsx"),
            ("data/raw/metformin clinical trial.pdf", "outputs/metformin_structured_extracted.xlsx"),
            ("data/raw/semaglutide trial.pdf", "outputs/semaglutide_structured_extracted.xlsx")
        ]
        for pdf, out in trials:
            process_single_trial(pdf, out)
    else:
        out = args.output or f"outputs/{os.path.splitext(os.path.basename(args.input))[0]}_extracted.xlsx"
        process_single_trial(args.input, out)


if __name__ == "__main__":
    main()
