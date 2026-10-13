"""Extraction backends.

`rules`     : deterministic, offline heuristics (always available).
`openai`     : OpenAI-compatible chat completions with structured output.
`anthropic`  : Anthropic Messages API.

All backends return a document matching schema/extraction_schema.json.
"""
from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any

from .io import read_pdf_pages
from .canonical import ENTITIES, json_schema

PROMPT_PATH = "prompts/extract_rct.md"
SCHEMA_PATH = "schema/extraction_schema.json"
DICT_PATH = "schema/data_dictionary.csv"

RE_YEAR = re.compile(r"\b(19|20)\d{2}\b")
RE_RANDOMISED = re.compile(r"randomi[sz]ed|randomly assigned", re.I)
RE_PHASE = re.compile(r"phase\s*(I{1,3}V?|IV|[1-4])\b", re.I)
RE_BETWEEN = re.compile(r"(\d+(?:\.\d+)?)\s*(?:-|–|to|and)\s*(\d+(?:\.\d+)?)\s*(years?|months?|weeks?|kg/m2|kg)?", re.I)
RE_GE = re.compile(r"(?:>|≥|>=)\s*=?\s*(\d+(?:\.\d+)?)\s*(years?|months?|weeks?)?", re.I)
RE_LE = re.compile(r"(?:<|≤|<=)\s*=?\s*(\d+(?:\.\d+)?)\s*(years?|months?|weeks?)?", re.I)
RE_MEAN_SD = re.compile(r"(\d+(?:\.\d+)?)\s*(?:\u00b1|\+/-|\+\/-)\s*(\d+(?:\.\d+)?)")
RE_P = re.compile(r"p\s*[<>=≤≥]\s*(0?\.\d+|\d+(?:\.\d+)?)")
RE_CI = re.compile(r"(95%\s*CI|CI)?\s*\[?\s*(-?\d+(?:\.\d+)?)\s*,\s*(-?\d+(?:\.\d+)?)\s*\]?")


def _init_doc(study_id: str) -> dict[str, Any]:
    return {e: [] for e in ENTITIES}


def _counter():
    n = 0
    while True:
        n += 1
        yield n


class RulesBackend:
    """Offline deterministic extractor. Baseline + smoke tests, not the target system."""

    name = "rules"

    def extract_from_pdf(self, pdf_path: str, study_id: str) -> dict[str, Any]:
        pages = read_pdf_pages(pdf_path)
        doc = _init_doc(study_id)
        ctr = _counter()

        def rid(prefix: str) -> str:
            return f"{prefix}_{next(ctr):04d}"

        full = "\n".join(pages)
        year_m = RE_YEAR.search(full)
        doc["Studies"].append({
            "study_id": study_id,
            "title": None,
            "authors": None,
            "publication_year": int(year_m.group(0)) if year_m else None,
            "journal": None,
            "doi": None,
            "study_design": "RCT" if RE_RANDOMISED.search(full) else None,
            "study_phase": self._phase(full),
            "total_sample_size": None,
            "duration_value": None,
            "duration_unit": None,
            "condition_studied": None,
        })

        for pi, text in enumerate(pages, start=1):
            self._extract_eligibility(doc, study_id, text, pi, rid)
            self._extract_outcomes(doc, study_id, text, pi, rid)

        return doc

    @staticmethod
    def _phase(text):
        m = RE_PHASE.search(text)
        return f"Phase {m.group(1).upper()}" if m else None

    def _prov(self, doc, page, text, rid):
        return {
            "provenance_id": rid("PROV"),
            "study_id": doc["Studies"][0]["study_id"],
            "target_entity": "Studies",
            "target_id": doc["Studies"][0]["study_id"],
            "field_name": "raw_source_text",
            "source_page": page,
            "source_location": None,
            "exact_source_text": text.strip()[:300],
        }

    def _extract_eligibility(self, doc, study_id, text, page, rid):
        for m in re.finditer(r"(?:aged?|age|ages)\s+(.{0,60})", text, re.I):
            frag = m.group(0) + " " + m.group(1)
            bm = RE_BETWEEN.search(frag)
            gm = RE_GE.search(frag)
            lm = RE_LE.search(frag)
            prov = self._prov(doc, page, frag, rid)
            doc["Provenance"].append(prov)
            if bm:
                doc["Eligibility"].append({
                    "criterion_id": rid("ELIG"),
                    "study_id": study_id,
                    "criterion_type": "inclusion",
                    "domain": "demographic",
                    "criterion_name": "age",
                    "operator": "between",
                    "value": None,
                    "min_value": float(bm.group(1)),
                    "max_value": float(bm.group(2)),
                    "unit": bm.group(3) or "years",
                    "raw_source_text": frag.strip(),
                    "source_page": page,
                })
            elif gm:
                doc["Eligibility"].append({
                    "criterion_id": rid("ELIG"),
                    "study_id": study_id,
                    "criterion_type": "inclusion",
                    "domain": "demographic",
                    "criterion_name": "age",
                    "operator": ">=",
                    "value": float(gm.group(1)),
                    "min_value": None,
                    "max_value": None,
                    "unit": gm.group(2) or "years",
                    "raw_source_text": frag.strip(),
                    "source_page": page,
                })
            elif lm:
                doc["Eligibility"].append({
                    "criterion_id": rid("ELIG"),
                    "study_id": study_id,
                    "criterion_type": "inclusion",
                    "domain": "demographic",
                    "criterion_name": "age",
                    "operator": "<=",
                    "value": float(lm.group(1)),
                    "min_value": None,
                    "max_value": None,
                    "unit": lm.group(2) or "years",
                    "raw_source_text": frag.strip(),
                    "source_page": page,
                })

    def _extract_outcomes(self, doc, study_id, text, page, rid):
        for m in RE_MEAN_SD.finditer(text):
            ls = text.rfind("\n", 0, m.start()) + 1
            le = text.find("\n", m.end())
            line = text[ls: le if le != -1 else len(text)]
            prov = self._prov(doc, page, line, rid)
            doc["Provenance"].append(prov)
            doc["Outcomes"].append({
                "outcome_id": rid("OUT"),
                "study_id": study_id,
                "arm_id": None,
                "domain": None,
                "parameter_name": None,
                "statistical_type": "continuous",
                "timepoint": None,
                "sample_size": None,
                "mean": float(m.group(1)),
                "sd": float(m.group(2)),
                "change_value": None,
                "change_sd": None,
                "events": None,
                "total": None,
                "percentage": None,
                "unit": None,
                "effect_measure": None,
                "effect_value": None,
                "p_value": None,
                "source_page": page,
                "source_location": None,
                "raw_source_text": line.strip(),
            })


