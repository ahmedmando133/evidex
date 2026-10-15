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
        try:
            reader = pypdf.PdfReader(self.file_path, strict=False)
            if getattr(reader, "is_encrypted", False):
                try:
                    reader.decrypt("")
                except Exception:
                    pass
            for idx, page in enumerate(reader.pages):
                try:
                    txt = page.extract_text() or ""
                except Exception:
                    txt = ""
                # Clean non-printable characters while preserving newlines
                cleaned = re.sub(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]', '', txt)
                self.pages.append(PDFPage(page_number=idx + 1, text=cleaned))
        except Exception as e:
            print(f"[!] Error loading PDF {self.file_path}: {e}")

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
        - figures_charts (search for Figure, Fig., curves, AUC, PPG time course)
        - methodology_text (search for participants, population, methods)
        """
        sections = {
            "title_abstract": [],
            "methods_eligibility": [],
            "baseline_tables": [],
            "results_tables": [],
            "figures_charts": [],
            "methodology_text": []
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
            if any(k in lower_text for k in ["inclusion criteria", "exclusion criteria", "eligibility", "randomization", "study design", "intervention", "patients and methods", "participants"]):
                sections["methods_eligibility"].append({
                    "page": p.page_number,
                    "text": p.text
                })
                sections["methodology_text"].append({
                    "page": p.page_number,
                    "text": p.text
                })

            # Baseline Table (usually Table 1)
            if "table 1" in lower_text or "baseline characteristics" in lower_text or "demographic" in lower_text or "baseline patient" in lower_text:
                sections["baseline_tables"].append({
                    "page": p.page_number,
                    "text": p.text
                })

            # Results Tables (Table 2, 3, etc.)
            if any(f"table {i}" in lower_text for i in range(2, 15)) or "table" in lower_text or "changes in" in lower_text or "outcomes" in lower_text or "endpoints" in lower_text:
                sections["results_tables"].append({
                    "page": p.page_number,
                    "text": p.text
                })

            # Figures & Curves (Figure 1, 2, AUC, PPG time-course, etc.)
            if any(k in lower_text for k in ["figure", "fig.", "auc", "area under", "time course", "plasma glucose", "concentration-time", "postprandial", "delta", "error bar"]):
                sections["figures_charts"].append({
                    "page": p.page_number,
                    "text": p.text
                })

        return sections

    def extract_methodology_demographics(self) -> Dict[str, Any]:
        """
        Scans Methodology, Eligibility, and Patient Selection text for demographic proportions
        when Table 1 does not explicitly stratify gender or race.
        """
        full_text = self.get_full_text()
        demographics = {
            "male_count": None,
            "male_pct": None,
            "female_count": None,
            "female_pct": None,
            "races": {},
            "raw_text": None
        }

        # 1. Search for gender counts: e.g. "450 men and 550 women"
        m_counts = re.search(r'(\d+)\s*(?:men|males?)\b(?:\s*(?:and|,)\s*(\d+)\s*(?:women|females?))?', full_text, re.I)
        if m_counts:
            demographics["male_count"] = int(m_counts.group(1))
            if m_counts.group(2):
                demographics["female_count"] = int(m_counts.group(2))
            demographics["raw_text"] = m_counts.group(0)

        # 2. Search for female percentage: e.g. "52.3% were female" or "60% women"
        f_pct = re.search(r'(\d+(?:\.\d+)?)\s*%\s*(?:were\s*)?(?:female|women|females)\b', full_text, re.I)
        if f_pct:
            pct_val = float(f_pct.group(1))
            demographics["female_pct"] = pct_val
            demographics["male_pct"] = round(100.0 - pct_val, 1)
            demographics["raw_text"] = f_pct.group(0)

        # 3. Search for male percentage
        m_pct = re.search(r'(\d+(?:\.\d+)?)\s*%\s*(?:were\s*)?(?:male|men|males)\b', full_text, re.I)
        if m_pct and not demographics["male_pct"]:
            pct_val = float(m_pct.group(1))
            demographics["male_pct"] = pct_val
            demographics["female_pct"] = round(100.0 - pct_val, 1)
            demographics["raw_text"] = m_pct.group(0)

        # 4. Search for racial subgroups
        for r_name in ["white", "caucasian", "black", "african american", "asian", "hispanic", "indigenous"]:
            r_match = re.search(rf'(\d+(?:\.\d+)?)\s*%\s*(?:were\s*)?{r_name}', full_text, re.I)
            if r_match:
                demographics["races"][r_name.title()] = float(r_match.group(1))

        return demographics
