"""Shared ethical HTTP helpers for Lebanese job-board collectors."""

from __future__ import annotations

import hashlib
import json
import re
import time
from datetime import date
from pathlib import Path
from typing import Any
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser

import httpx
from bs4 import BeautifulSoup

ROOT = Path(__file__).resolve().parents[2]
RAW_ROOT = ROOT / "raw_data"


class EthicalClient:
    def __init__(
        self,
        user_agent: str = (
            "Mozilla/5.0 (compatible; LebanonCareerAI-ResearchBot/1.0; "
            "+https://github.com/local/careerai; research use)"
        ),
        delay_sec: float = 2.0,
        allow_missing_robots: bool = False,
    ):
        self.user_agent = user_agent
        self.delay_sec = delay_sec
        self.allow_missing_robots = allow_missing_robots
        self._last_request = 0.0
        self._robots_cache: dict[str, RobotFileParser | None] = {}
        self._client = httpx.Client(
            headers={
                "User-Agent": user_agent,
                "Accept": "text/html,application/xhtml+xml,application/json;q=0.9,*/*;q=0.8",
            },
            timeout=40.0,
            follow_redirects=True,
        )

    def close(self) -> None:
        self._client.close()

    def __enter__(self) -> "EthicalClient":
        return self

    def __exit__(self, *args) -> None:
        self.close()

    def _robots(self, netloc: str, scheme: str) -> RobotFileParser | None:
        if netloc in self._robots_cache:
            return self._robots_cache[netloc]
        robots_url = f"{scheme}://{netloc}/robots.txt"
        rp = RobotFileParser()
        try:
            resp = self._client.get(robots_url)
            if resp.status_code == 404:
                self._robots_cache[netloc] = None
                return None
            resp.raise_for_status()
            rp.parse(resp.text.splitlines())
            self._robots_cache[netloc] = rp
            return rp
        except Exception:
            self._robots_cache[netloc] = None
            return None

    def allowed(self, url: str) -> bool:
        parsed = urlparse(url)
        rp = self._robots(parsed.netloc, parsed.scheme or "https")
        if rp is None:
            return bool(self.allow_missing_robots)
        try:
            return rp.can_fetch(self.user_agent, url)
        except Exception:
            return False

    def _throttle(self) -> None:
        elapsed = time.time() - self._last_request
        if elapsed < self.delay_sec:
            time.sleep(self.delay_sec - elapsed)

    def fetch(self, url: str, force: bool = False) -> str | None:
        if not force and not self.allowed(url):
            print(f"[blocked] {url}")
            return None
        self._throttle()
        resp = self._client.get(url)
        self._last_request = time.time()
        if resp.status_code >= 400:
            print(f"[http {resp.status_code}] {url}")
            return None
        return resp.text

    def post(
        self,
        url: str,
        data: dict[str, Any] | None = None,
        force: bool = False,
    ) -> str | None:
        """POST helper for robots-allowed endpoints (e.g. WP admin-ajax)."""
        if not force and not self.allowed(url):
            print(f"[blocked] {url}")
            return None
        self._throttle()
        resp = self._client.post(url, data=data or {})
        self._last_request = time.time()
        if resp.status_code >= 400:
            print(f"[http {resp.status_code}] POST {url}")
            return None
        return resp.text

    def save_raw(self, source: str, name: str, content: str) -> Path:
        folder = RAW_ROOT / source
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / name
        path.write_text(content, encoding="utf-8", errors="ignore")
        return path


def make_job_id(source: str, source_url: str, title: str = "") -> str:
    blob = f"{source}|{source_url}|{title}".encode("utf-8", errors="ignore")
    return source[:12] + "_" + hashlib.md5(blob).hexdigest()[:12]


def base_record(**kwargs: Any) -> dict[str, Any]:
    today = date.today().isoformat()
    out = {
        "job_id": None,
        "source": kwargs.get("source") or "unknown",
        "source_url": kwargs.get("source_url"),
        "collection_date": today,
        "job_title": kwargs.get("job_title") or "Untitled",
        "company": kwargs.get("company"),
        "industry": kwargs.get("industry"),
        "location": kwargs.get("location") or "Lebanon",
        "date_posted": kwargs.get("date_posted"),
        "employment_type": kwargs.get("employment_type"),
        "education": kwargs.get("education"),
        "experience": kwargs.get("experience"),
        "languages": kwargs.get("languages"),
        "description": kwargs.get("description") or "",
        "requirements": kwargs.get("requirements"),
        "preferred_skills": kwargs.get("preferred_skills"),
        "salary": kwargs.get("salary"),
        "raw_text": kwargs.get("raw_text"),
    }
    out["job_id"] = kwargs.get("job_id") or make_job_id(
        out["source"], out.get("source_url") or "", out["job_title"]
    )
    if not out.get("raw_text"):
        out["raw_text"] = "\n".join(
            filter(
                None,
                [
                    out["job_title"],
                    out.get("company"),
                    out.get("location"),
                    out.get("description"),
                    out.get("requirements"),
                ],
            )
        )
    return out


def strip_html_text(html: str) -> str:
    soup = BeautifulSoup(html, "lxml")
    for tag in soup(["script", "style", "noscript"]):
        tag.decompose()
    return re.sub(r"\n{3,}", "\n\n", soup.get_text("\n", strip=True))


def write_collection(source: str, jobs: list[dict[str, Any]]) -> Path:
    RAW_ROOT.mkdir(parents=True, exist_ok=True)
    path = RAW_ROOT / f"{source}_jobs.json"
    path.write_text(json.dumps(jobs, ensure_ascii=False, indent=2), encoding="utf-8")
    print(f"[{source}] wrote {len(jobs)} jobs -> {path}")
    return path
