from typing import Any

from fastapi import APIRouter, Depends, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.services.matching import MatchingEngine

router = APIRouter()
engine = MatchingEngine()


class CandidateProfile(BaseModel):
    skills: list[str] = Field(default_factory=list)
    education_level: str | None = None
    education_fields: list[str] = Field(default_factory=list)
    experience_level: str | None = None
    languages: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)
    target_categories: list[str] = Field(default_factory=list)
    summary: str | None = None


class MatchRequest(BaseModel):
    candidate: CandidateProfile
    method: str = "both"
    limit: int = 20
    category: str | None = None


@router.post("")
def match_jobs(payload: MatchRequest, db: Session = Depends(get_db)):
    return engine.rank_jobs(
        db,
        candidate=payload.candidate.model_dump(),
        method=payload.method,
        limit=payload.limit,
        category=payload.category,
    )
