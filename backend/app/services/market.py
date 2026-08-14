from __future__ import annotations

from collections import Counter
from typing import Any

from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from backend.app.db.models import Job, JobSkill
from data_pipeline.cleaning.company import is_placeholder_company
from data_pipeline.taxonomy.loader import load_taxonomy


class MarketService:
    def __init__(self):
        self.taxonomy = load_taxonomy()

    def overview(self, db: Session) -> dict[str, Any]:
        total = db.query(func.count(Job.id)).scalar() or 0
        company_names = [
            name
            for (name,) in db.query(Job.company).distinct().all()
            if not is_placeholder_company(name)
        ]
        companies = len(company_names)
        industries = (
            db.query(Job.industry, func.count(Job.id))
            .group_by(Job.industry)
            .order_by(func.count(Job.id).desc())
            .limit(15)
            .all()
        )
        categories = (
            db.query(Job.job_category, func.count(Job.id))
            .group_by(Job.job_category)
            .order_by(func.count(Job.id).desc())
            .all()
        )
        locations = (
            db.query(Job.location, func.count(Job.id))
            .group_by(Job.location)
            .order_by(func.count(Job.id).desc())
            .all()
        )
        sources = (
            db.query(Job.source, func.count(Job.id))
            .group_by(Job.source)
            .order_by(func.count(Job.id).desc())
            .all()
        )
        min_c = db.query(func.min(Job.collection_date)).scalar()
        max_c = db.query(func.max(Job.collection_date)).scalar()
        min_p = db.query(func.min(Job.date_posted)).scalar()
        max_p = db.query(func.max(Job.date_posted)).scalar()

        synthetic_markers = ("synthetic", "example.local")
        real_count = 0
        for src, cnt in sources:
            s = (src or "").lower()
            if any(m in s for m in synthetic_markers):
                continue
            real_count += cnt

        internship_count = (
            db.query(func.count(Job.id)).filter(Job.is_internship.is_(True)).scalar() or 0
        )

        return {
            "total_jobs": total,
            "real_job_count": real_count,
            "synthetic_job_count": max(0, total - real_count),
            "internship_count": internship_count,
            "non_internship_count": max(0, total - internship_count),
            "companies": companies,
            "industries": [{"name": i or "Unknown", "count": c} for i, c in industries],
            "categories": [{"name": i or "Other", "count": c} for i, c in categories],
            "locations": [{"name": i or "Unknown", "count": c} for i, c in locations],
            "sources": [{"name": s or "unknown", "count": c} for s, c in sources],
            "collection_window": {
                "collection_date_min": min_c.isoformat() if min_c else None,
                "collection_date_max": max_c.isoformat() if max_c else None,
                "date_posted_min": min_p.isoformat() if min_p else None,
                "date_posted_max": max_p.isoformat() if max_p else None,
            },
            "top_skills": self.skill_frequency(db, limit=15),
            "is_real_dataset": real_count > 0 and real_count >= total * 0.8,
            "is_engineering_dataset": True,
            "dataset_note": (
                "Engineering-focused dataset of publicly accessible Lebanese job and internship "
                "postings collected during the project's data-collection period — not the entire market."
            ),
        }

    def skill_frequency(
        self, db: Session, category: str | None = None, limit: int = 30
    ) -> list[dict[str, Any]]:
        q = db.query(Job).options(joinedload(Job.skills))
        if category:
            q = q.filter(Job.job_category == category)
        jobs = q.all()
        n = max(1, len(jobs))
        counter: Counter = Counter()
        language_ids = {
            sid
            for sid, meta in self.taxonomy.skills.items()
            if meta.get("parent_id") == "languages" or sid == "languages"
        }
        for job in jobs:
            for js in {s.skill_id for s in job.skills}:
                if js in language_ids:
                    continue
                counter[js] += 1
        out = []
        for sid, count in counter.most_common(limit):
            out.append(
                {
                    "skill_id": sid,
                    "skill": self.taxonomy.skills.get(sid, {}).get("name", sid),
                    "count": count,
                    "pct": round(100 * count / n, 1),
                }
            )
        return out

    def distribution(self, db: Session, field: str) -> list[dict[str, Any]]:
        col = getattr(Job, field, None)
        if col is None:
            return []
        rows = (
            db.query(col, func.count(Job.id)).group_by(col).order_by(func.count(Job.id).desc()).all()
        )
        return [{"name": (r[0] or "Not specified"), "count": r[1]} for r in rows]

    def languages(self, db: Session) -> list[dict[str, Any]]:
        jobs = db.query(Job.languages).all()
        counter: Counter = Counter()
        for (langs,) in jobs:
            if not langs:
                continue
            if isinstance(langs, list):
                for lang in langs:
                    counter[str(lang)] += 1
            elif isinstance(langs, str):
                for lang in langs.split(","):
                    counter[lang.strip()] += 1
        total = max(1, len(jobs))
        return [
            {"name": k, "count": v, "pct": round(100 * v / total, 1)}
            for k, v in counter.most_common()
        ]

    def companies(self, db: Session, limit: int = 100) -> dict[str, Any]:
        total = db.query(func.count(Job.id)).scalar() or 0
        unnamed = 0
        for (name,) in db.query(Job.company).all():
            if is_placeholder_company(name):
                unnamed += 1
        rows = (
            db.query(Job.company, func.count(Job.id))
            .filter(Job.company.isnot(None), Job.company != "")
            .group_by(Job.company)
            .order_by(func.count(Job.id).desc())
            .all()
        )
        out: list[dict[str, Any]] = []
        named_jobs = 0
        for company, count in rows:
            if is_placeholder_company(company):
                continue
            named_jobs += count
            cats = (
                db.query(Job.job_category, func.count(Job.id))
                .filter(Job.company == company)
                .group_by(Job.job_category)
                .order_by(func.count(Job.id).desc())
                .limit(3)
                .all()
            )
            if len(out) < limit:
                out.append(
                    {
                        "company": company,
                        "job_count": count,
                        "top_categories": [{"name": c or "Other", "count": n} for c, n in cats],
                    }
                )
        return {
            "companies": out,
            "unnamed_job_count": unnamed,
            "named_job_count": named_jobs,
            "total_jobs": total,
        }

    def career(self, db: Session, category: str) -> dict[str, Any]:
        jobs = (
            db.query(Job)
            .options(joinedload(Job.skills))
            .filter(Job.job_category == category)
            .all()
        )
        if not jobs:
            return {"category": category, "job_count": 0, "message": "No jobs in this category yet."}

        # related careers by skill overlap
        all_jobs = db.query(Job).options(joinedload(Job.skills)).all()
        cat_skills = Counter()
        for job in jobs:
            for js in job.skills:
                cat_skills[js.skill_id] += 1
        top_skill_ids = {s for s, _ in cat_skills.most_common(25)}

        related_scores: dict[str, float] = {}
        for job in all_jobs:
            if job.job_category == category or not job.job_category:
                continue
            skills = {js.skill_id for js in job.skills}
            if not skills:
                continue
            overlap = len(skills & top_skill_ids) / max(1, len(top_skill_ids))
            related_scores[job.job_category] = related_scores.get(job.job_category, 0) + overlap

        related = sorted(related_scores.items(), key=lambda x: x[1], reverse=True)[:5]

        edu = Counter(j.education_level or "Not specified" for j in jobs)
        exp = Counter(j.experience_level or "Not specified" for j in jobs)
        sample_titles = [
            {
                "title": j.job_title,
                "company": j.company,
                "source": j.source,
                "source_url": j.source_url,
                "job_id": j.job_id,
            }
            for j in jobs[:12]
        ]

        return {
            "category": category,
            "job_count": len(jobs),
            "top_skills": self.skill_frequency(db, category=category, limit=15),
            "education": [{"name": k, "count": v} for k, v in edu.most_common()],
            "experience": [{"name": k, "count": v} for k, v in exp.most_common()],
            "related_careers": [{"name": k, "score": round(v, 3)} for k, v in related],
            "sample_jobs": sample_titles,
        }
