"""Daleel Madani jobs collector — may be blocked (403); fails soft."""

from __future__ import annotations

from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from data_pipeline.collectors.base import EthicalClient, base_record, write_collection

BASE = "https://daleel-madani.org"


def collect(max_jobs: int = 150) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    with EthicalClient(delay_sec=2.0, allow_missing_robots=False) as client:
        html = client.fetch(f"{BASE}/JOBS")
        if not html:
            print("[daleel_madani] listing unavailable (blocked or robots). Skipping.")
            write_collection("daleel_madani", jobs)
            return jobs
        soup = BeautifulSoup(html, "lxml")
        urls = []
        for a in soup.select('a[href*="/jobs/"]'):
            full = urljoin(BASE, a.get("href") or "")
            if full not in urls:
                urls.append(full)
        for i, url in enumerate(urls[:max_jobs]):
            page = client.fetch(url)
            if not page:
                continue
            client.save_raw("daleel_madani", f"job_{i}.html", page)
            dsoup = BeautifulSoup(page, "lxml")
            title = dsoup.select_one("h1")
            title_txt = title.get_text(strip=True) if title else None
            main = dsoup.select_one("article, .node, main") or dsoup.body
            desc = main.get_text("\n", strip=True) if main else ""
            if not title_txt or len(desc) < 40:
                continue
            jobs.append(
                base_record(
                    source="daleel_madani",
                    source_url=url,
                    job_title=title_txt[:300],
                    location="Lebanon",
                    description=desc[:20000],
                )
            )
    write_collection("daleel_madani", jobs)
    return jobs


if __name__ == "__main__":
    collect()
