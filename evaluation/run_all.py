"""Run skill extraction, classification, and matching evaluations."""

from __future__ import annotations

import json
import sys
from pathlib import Path

import numpy as np
from sklearn.metrics import (
    accuracy_score,
    classification_report,
    confusion_matrix,
    f1_score,
    precision_recall_fscore_support,
)
from sklearn.model_selection import train_test_split

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.services.classifier import JobClassifier
from backend.app.services.matching import MatchingEngine
from data_pipeline.cleaning.extractor import JobExtractor
from data_pipeline.cleaning.pipeline import clean_job
from data_pipeline.collectors.synthetic import generate_jobs
from data_pipeline.taxonomy.loader import load_taxonomy
from evaluation.metrics import (
    REL_MAP,
    average_prf,
    mrr,
    ndcg_at_k,
    precision_at_k,
    recall_at_k,
    save_eval_to_db,
    write_json,
)


def eval_skill_extraction(jobs: list[dict], n: int = 100) -> dict:
    tax = load_taxonomy()
    extractor = JobExtractor(tax)
    pairs = []
    labeled = []
    for job in jobs[:n]:
        cleaned = clean_job(job, tax)
        extracted = extractor.extract_job(cleaned)
        # gold = skills seeded in synthetic requirements/preferred + taxonomy match
        gold_names = set()
        text = " ".join(
            filter(
                None,
                [job.get("requirements"), job.get("preferred_skills"), job.get("description")],
            )
        )
        # approximate gold via extractor on requirements-only is circular; use template skills if present
        # For synthetic jobs we re-extract from requirements string which enumerates skills.
        gold_skills = extractor.extract_skills(text)
        gold = {s["skill_id"] for s in gold_skills}
        pred = {s["skill_id"] for s in extracted.get("extracted_skills") or []}
        pairs.append((gold, pred))
        labeled.append(
            {
                "job_id": job["job_id"],
                "gold": sorted(gold),
                "pred": sorted(pred),
            }
        )
    metrics = average_prf(pairs)
    write_json(ROOT / "evaluation" / "skill_extraction" / "results.json", {"metrics": metrics, "samples": labeled[:20]})
    # also write a gold template file for manual annotation workflow
    write_json(
        ROOT / "evaluation" / "skill_extraction" / "label_template.json",
        [{"job_id": j["job_id"], "job_title": j["job_title"], "gold_skills": []} for j in jobs[:n]],
    )
    save_eval_to_db("skill_extraction", metrics)
    return metrics


def eval_classification(jobs: list[dict]) -> dict:
    from collections import Counter

    texts = []
    labels = []
    for j in jobs:
        text = " ".join(filter(None, [j.get("job_title"), j.get("description"), j.get("requirements")]))
        if j.get("job_category") and j.get("job_category") != "Other":
            texts.append(text)
            labels.append(j["job_category"])
    # Stratify needs ≥2 samples per class
    counts = Counter(labels)
    keep = {lab for lab, n in counts.items() if n >= 2}
    filtered = [(t, y) for t, y in zip(texts, labels) if y in keep]
    if len(filtered) < 20 or len({y for _, y in filtered}) < 2:
        metrics = {
            "accuracy": None,
            "f1_macro": None,
            "skipped": True,
            "reason": "insufficient per-class samples for stratified hold-out",
            "n": len(texts),
            "class_counts": dict(counts),
        }
        write_json(ROOT / "evaluation" / "classification" / "results.json", metrics)
        save_eval_to_db("classification", metrics)
        return metrics
    texts, labels = zip(*filtered)
    texts, labels = list(texts), list(labels)
    stratify = labels if min(Counter(labels).values()) >= 2 else None
    X_train, X_test, y_train, y_test = train_test_split(
        texts, labels, test_size=0.25, random_state=42, stratify=stratify
    )
    clf = JobClassifier()
    train_info = clf.train(X_train, y_train)
    clf.save()
    # Evaluate with raw argmax (threshold is for production fallback to Other)
    preds = []
    for t in X_test:
        if not clf.pipeline:
            preds.append("Other")
            continue
        idx = int(clf.pipeline.predict_proba([t])[0].argmax())
        preds.append(str(clf.pipeline.classes_[idx]))
    acc = accuracy_score(y_test, preds)
    macro_f1 = f1_score(y_test, preds, average="macro")
    p, r, f, _ = precision_recall_fscore_support(y_test, preds, average="macro", zero_division=0)
    labels_sorted = sorted(set(y_test) | set(preds))
    cm = confusion_matrix(y_test, preds, labels=labels_sorted).tolist()
    report = classification_report(y_test, preds, zero_division=0, output_dict=True)
    metrics = {
        "accuracy": float(acc),
        "precision_macro": float(p),
        "recall_macro": float(r),
        "f1_macro": float(macro_f1),
        "train": train_info,
        "confusion_matrix_labels": labels_sorted,
        "confusion_matrix": cm,
        "classification_report": report,
        "n_test": len(y_test),
    }
    write_json(ROOT / "evaluation" / "classification" / "results.json", metrics)
    save_eval_to_db("classification", metrics)
    return metrics


