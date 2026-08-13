from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from backend.app.db.models import EvaluationResult
from backend.app.db.session import get_db

router = APIRouter()


@router.get("/summary")
def evaluation_summary(db: Session = Depends(get_db)):
    rows = (
        db.query(EvaluationResult)
        .order_by(EvaluationResult.created_at.desc())
        .limit(20)
        .all()
    )
    by_exp: dict = {}
    for row in rows:
        if row.experiment not in by_exp:
            by_exp[row.experiment] = {
                "experiment": row.experiment,
                "metrics": row.metrics,
                "created_at": row.created_at.isoformat() if row.created_at else None,
            }
    if not by_exp:
        return {
            "results": {},
            "note": "Run `python -m evaluation.run_all` after ingest to populate metrics.",
        }
    return {"results": by_exp}
