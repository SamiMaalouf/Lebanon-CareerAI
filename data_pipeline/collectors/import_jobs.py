"""CSV/JSON/Excel import collector for curated Lebanese job postings."""

from __future__ import annotations

import csv
import json
from datetime import date
from pathlib import Path
from typing import Any

REQUIRED_FIELDS = ["job_title", "description"]

COLUMN_ALIASES = {
    "job_title": ["job_title", "title", "position", "role", "job title", "jobname"],
    "company": ["company", "employer", "organization", "organisation", "hiring_organization"],
    "location": ["location", "city", "area", "governorate", "job_location"],
    "description": ["description", "job_description", "details", "body", "text", "content"],
    "requirements": ["requirements", "qualifications", "must_have"],
    "source": ["source", "board", "origin"],
    "source_url": ["source_url", "url", "link", "job_url", "apply_url"],
    "date_posted": ["date_posted", "posted", "posted_date", "date"],
    "collection_date": ["collection_date", "collected_at", "scraped_at"],
    "employment_type": ["employment_type", "job_type", "type"],
    "industry": ["industry", "sector", "category"],
    "education": ["education", "degree"],
    "experience": ["experience", "experience_level"],
    "salary": ["salary", "compensation", "pay"],
    "job_id": ["job_id", "id", "external_id"],
}


def _canonical_key(key: str) -> str | None:
    k = key.strip().lower().replace("-", "_")
    for canon, aliases in COLUMN_ALIASES.items():
        if k in aliases or k == canon:
            return canon
    return None


def _normalize_row(row: dict[str, Any], source: str) -> dict[str, Any]:
    mapped: dict[str, Any] = {}
    for k, v in row.items():
        if k is None:
            continue
        canon = _canonical_key(str(k))
        if not canon:
            continue
        if isinstance(v, str):
            v = v.strip()
        mapped[canon] = v
    for field in REQUIRED_FIELDS:
        if not mapped.get(field):
            raise ValueError(f"Missing required field '{field}' in record: {mapped.get('job_id')}")
    mapped.setdefault("source", source)
    mapped.setdefault("collection_date", date.today().isoformat())
    mapped.setdefault("location", "Lebanon")
    mapped.setdefault("job_id", None)
    if isinstance(mapped.get("languages"), str):
        mapped["languages"] = [x.strip() for x in mapped["languages"].split(",") if x.strip()]
    if not mapped.get("source_url"):
        # allow missing URL but mark
        mapped["source_url"] = None
    return mapped


def load_json(path: str | Path) -> list[dict[str, Any]]:
    data = json.loads(Path(path).read_text(encoding="utf-8"))
    if isinstance(data, dict) and "jobs" in data:
        data = data["jobs"]
    if not isinstance(data, list):
        raise ValueError("JSON must be a list of job objects or {jobs: [...]}")
    return [_normalize_row(row, source=f"json:{Path(path).name}") for row in data]


def load_csv(path: str | Path) -> list[dict[str, Any]]:
    rows: list[dict[str, Any]] = []
    with Path(path).open(encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(_normalize_row(row, source=f"csv:{Path(path).name}"))
    return rows


def load_excel(path: str | Path) -> list[dict[str, Any]]:
    try:
        import openpyxl
    except ImportError as exc:
        raise ImportError("Install openpyxl to import Excel files: pip install openpyxl") from exc
    wb = openpyxl.load_workbook(path, read_only=True, data_only=True)
    ws = wb.active
    rows_iter = ws.iter_rows(values_only=True)
    headers = [str(h).strip() if h is not None else "" for h in next(rows_iter)]
    out: list[dict[str, Any]] = []
    for values in rows_iter:
        raw = {headers[i]: values[i] for i in range(len(headers)) if headers[i]}
        if not any(raw.values()):
            continue
        out.append(_normalize_row(raw, source=f"excel:{Path(path).name}"))
    return out


def load_any(path: str | Path) -> list[dict[str, Any]]:
    p = Path(path)
    suffix = p.suffix.lower()
    if suffix == ".json":
        return load_json(p)
    if suffix == ".csv":
        return load_csv(p)
    if suffix in {".xlsx", ".xlsm"}:
        return load_excel(p)
    raise ValueError(f"Unsupported import format: {suffix}")
