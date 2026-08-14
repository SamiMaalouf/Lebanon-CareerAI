from fastapi import APIRouter, Depends, HTTPException
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
    limit: int = Field(20, ge=1, le=50)
    category: str | None = None


@router.post("")
def match_jobs(payload: MatchRequest, db: Session = Depends(get_db)):
    if payload.method not in ("keyword", "semantic", "both"):
        raise HTTPException(
            status_code=400, detail="method must be keyword, semantic, or both"
        )
    return engine.rank_jobs(
        db,
        candidate=payload.candidate.model_dump(),
        method=payload.method,
        limit=payload.limit,
        category=payload.category,
    )
