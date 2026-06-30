"""Tiny local RAG corpus tests for V2 Phase 11D Option A.

These tests build temporary FAISS/metadata files under pytest tmp_path only.
They do not copy V1 policy docs or persist vector artifacts in the project tree.
"""

from pathlib import Path

import numpy as np

from api.rag.retriever import lazy_faiss
from api.rag.retriever.policy_retriever import search_policy
from api.rag.vector_store.faiss_manager import add_embeddings, create_index, save_index
from api.rag.vector_store.metadata_manager import load_metadata, save_metadata


class TinyEmbeddingModel:
    def encode(self, queries):
        vectors = []
        for query in queries:
            text = query.lower()
            if "security" in text or "lc" in text or "collateral" in text:
                vectors.append([0.0, 1.0])
            else:
                vectors.append([1.0, 0.0])
        return np.array(vectors, dtype="float32")


def build_tiny_policy_index(tmp_path: Path):
    documents = [
        "Policy source: standard tenor is capped at 30 days for weak liquidity.",
        "Policy source: standby LC is required when collateral support is weak.",
    ]
    embeddings = np.array(
        [
            [1.0, 0.0],
            [0.0, 1.0],
        ],
        dtype="float32",
    )

    index = create_index(dimension=2)
    add_embeddings(index, embeddings)

    index_path = tmp_path / "policy_index.faiss"
    metadata_path = tmp_path / "policy_metadata.pkl"
    save_index(index, str(index_path))
    save_metadata({"documents": documents}, str(metadata_path))
    return index_path, metadata_path, documents


def test_tiny_policy_corpus_can_be_retrieved_from_temp_vector_store(tmp_path, monkeypatch):
    _, _, documents = build_tiny_policy_index(tmp_path)
    lazy_faiss._load_index.cache_clear()
    lazy_faiss._embedding_model.cache_clear()

    monkeypatch.setattr(lazy_faiss, "vector_store_path", lambda filename: str(tmp_path / filename))
    monkeypatch.setattr(lazy_faiss, "_embedding_model", lambda: TinyEmbeddingModel())

    tenor_results = search_policy("What tenor is allowed for weak liquidity?", k=1)
    security_results = search_policy("What security or LC is required?", k=1)

    assert tenor_results == [documents[0]]
    assert security_results == [documents[1]]


def test_tiny_corpus_metadata_round_trip_stays_in_tmp_path(tmp_path):
    _, metadata_path, documents = build_tiny_policy_index(tmp_path)

    metadata = load_metadata(str(metadata_path))

    assert metadata == {"documents": documents}
    assert tmp_path in metadata_path.parents
    assert not Path("api/rag/data").exists()
    assert not Path("api/rag/documents").exists()


def test_missing_tiny_corpus_returns_empty_without_model_load(tmp_path, monkeypatch):
    lazy_faiss._load_index.cache_clear()
    lazy_faiss._embedding_model.cache_clear()

    def fail_model_load():
        raise AssertionError("Embedding model should not load when artifacts are missing")

    monkeypatch.setattr(lazy_faiss, "vector_store_path", lambda filename: str(tmp_path / filename))
    monkeypatch.setattr(lazy_faiss, "_embedding_model", fail_model_load)

    assert search_policy("missing policy", k=1) == []
