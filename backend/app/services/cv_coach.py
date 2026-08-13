"""Student-facing CV Coach: CV fixes, technical skill gaps, concrete postings."""

from __future__ import annotations

import re
from typing import Any

from sqlalchemy.orm import Session, joinedload

from backend.app.db.models import Job
from backend.app.services.matching import MatchingEngine
from backend.app.services.skill_filters import (
    CATEGORY_FALLBACK,
    SOFTWARE_CATS,
    canonical_category,
    is_technical,
    skill_fits_category,
)
from backend.app.services.skill_gap import SkillGapEngine
from data_pipeline.taxonomy.loader import load_taxonomy

# Titles that are not useful apply targets for engineering students
SKIP_TITLE = re.compile(
    r"(?i)\b("
    r"customer success|account manager|sales intern|sales executive|"
    r"marketing|social media|community manager|hr intern|human resources|"
    r"receptionist|call center|accountan|accoutant|bookkeep|cashier|"
    r"content creation|video content|irrigation|hvac technician|waiter|barista"
    r")\b"
)
SOFTWARE_TITLE = re.compile(
    r"(?i)\b("
    r"software|developer|devops|programmer|backend|frontend|full.?stack|"
    r"data (scien|engineer|analyst)|machine learning|\bai\b|cyber|"
    r"security engineer|embedded|firmware|web develop|mobile (dev|engineer)"
    r")\b"
)
RELATED_HINTS = {
    "react": "javascript",
    "nextjs": "javascript",
    "nodejs": "javascript",
    "express": "javascript",
    "typescript": "javascript",
    "django": "python",
    "flask": "python",
    "fastapi": "python",
    "pytorch": "python",
    "tensorflow": "python",
    "pandas": "python",
    "spring": "java",
    "docker": "linux",
    "kubernetes": "docker",
}


