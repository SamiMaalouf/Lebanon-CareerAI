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


def ids_from(url: str) -> tuple[int, set[str], str]:
    r = httpx.get(url, headers=UA, timeout=40, follow_redirects=True)
    return r.status_code, set(re.findall(r"jobdetails\.aspx\?id=(\d+)", r.text, flags=re.I)), r.text


def main() -> None:
    for featured in (0, 1):
        for pg in (1, 2, 3):
            url = (
                "https://www.hirelebanese.com/searchresults.aspx?"
                f"top=0&order=date&keywords=&category=&type=&duration=&country=&state=&city=&emp=&pg={pg}&s=-1&featured={featured}"
            )
            st, ids, txt = ids_from(url)
            print("feat", featured, "pg", pg, "ids", len(ids))
            time.sleep(0.35)

    cats = [1, 7, 8, 9, 10, 11, 15, 16, 17, 19, 23, 29]
    all_ids: set[str] = set()
    for c in cats:
        url2 = (
            "https://www.hirelebanese.com/searchresults.aspx?"
            f"top=0&order=date&keywords=&category={c}&type=&duration=&country=&state=&city=&emp=&pg=1&s=-1&featured=0"
        )
        st2, ids2, _ = ids_from(url2)
        # paginate category
        for pg in range(1, 15):
            urlp = (
                "https://www.hirelebanese.com/searchresults.aspx?"
                f"top=0&order=date&keywords=&category={c}&type=&duration=&country=&state=&city=&emp=&pg={pg}&s=-1&featured=0"
            )
            _, idsp, _ = ids_from(urlp)
            if not idsp:
                break
            all_ids |= idsp
            time.sleep(0.3)
        print("cat", c, "running total", len(all_ids))
        time.sleep(0.3)

    print("ALL from categories", len(all_ids))

    r = httpx.get(
        "https://www.hirelebanese.com/jseeker/findjobhome.aspx",
        headers=UA,
        timeout=40,
        follow_redirects=True,
    )
    soup = BeautifulSoup(r.text, "lxml")
    for a in soup.select("a[href*='pg=']")[:30]:
        print("pager", a.get("href"), "|", a.get_text(strip=True)[:40])
    for a in soup.select("a[href*='searchresults']")[:20]:
        print("sr", a.get("href")[:120], "|", a.get_text(strip=True)[:40])


if __name__ == "__main__":
    main()
