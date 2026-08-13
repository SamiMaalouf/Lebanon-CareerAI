"""Best-effort HireLebanese collector (robots.txt missing — cautious rate limits)."""

from __future__ import annotations

import re
from typing import Any

from bs4 import BeautifulSoup

from data_pipeline.cleaning.company import clean_company, infer_company_from_text
from data_pipeline.collectors.base import EthicalClient, base_record, write_collection
from data_pipeline.collectors.quality import is_usable_job

LIST_TEMPLATES = [
    "https://www.hirelebanese.com/searchresults.aspx?top=0&order=date&location=Lebanon&pg={page}",
    "https://www.hirelebanese.com/searchresults.aspx?top=0&order=date&location=Lebanon+-+Beirut&pg={page}",
    "https://www.hirelebanese.com/searchresults.aspx?top=0&order=date&location=Lebanon&keywords=engineer&pg={page}",
    "https://www.hirelebanese.com/searchresults.aspx?top=0&order=date&location=Lebanon&keywords=engineering&pg={page}",
    "https://www.hirelebanese.com/searchresults.aspx?top=0&order=date&location=Lebanon&keywords=software&pg={page}",
    "https://www.hirelebanese.com/searchresults.aspx?top=0&order=date&location=Lebanon&keywords=developer&pg={page}",
    "https://www.hirelebanese.com/searchresults.aspx?top=0&order=date&location=Lebanon&keywords=internship&pg={page}",
    "https://www.hirelebanese.com/searchresults.aspx?top=0&order=date&location=Lebanon&keywords=mechanical&pg={page}",
    "https://www.hirelebanese.com/searchresults.aspx?top=0&order=date&location=Lebanon&keywords=electrical&pg={page}",
    "https://www.hirelebanese.com/searchresults.aspx?top=0&order=date&location=Lebanon&keywords=civil&pg={page}",
    "https://www.hirelebanese.com/searchresults.aspx?top=0&order=date&location=Lebanon&keywords=mechatronics&pg={page}",
    "https://www.hirelebanese.com/searchresults.aspx?top=0&order=date&location=Lebanon&keywords=automation&pg={page}",
    "https://www.hirelebanese.com/searchresults.aspx?top=0&order=date&location=Lebanon&keywords=architect&pg={page}",
    "https://www.hirelebanese.com/searchresults.aspx?top=0&order=date&location=Lebanon&keywords=technician&pg={page}",
    "https://www.hirelebanese.com/searchresults.aspx?top=0&order=date&location=Lebanon&keywords=devops&pg={page}",
    "https://www.hirelebanese.com/searchresults.aspx?top=0&order=date&location=Lebanon&keywords=java&pg={page}",
    "https://www.hirelebanese.com/searchresults.aspx?top=0&order=date&location=Lebanon&keywords=python&pg={page}",
    "https://www.hirelebanese.com/searchresults.aspx?top=0&order=date&location=Lebanon&keywords=plc&pg={page}",
    "https://www.hirelebanese.com/searchresults.aspx?top=0&order=date&location=Lebanon&keywords=autocad&pg={page}",
    "https://www.hirelebanese.com/searchresults.aspx?top=0&order=date&location=Lebanon&keywords=full+stack&pg={page}",
    "https://www.hirelebanese.com/searchresults.aspx?top=0&order=date&location=Lebanon&keywords=computer+engineering&pg={page}",
    "https://www.hirelebanese.com/searchresults.aspx?top=0&order=date&location=Lebanon&keywords=embedded&pg={page}",
    "https://www.hirelebanese.com/searchresults.aspx?top=0&order=date&location=Lebanon&keywords=firmware&pg={page}",
    "https://www.hirelebanese.com/searchresults.aspx?top=0&order=date&location=Lebanon&keywords=cce&pg={page}",
    "https://www.hirelebanese.com/searchresults.aspx?top=0&order=date&location=Lebanon&keywords=fpga&pg={page}",
]
CE_LIST_TEMPLATES = [
    "https://www.hirelebanese.com/searchresults.aspx?top=0&order=date&location=Lebanon&keywords=computer+engineering&pg={page}",
    "https://www.hirelebanese.com/searchresults.aspx?top=0&order=date&location=Lebanon&keywords=embedded&pg={page}",
    "https://www.hirelebanese.com/searchresults.aspx?top=0&order=date&location=Lebanon&keywords=firmware&pg={page}",
    "https://www.hirelebanese.com/searchresults.aspx?top=0&order=date&location=Lebanon&keywords=cce&pg={page}",
    "https://www.hirelebanese.com/searchresults.aspx?top=0&order=date&location=Lebanon&keywords=fpga&pg={page}",
]
DETAIL_URL = "https://www.hirelebanese.com/jobdetails.aspx?id={job_id}"

JUNK_TITLE_FRAGMENTS = (
    "toggle navigation",
    "job details",
    "find jobs",
    "browse jobs",
    "advanced job search",
)


