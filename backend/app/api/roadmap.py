from fastapi import APIRouter, Depends
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.services.skill_gap import SkillGapEngine

router = APIRouter()
engine = SkillGapEngine()


class RoadmapRequest(BaseModel):
    skills: list[str] = Field(default_factory=list)
    category: str | None = None
    target_categories: list[str] = Field(default_factory=list)
    top_n: int = 10


@router.post("")
def roadmap(payload: RoadmapRequest, db: Session = Depends(get_db)):
    category = payload.category
    if not category and payload.target_categories:
        category = payload.target_categories[0]
    result = engine.analyze(db, payload.model_dump(), category=category, top_n=payload.top_n)
    return {
        "target": category or "All categories",
        "roadmap": result["roadmap"],
        "possessed": result["possessed"],
        "disclaimer": result["disclaimer"],
    }
