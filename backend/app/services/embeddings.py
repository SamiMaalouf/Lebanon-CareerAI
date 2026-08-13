from __future__ import annotations

from functools import lru_cache
from typing import TYPE_CHECKING

import numpy as np
from sqlalchemy.orm import Session

from backend.app.core.config import settings
from backend.app.db.models import Job, JobEmbedding

if TYPE_CHECKING:
    pass


class EmbeddingService:
    """Sentence-Transformer embeddings with a deterministic hashing fallback."""

    def __init__(self, model_name: str | None = None):
        self.model_name = model_name or settings.embedding_model
        self._model = None
        self._backend = "unset"
        self.dim = 384

    def _load(self) -> None:
        if self._backend != "unset":
            return
        try:
            from sentence_transformers import SentenceTransformer

            self._model = SentenceTransformer(self.model_name)
            self._backend = "sentence-transformers"
            dim_fn = getattr(self._model, "get_embedding_dimension", None) or getattr(
                self._model, "get_sentence_embedding_dimension", None
            )
            self.dim = int(dim_fn()) if dim_fn else 384
        except Exception as exc:  # noqa: BLE001
            print(f"[embeddings] Falling back to hashing encoder ({exc})")
            self._model = None
            self._backend = "hash"
            self.dim = 384

    def encode(self, texts: list[str]) -> np.ndarray:
        self._load()
        cleaned = [t if t and t.strip() else " " for t in texts]
        if self._backend == "sentence-transformers":
            vectors = self._model.encode(
                cleaned, normalize_embeddings=True, show_progress_bar=False
            )
            return np.asarray(vectors, dtype=np.float32)
        return np.vstack([self._hash_embed(t) for t in cleaned])

    def _hash_embed(self, text: str) -> np.ndarray:
        vec = np.zeros(self.dim, dtype=np.float32)
        tokens = text.lower().split()
        if not tokens:
            return vec
        for tok in tokens:
            h = hash(tok) % self.dim
            vec[h] += 1.0
            h2 = hash(tok[::-1]) % self.dim
            vec[h2] -= 0.5
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm
        return vec

    def encode_one(self, text: str) -> np.ndarray:
        return self.encode([text])[0]

    def job_text(self, job: Job) -> str:
        parts = [
            job.job_title or "",
            job.job_category or "",
            job.cleaned_text or "",
            job.description or "",
            job.requirements or "",
        ]
        return "\n".join(p for p in parts if p)

    def embed_jobs(self, db: Session, jobs: list[Job], batch_size: int = 32) -> int:
        self._load()
        ids = [j.id for j in jobs]
        if ids:
            db.query(JobEmbedding).filter(JobEmbedding.job_id.in_(ids)).delete(
                synchronize_session=False
            )
            db.commit()

        count = 0
        label = self.model_name if self._backend == "sentence-transformers" else "hashing-encoder"
        for i in range(0, len(jobs), batch_size):
            batch = jobs[i : i + batch_size]
            texts = [self.job_text(j) for j in batch]
            vectors = self.encode(texts)
            for job, vec in zip(batch, vectors):
                # pad/trim to 384 for pgvector column
                arr = np.asarray(vec, dtype=np.float32)
                if arr.shape[0] < 384:
                    arr = np.pad(arr, (0, 384 - arr.shape[0]))
                elif arr.shape[0] > 384:
                    arr = arr[:384]
                db.add(
                    JobEmbedding(
                        job_id=job.id,
                        model_name=label,
                        embedding=arr.tolist(),
                    )
                )
                count += 1
            db.commit()
        return count

    @staticmethod
    def cosine(a: np.ndarray, b: np.ndarray) -> float:
        a = np.asarray(a, dtype=np.float32)
        b = np.asarray(b, dtype=np.float32)
        denom = float(np.linalg.norm(a) * np.linalg.norm(b))
        if denom == 0:
            return 0.0
        return float(np.dot(a, b) / denom)


@lru_cache(maxsize=1)
def get_model():
    svc = EmbeddingService()
    svc._load()
    return svc._model
