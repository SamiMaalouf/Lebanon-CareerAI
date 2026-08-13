"""Ingest cleaned + extracted engineering jobs into PostgreSQL/SQLite."""

from __future__ import annotations

import argparse
import json
import sys
from datetime import date, datetime
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.db.models import Job, JobSkill, Skill
from backend.app.db.session import SessionLocal, init_db
from backend.app.services.classifier import JobClassifier
from backend.app.services.embeddings import EmbeddingService
from data_pipeline.cleaning.company import clean_company
from data_pipeline.cleaning.engineering_filter import (
    ENGINEERING_CATEGORIES,
    filter_engineering_jobs,
)
from data_pipeline.cleaning.extractor import JobExtractor
from data_pipeline.cleaning.pipeline import clean_job, deduplicate_jobs
from data_pipeline.collectors.import_jobs import load_any, load_csv, load_json
from data_pipeline.collectors.synthetic import generate_jobs
from data_pipeline.taxonomy.loader import load_taxonomy

SYNTHETIC_MARKERS = {"synthetic_lebanon_corpus", "synthetic", "example.local"}
ENG_SET = set(ENGINEERING_CATEGORIES)
CATEGORY_REMAP = {"Computer Engineering": "Software Engineering"}


def parse_date(value) -> date | None:
    if not value:
        return None
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    try:
        return date.fromisoformat(str(value)[:10])
    except Exception:
        return None


def upsert_taxonomy(db) -> None:
    tax = load_taxonomy()
    for sid, meta in tax.skills.items():
        existing = db.query(Skill).filter(Skill.skill_id == sid).one_or_none()
        if existing:
            existing.name = meta["name"]
            existing.parent_id = meta.get("parent_id")
            existing.subcategory = meta.get("subcategory")
            existing.aliases = meta.get("aliases")
        else:
            db.add(
                Skill(
                    skill_id=sid,
                    name=meta["name"],
                    parent_id=meta.get("parent_id"),
                    subcategory=meta.get("subcategory"),
                    aliases=meta.get("aliases"),
                )
            )
    db.commit()


def _is_synthetic(record: dict) -> bool:
    source = str(record.get("source") or "").lower()
    url = str(record.get("source_url") or "").lower()
    if any(m in source for m in SYNTHETIC_MARKERS):
        return True
    if "example.local" in url:
        return True
    return False


