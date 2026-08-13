from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.services.skill_gap import SkillGapEngine

router = APIRouter()
engine = SkillGapEngine()


class GapRequest(BaseModel):
    skills: list[str] = Field(default_factory=list)
    education_level: str | None = None
    education_fields: list[str] = Field(default_factory=list)
    experience_level: str | None = None
    target_categories: list[str] = Field(default_factory=list)
    category: str | None = None
    top_n: int = 15


@router.post("")
def skill_gap(payload: GapRequest, db: Session = Depends(get_db)):
    category = payload.category
    if not category and payload.target_categories:
        category = payload.target_categories[0]
    return engine.analyze(db, payload.model_dump(), category=category, top_n=payload.top_n)
