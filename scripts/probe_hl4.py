from __future__ import annotations

import re
import time

import httpx
from bs4 import BeautifulSoup

UA = {
    "User-Agent": (
        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
        "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )
}


def main() -> None:
    client = httpx.Client(headers=UA, timeout=40.0, follow_redirects=True)
    all_ids: set[str] = set()
    locations = [
        "Lebanon",
        "Lebanon - Beirut",
        "Lebanon - Bekaa",
        "Lebanon - Saidon",
        "Lebanon - Tripoli",
        "Lebanon - Mount Lebanon",
    ]
    for loc in locations:
        for pg in range(1, 40):
            url = (
                "https://www.hirelebanese.com/searchresults.aspx?"
                f"top=0&order=date&location={loc.replace(' ', '%20')}&pg={pg}"
            )
            r = client.get(url)
            ids = set(re.findall(r"jobdetails\.aspx\?id=(\d+)", r.text, flags=re.I))
            before = len(all_ids)
            all_ids |= ids
            print(loc, "pg", pg, "page", len(ids), "total", len(all_ids), "new", len(all_ids) - before)
            if not ids:
                break
            # if no new ids after first page, stop
            if pg > 1 and len(all_ids) == before:
                break
            time.sleep(0.4)

    print("UNIQUE IDS", len(all_ids))

    # better detail parse
    r = client.get("https://www.hirelebanese.com/jobdetails.aspx?id=284444")
    soup = BeautifulSoup(r.text, "lxml")
    # try table rows
    for tr in soup.select("tr")[:20]:
        cells = [c.get_text(" ", strip=True) for c in tr.select("td, th")]
        if cells:
            print("TR", cells)


if __name__ == "__main__":
    main()
