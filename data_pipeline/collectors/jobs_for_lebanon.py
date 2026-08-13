"""Jobs for Lebanon collector via robots-allowed admin-ajax listing + public job pages.

robots.txt: Allow / ; Disallow /wp-admin/ ; Allow /wp-admin/admin-ajax.php
Does NOT call api.smartrecruiters.com (Disallow: / for general bots).
"""

from __future__ import annotations

import re
from typing import Any
from urllib.parse import urljoin

from bs4 import BeautifulSoup

from data_pipeline.collectors.base import EthicalClient, base_record, strip_html_text, write_collection

BASE = "https://www.jobsforlebanon.com"
AJAX = f"{BASE}/wp-admin/admin-ajax.php"
BROWSER_UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
)


ENG_FUNCTIONS = [
    "engineering",
    "information_technology",
    "design",
    "product_management",
    "manufacturing",
    "production",
    "data_science",
    "analyst",
]


def _list_job_ids(client: EthicalClient, max_pages: int = 40, page_size: int = 50) -> list[str]:
    ordered: list[str] = []
    seen: set[str] = set()
    client.fetch(f"{BASE}/")

    def _paginate(extra_opts: dict[str, str], label: str, pages: int) -> None:
        for offset in range(0, pages):
            data = {
                "action": "jfh_ajax_get_jobs",
                "offset": str(offset),
                "limit": str(page_size),
                "uibehavior": "append",
                "options[country]": "lb",
                "options[countrylabel]": "Lebanon",
            }
            data.update({f"options[{k}]": v for k, v in extra_opts.items()})
            html = client.post(AJAX, data=data)
            if not html:
                break
            if "data-notfound" in html and not re.search(r"/job\?id=", html, flags=re.I):
                break
            ids = re.findall(r"/job\?id=([0-9a-f\-]{20,})", html, flags=re.I)
            new = 0
            for jid in ids:
                if jid not in seen:
                    seen.add(jid)
                    ordered.append(jid)
                    new += 1
            print(f"[jobs_for_lebanon] {label} offset {offset}: +{new} (total {len(ordered)})")
            if new == 0:
                break

    # Broad Lebanon listing first
    _paginate({}, "all", max_pages)
    # Engineering-biased function slices (catch roles missed in default ranking)
    for fn in ENG_FUNCTIONS:
        _paginate({"function": fn}, fn, min(8, max_pages))
    return ordered


def _parse_detail(url: str, html: str) -> dict[str, Any] | None:
    soup = BeautifulSoup(html, "lxml")
    title = None
    h1 = soup.select_one("h1, .catalogue-title, .job-title")
    if h1:
        title = h1.get_text(" ", strip=True)
    if not title and soup.title:
        title = soup.title.get_text(strip=True).split("|")[0].split("–")[0].strip()

    company = None
    for a in soup.select('a[href*="/company"]'):
        txt = a.get_text(" ", strip=True)
        if txt and len(txt) < 160:
            company = txt
            break

    location = "Lebanon"
    text_blob = soup.get_text("\n", strip=True)
    for pat in (
        r"Location\s*[:\-]\s*(.+)",
        r"City\s*[:\-]\s*(.+)",
        r"(Beirut[^,\n]{0,40}|Mount Lebanon[^,\n]{0,40}|Tripoli[^,\n]{0,40})",
    ):
        m = re.search(pat, text_blob, flags=re.I)
        if m:
            location = m.group(1).split("\n")[0].strip()[:200]
            break

    main = soup.select_one(
        "main, article, .job-description, .job-content, .catalogue-job-description, .content"
    )
    if main:
        description = main.get_text("\n", strip=True)
    else:
        description = strip_html_text(html)
    description = re.sub(r"\n{3,}", "\n\n", description).strip()

    if not title or len(description) < 80:
        return None

    return base_record(
        source="jobs_for_lebanon",
        source_url=url,
        job_id="jfl_" + url.split("id=")[-1][:36].replace("-", "")[:16],
        job_title=title[:300],
        company=company,
        location=location or "Lebanon",
        description=description[:20000],
    )


def collect(max_jobs: int = 700, max_list_pages: int = 40) -> list[dict[str, Any]]:
    jobs: list[dict[str, Any]] = []
    with EthicalClient(user_agent=BROWSER_UA, delay_sec=1.5, allow_missing_robots=False) as client:
        ids = _list_job_ids(client, max_pages=max_list_pages)
        print(f"[jobs_for_lebanon] unique listing ids: {len(ids)}")
        for jid in ids:
            if len(jobs) >= max_jobs:
                break
            url = f"{BASE}/job?id={jid}"
            html = client.fetch(url)
            if not html:
                continue
            client.save_raw("jobs_for_lebanon", f"job_{jid}.html", html)
            rec = _parse_detail(url, html)
            if rec:
                jobs.append(rec)
                if len(jobs) % 25 == 0:
                    print(f"[jobs_for_lebanon] collected {len(jobs)}")
    write_collection("jobs_for_lebanon", jobs)
    return jobs


if __name__ == "__main__":
    collect(max_jobs=40, max_list_pages=2)
