"""Temporary probe for Lebanese job board HTML structures."""
from __future__ import annotations

import json
import re
from pathlib import Path
from urllib.parse import urljoin

import httpx
from bs4 import BeautifulSoup

UA = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}


def get(url: str) -> httpx.Response:
    return httpx.get(url, headers=UA, timeout=40.0, follow_redirects=True)


def main() -> None:
    url = "https://jobslebanon.com/companies/studiolebanon/jobs/hostess-6f6f4c6994cf4abcacf26d7ef5d453d5"
    r = get(url)
    soup = BeautifulSoup(r.text, "lxml")
    print("JL detail title:", soup.title.get_text(strip=True) if soup.title else None)
    for s in soup.select('script[type="application/ld+json"]'):
        print("LDJSON:", s.get_text()[:1000])
    nd = soup.select_one("#__NEXT_DATA__")
    if nd and nd.string:
        data = json.loads(nd.string)
        Path("raw_data/_probe_jl_next.json").write_text(
            json.dumps(data, ensure_ascii=False, indent=2)[:20000], encoding="utf-8"
        )
        print("Wrote NEXT_DATA probe")

    # JobsLebanon all job URLs from sitemap
    sx = get("https://jobslebanon.com/sitemap.xml").text
    locs = re.findall(r"<loc>(.*?)</loc>", sx)
    job_locs = [l for l in locs if "/jobs/" in l and "/companies/" in l]
    print("JL job URLs in sitemap:", len(job_locs))

    # Daleel Madani
    r = get("https://daleel-madani.org/JOBS")
    print("DM status", r.status_code, len(r.text))
    soup = BeautifulSoup(r.text, "lxml")
    links = sorted(
        {
            urljoin("https://daleel-madani.org", a.get("href") or "")
            for a in soup.select('a[href*="/jobs/"]')
        }
    )
    print("DM unique job links page1:", len(links))
    print("\n".join(links[:8]))

    # pagination?
    for a in soup.select("a"):
        t = (a.get_text() or "").strip().lower()
        if "next" in t or "page" in t:
            print("DM nav:", a.get("href"), t[:40])

    # Daleel el 3amal
    r = get("https://daleel-el3amal.org/jobs")
    print("D3 status", r.status_code, r.url, len(r.text))
    soup = BeautifulSoup(r.text, "lxml")
    links = sorted(
        {
            urljoin(str(r.url), a.get("href") or "")
            for a in soup.select("a[href]")
            if "job" in (a.get("href") or "").lower()
        }
    )
    print("D3 job-ish links:", len(links))
    print("\n".join(links[:15]))

    # Jobs for Lebanon search Lebanon
    for q in [
        "https://www.jobsforlebanon.com/search/?location=lebanon",
        "https://www.jobsforlebanon.com/search/?country=lb",
        "https://www.jobsforhumanity.com/jobs/search/?filters=1&country=lb",
        "https://www.jobsforhumanity.com/jobs/search/?filters=1&location=Lebanon",
    ]:
        try:
            rr = get(q)
            print(q, rr.status_code, len(rr.text), rr.url)
            soup = BeautifulSoup(rr.text, "lxml")
            job_as = [
                a.get("href")
                for a in soup.select("a[href]")
                if a.get("href") and "/job" in a.get("href").lower()
            ]
            print("  job hrefs", len(job_as), job_as[:5])
        except Exception as e:
            print(q, e)

    # HireLebanese
    for q in [
        "https://www.hirelebanese.com/",
        "https://hirelebanese.com/jobsearch.aspx",
        "https://www.hirelebanese.com/jseeker/findjobhome.aspx",
    ]:
        try:
            rr = get(q)
            print("HL", q, rr.status_code, len(rr.text))
        except Exception as e:
            print("HL", q, e)


if __name__ == "__main__":
    main()
