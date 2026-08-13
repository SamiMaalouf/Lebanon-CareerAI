from datetime import date, datetime
from typing import Any, Optional

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship

from backend.app.core.config import settings


def _vector_type():
    if settings.database_url.startswith("sqlite"):
        return JSON
    from pgvector.sqlalchemy import Vector

    return Vector(384)


class Base(DeclarativeBase):
    pass


class Job(Base):
    __tablename__ = "jobs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    source: Mapped[str] = mapped_column(String(128), default="unknown")
    source_url: Mapped[Optional[str]] = mapped_column(String(1024), nullable=True)
    collection_date: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    job_title: Mapped[str] = mapped_column(String(512))
    company: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    industry: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    location: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    date_posted: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    employment_type: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    education: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    experience: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    languages: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)
    description: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    requirements: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    preferred_skills: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    salary: Mapped[Optional[str]] = mapped_column(String(256), nullable=True)
    raw_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    cleaned_text: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    job_category: Mapped[Optional[str]] = mapped_column(String(128), index=True, nullable=True)
    experience_level: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    education_level: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    category_confidence: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    is_internship: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)

    skills: Mapped[list["JobSkill"]] = relationship(back_populates="job", cascade="all, delete-orphan")
    embedding: Mapped[Optional["JobEmbedding"]] = relationship(
        back_populates="job", uselist=False, cascade="all, delete-orphan"
    )


class Skill(Base):
    __tablename__ = "skills"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    skill_id: Mapped[str] = mapped_column(String(128), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(256))
    parent_id: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    subcategory: Mapped[Optional[str]] = mapped_column(String(128), nullable=True)
    aliases: Mapped[Optional[Any]] = mapped_column(JSON, nullable=True)


class JobSkill(Base):
    __tablename__ = "job_skills"
    __table_args__ = (UniqueConstraint("job_id", "skill_id", "is_required", name="uq_job_skill_req"),)

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), index=True)
    skill_id: Mapped[str] = mapped_column(String(128), index=True)
    is_required: Mapped[bool] = mapped_column(Boolean, default=True)
    confidence: Mapped[float] = mapped_column(Float, default=1.0)

    job: Mapped["Job"] = relationship(back_populates="skills")


class JobEmbedding(Base):
    __tablename__ = "job_embeddings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    job_id: Mapped[int] = mapped_column(ForeignKey("jobs.id", ondelete="CASCADE"), unique=True)
    model_name: Mapped[str] = mapped_column(String(256))
    embedding: Mapped[Any] = mapped_column(_vector_type())

    job: Mapped["Job"] = relationship(back_populates="embedding")


class EvaluationResult(Base):
    __tablename__ = "evaluation_results"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    experiment: Mapped[str] = mapped_column(String(128), index=True)
    metrics: Mapped[Any] = mapped_column(JSON)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
