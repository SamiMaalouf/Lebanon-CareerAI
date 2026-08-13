from __future__ import annotations

import re
import time
from urllib.parse import urljoin

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
    r = client.get("https://www.hirelebanese.com/jseeker/findjobhome.aspx")
    soup = BeautifulSoup(r.text, "lxml")
    for a in soup.select("a[href]"):
        h = a.get("href") or ""
        t = a.get_text(" ", strip=True)
        if "Lebanon" in t or "lebanon" in h.lower() or "Beirut" in t:
            print(urljoin(str(r.url), h), "|", t[:80])

    # try POST next page on findjobhome
    view = soup.select_one("#__VIEWSTATE")
    gen = soup.select_one("#__VIEWSTATEGENERATOR")
    ev = soup.select_one("#__EVENTVALIDATION")
    print("has form fields", bool(view), bool(gen), bool(ev))

    # look for LinkButton page numbers
    for a in soup.select("a[href*='__doPostBack']")[:40]:
        print("postback", a.get("href")[:120], a.get_text(strip=True)[:30])

    # try country Lebanon search patterns
    for url in [
        "https://www.hirelebanese.com/searchresults.aspx?top=0&order=date&keywords=&category=&type=&duration=&country=Lebanon&state=&city=&emp=&pg=1&s=-1&featured=0",
        "https://www.hirelebanese.com/searchresults.aspx?top=0&order=date&location=Lebanon%20-%20Beirut&pg=1",
        "https://www.hirelebanese.com/searchresults.aspx?top=0&order=date&keywords=Lebanon&pg=1&featured=0",
    ]:
        rr = client.get(url)
        ids = set(re.findall(r"jobdetails\.aspx\?id=(\d+)", rr.text, flags=re.I))
        print(url.split("?")[1][:80], "->", len(ids))
        time.sleep(0.4)

    # ID walk sample: check last 30 IDs for Lebanon
    max_id = 284444
    leb = 0
    checked = 0
    for jid in range(max_id, max_id - 40, -1):
        rr = client.get(f"https://www.hirelebanese.com/jobdetails.aspx?id={jid}")
        checked += 1
        txt = rr.text
        if "General Information" not in txt and "Description" not in txt:
            print(jid, "empty/missing")
            time.sleep(0.25)
            continue
        loc_m = re.search(r"Location:\s*</[^>]+>\s*([^<\n]+)", txt, flags=re.I)
        # simpler
        soup = BeautifulSoup(txt, "lxml")
        plain = soup.get_text("\n", strip=True)
        is_lb = "Lebanon" in plain[:2000]
        title = ""
        for line in plain.splitlines():
            if line and line not in {"Job Details", "Login", "Apply Now"}:
                title = line
                break
        if is_lb:
            leb += 1
            print("LB", jid, title[:60])
        else:
            print("xx", jid, title[:60])
        time.sleep(0.35)
    print("checked", checked, "lebanon", leb)


if __name__ == "__main__":
    main()
