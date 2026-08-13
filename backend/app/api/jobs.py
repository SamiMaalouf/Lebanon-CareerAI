from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_
from sqlalchemy.orm import Session, joinedload

from backend.app.db.models import Job, JobSkill
from backend.app.db.session import get_db
from backend.app.services.skill_filters import canonical_category
from data_pipeline.taxonomy.loader import load_taxonomy

router = APIRouter()
taxonomy = load_taxonomy()


def _serialize_job(job: Job, include_text: bool = False) -> dict[str, Any]:
    skills = [
        {
            "skill_id": js.skill_id,
            "name": taxonomy.skills.get(js.skill_id, {}).get("name", js.skill_id),
            "is_required": js.is_required,
        }
        for js in (job.skills or [])
    ]
    out = {
        "job_id": job.job_id,
        "title": job.job_title,
        "company": job.company,
        "location": job.location,
        "category": job.job_category,
        "category_confidence": job.category_confidence,
        "source": job.source,
        "source_url": job.source_url,
        "collection_date": job.collection_date.isoformat() if job.collection_date else None,
        "date_posted": job.date_posted.isoformat() if job.date_posted else None,
        "employment_type": job.employment_type,
        "industry": job.industry,
        "experience_level": job.experience_level,
        "education_level": job.education_level,
        "salary": job.salary,
        "is_internship": bool(getattr(job, "is_internship", False)),
        "skills": skills,
    }
    if include_text:
        out.update(
            {
                "description": job.description,
                "requirements": job.requirements,
                "preferred_skills": job.preferred_skills,
                "education": job.education,
                "experience": job.experience,
                "languages": job.languages,
                "cleaned_text": job.cleaned_text,
            }
        )
    return out


@router.get("")
def list_jobs(
    q: str | None = Query(None),
    category: str | None = None,
    location: str | None = None,
    company: str | None = None,
    source: str | None = None,
    skill: str | None = None,
    internship: bool | None = Query(None, description="Filter engineering internships"),
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: Session = Depends(get_db),
):
    query = db.query(Job).options(joinedload(Job.skills))
    if q:
        like = f"%{q}%"
        query = query.filter(
            or_(
                Job.job_title.ilike(like),
                Job.company.ilike(like),
                Job.description.ilike(like),
                Job.cleaned_text.ilike(like),
            )
        )
    if category:
        category = canonical_category(category) or category
        query = query.filter(Job.job_category == category)
    if location:
        query = query.filter(Job.location.ilike(f"%{location}%"))
    if company:
        query = query.filter(Job.company.ilike(f"%{company}%"))
    if source:
        query = query.filter(Job.source == source)
    if internship is True:
        query = query.filter(Job.is_internship.is_(True))
    elif internship is False:
        query = query.filter(Job.is_internship.is_(False))
    if skill:
        sid = taxonomy.canonical_id(skill) or taxonomy._slug(skill)
        query = query.join(JobSkill).filter(JobSkill.skill_id == sid)

    total = query.count()
    rows = (
        query.order_by(Job.id.desc())
        .offset((page - 1) * page_size)
        .limit(page_size)
        .all()
    )
    return {
        "total": total,
        "page": page,
        "page_size": page_size,
        "jobs": [_serialize_job(j) for j in rows],
    }


@router.get("/{job_id}")
def job_detail(job_id: str, db: Session = Depends(get_db)):
    job = (
        db.query(Job)
        .options(joinedload(Job.skills))
        .filter(Job.job_id == job_id)
        .one_or_none()
    )
    if not job:
        raise HTTPException(status_code=404, detail="Job not found")
    return _serialize_job(job, include_text=True)