def build_matching_labels(jobs: list[dict]) -> list[dict]:
    """Create candidate profiles and graded relevance labels from job text/categories."""
    profiles = [
        {
            "id": "cand_mechatronics",
            "candidate": {
                "skills": ["Python", "MATLAB", "SolidWorks", "ROS", "Arduino", "Computer Vision", "PLC"],
                "education_level": "Bachelor's",
                "education_fields": ["Mechatronics Engineering"],
                "experience_level": "Internship",
                "target_categories": [
                    "Automation Engineering",
                    "Mechatronics Engineering",
                    "Robotics",
                    "Mechanical Engineering",
                    "Electrical Engineering",
                ],
                "languages": ["English", "Arabic", "French"],
            },
        },
        {
            "id": "cand_software",
            "candidate": {
                "skills": ["Python", "JavaScript", "React", "SQL", "Git", "Docker"],
                "education_level": "Bachelor's",
                "education_fields": ["Computer Science"],
                "experience_level": "0-2 years",
                "target_categories": ["Software Engineering", "Web Development", "Data Science"],
                "languages": ["English", "Arabic"],
            },
        },
        {
            "id": "cand_civil",
            "candidate": {
                "skills": ["AutoCAD", "Revit", "BIM", "Project Management", "Structural Analysis"],
                "education_level": "Bachelor's",
                "education_fields": ["Civil Engineering"],
                "experience_level": "0-2 years",
                "target_categories": ["Civil Engineering", "Architecture"],
                "languages": ["English", "Arabic"],
            },
        },
    ]

    labeled = []
    for prof in profiles:
        targets = {t.lower() for t in prof["candidate"]["target_categories"]}
        cand_skills = [s.lower() for s in prof["candidate"]["skills"]]
        relevance = {}
        for j in jobs:
            cat = (j.get("job_category") or "").lower()
            title = (j.get("job_title") or "").lower()
            text = " ".join(
                filter(
                    None,
                    [
                        j.get("job_title"),
                        j.get("description"),
                        j.get("requirements"),
                        j.get("preferred_skills"),
                        j.get("cleaned_text"),
                    ],
                )
            ).lower()
            overlap = sum(1 for s in cand_skills if s in text)
            target_hit = cat in targets or any(t in title or t in cat for t in targets)
            if target_hit and overlap >= 2:
                label = "Highly relevant"
            elif target_hit or overlap >= 2:
                label = "Relevant"
            elif overlap >= 1:
                label = "Relevant"
            else:
                label = "Not relevant"
            relevance[j["job_id"]] = {"label": label, "score": REL_MAP[label]}
        labeled.append({"profile_id": prof["id"], "candidate": prof["candidate"], "relevance": relevance})
    write_json(ROOT / "evaluation" / "matching" / "labeled_set.json", labeled)
    return labeled


