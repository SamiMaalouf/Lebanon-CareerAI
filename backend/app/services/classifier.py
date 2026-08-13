from __future__ import annotations

from pathlib import Path

import joblib
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from backend.app.core.config import settings

MODEL_DIR = Path("models/job_classifier")
MODEL_PATH = MODEL_DIR / "classifier.joblib"

DEFAULT_CATEGORIES = [
    "Software Engineering",
    "Data Science",
    "Artificial Intelligence",
    "Cybersecurity",
    "Web Development",
    "Electrical Engineering",
    "Electronics Engineering",
    "Mechanical Engineering",
    "Mechatronics Engineering",
    "Automation Engineering",
    "Robotics",
    "Civil Engineering",
    "Architecture",
    "Other",
]


class JobClassifier:
    def __init__(self, confidence_threshold: float | None = None):
        self.confidence_threshold = (
            confidence_threshold
            if confidence_threshold is not None
            else settings.confidence_threshold
        )
        self.pipeline: Pipeline | None = None

    def train(self, texts: list[str], labels: list[str]) -> dict:
        self.pipeline = Pipeline(
            [
                (
                    "tfidf",
                    TfidfVectorizer(
                        ngram_range=(1, 2),
                        min_df=1,
                        max_features=20000,
                        stop_words="english",
                    ),
                ),
                (
                    "clf",
                    LogisticRegression(
                        max_iter=2000,
                        class_weight="balanced",
                    ),
                ),
            ]
        )
        self.pipeline.fit(texts, labels)
        preds = self.pipeline.predict(texts)
        acc = float(np.mean(preds == np.array(labels)))
        return {"train_accuracy": acc, "n": len(texts)}

    def save(self, path: Path | None = None) -> None:
        path = path or MODEL_PATH
        path.parent.mkdir(parents=True, exist_ok=True)
        joblib.dump(
            {"pipeline": self.pipeline, "threshold": self.confidence_threshold},
            path,
        )

    def load(self, path: Path | None = None) -> bool:
        path = path or MODEL_PATH
        if not path.exists():
            self.pipeline = None
            return False
        payload = joblib.load(path)
        self.pipeline = payload["pipeline"]
        self.confidence_threshold = payload.get("threshold", self.confidence_threshold)
        return True

    def predict(self, text: str) -> tuple[str, float]:
        if not self.pipeline or not text:
            return "Other", 0.0
        proba = self.pipeline.predict_proba([text])[0]
        idx = int(np.argmax(proba))
        conf = float(proba[idx])
        label = str(self.pipeline.classes_[idx])
        if label not in DEFAULT_CATEGORIES:
            return "Other", conf
        if conf < self.confidence_threshold:
            return "Other", conf
        return label, conf

    def predict_batch(self, texts: list[str]) -> list[tuple[str, float]]:
        return [self.predict(t) for t in texts]