def _list_ids(
    client: EthicalClient,
    max_pages: int = 40,
    templates: list[str] | None = None,
) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    for template in templates or LIST_TEMPLATES:
        empty_streak = 0
        for page in range(1, max_pages + 1):
            html = client.fetch(template.format(page=page), force=True)
            if not html:
                empty_streak += 1
                if empty_streak >= 2:
                    break
                continue
            ids = re.findall(r"jobdetails\.aspx\?id=(\d+)", html, flags=re.I)
            new = 0
            for jid in ids:
                if jid not in seen:
                    seen.add(jid)
                    ordered.append(jid)
                    new += 1
            label = "kw" if "keywords=" in template else ("Beirut" if "Beirut" in template else "Lebanon")
            print(f"[hirelebanese] {label} page {page}: +{new} (total {len(ordered)})")
            # Keyword queries usually have fewer pages
            page_cap = 12 if "keywords=" in template else max_pages
            if page >= page_cap:
                break
            if new == 0:
                empty_streak += 1
                if empty_streak >= 2:
                    break
            else:
                empty_streak = 0
    return ordered


def _field_map(soup: BeautifulSoup) -> dict[str, str]:
    text = soup.get_text("\n", strip=True)
    lines = [ln.strip() for ln in text.splitlines() if ln.strip()]
    mapping: dict[str, str] = {}
    labels = {
        "Company:",
        "Job Type:",
        "Location:",
        "Date Posted:",
        "Salary:",
        "Employee Type:",
        "Gender:",
    }
    for i, line in enumerate(lines):
        if line not in labels or i + 1 >= len(lines):
            continue
        key = line[:-1]
        if key == "Company":
            mapping[key] = ""
            for nxt in lines[i + 1 : i + 6]:
                if nxt in labels:
                    break
                cleaned = clean_company(nxt)
                if cleaned:
                    mapping[key] = cleaned
                    break
            continue
        mapping[key] = lines[i + 1]
    title = None
    if "Apply Now" in lines:
        idx = lines.index("Apply Now")
        for j in range(idx - 1, -1, -1):
            cand = lines[j]
            if cand.lower() in {
                "job details",
                "login",
                "toggle navigation",
                "find jobs",
                "browse jobs",
                "advanced job search",
                "job seekers",
                "employers",
                "recruiting services",
                "contact us",
            }:
                continue
            if len(cand) >= 3:
                title = cand
                break
    if title:
        mapping["Title"] = title

    if "Description" in lines:
        start = lines.index("Description") + 1
        end = len(lines)
        end_candidates = []
        for stop in ("Company Profile", "Privacy Policy", "Hirelebanese"):
            if stop in lines[start:]:
                end_candidates.append(start + lines[start:].index(stop))
        if end_candidates:
            end = min(end_candidates)
        mapping["Description"] = "\n".join(lines[start:end]).strip()
    return mapping


def _parse_detail(job_id: str, html: str) -> dict[str, Any] | None:
    soup = BeautifulSoup(html, "lxml")
    fields = _field_map(soup)
    title = fields.get("Title")
    desc = fields.get("Description") or ""
    location = fields.get("Location") or ""
    if not title or any(j in title.lower() for j in JUNK_TITLE_FRAGMENTS):
        return None
    if len(desc) < 80:
        return None
    loc_l = location.lower()
    if loc_l and "lebanon" not in loc_l and loc_l not in {"lb"}:
        if "lebanon" not in desc.lower()[:800]:
            return None
    rec = base_record(
        source="hirelebanese",
        source_url=DETAIL_URL.format(job_id=job_id),
        job_id=f"hl_{job_id}",
        job_title=title[:300],
        company=clean_company(fields.get("Company")) or infer_company_from_text(desc),
        location=location or "Lebanon",
        date_posted=_normalize_date(fields.get("Date Posted")),
        employment_type=fields.get("Employee Type") or fields.get("Job Type"),
        industry=fields.get("Job Type"),
        salary=fields.get("Salary"),
        description=desc[:20000],
    )
    ok, _reason = is_usable_job(rec, min_description=80)
    return rec if ok else None


def _normalize_date(value: str | None) -> str | None:
    if not value:
        return None
    try:
        from datetime import datetime

        return datetime.strptime(value.strip(), "%b %d, %Y").date().isoformat()
    except Exception:
        return None


def collect(
    max_jobs: int = 1000,
    max_list_pages: int = 40,
    templates: list[str] | None = None,
    save: bool = True,
) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    with EthicalClient(delay_sec=1.6, allow_missing_robots=True) as client:
        ids = _list_ids(client, max_pages=max_list_pages, templates=templates)
        print(f"[hirelebanese] unique listing ids: {len(ids)}")
        for jid in ids:
            if len(jobs) >= max_jobs:
                break
            html = client.fetch(DETAIL_URL.format(job_id=jid), force=True)
            if not html:
                continue
            client.save_raw("hirelebanese", f"job_{jid}.html", html)
            rec = _parse_detail(jid, html)
            if rec:
                jobs.append(rec)
                if len(jobs) % 50 == 0:
                    print(f"[hirelebanese] collected {len(jobs)}")
    if save:
        write_collection("hirelebanese", jobs)
    return jobs


if __name__ == "__main__":
    collect(max_jobs=50, max_list_pages=2)
