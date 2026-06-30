"""Lazy FAISS retrieval helpers for V2 RAG.

The module deliberately avoids loading sentence-transformer models or FAISS
artifacts at import time. V2 does not copy vector artifacts by default, so a
missing index returns no retrieved context instead of breaking API startup.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path
from typing import Any

from api.core.config import settings


@lru_cache(maxsize=1)
def _embedding_model():
    from sentence_transformers import SentenceTransformer

    try:
        return SentenceTransformer(
            settings.embeddings_model_name,
            local_files_only=True,
        )
    except TypeError:
        return SentenceTransformer(settings.embeddings_model_name)


@lru_cache(maxsize=None)
def _load_index(index_path: str, metadata_path: str) -> tuple[Any, dict[str, Any]]:
    import pickle

    import faiss

    index_file = Path(index_path)
    metadata_file = Path(metadata_path)
    if not index_file.exists() or not metadata_file.exists():
        return None, {"documents": []}

    index = faiss.read_index(str(index_file))
    with metadata_file.open("rb") as handle:
        metadata = pickle.load(handle)
    return index, metadata


def vector_store_path(filename: str) -> str:
    return str(settings.vector_store_dir / filename)


def search_index(query: str, index_filename: str, metadata_filename: str, k: int) -> list[str]:
    index, metadata = _load_index(
        vector_store_path(index_filename),
        vector_store_path(metadata_filename),
    )
    if index is None:
        return []

    try:
        query_embedding = _embedding_model().encode([query])
        _, indices = index.search(query_embedding, k)
    except Exception:
        if hasattr(_embedding_model, "cache_clear"):
            _embedding_model.cache_clear()
        return []

    results: list[str] = []
    seen: set[str] = set()
    documents = metadata.get("documents", [])
    for idx in indices[0]:
        if idx < 0 or idx >= len(documents):
            continue
        doc = documents[idx]
        if doc not in seen:
            seen.add(doc)
            results.append(doc)
    return results
