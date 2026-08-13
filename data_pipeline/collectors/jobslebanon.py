"""Collector for JobsLebanon (robots allow public pages; skip /api and /auth)."""

from __future__ import annotations

import json
import re
from typing import Any
from urllib.parse import urlparse

from bs4 import BeautifulSoup

from data_pipeline.collectors.base import EthicalClient, base_record, write_collection


def _job_urls_from_sitemap(client: EthicalClient) -> list[str]:
    xml = client.fetch("https://jobslebanon.com/sitemap.xml")
    if not xml:
        return []
    locs = re.findall(r"<loc>(.*?)</loc>", xml)
    return [u for u in locs if "/companies/" in u and "/jobs/" in u]


def _parse_detail(url: str, html: str) -> dict[str, Any] | None:
    soup = BeautifulSoup(html, "lxml")
    title = None
    company = None
    location = None
    description = ""
    salary = None
    employment_type = None
    date_posted = None

    for script in soup.select('script[type="application/ld+json"]'):
        try:
            data = json.loads(script.string or "")
        except Exception:
            continue
        items = data if isinstance(data, list) else [data]
        for item in items:
            if not isinstance(item, dict):
                continue
            if item.get("@type") != "JobPosting":
                continue
            title = item.get("title") or title
            description = item.get("description") or description
            salary = item.get("salary") or salary
            employment_type = item.get("employmentType") or employment_type
            date_posted = (item.get("datePosted") or "")[:10] or date_posted
            org = item.get("hiringOrganization") or {}
            if isinstance(org, dict):
                company = org.get("name") or company
            loc = item.get("jobLocation")
            if isinstance(loc, dict):
                addr = loc.get("address") or {}
                if isinstance(addr, dict):
                    location = (
                        addr.get("addressLocality")
                        or addr.get("addressRegion")
                        or addr.get("addressCountry")
                        or location
                    )
            elif isinstance(loc, list) and loc:
                addr = (loc[0] or {}).get("address") if isinstance(loc[0], dict) else {}
                if isinstance(addr, dict):
                    location = addr.get("addressLocality") or location

    if not title and soup.title:
        title = soup.title.get_text(strip=True).split("|")[0].strip()
    if not description:
        main = soup.select_one("main, article, .job-description, .rich-content")
        description = main.get_text("\n", strip=True) if main else soup.get_text("\n", strip=True)[:5000]
    # strip residual CSS dumped into ld+json rich content
    if description and ".rich-content" in description[:200]:
        # fall back to visible text
        main = soup.select_one("main, article")
        if main:
            description = main.get_text("\n", strip=True)

    if not title or len(description) < 40:
        return None

    # Lebanon filter: keep Lebanon locations / LB host jobs; drop obvious non-LB
    loc_l = (location or "").lower()
    if loc_l and "lebanon" not in loc_l and loc_l not in {"lb", "remote"}:
        # still keep if URL is jobslebanon and location empty-ish
        if any(x in loc_l for x in ("riyadh", "dubai", "saudi", "uae", "qatar", "kuwait")):
            return None

    path = urlparse(url).path
    return base_record(
        source="jobslebanon",
        source_url=url,
        job_title=title[:300],
        company=company,
        location=location or "Lebanon",
        description=description[:20000],
        salary=str(salary) if salary else None,
        employment_type=str(employment_type) if employment_type else None,
        date_posted=date_posted,
        job_id="jl_" + hashlib_tail(path),
    )


def hashlib_tail(text: str) -> str:
    import hashlib

    return hashlib.md5(text.encode("utf-8")).hexdigest()[:14]


def collect(max_jobs: int = 300) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    with EthicalClient(delay_sec=1.5, allow_missing_robots=False) as client:
        urls = _job_urls_from_sitemap(client)
        print(f"[jobslebanon] sitemap job urls: {len(urls)}")
        for i, url in enumerate(urls):
            if len(jobs) >= max_jobs:
                break
            html = client.fetch(url)
            if not html:
                continue
            client.save_raw("jobslebanon", f"job_{i}.html", html)
            rec = _parse_detail(url, html)
            if rec:
                jobs.append(rec)
                print(f"[jobslebanon] {len(jobs)} {rec['job_title'][:60]}")
    write_collection("jobslebanon", jobs)
    return jobs


if __name__ == "__main__":
    collect()
