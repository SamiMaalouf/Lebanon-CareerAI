"""Probe HireLebanese listing pagination and job detail fields."""
from __future__ import annotations

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
    # Advanced search - Lebanon locations
    urls = [
        "https://www.hirelebanese.com/jobsearch.aspx",
        "https://www.hirelebanese.com/jobsearch.aspx?loc=Lebanon%20-%20Beirut",
        "https://www.hirelebanese.com/jseeker/findjobhome.aspx?page=2",
        "https://www.hirelebanese.com/jseeker/findjobhome.aspx?p=2",
    ]
    for u in urls:
        r = get(u)
        soup = BeautifulSoup(r.text, "lxml")
        ids = sorted(set(re.findall(r"jobdetails\.aspx\?id=(\d+)", r.text, flags=re.I)))
        print(u, "status", r.status_code, "ids", len(ids), "sample", ids[:8])

    # detail parse
    r = get("https://www.hirelebanese.com/jobdetails.aspx?id=284444")
    soup = BeautifulSoup(r.text, "lxml")
    print("detail title", soup.title.get_text(strip=True) if soup.title else None)
    text = soup.get_text("\n", strip=True)
    print(text[:1500])

    # try find all numeric job ids referenced on home sectors
    r = get("https://www.hirelebanese.com/")
    ids = sorted(set(re.findall(r"jobdetails\.aspx\?id=(\d+)", r.text, flags=re.I)))
    print("home ids", len(ids))

    # sector pages?
    soup = BeautifulSoup(r.text, "lxml")
    for a in soup.select("a[href]")[:40]:
        h = a.get("href") or ""
        if "sector" in h.lower() or "category" in h.lower() or "findjob" in h.lower():
            print("nav", urljoin(str(r.url), h), a.get_text(strip=True)[:50])


if __name__ == "__main__":
    main()