class OpenAIBackend:
    name = "openai"

    def __init__(self, model: str | None = None, base_url: str | None = None):
        from openai import OpenAI
        self.client = OpenAI(
            api_key=os.environ.get("OPENAI_API_KEY"),
            base_url=base_url or os.environ.get("OPENAI_BASE_URL"),
        )
        self.model = model or os.environ.get("OPENAI_MODEL", "gpt-4o-mini")

    def extract_from_pdf(self, pdf_path: str, study_id: str) -> dict[str, Any]:
        pages = read_pdf_pages(pdf_path)
        prompt = self._render(pages, study_id)
        resp = self.client.chat.completions.create(
            model=self.model,
            temperature=0,
            response_format={"type": "json_object"},
            messages=[{"role": "user", "content": prompt}],
        )
        data = json.loads(resp.choices[0].message.content)
        # Normalise keys to canonical entity names
        return _normalise_doc(data, study_id)

    @staticmethod
    def _render(pages, study_id) -> str:
        root = Path(".")
        tmpl = (root / PROMPT_PATH).read_text(encoding="utf-8")
        schema = (root / SCHEMA_PATH).read_text(encoding="utf-8")
        dict_txt = (root / DICT_PATH).read_text(encoding="utf-8")
        few = json.dumps({"studies": [{"study_id": study_id, "title": "EXAMPLE", "condition": "EXAMPLE", "study_design": "RCT", "n_total": 100}]}, ensure_ascii=False)
        chunks = "".join(f"\n----- PAGE {i} -----\n{p}" for i, p in enumerate(pages, 1))
        return (tmpl.replace("{study_id}", study_id).replace("{data_dictionary}", dict_txt)
                .replace("{schema}", schema).replace("{few_shot}", few)
                .replace("{page}", "1").replace("{page_text}", chunks))


class AnthropicBackend:
    name = "anthropic"

    def __init__(self, model: str | None = None):
        import anthropic
        self.client = anthropic.Anthropic(api_key=os.environ.get("ANTHROPIC_API_KEY"))
        self.model = model or os.environ.get("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest")

    def extract_from_pdf(self, pdf_path: str, study_id: str) -> dict[str, Any]:
        pages = read_pdf_pages(pdf_path)
        root = Path(".")
        tmpl = (root / PROMPT_PATH).read_text(encoding="utf-8")
        schema = (root / SCHEMA_PATH).read_text(encoding="utf-8")
        dict_txt = (root / DICT_PATH).read_text(encoding="utf-8")
        prompt = (tmpl.replace("{study_id}", study_id).replace("{data_dictionary}", dict_txt)
                  .replace("{schema}", schema).replace("{few_shot}", "{}")
                  .replace("{page}", "1").replace("{page_text}", "\n".join(f"\n----- PAGE {i} -----\n{p}" for i, p in enumerate(pages, 1))))
        msg = self.client.messages.create(
            model=self.model, max_tokens=8192, temperature=0,
            messages=[{"role": "user", "content": prompt}],
        )
        text = "".join(getattr(b, "text", "") for b in msg.content)
        data = json.loads(text)
        return _normalise_doc(data, study_id)


def _normalise_doc(data: dict, study_id: str) -> dict[str, Any]:
    """Map lowercase entity keys from LLM output to canonical names."""
    doc = _init_doc(study_id)
    for entity in ENTITIES:
        key = entity.lower()
        if key in data:
            doc[entity] = data[key]
    return doc


def make_backend(name: str, **kw):
    if name == "rules":
        return RulesBackend()
    if name == "openai":
        return OpenAIBackend(**kw)
    if name == "anthropic":
        return AnthropicBackend(**kw)
    raise ValueError(f"unknown backend: {name}")
