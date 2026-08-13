from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.services.market import MarketService

router = APIRouter()
market = MarketService()


@router.get("/overview")
def overview(db: Session = Depends(get_db)):
    return market.overview(db)


@router.get("/skills")
def skills(
    category: str | None = Query(None),
    limit: int = Query(30, ge=1, le=100),
    db: Session = Depends(get_db),
):
    return {"skills": market.skill_frequency(db, category=category, limit=limit)}


@router.get("/by-category")
def by_category(db: Session = Depends(get_db)):
    return {"categories": market.distribution(db, "job_category")}


@router.get("/education")
def education(db: Session = Depends(get_db)):
    return {"education": market.distribution(db, "education_level")}


@router.get("/experience")
def experience(db: Session = Depends(get_db)):
    return {"experience": market.distribution(db, "experience_level")}


@router.get("/languages")
def languages(db: Session = Depends(get_db)):
    return {"languages": market.languages(db)}


@router.get("/locations")
def locations(db: Session = Depends(get_db)):
    return {"locations": market.distribution(db, "location")}


@router.get("/industries")
def industries(db: Session = Depends(get_db)):
    return {"industries": market.distribution(db, "industry")}


@router.get("/companies")
def companies(
    limit: int = Query(100, ge=1, le=200),
    db: Session = Depends(get_db),
):
    return market.companies(db, limit=limit)
