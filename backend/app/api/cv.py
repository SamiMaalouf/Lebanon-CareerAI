from fastapi import APIRouter, Depends, File, HTTPException, UploadFile
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.services.cv_analyzer import CVAnalyzer
from backend.app.services.cv_coach import CVCoach

router = APIRouter()
analyzer = CVAnalyzer()
coach = CVCoach()


class ProfileIn(BaseModel):
    skills: list[str] = Field(default_factory=list)
    education_level: str | None = None
    education_fields: list[str] = Field(default_factory=list)
    experience_level: str | None = None
    languages: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)
    target_categories: list[str] = Field(default_factory=list)
    summary: str | None = None


class TextIn(BaseModel):
    text: str


class CoachRequest(BaseModel):
    skills: list[str] = Field(default_factory=list)
    education_level: str | None = None
    education_fields: list[str] = Field(default_factory=list)
    experience_level: str | None = None
    languages: list[str] = Field(default_factory=list)
    projects: list[str] = Field(default_factory=list)
    target_categories: list[str] = Field(default_factory=list)
    detected_sections: list[str] = Field(default_factory=list)
    projects_section_found: bool | None = None
    category: str | None = None
    summary: str | None = None


@router.post("/analyze")
async def analyze_cv(file: UploadFile = File(...)):
    if not file.filename:
        raise HTTPException(status_code=400, detail="Missing filename")
    lower = file.filename.lower()
    if not (lower.endswith(".pdf") or lower.endswith(".docx") or lower.endswith(".txt")):
        raise HTTPException(status_code=400, detail="Supported formats: PDF, DOCX, TXT")
    data = await file.read()
    if len(data) > 8 * 1024 * 1024:
        raise HTTPException(status_code=400, detail="File too large (max 8MB)")
    try:
        return analyzer.analyze_file(file.filename, data)
    except Exception:
        raise HTTPException(
            status_code=400,
            detail="Could not parse this file. Try a text-based PDF, DOCX, or paste the CV text.",
        )


@router.post("/analyze-text")
def analyze_text(payload: TextIn):
    if not payload.text.strip():
        raise HTTPException(status_code=400, detail="text is required")
    try:
        return analyzer.analyze_text(payload.text)
    except Exception:
        raise HTTPException(status_code=400, detail="Could not analyze this CV text.")


@router.post("/coach")
def cv_coach(payload: CoachRequest, db: Session = Depends(get_db)):
    category = payload.category
    if not category and payload.target_categories:
        category = payload.target_categories[0]
    if not category:
        category = "Software Engineering"
    return coach.analyze(db, payload.model_dump(), category=category)