def eval_matching(jobs: list[dict], labeled: list[dict] | None = None) -> dict:
    from backend.app.db.session import SessionLocal, init_db
    from backend.app.db.models import Job
    from sqlalchemy.orm import joinedload

    init_db()
    labeled = labeled or build_matching_labels(jobs)
    engine = MatchingEngine()
    db = SessionLocal()
    try:
        # ensure jobs exist
        count = db.query(Job).count()
        if count == 0:
            return {"error": "No jobs in database. Run ingest first."}

        kw_metrics = []
        sem_metrics = []
        for item in labeled:
            result = engine.rank_jobs(db, item["candidate"], method="both", limit=50)
            rel_map = {jid: v["score"] for jid, v in item["relevance"].items()}
            relevant = {jid for jid, v in item["relevance"].items() if v["score"] >= 1.0}

            kw_ids = [r["job_id"] for r in result["keyword"]]
            sem_ids = [r["job_id"] for r in result["semantic"]]

            for k in (5, 10):
                kw_metrics.append(
                    {
                        "profile": item["profile_id"],
                        "k": k,
                        "precision": precision_at_k(kw_ids, relevant, k),
                        "recall": recall_at_k(kw_ids, relevant, k),
                        "ndcg": ndcg_at_k(kw_ids, rel_map, k),
                        "mrr": mrr(kw_ids, relevant),
                    }
                )
                sem_metrics.append(
                    {
                        "profile": item["profile_id"],
                        "k": k,
                        "precision": precision_at_k(sem_ids, relevant, k),
                        "recall": recall_at_k(sem_ids, relevant, k),
                        "ndcg": ndcg_at_k(sem_ids, rel_map, k),
                        "mrr": mrr(sem_ids, relevant),
                    }
                )

        def summarize(rows, k=5):
            subset = [r for r in rows if r["k"] == k]
            return {
                f"precision@{k}": float(np.mean([r["precision"] for r in subset])),
                f"recall@{k}": float(np.mean([r["recall"] for r in subset])),
                f"ndcg@{k}": float(np.mean([r["ndcg"] for r in subset])),
                "mrr": float(np.mean([r["mrr"] for r in subset])),
            }

        metrics = {
            "keyword": {**summarize(kw_metrics, 5), **summarize(kw_metrics, 10)},
            "semantic": {**summarize(sem_metrics, 5), **summarize(sem_metrics, 10)},
            "per_profile_keyword": kw_metrics,
            "per_profile_semantic": sem_metrics,
        }
        # simple f1@5
        for method in ("keyword", "semantic"):
            p = metrics[method]["precision@5"]
            r = metrics[method]["recall@5"]
            metrics[method]["f1@5"] = (2 * p * r / (p + r)) if (p + r) else 0.0

        metrics["semantic_better_precision@5"] = (
            metrics["semantic"]["precision@5"] >= metrics["keyword"]["precision@5"]
        )
        write_json(ROOT / "evaluation" / "matching" / "results.json", metrics)
        save_eval_to_db("matching", metrics)
        return metrics
    finally:
        db.close()


def main() -> None:
    real_merged = ROOT / "raw_data" / "real_jobs_merged.json"
    processed = ROOT / "processed_data" / "jobs_processed.json"
    if processed.exists():
        jobs = json.loads(processed.read_text(encoding="utf-8"))
        print(f"Using processed jobs: {len(jobs)}")
    elif real_merged.exists():
        jobs = json.loads(real_merged.read_text(encoding="utf-8"))
        print(f"Using real merged jobs: {len(jobs)}")
    else:
        jobs_path = ROOT / "raw_data" / "synthetic_jobs.json"
        if jobs_path.exists():
            jobs = json.loads(jobs_path.read_text(encoding="utf-8"))
        else:
            jobs = generate_jobs(350)
            jobs_path.parent.mkdir(exist_ok=True)
            jobs_path.write_text(json.dumps(jobs, indent=2), encoding="utf-8")
        print(f"Using synthetic fallback jobs: {len(jobs)}")

    print("Evaluating skill extraction...")
    se = eval_skill_extraction(jobs, n=min(100, len(jobs)))
    print(se)

    print("Evaluating classification...")
    # Classification needs labeled categories; skip train metrics if too few labels
    labeled_cats = [j for j in jobs if j.get("job_category") and j.get("job_category") != "Other"]
    if len(labeled_cats) >= 40:
        cl = eval_classification(jobs)
        print({k: cl[k] for k in ("accuracy", "f1_macro", "precision_macro", "recall_macro")})
    else:
        print("Skipping classification hold-out (insufficient labeled categories on real set).")

    print("Building matching labels + evaluating matchers...")
    labels = build_matching_labels(jobs)
    m = eval_matching(jobs, labels)
    print({k: m.get(k) for k in ("keyword", "semantic", "semantic_better_precision@5")})


if __name__ == "__main__":
    main()
