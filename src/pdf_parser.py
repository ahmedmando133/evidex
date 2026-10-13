"""
PDF parser for extracting page-aware text and section chunks from clinical trial PDFs.
Uses pypdf for extraction with fallback cleaning and heading detection.
"""

import re
from typing import List, Dict, Any, Optional
import pypdf


class PDFPage:
    def __init__(self, page_number: int, text: str):
        self.page_number = page_number
        self.text = text


class PDFDocument:
    def __init__(self, file_path: str):
        self.file_path = file_path
        self.pages: List[PDFPage] = []
        self._load()

    def _load(self):
        reader = pypdf.PdfReader(self.file_path)
        for idx, page in enumerate(reader.pages):
            txt = page.extract_text() or ""
            # Clean non-printable characters while preserving newlines
            cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', txt)
            self.pages.append(PDFPage(page_number=idx + 1, text=cleaned))

    @property
    def total_pages(self) -> int:
        return len(self.pages)

    def get_full_text(self) -> str:
        return "\n\n".join([f"--- PAGE {p.page_number} ---\n{p.text}" for p in self.pages])

    def get_page_text(self, page_number: int) -> str:
        for p in self.pages:
            if p.page_number == page_number:
                return p.text
        return ""

    def search_sections(self) -> Dict[str, List[Dict[str, Any]]]:
        """
        Segments document into functional clinical trial sections:
        - title_abstract (pages 1-2)
        - methods_eligibility (search for inclusion, eligibility, methods)
        - baseline_tables (search for Table 1, baseline characteristics)
        - results_tables (search for Table 2, Table 3, outcomes, endpoints)
        """
        sections = {
            "title_abstract": [],
            "methods_eligibility": [],
            "baseline_tables": [],
            "results_tables": []
        }

        # Page 1 & 2 are almost always title, abstract, introductory design
        for p in self.pages[:2]:
            sections["title_abstract"].append({
                "page": p.page_number,
                "text": p.text
            })

        for p in self.pages:
            lower_text = p.text.lower()
            
            # Methods and Eligibility
            if any(k in lower_text for k in ["inclusion criteria", "eligibility", "randomization", "study design", "intervention", "patients and methods"]):
                sections["methods_eligibility"].append({
                    "page": p.page_number,
                    "text": p.text
                })

            # Baseline Table (usually Table 1)
            if "table 1" in lower_text or "baseline characteristics" in lower_text or "demographic" in lower_text:
                sections["baseline_tables"].append({
                    "page": p.page_number,
                    "text": p.text
                })

            # Results Tables (Table 2, 3, etc.)
            if any(f"table {i}" in lower_text for i in range(2, 6)) or "changes in" in lower_text or "outcomes" in lower_text:
                sections["results_tables"].append({
                    "page": p.page_number,
                    "text": p.text
                })

        return sections
