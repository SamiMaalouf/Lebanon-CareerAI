"""Quality gates for collected Lebanese job postings."""

from __future__ import annotations

import re
from typing import Any

from data_pipeline.cleaning.pipeline import content_hash, normalize_whitespace, strip_html

JUNK_TITLES = {
    "toggle navigation",
    "job details",
    "find jobs",
    "browse jobs",
    "login",
    "untitled",
    "apply now",
    "privacy policy",
    "home",
    "search",
    "jobs",
    "careers",
}

CSS_MARKERS = (
    ".rich-content",
    "{display:",
    "margin-top:",
    "font-family:",
    "!important",
    "@media",
)

LEBANON_HINTS = re.compile(
    r"\b("
    r"lebanon|lebanese|beirut|tripoli|sidon|saida|saidon|tyre|sour|"
    r"bekaa|bekkaa|jounieh|byblos|jbeil|zahle|zahleh|baalbek|"
    r"mount lebanon|nabatieh|keserwan|metn|chouf|akkar|batroun|"
    r"dbayeh|achrafieh|hamra|verdun|jal el dib|sin el fil|"
    r"\blb\b"
    r")\b",
    flags=re.I,
)

SOURCE_ASSUMED_LEBANON = {
    "jobslebanon",
    "daleel_el3amal",
    "daleel_madani",
    "jobs_for_lebanon",
    "hirelebanese",
}


def _norm_title(title: str) -> str:
    t = normalize_whitespace(strip_html(title or "")).lower()
    t = re.sub(r"[^a-z0-9\s\+\#\.\-/]", "", t)
    return re.sub(r"\s+", " ", t).strip()


def is_usable_job(job: dict[str, Any], min_description: int = 80) -> tuple[bool, str]:
    """Return (ok, reason). Prefer rejecting noisy / non-LB / stub postings."""
    title = normalize_whitespace(strip_html(job.get("job_title") or ""))
    if not title or len(title) < 3:
        return False, "missing_title"
    if _norm_title(title) in JUNK_TITLES:
        return False, "junk_title"
    if title.lower().startswith("http"):
        return False, "url_title"

    desc = normalize_whitespace(strip_html(job.get("description") or job.get("raw_text") or ""))
    if len(desc) < min_description:
        return False, "short_description"
    head = desc[:400].lower()
    if sum(1 for m in CSS_MARKERS if m.lower() in head) >= 2:
        return False, "css_noise"

    source = str(job.get("source") or "").lower()
    location = str(job.get("location") or "")
    blob = f"{location}\n{title}\n{desc[:1200]}"
    has_lb = bool(LEBANON_HINTS.search(blob))
    if source in SOURCE_ASSUMED_LEBANON:
        # Drop obvious non-LB locations even on LB boards
        loc_l = location.lower()
        if loc_l and not has_lb and any(
            x in loc_l for x in ("dubai", "riyadh", "saudi", "uae", "qatar", "kuwait", "egypt", "jordan")
        ):
            return False, "non_lebanon_location"
    elif not has_lb:
        return False, "no_lebanon_signal"

    if not job.get("source_url"):
        return False, "missing_source_url"
    return True, "ok"


def filter_jobs(jobs: list[dict[str, Any]], min_description: int = 80) -> tuple[list[dict[str, Any]], dict[str, int]]:
    kept: list[dict[str, Any]] = []
    reasons: dict[str, int] = {}
    seen_ids: set[str] = set()
    seen_content: set[str] = set()
    seen_title_company: set[str] = set()

    for job in jobs:
        ok, reason = is_usable_job(job, min_description=min_description)
        if not ok:
            reasons[reason] = reasons.get(reason, 0) + 1
            continue

        jid = str(job.get("job_id") or "")
        if jid and jid in seen_ids:
            reasons["dup_job_id"] = reasons.get("dup_job_id", 0) + 1
            continue

        ch = content_hash(
            job.get("job_title") or "",
            job.get("company"),
            job.get("description"),
        )
        if ch in seen_content:
            reasons["dup_content"] = reasons.get("dup_content", 0) + 1
            continue

        tc = f"{_norm_title(job.get('job_title') or '')}|{(job.get('company') or '').strip().lower()}"
        if len(tc) > 5 and tc in seen_title_company:
            reasons["dup_title_company"] = reasons.get("dup_title_company", 0) + 1
            continue

        if jid:
            seen_ids.add(jid)
        seen_content.add(ch)
        if len(tc) > 5:
            seen_title_company.add(tc)
        kept.append(job)
        reasons["ok"] = reasons.get("ok", 0) + 1

    return kept, reasons
