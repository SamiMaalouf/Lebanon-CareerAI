from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from backend.app.db.session import get_db
from backend.app.services.market import MarketService

router = APIRouter()
market = MarketService()


@router.get("/{category}")
def career_detail(category: str, db: Session = Depends(get_db)):
    # allow URL-encoded spaces
    data = market.career(db, category)
    if data.get("job_count", 0) == 0:
        # try replace dashes
        alt = category.replace("-", " ")
        data = market.career(db, alt)
    if data.get("job_count", 0) == 0:
        raise HTTPException(status_code=404, detail=f"No jobs found for category '{category}'")
    return data