class CVCoach:
    def __init__(self):
        self.taxonomy = load_taxonomy()
        self.gap = SkillGapEngine()
        self.matcher = MatchingEngine()

    def _is_technical(self, skill_id: str) -> bool:
        return is_technical(self.taxonomy, skill_id)

    def _skill_fits_category(self, skill_id: str, category: str) -> bool:
        return skill_fits_category(self.taxonomy, skill_id, category)

    def _normalize_ids(self, skills: list[str]) -> set[str]:
        out: set[str] = set()
        for s in skills:
            cid = self.taxonomy.canonical_id(s)
            out.add(cid if cid else self.taxonomy._slug(s))
        return out

    def _cv_fixes(self, candidate: dict[str, Any], category: str | None = None) -> list[dict[str, Any]]:
        projects = [p for p in (candidate.get("projects") or []) if str(p).strip()]
        sections = [s.lower() for s in (candidate.get("detected_sections") or [])]
        fields = [f for f in (candidate.get("education_fields") or []) if str(f).strip()]
        langs = [str(x).lower() for x in (candidate.get("languages") or [])]
        skills = candidate.get("skills") or []
        found_projects = bool(candidate.get("projects_section_found")) or "projects" in sections
        major_example = category or "your engineering major"

        fixes: list[dict[str, Any]] = []

        if not found_projects or len(projects) == 0:
            fixes.append(
                {
                    "id": "projects",
                    "ok": False,
                    "title": "Projects section",
                    "action": "Add a Projects heading with 2–4 named titles from coursework or personal work.",
                }
            )
        elif len(projects) == 1:
            fixes.append(
                {
                    "id": "projects",
                    "ok": False,
                    "title": "Projects section",
                    "action": f"You only have one project title ({projects[0]}). Add 1–2 more named projects.",
                }
            )

        quantified = any(re.search(r"\d", p) for p in projects)
        if projects and not quantified:
            fixes.append(
                {
                    "id": "impact",
                    "ok": False,
                    "title": "Project impact",
                    "action": (
                        f"Add one number or result under “{projects[0]}” "
                        "(users, latency, accuracy, lines of code, weeks saved)."
                    ),
                }
            )

        if "skills" not in sections and len(skills) < 4:
            fixes.append(
                {
                    "id": "skills",
                    "ok": False,
                    "title": "Skills section",
                    "action": "Add a Skills heading and list tools as plain words (Python, Git, SQL, React).",
                }
            )

        if not fields:
            fixes.append(
                {
                    "id": "major",
                    "ok": False,
                    "title": "Degree / major",
                    "action": f"Write your major in full, e.g. Bachelor of {major_example}.",
                }
            )

        if not any("english" in x for x in langs):
            fixes.append(
                {
                    "id": "english",
                    "ok": False,
                    "title": "Languages",
                    "action": "List English (and Arabic) under Languages — most Lebanese ads expect it.",
                }
            )

        return [f for f in fixes if not f.get("ok")]

    def _learn_next(
        self,
        stats: dict[str, dict],
        cand_ids: set[str],
        category: str,
        projects: list[str],
        min_count: int,
        market_label: str | None = None,
    ) -> list[dict[str, Any]]:
        missing = []
        for sid, meta in stats.items():
            if sid in cand_ids:
                continue
            if not self._skill_fits_category(sid, category):
                continue
            if meta["count"] < min_count:
                continue
            missing.append(meta)
        missing.sort(key=lambda m: (m["frequency"] * max(m["required_rate"], 0.15)), reverse=True)

        jobs_n = next((m["jobs_in_scope"] for m in stats.values()), 0)
        project_hint = projects[0] if projects else None
        label = market_label or category
        out: list[dict[str, Any]] = []
        for m in missing[:5]:
            sid = m["skill_id"]
            related = RELATED_HINTS.get(sid)
            extra = ""
            if related and related in cand_ids:
                rel_name = self.taxonomy.skills.get(related, {}).get("name", related)
                if project_hint:
                    extra = f" You already have {rel_name} — add {m['name']} if you used it in {project_hint}."
                else:
                    extra = f" You already have {rel_name} — add {m['name']} if you have used it."
            n = m["count"]
            action = (
                f"Add {m['name']} to your Skills section — in {n}/{jobs_n} "
                f"{label} ads in this dataset.{extra}"
            )
            out.append(
                {
                    "skill": m["name"],
                    "skill_id": sid,
                    "count": n,
                    "jobs_in_scope": jobs_n,
                    "demand_pct": round(100 * m["frequency"], 1),
                    "action": action,
                }
            )
        return out

    def _strengths(
        self, stats: dict[str, dict], cand_ids: set[str], category: str
    ) -> list[dict[str, Any]]:
        have = []
        for sid in cand_ids:
            meta = stats.get(sid)
            if not meta or not self._skill_fits_category(sid, category):
                continue
            have.append(
                {
                    "skill": meta["name"],
                    "demand_pct": round(100 * meta["frequency"], 1),
                    "count": meta["count"],
                }
            )
        have.sort(key=lambda x: x["demand_pct"], reverse=True)
        return have[:4]

    def _tech_names(self, names: list[str], category: str) -> list[str]:
        out: list[str] = []
        seen: set[str] = set()
        for name in names or []:
            sid = self.taxonomy.canonical_id(name) or self.taxonomy._slug(name)
            if not self._skill_fits_category(sid, category):
                continue
            if name.lower() in seen:
                continue
            seen.add(name.lower())
            out.append(name)
        return out

    def _apply_now(
        self,
        db: Session,
        candidate: dict[str, Any],
        category: str,
        target_category: str,
        limit: int = 3,
    ) -> list[dict[str, Any]]:
        q = db.query(Job).options(joinedload(Job.skills))
        if category:
            q = q.filter(Job.job_category == category)
        jobs = q.all()
        scored: list[dict[str, Any]] = []
        for job in jobs:
            title = job.job_title or ""
            if SKIP_TITLE.search(title):
                continue
            kw = self.matcher.keyword_score(candidate, job)
            intern = bool(getattr(job, "is_internship", False))
            matched = self._tech_names(kw.get("matched_skills") or [], target_category)
            missing = self._tech_names(kw.get("missing_required") or [], target_category)
            tech_score = 100.0 * (
                (len(matched) / max(1, len(matched) + len(missing))) if (matched or missing) else 0.0
            )
            if not matched:
                if intern and target_category in SOFTWARE_CATS and SOFTWARE_TITLE.search(title):
                    pass  # e.g. DevOps intern with no overlapping tools yet
                else:
                    continue
            scored.append(
                {
                    "job_id": job.job_id,
                    "title": job.job_title,
                    "company": job.company,
                    "location": job.location,
                    "category": job.job_category,
                    "source_url": job.source_url,
                    "is_internship": intern,
                    "compatibility_score": round(tech_score, 1),
                    "matched_skills": matched[:6],
                    "missing_skills": missing[:4],
                }
            )
        # Prefer internships that actually share tools, then higher technical overlap
        scored.sort(
            key=lambda x: (
                not (x["is_internship"] and x["matched_skills"]),
                -len(x["matched_skills"]),
                -float(x["compatibility_score"] or 0),
            ),
        )
        return scored[:limit]

    def analyze(self, db: Session, candidate: dict[str, Any], category: str) -> dict[str, Any]:
        category = canonical_category(category) or category
        q = db.query(Job)
        if category:
            q = q.filter(Job.job_category == category)
        job_count = q.count()
        market_category = category
        fallback = None
        if job_count == 0:
            fallback = CATEGORY_FALLBACK.get(category)
            if fallback:
                market_category = fallback
                job_count = db.query(Job).filter(Job.job_category == fallback).count()
        stats = self.gap.market_skill_stats(db, market_category)
        min_count = 2 if job_count >= 10 else 1
        cand_ids = self._normalize_ids(candidate.get("skills") or [])
        projects = [p for p in (candidate.get("projects") or []) if str(p).strip()]
        learn_label = fallback or category

        return {
            "category": category,
            "market_category": market_category,
            "job_count": job_count,
            "sparse": job_count < 20 or bool(fallback),
            "cv_fixes": self._cv_fixes(candidate, category=category),
            "learn_next": self._learn_next(
                stats, cand_ids, category, projects, min_count, market_category
            ),
            "strengths": self._strengths(stats, cand_ids, category),
            "apply_now": self._apply_now(db, candidate, market_category, category),
            "disclaimer": (
                "Tips use this project's Lebanese engineering job sample — not the entire market. "
                "Fix the CV items first, then apply."
                + (
                    f" No {category} ads yet; skills/jobs use {fallback} as the closest bucket."
                    if fallback
                    else ""
                )
            ),
        }
