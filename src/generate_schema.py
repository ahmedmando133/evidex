"""Generate schema/data_dictionary.csv and schema/extraction_schema.json
from the single source of truth (src/canonical.py)."""
import csv
import json
from pathlib import Path

from src.canonical import data_dictionary_rows, json_schema

ROOT = Path(__file__).parent


def main():
    schema_dir = ROOT / "schema"
    schema_dir.mkdir(exist_ok=True)

    # data_dictionary.csv
    rows = data_dictionary_rows()
    with open(schema_dir / "data_dictionary.csv", "w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    # extraction_schema.json
    with open(schema_dir / "extraction_schema.json", "w", encoding="utf-8") as fh:
        json.dump(json_schema(), fh, ensure_ascii=False, indent=2)
        fh.write("\n")

    print(f"Generated {len(rows)} dictionary rows and JSON schema")


if __name__ == "__main__":
    main()
