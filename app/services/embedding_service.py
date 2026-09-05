from __future__ import annotations

from functools import lru_cache

from sentence_transformers import SentenceTransformer

from app.core.config import settings


@lru_cache(maxsize=1)
def _get_model() -> SentenceTransformer:
    return SentenceTransformer(settings.embedding_model_name)


def embed_text(text: str) -> list[float]:
    vector = _get_model().encode(text, normalize_embeddings=True)
    return [float(value) for value in vector.tolist()]


def embed_texts(texts: list[str]) -> list[list[float]]:
    vectors = _get_model().encode(texts, normalize_embeddings=True)
    return [[float(value) for value in vector.tolist()] for vector in vectors]