def ingest_records(
    records: list[dict],
    embed: bool = True,
    train_classifier: bool = True,
    require_real: bool = False,
    append: bool = False,
    engineering_only: bool = True,
) -> dict:
    if require_real:
        synth = [r for r in records if _is_synthetic(r)]
        if synth:
            raise ValueError(
                f"--require-real set but {len(synth)} synthetic records found. Refusing ingest."
            )
        if not records:
            raise ValueError("--require-real set but no records provided.")

    init_db()
    tax = load_taxonomy()
    extractor = JobExtractor(tax)
    classifier = JobClassifier()

    gate_stats: dict[str, int] = {}
    if engineering_only:
        records, gate_stats = filter_engineering_jobs(records)
        print(f"Engineering gate: kept {len(records)} | {gate_stats}")
        if not records:
            raise ValueError("No engineering/internship jobs left after filter.")

    cleaned = [clean_job(r, tax) for r in records]
    cleaned = deduplicate_jobs(cleaned)
    extracted = [extractor.extract_job(r) for r in cleaned]

    # Clamp non-eng categories (legacy imports); fold Computer Engineering into Software
    for r in extracted:
        mapped = CATEGORY_REMAP.get(r.get("job_category") or "")
        if mapped:
            r["job_category"] = mapped
        if r.get("job_category") not in ENG_SET and r.get("job_category") != "Other":
            r["job_category"] = "Other"
            r["category_confidence"] = 0.0

    labeled = [
        r
        for r in extracted
        if r.get("job_category") in ENG_SET and r.get("job_category") != "Other"
    ]
    if train_classifier and len(labeled) >= 15:
        texts = [
            " ".join(filter(None, [r.get("job_title"), r.get("cleaned_text"), r.get("description")]))
            for r in labeled
        ]
        labels = [r["job_category"] for r in labeled]
        classifier.train(texts, labels)
        classifier.save()
        print(f"Trained eng classifier on {len(labeled)} rule-labeled jobs")
    else:
        classifier.load()

    for r in extracted:
        text = " ".join(
            filter(None, [r.get("job_title"), r.get("cleaned_text"), r.get("description")])
        )
        if not r.get("job_category") or r.get("job_category") == "Other":
            cat, conf = classifier.predict(text)
            if cat in ENG_SET and cat != "Other":
                r["job_category"] = cat
                r["category_confidence"] = conf
            else:
                # Last resort: keep Other but prefer any weak rule already applied
                r["job_category"] = "Other"
                r["category_confidence"] = conf
        else:
            r["category_confidence"] = r.get("category_confidence") or 1.0

    db = SessionLocal()
    try:
        upsert_taxonomy(db)
        if not append:
            db.query(JobSkill).delete()
            from backend.app.db.models import JobEmbedding

            db.query(JobEmbedding).delete()
            db.query(Job).delete()
            db.commit()

        job_rows: list[Job] = []
        for r in extracted:
            jid = str(r.get("job_id") or r.get("dedupe_hash"))
            existing = db.query(Job).filter(Job.job_id == jid).one_or_none() if append else None
            if existing:
                continue
            job = Job(
                job_id=jid,
                source=r.get("source") or "unknown",
                source_url=r.get("source_url"),
                collection_date=parse_date(r.get("collection_date")),
                job_title=r.get("job_title") or "Untitled",
                company=clean_company(r.get("company")),
                industry=r.get("industry"),
                location=r.get("location_normalized") or r.get("location"),
                date_posted=parse_date(r.get("date_posted")),
                employment_type=r.get("employment_type"),
                education=r.get("education"),
                experience=r.get("experience"),
                languages=r.get("languages_extracted") or r.get("languages"),
                description=r.get("description"),
                requirements=r.get("requirements"),
                preferred_skills=r.get("preferred_skills")
                if isinstance(r.get("preferred_skills"), str)
                else ", ".join(r.get("preferred_skills_list") or []),
                salary=r.get("salary"),
                raw_text=r.get("raw_text"),
                cleaned_text=r.get("cleaned_text"),
                job_category=r.get("job_category"),
                experience_level=r.get("experience_level"),
                education_level=r.get("education_level"),
                category_confidence=r.get("category_confidence"),
                is_internship=bool(r.get("is_internship")),
            )
            db.add(job)
            db.flush()
            for s in r.get("extracted_skills") or []:
                db.add(
                    JobSkill(
                        job_id=job.id,
                        skill_id=s["skill_id"],
                        is_required=bool(s.get("is_required", True)),
                        confidence=float(s.get("confidence", 1.0)),
                    )
                )
            job_rows.append(job)
        db.commit()

        if embed and job_rows:
            emb = EmbeddingService()
            emb.embed_jobs(db, job_rows)

        out_path = ROOT / "processed_data" / "jobs_processed.json"
        serializable = []
        for r in extracted:
            item = {k: v for k, v in r.items() if k != "extracted_skills"}
            item["extracted_skills"] = r.get("extracted_skills")
            serializable.append(item)
        out_path.write_text(json.dumps(serializable, ensure_ascii=False, indent=2), encoding="utf-8")

        real_count = sum(1 for r in extracted if not _is_synthetic(r))
        cats: dict[str, int] = {}
        for r in extracted:
            c = r.get("job_category") or "Other"
            cats[c] = cats.get(c, 0) + 1
        return {
            "ingested": len(job_rows),
            "real_count": real_count,
            "synthetic_count": len(extracted) - real_count,
            "internship_count": sum(1 for r in extracted if r.get("is_internship")),
            "categories": cats,
            "engineering_gate": gate_stats,
            "processed_path": str(out_path),
        }
    finally:
        db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest Lebanese engineering job postings")
    parser.add_argument("--json", type=str, default=None)
    parser.add_argument("--csv", type=str, default=None)
    parser.add_argument("--excel", type=str, default=None)
    parser.add_argument("--file", type=str, default=None, help="Auto-detect json/csv/xlsx")
    parser.add_argument("--synthetic", type=int, default=0, help="Only used if no files given and >0")
    parser.add_argument("--no-embed", action="store_true")
    parser.add_argument("--require-real", action="store_true")
    parser.add_argument("--append", action="store_true")
    parser.add_argument(
        "--all-jobs",
        action="store_true",
        help="Disable engineering-only filter (not recommended for demo)",
    )
    args = parser.parse_args()

    records: list[dict] = []
    if args.file:
        records.extend(load_any(args.file))
    if args.json:
        records.extend(load_json(args.json))
    if args.csv:
        records.extend(load_csv(args.csv))
    if args.excel:
        records.extend(load_any(args.excel))

    if not records:
        if args.require_real:
            raise SystemExit("--require-real set but no input files provided.")
        if args.synthetic and args.synthetic > 0:
            records = generate_jobs(args.synthetic)
            raw_path = ROOT / "raw_data" / "synthetic_jobs.json"
            raw_path.write_text(json.dumps(records, ensure_ascii=False, indent=2), encoding="utf-8")
            print(f"Generated {len(records)} synthetic jobs -> {raw_path}")
        else:
            merged = ROOT / "raw_data" / "real_jobs_merged.json"
            if merged.exists():
                records = load_json(merged)
                print(f"Loaded {len(records)} from {merged}")
            else:
                raise SystemExit(
                    "No input provided. Use --json/--csv/--file or run collectors first "
                    "(python -m data_pipeline.collectors.run_all)."
                )

    result = ingest_records(
        records,
        embed=not args.no_embed,
        require_real=args.require_real,
        append=args.append,
        engineering_only=not args.all_jobs,
    )
    print(result)


if __name__ == "__main__":
    main()
