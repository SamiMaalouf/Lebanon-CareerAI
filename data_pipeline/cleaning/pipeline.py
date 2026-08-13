from __future__ import annotations

import hashlib
import re
from typing import Any

from bs4 import BeautifulSoup

from data_pipeline.cleaning.company import resolve_company
from data_pipeline.taxonomy.loader import SkillTaxonomy, load_taxonomy

BOILERPLATE_PATTERNS = [
    r"we are an equal opportunity employer.*?$",
    r"all qualified applicants.*?$",
    r"please send your cv.*?$",
    r"only shortlisted candidates.*?$",
    r"confidentiality is guaranteed.*?$",
]

REQUIREMENT_HEADERS = re.compile(
    r"(?i)\b(requirements?|qualifications?|must have|you (will|should) have|"
    r"what (we|you).{0,20}need|skills (required|needed)|job requirements)\b"
)


def strip_html(text: str) -> str:
    if not text:
        return ""
    if "<" in text and ">" in text:
        soup = BeautifulSoup(text, "lxml")
        return soup.get_text(separator=" ")
    return text


def normalize_whitespace(text: str) -> str:
    text = text.replace("\xa0", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def apply_abbreviations(text: str, taxonomy: SkillTaxonomy | None = None) -> str:
    tax = taxonomy or load_taxonomy()
    out = text
    # word-boundary replacements for known abbreviations
    for abbr, expansion in sorted(tax.abbreviations.items(), key=lambda x: -len(x[0])):
        out = re.sub(rf"\b{re.escape(abbr)}\b", expansion, out, flags=re.IGNORECASE)
    return out


def remove_boilerplate(text: str) -> str:
    out = text
    for pat in BOILERPLATE_PATTERNS:
        out = re.sub(pat, " ", out, flags=re.IGNORECASE | re.DOTALL)
    return normalize_whitespace(out)


def split_description_requirements(text: str) -> tuple[str, str]:
    match = REQUIREMENT_HEADERS.search(text)
    if not match:
        return text, ""
    desc = text[: match.start()].strip()
    reqs = text[match.start() :].strip()
    return desc, reqs


def content_hash(title: str, company: str | None, description: str | None) -> str:
    blob = f"{(title or '').lower()}|{(company or '').lower()}|{(description or '')[:800].lower()}"
    return hashlib.sha256(blob.encode("utf-8")).hexdigest()[:16]


def clean_job(record: dict[str, Any], taxonomy: SkillTaxonomy | None = None) -> dict[str, Any]:
    """Clean a raw job record while preserving original raw_text."""
    tax = taxonomy or load_taxonomy()
    raw_parts = [
        record.get("job_title") or "",
        record.get("description") or "",
        record.get("requirements") or "",
        record.get("preferred_skills") or "",
    ]
    raw_text = record.get("raw_text") or "\n".join(p for p in raw_parts if p)

    cleaned = strip_html(raw_text)
    cleaned = normalize_whitespace(cleaned)
    cleaned = apply_abbreviations(cleaned, tax)
    cleaned = remove_boilerplate(cleaned)

    desc = strip_html(record.get("description") or "")
    reqs = strip_html(record.get("requirements") or "")
    if not reqs and desc:
        desc, reqs = split_description_requirements(desc)
    elif not desc and cleaned:
        desc, reqs = split_description_requirements(cleaned)

    desc = normalize_whitespace(apply_abbreviations(desc, tax))
    reqs = normalize_whitespace(apply_abbreviations(reqs, tax))

    out = dict(record)
    out["raw_text"] = raw_text
    out["cleaned_text"] = cleaned
    out["description"] = desc or cleaned
    out["requirements"] = reqs or record.get("requirements")
    out["company"] = resolve_company(out.get("company"), desc or cleaned)
    out["dedupe_hash"] = content_hash(
        out.get("job_title") or "",
        out.get("company"),
        out.get("description"),
    )
    return out


def deduplicate_jobs(jobs: list[dict[str, Any]]) -> list[dict[str, Any]]:
    seen: set[str] = set()
    unique: list[dict[str, Any]] = []
    for job in jobs:
        h = job.get("dedupe_hash") or content_hash(
            job.get("job_title") or "",
            job.get("company"),
            job.get("description"),
        )
        if h in seen:
            continue
        seen.add(h)
        unique.append(job)
    return unique
