"""Public HTML collector stub.

Only use this for sources whose Terms of Service and robots.txt explicitly permit
automated collection. Default rate limit is conservative.
"""

from __future__ import annotations

import time
from datetime import date
from typing import Any
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup


class EthicalHTMLCollector:
    def __init__(self, user_agent: str = "LebanonCareerAI-ResearchBot/1.0", delay_sec: float = 2.0):
        self.user_agent = user_agent
        self.delay_sec = delay_sec
        self._last_request = 0.0

    def allowed(self, url: str) -> bool:
        parsed = urlparse(url)
        robots_url = f"{parsed.scheme}://{parsed.netloc}/robots.txt"
        rp = RobotFileParser()
        try:
            rp.set_url(robots_url)
            rp.read()
            return rp.can_fetch(self.user_agent, url)
        except Exception:
            # If robots.txt cannot be read, do not scrape.
            return False

    def fetch(self, url: str) -> str | None:
        if not self.allowed(url):
            print(f"Blocked by robots.txt or unreadable robots.txt: {url}")
            return None
        elapsed = time.time() - self._last_request
        if elapsed < self.delay_sec:
            time.sleep(self.delay_sec - elapsed)
        with httpx.Client(headers={"User-Agent": self.user_agent}, timeout=30.0) as client:
            resp = client.get(url)
            self._last_request = time.time()
            resp.raise_for_status()
            return resp.text

    def parse_generic_listing(self, html: str, source: str, source_url: str) -> list[dict[str, Any]]:
        """Very generic parser — customize per source. Extracts title/link/snippet cards."""
        soup = BeautifulSoup(html, "lxml")
        jobs: list[dict[str, Any]] = []
        for a in soup.select("a"):
            title = (a.get_text() or "").strip()
            href = a.get("href") or ""
            if len(title) < 8 or "job" not in (href + title).lower():
                continue
            jobs.append(
                {
                    "job_title": title[:200],
                    "description": title,
                    "source": source,
                    "source_url": href if href.startswith("http") else source_url,
                    "collection_date": date.today().isoformat(),
                    "location": "Lebanon",
                }
            )
        return jobs
