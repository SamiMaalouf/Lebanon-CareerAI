from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from backend.app.api import careers, cv, evaluation, jobs, market, match, roadmap, skill_gap
from backend.app.core.config import settings
from backend.app.db.session import init_db

app = FastAPI(
    title="Lebanon CareerAI",
    description="AI-Powered Lebanese Career & Skill Gap Analyzer",
    version="1.0.0",
)

origins = [o.strip() for o in settings.cors_origins.split(",") if o.strip()]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins or ["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(market.router, prefix="/api/market", tags=["market"])
app.include_router(jobs.router, prefix="/api/jobs", tags=["jobs"])
app.include_router(careers.router, prefix="/api/careers", tags=["careers"])
app.include_router(cv.router, prefix="/api/cv", tags=["cv"])
app.include_router(match.router, prefix="/api/match", tags=["match"])
app.include_router(skill_gap.router, prefix="/api/skill-gap", tags=["skill-gap"])
app.include_router(roadmap.router, prefix="/api/roadmap", tags=["roadmap"])
app.include_router(evaluation.router, prefix="/api/evaluation", tags=["evaluation"])


@app.on_event("startup")
def on_startup() -> None:
    init_db()


@app.get("/api/health")
def health() -> dict:
    return {"status": "ok", "service": "Lebanon CareerAI"}
