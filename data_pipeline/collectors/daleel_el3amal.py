"""Collector for Daleel el 3amal public job listings."""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from data_pipeline.collectors.base import EthicalClient, base_record, write_collection

BASE = "https://daleel-el3amal.org"


def _job_links(client: EthicalClient, max_pages: int = 20) -> list[str]:
    links: list[str] = []
    seen: set[str] = set()
    for page in range(0, max_pages):
        url = f"{BASE}/jobs" if page == 0 else f"{BASE}/jobs?page={page}"
        html = client.fetch(url)
        if not html:
            break
        soup = BeautifulSoup(html, "lxml")
        page_links = []
        for a in soup.select('a[href*="/jobs/"]'):
            href = a.get("href") or ""
            full = urljoin(BASE, href)
            if "?" in full:
                continue
            if not re.search(r"/jobs/[a-z0-9\-]+/?$", full):
                continue
            if full.rstrip("/").endswith("/jobs"):
                continue
            if full not in seen:
                seen.add(full)
                page_links.append(full)
        print(f"[daleel_el3amal] page {page}: +{len(page_links)}")
        if not page_links:
            break
        links.extend(page_links)
    return links


def _parse_detail(url: str, html: str) -> dict[str, Any] | None:
    soup = BeautifulSoup(html, "lxml")
    title = None
    if soup.select_one("h1"):
        title = soup.select_one("h1").get_text(" ", strip=True)
    if not title and soup.title:
        title = soup.title.get_text(strip=True).split("|")[0].strip()
    main = soup.select_one("article, .node--type-job, .region-content, main") or soup.body
    text = main.get_text("\n", strip=True) if main else ""
    if not title or len(text) < 40:
        return None
    # skip clearly expired-only stubs if almost empty
    company = None
    location = "Lebanon"
    for label in ("Organization", "Company", "Employer"):
        m = re.search(rf"{label}\s*[:\-]\s*(.+)", text, flags=re.I)
        if m:
            company = m.group(1).split("\n")[0].strip()[:200]
            break
    for label in ("Location", "Duty station", "City"):
        m = re.search(rf"{label}\s*[:\-]\s*(.+)", text, flags=re.I)
        if m:
            location = m.group(1).split("\n")[0].strip()[:200]
            break
    return base_record(
        source="daleel_el3amal",
        source_url=url,
        job_title=title[:300],
        company=company,
        location=location,
        description=text[:20000],
    )


def collect(max_jobs: int = 200) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    with EthicalClient(delay_sec=1.5, allow_missing_robots=False) as client:
        urls = _job_links(client, max_pages=20)
        print(f"[daleel_el3amal] job urls: {len(urls)}")
        for i, url in enumerate(urls):
            if len(jobs) >= max_jobs:
                break
            html = client.fetch(url)
            if not html:
                continue
            client.save_raw("daleel_el3amal", f"job_{i}.html", html)
            rec = _parse_detail(url, html)
            if rec:
                jobs.append(rec)
    write_collection("daleel_el3amal", jobs)
    return jobs


if __name__ == "__main__":
    collect()
