from __future__ import annotations

from collections import Counter
from typing import Any

from sqlalchemy.orm import Session, joinedload

from backend.app.db.models import Job
from backend.app.services.skill_filters import (
    CATEGORY_FALLBACK,
    canonical_category,
    is_technical,
    skill_fits_category,
)
from data_pipeline.taxonomy.loader import load_taxonomy

# One-line Lebanese-student CV tips keyed by taxonomy skill_id
CV_EXAMPLES = {
    "git": "Git — GitHub link under Projects",
    "python": "Python — one campus project (e.g. Flask API) under Projects",
    "sql": "SQL — list under Skills; mention queries in a project bullet",
    "react": "React — name the UI in a project (e.g. React dashboard)",
    "javascript": "JavaScript — Skills line + GitHub repo under Projects",
    "typescript": "TypeScript — Skills; note it on the same GitHub project as JS",
    "docker": "Docker — Skills; one line if you containerized a project",
    "linux": "Linux — Skills (Ubuntu/lab PCs); mention in a systems project",
    "c": "C — Skills; point to an embedded or systems course project",
    "cplusplus": "C++ — Skills; mention an OOP/course project under Projects",
    "matlab": "MATLAB — Skills; lab or simulation project under Projects",
    "plc": "PLC — Skills; lab/TIA Portal exercise under Projects",
    "autocad": "AutoCAD — Skills; CAD course drawing under Projects",
    "solidworks": "SolidWorks — Skills; CAD model under Projects",
    "java": "Java — Skills; GitHub link for a class assignment",
    "html": "HTML/CSS — Skills; GitHub Pages link under Projects",
    "css": "CSS — Skills; same project as HTML under Projects",
    "nodejs": "Node.js — Skills; backend repo link under Projects",
    "aws": "AWS — Skills; note any free-tier lab or course cert",
    "pandas": "Pandas — Skills; data-analysis notebook under Projects",
    "machine_learning": "Machine Learning — Skills; one notebook under Projects",
    "scada": "SCADA — Skills; lab or internship line under Experience",
    "revit": "Revit — Skills; BIM course model under Projects",
    "excel": "Excel — Skills; internship or lab analysis under Experience",
}


def cv_example_for(skill_id: str, name: str) -> str:
    if skill_id in CV_EXAMPLES:
        return CV_EXAMPLES[skill_id]
    return f"{name} — add it under Skills; mention it in one project if you used it"


class SkillGapEngine:
    def __init__(self):
        self.taxonomy = load_taxonomy()

    def _normalize(self, skills: list[str]) -> set[str]:
        out: set[str] = set()
        for s in skills:
            cid = self.taxonomy.canonical_id(s)
            out.add(cid if cid else self.taxonomy._slug(s))
        return out

    def market_skill_stats(self, db: Session, category: str | None = None) -> dict[str, dict]:
        q = db.query(Job).options(joinedload(Job.skills))
        if category:
            q = q.filter(Job.job_category == category)
        jobs = q.all()
        n = max(1, len(jobs))
        freq: Counter = Counter()
        required_freq: Counter = Counter()
        for job in jobs:
            seen = set()
            for js in job.skills:
                if js.skill_id in seen:
                    continue
                seen.add(js.skill_id)
                freq[js.skill_id] += 1
                if js.is_required:
                    required_freq[js.skill_id] += 1
        stats = {}
        for sid, count in freq.items():
            stats[sid] = {
                "skill_id": sid,
                "name": self.taxonomy.skills.get(sid, {}).get("name", sid),
                "frequency": count / n,
                "count": count,
                "required_rate": required_freq[sid] / n,
                "jobs_in_scope": n,
            }
        return stats

    def analyze(
        self,
        db: Session,
        candidate: dict[str, Any],
        category: str | None = None,
        top_n: int = 15,
    ) -> dict[str, Any]:
        category = canonical_category(category) or category
        target = category or "All"
        q = db.query(Job)
        if category:
            q = q.filter(Job.job_category == category)
        job_count = q.count() if category else db.query(Job).count()
        market_category = category
        fallback = None
        if category and job_count == 0:
            fallback = CATEGORY_FALLBACK.get(category)
            if fallback:
                market_category = fallback
                job_count = db.query(Job).filter(Job.job_category == fallback).count()

        cand = self._normalize(candidate.get("skills") or [])
        stats = self.market_skill_stats(db, market_category)
        min_count = 2 if job_count >= 10 else 1
        fit_category = category or market_category or "Software Engineering"

        possessed = []
        missing = []
        for sid, meta in stats.items():
            if not is_technical(self.taxonomy, sid):
                continue
            if category and not skill_fits_category(self.taxonomy, sid, fit_category):
                continue
            if meta["count"] < min_count:
                continue
            req_pct = round(100 * meta["required_rate"], 1)
            item = {
                **meta,
                "demand_pct": round(100 * meta["frequency"], 1),
                "required_rate_pct": req_pct,
                "priority_score": round(
                    meta["frequency"] * max(meta["required_rate"], 0.15) * (0 if sid in cand else 1),
                    4,
                ),
            }
            if sid in cand:
                possessed.append(item)
            else:
                missing.append(item)

        possessed.sort(key=lambda x: x["frequency"], reverse=True)
        missing.sort(key=lambda x: x["priority_score"], reverse=True)

        def priority_label(score: float) -> str:
            if score >= 0.15:
                return "Very High"
            if score >= 0.08:
                return "High"
            if score >= 0.04:
                return "Medium"
            return "Low"

        def required_phrase(rate: float) -> str:
            if rate >= 50:
                return "often required"
            if rate >= 25:
                return "sometimes required"
            return "usually preferred"

        label = market_category or target
        roadmap = []
        missing_out = []
        for m in missing[:top_n]:
            if m["priority_score"] <= 0:
                continue
            why = (
                f"In {m['count']}/{m['jobs_in_scope']} {label} ads "
                f"({required_phrase(m['required_rate_pct'])}). Not on your CV."
            )
            prio = priority_label(m["priority_score"])
            missing_out.append(
                {
                    "skill": m["name"],
                    "demand_pct": m["demand_pct"],
                    "count": m["count"],
                    "jobs_in_scope": m["jobs_in_scope"],
                    "required_rate_pct": m["required_rate_pct"],
                    "priority_score": m["priority_score"],
                    "priority": prio,
                    "why": why,
                    "cv_example": cv_example_for(m["skill_id"], m["name"]),
                }
            )
            roadmap.append(
                {
                    "skill": m["name"],
                    "skill_id": m["skill_id"],
                    "market_demand_pct": m["demand_pct"],
                    "required_rate_pct": m["required_rate_pct"],
                    "priority_score": m["priority_score"],
                    "priority": prio,
                    "why": why,
                }
            )

        return {
            "category": target,
            "market_category": market_category or target,
            "job_count": job_count,
            "sparse": job_count < 20 or bool(fallback),
            "possessed": [
                {
                    "skill": p["name"],
                    "demand_pct": p["demand_pct"],
                    "count": p["count"],
                    "jobs_in_scope": p["jobs_in_scope"],
                    "required_rate_pct": p["required_rate_pct"],
                }
                for p in possessed[:top_n]
            ],
            "missing": missing_out,
            "roadmap": roadmap,
            "disclaimer": (
                "Recommendations are derived from the publicly accessible Lebanese job "
                "postings collected for this project, not the entire Lebanese job market."
                + (
                    f" No {category} ads yet; comparison uses {fallback} as the closest bucket."
                    if fallback
                    else ""
                )
            ),
        }
