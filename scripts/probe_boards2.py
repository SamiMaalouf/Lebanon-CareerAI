"""Probe HireLebanese and Daleel el 3amal listing/detail pages."""
from __future__ import annotations

import json
import re
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
    # HireLebanese home / find jobs
    r = get("https://www.hirelebanese.com/jseeker/findjobhome.aspx")
    soup = BeautifulSoup(r.text, "lxml")
    print("HL title", soup.title.get_text(strip=True) if soup.title else None)
    hrefs = []
    for a in soup.select("a[href]"):
        h = a.get("href") or ""
        t = a.get_text(" ", strip=True)[:70]
        if any(k in h.lower() for k in ("job", "vacanc", "detail", "viewjob")):
            hrefs.append((urljoin(str(r.url), h), t))
    print("HL job-ish hrefs", len(hrefs))
    for h, t in hrefs[:25]:
        print(" ", h, "|", t)

    # forms / viewstate suggests ASP.NET
    print("viewstate", bool(soup.select_one("#__VIEWSTATE")))

    # try common job detail patterns
    for q in [
        "https://www.hirelebanese.com/jobdetails.aspx",
        "https://hirelebanese.com/jseeker/jobdetails.aspx",
        "https://www.hirelebanese.com/Jobs.aspx",
    ]:
        try:
            rr = get(q)
            print(q, rr.status_code, len(rr.text))
        except Exception as e:
            print(q, e)

    # Daleel el 3amal pagination
    r = get("https://daleel-el3amal.org/jobs")
    soup = BeautifulSoup(r.text, "lxml")
    job_links = sorted(
        {
            urljoin(str(r.url), a.get("href") or "")
            for a in soup.select('a[href*="/jobs/"]')
            if a.get("href")
            and "?" not in (a.get("href") or "")
            and a.get("href").rstrip("/").count("/") >= 2
        }
    )
    # filter to actual job pages
    job_links = [u for u in job_links if re.search(r"/jobs/[a-z0-9\-]+$", u) and not u.endswith("/jobs")]
    print("D3 job pages page1", len(job_links))
    print(job_links[:10])

    # pager links
    for a in soup.select("a[href*='page='], a[href*='page%'], li.pager__item a, .pager a"):
        print("pager", a.get("href"), a.get_text(strip=True)[:30])

    # sample detail
    if job_links:
        d = get(job_links[0])
        soup = BeautifulSoup(d.text, "lxml")
        print("D3 detail title", soup.title.get_text(strip=True) if soup.title else None)
        for s in soup.select('script[type="application/ld+json"]'):
            print("D3 LD", s.get_text()[:500])
        main = soup.select_one("article, .node, main, .region-content")
        if main:
            print("D3 main text sample:", main.get_text(" ", strip=True)[:500])

    # JobsLebanon NEXT_DATA for listing?
    r = get("https://jobslebanon.com/jobs")
    nd = BeautifulSoup(r.text, "lxml").select_one("#__NEXT_DATA__")
    if nd and nd.string:
        data = json.loads(nd.string)
        print("JL listing NEXT keys", list(data.get("props", {}).get("pageProps", {}).keys())[:30])
        pp = data.get("props", {}).get("pageProps", {})
        # print shallow
        for k, v in pp.items():
            if isinstance(v, (list, dict)):
                print(" ", k, type(v).__name__, (len(v) if hasattr(v, "__len__") else ""))
            else:
                print(" ", k, v)


if __name__ == "__main__":
    main()
