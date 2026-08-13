"""Evaluation metrics and runners for skill extraction, classification, and matching."""

from __future__ import annotations

import json
import math
from collections import defaultdict
from pathlib import Path
from typing import Any

import numpy as np

ROOT = Path(__file__).resolve().parents[1]


def precision_recall_f1(gold: set[str], pred: set[str]) -> dict[str, float]:
    if not gold and not pred:
        return {"precision": 1.0, "recall": 1.0, "f1": 1.0}
    tp = len(gold & pred)
    precision = tp / len(pred) if pred else 0.0
    recall = tp / len(gold) if gold else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) else 0.0
    return {"precision": precision, "recall": recall, "f1": f1}


def average_prf(pairs: list[tuple[set[str], set[str]]]) -> dict[str, float]:
    if not pairs:
        return {"precision": 0.0, "recall": 0.0, "f1": 0.0, "n": 0}
    scores = [precision_recall_f1(g, p) for g, p in pairs]
    return {
        "precision": float(np.mean([s["precision"] for s in scores])),
        "recall": float(np.mean([s["recall"] for s in scores])),
        "f1": float(np.mean([s["f1"] for s in scores])),
        "n": len(scores),
    }


def dcg(relevances: list[float], k: int) -> float:
    total = 0.0
    for i, rel in enumerate(relevances[:k]):
        total += (2**rel - 1) / math.log2(i + 2)
    return total


def ndcg_at_k(ranked_ids: list[str], relevance: dict[str, float], k: int = 5) -> float:
    rels = [relevance.get(i, 0.0) for i in ranked_ids[:k]]
    ideal = sorted(relevance.values(), reverse=True)
    idcg = dcg(ideal, k)
    if idcg == 0:
        return 0.0
    return dcg(rels, k) / idcg


def precision_at_k(ranked_ids: list[str], relevant: set[str], k: int = 5) -> float:
    top = ranked_ids[:k]
    if not top:
        return 0.0
    return len([x for x in top if x in relevant]) / len(top)


def recall_at_k(ranked_ids: list[str], relevant: set[str], k: int = 5) -> float:
    if not relevant:
        return 0.0
    top = set(ranked_ids[:k])
    return len(top & relevant) / len(relevant)


def mrr(ranked_ids: list[str], relevant: set[str]) -> float:
    for i, rid in enumerate(ranked_ids):
        if rid in relevant:
            return 1.0 / (i + 1)
    return 0.0


REL_MAP = {"Highly relevant": 2.0, "Relevant": 1.0, "Not relevant": 0.0}


def save_eval_to_db(experiment: str, metrics: dict[str, Any]) -> None:
    import sys

    if str(ROOT) not in sys.path:
        sys.path.insert(0, str(ROOT))
    from backend.app.db.models import EvaluationResult
    from backend.app.db.session import SessionLocal, init_db

    init_db()
    db = SessionLocal()
    try:
        db.add(EvaluationResult(experiment=experiment, metrics=metrics))
        db.commit()
    finally:
        db.close()


def write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
