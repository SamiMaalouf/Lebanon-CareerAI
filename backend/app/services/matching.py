from __future__ import annotations

from typing import Any

import numpy as np
from sqlalchemy.orm import Session, joinedload

from backend.app.core.config import settings
from backend.app.db.models import Job, JobEmbedding
from backend.app.services.embeddings import EmbeddingService
from backend.app.services.skill_filters import (
    canonical_category,
    education_field_to_category,
    is_technical,
)
from data_pipeline.taxonomy.loader import load_taxonomy


def _jaccard(a: set[str], b: set[str]) -> float:
    if not a and not b:
        return 0.0
    if not a or not b:
        return 0.0
    return len(a & b) / len(a | b)


def _coverage(have: set[str], needed: set[str]) -> float:
    if not needed:
        return 1.0
    return len(have & needed) / len(needed)


EDU_RANK = {
    None: 0,
    "Bachelor's": 1,
    "Master's": 2,
    "PhD": 3,
}

EXP_RANK = {
    None: 0,
    "Internship": 1,
    "Entry-level": 2,
    "0-2 years": 3,
    "2-5 years": 4,
    "5+ years": 5,
}


class MatchingEngine:
    def __init__(self):
        self.taxonomy = load_taxonomy()
        self.embedder = EmbeddingService()

    def _normalize_skills(self, skills: list[str]) -> set[str]:
        out: set[str] = set()
        for s in skills:
            cid = self.taxonomy.canonical_id(s)
            if cid:
                out.add(cid)
            else:
                out.add(self.taxonomy._slug(s))
        return out

    def _technical_ids(self, skill_ids: set[str]) -> set[str]:
        return {sid for sid in skill_ids if is_technical(self.taxonomy, sid)}

    def _skill_names(self, skill_ids: set[str]) -> list[str]:
        return [self.taxonomy.skills.get(s, {}).get("name", s) for s in skill_ids]

    def _tech_coverage(self, have: set[str], required: set[str], job_skills: set[str]) -> float:
        pool = required if required else job_skills
        if not pool:
            return 0.0
        return _coverage(have, pool)

    def _coverage_counts(
        self, have: set[str], required: set[str], job_skills: set[str]
    ) -> dict[str, int | str]:
        pool = required if required else job_skills
        return {
            "matched_count": len(have & pool),
            "listed_count": len(pool),
            "coverage_of": "required" if required else "listed",
        }

    def keyword_score(self, candidate: dict[str, Any], job: Job) -> dict[str, Any]:
        cand_skills = self._technical_ids(self._normalize_skills(candidate.get("skills") or []))
        job_skills = self._technical_ids({js.skill_id for js in (job.skills or [])})
        required = self._technical_ids(
            {js.skill_id for js in (job.skills or []) if js.is_required}
        )
        overlap = cand_skills & job_skills
        score = _jaccard(cand_skills, job_skills)
        coverage = self._tech_coverage(cand_skills, required, job_skills)
        return {
            "method": "keyword",
            "compatibility_score": round(100 * (0.6 * coverage + 0.4 * score), 2),
            "jaccard": round(score, 4),
            "required_coverage": round(coverage, 4),
            **self._coverage_counts(cand_skills, required, job_skills),
            "matched_skills": self._skill_names(overlap),
            "missing_required": self._skill_names(required - cand_skills),
        }

    def _education_compat(self, candidate: dict[str, Any], job: Job) -> float:
        cand = candidate.get("education_level")
        need = job.education_level
        if not need:
            return 1.0
        return 1.0 if EDU_RANK.get(cand, 0) >= EDU_RANK.get(need, 0) else 0.4

    def _experience_compat(self, candidate: dict[str, Any], job: Job) -> float:
        cand = candidate.get("experience_level")
        need = job.experience_level
        if not need:
            return 1.0
        diff = EXP_RANK.get(cand, 0) - EXP_RANK.get(need, 0)
        if diff >= 0:
            return 1.0
        if diff == -1:
            return 0.6
        return 0.3

    def _category_sim(self, candidate: dict[str, Any], job: Job) -> float:
        targets: set[str] = set()
        for t in candidate.get("target_categories") or []:
            mapped = canonical_category(t) or t
            if mapped:
                targets.add(mapped)
        for f in candidate.get("education_fields") or []:
            mapped = education_field_to_category(f)
            if mapped:
                targets.add(mapped)
        if not targets:
            return 0.5
        if job.job_category in targets:
            return 1.0
        jt = set((job.job_category or "").lower().split())
        best = 0.0
        for t in targets:
            tt = set(t.lower().split())
            if jt & tt:
                best = max(best, 0.7)
        return best

    def semantic_score(
        self,
        candidate: dict[str, Any],
        job: Job,
        cand_vec: np.ndarray | None = None,
        job_vec: np.ndarray | None = None,
    ) -> dict[str, Any]:
        cand_skills = self._technical_ids(self._normalize_skills(candidate.get("skills") or []))
        job_skills = self._technical_ids({js.skill_id for js in (job.skills or [])})
        required = self._technical_ids(
            {js.skill_id for js in (job.skills or []) if js.is_required}
        )

        expanded = set()
        for s in cand_skills:
            expanded |= self.taxonomy.related_ids(s)
        expanded = self._technical_ids(expanded)
        skill_overlap = (len(expanded & job_skills) / len(job_skills)) if job_skills else 0.0
        required_cov = self._tech_coverage(cand_skills, required, job_skills)

        if cand_vec is None:
            profile_text = self._candidate_text(candidate)
            cand_vec = self.embedder.encode_one(profile_text)
        if job_vec is None:
            if job.embedding is not None:
                job_vec = np.asarray(job.embedding.embedding, dtype=np.float32)
            else:
                job_vec = self.embedder.encode_one(self.embedder.job_text(job))

        emb_sim = max(0.0, self.embedder.cosine(cand_vec, job_vec))
        edu = self._education_compat(candidate, job)
        exp = self._experience_compat(candidate, job)
        cat = self._category_sim(candidate, job)

        # blend embedding similarity with taxonomy skill overlap
        skill_sim = 0.5 * emb_sim + 0.5 * skill_overlap
        has_tech_signal = bool(cand_skills & job_skills) or skill_overlap > 0 or required_cov > 0

        score = settings.w_skill_sim * skill_sim + settings.w_required_coverage * required_cov
        if has_tech_signal:
            score += (
                settings.w_education * edu
                + settings.w_experience * exp
                + settings.w_category * cat
            )
        return {
            "method": "semantic",
            "compatibility_score": round(100 * float(score), 2),
            "has_technical_overlap": has_tech_signal,
            "components": {
                "skill_similarity": round(skill_sim, 4),
                "embedding_similarity": round(emb_sim, 4),
                "required_coverage": round(required_cov, 4),
                "education_compatibility": round(edu, 4),
                "experience_compatibility": round(exp, 4),
                "category_similarity": round(cat, 4),
            },
            "matched_skills": self._skill_names(cand_skills & job_skills),
            "missing_required": self._skill_names(required - cand_skills),
            **self._coverage_counts(cand_skills, required, job_skills),
        }

    def _candidate_text(self, candidate: dict[str, Any]) -> str:
        tech_names = self._skill_names(
            self._technical_ids(self._normalize_skills(candidate.get("skills") or []))
        )
        parts = [
            " ".join(tech_names),
            " ".join(candidate.get("education_fields") or []),
            " ".join(candidate.get("projects") or []),
            " ".join(candidate.get("target_categories") or []),
            candidate.get("summary") or "",
        ]
        return "\n".join(p for p in parts if p)

    def rank_jobs(
        self,
        db: Session,
        candidate: dict[str, Any],
        method: str = "both",
        limit: int = 20,
        category: str | None = None,
    ) -> dict[str, Any]:
        q = db.query(Job).options(joinedload(Job.skills), joinedload(Job.embedding))
        if category:
            category = canonical_category(category) or category
            q = q.filter(Job.job_category == category)
        jobs = q.all()
        profile_text = self._candidate_text(candidate)
        cand_vec = self.embedder.encode_one(profile_text) if method in ("semantic", "both") else None

        keyword_ranked = []
        semantic_ranked = []
        for job in jobs:
            base = {
                "job_id": job.job_id,
                "title": job.job_title,
                "company": job.company,
                "location": job.location,
                "category": job.job_category,
            }
            if method in ("keyword", "both"):
                kw = self.keyword_score(candidate, job)
                keyword_ranked.append({**base, **kw})
            if method in ("semantic", "both"):
                job_vec = None
                if job.embedding is not None:
                    job_vec = np.asarray(job.embedding.embedding, dtype=np.float32)
                sem = self.semantic_score(candidate, job, cand_vec=cand_vec, job_vec=job_vec)
                semantic_ranked.append({**base, **sem})

        keyword_ranked = [r for r in keyword_ranked if r.get("matched_skills")]
        semantic_ranked = [
            r
            for r in semantic_ranked
            if r.get("matched_skills") or r.get("has_technical_overlap")
        ]
        keyword_ranked.sort(key=lambda x: x["compatibility_score"], reverse=True)
        semantic_ranked.sort(key=lambda x: x["compatibility_score"], reverse=True)
        return {
            "disclaimer": (
                "Compatibility Score is an analytical estimate based on the collected "
                "Lebanese job dataset and does not represent a guarantee of employment."
            ),
            "keyword": keyword_ranked[:limit],
            "semantic": semantic_ranked[:limit],
        }
