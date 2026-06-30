"""Free local retrieval for project-aware copilot answers.

This is Phase 5's retrieval layer. It deliberately uses local files and
scikit-learn TF-IDF so it works without paid APIs, external services, or model
downloads. Later phases can add FAISS/sentence-transformer indexing beside it.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity

from api.core.config import PROJECT_ROOT


MAX_CHARS_PER_CHUNK = 1800
CHUNK_OVERLAP = 250

CURATED_PROJECT_FILES = [
    "FORMULAS_AND_DATA_POINTS.md",
    "PROJECT_INTERVIEW_GUIDE.md",
    "SYNTHETIC_FLOW_CALCULATION_GUIDE.md",
    "CALIBRATION_PHASES_FINAL_GUIDE.md",
    "HARDCODED_ASSUMPTIONS_AUDIT.md",
    "COPILOT_PHASE_1_AUDIT.md",
    "docs/free_source_calibration_runbook.md",
    "docs/free_source_csv_schemas.md",
    "api/credit_decision/engine.py",
    "api/machine_learning/pd_model.py",
    "api/machine_learning/loss_model.py",
    "api/market_data/stress_index.py",
    "api/market_data/regime_detection.py",
    "api/shared/financial_ratios.py",
    "data/reports/calibration/training_summary.json",
    "data/reports/calibration/validation_report.json",
    "data/reports/calibration/artifact_manifest.json",
    "data/models/pd_blend_config.json",
    "data/models/scenario_multiplier_config.json",
    "data/models/default_correlation_config.json",
    "data/models/collateral_strength_config.json",
]


@dataclass(frozen=True)
class RetrievalChunk:
    chunk_id: str
    source_path: str
    title: str
    text: str
    metadata: dict[str, Any]


@dataclass(frozen=True)
class RetrievalIndex:
    chunks: list[RetrievalChunk]
    vectorizer: TfidfVectorizer
    matrix: Any


def _read_text(path: Path) -> str:
    if not path.exists() or not path.is_file():
        return ""
    try:
        return path.read_text(encoding="utf-8-sig", errors="ignore")
    except Exception:
        return ""


def _chunk_text(text: str, max_chars: int = MAX_CHARS_PER_CHUNK) -> list[str]:
    clean = "\n".join(line.rstrip() for line in text.splitlines()).strip()
    if not clean:
        return []
    chunks: list[str] = []
    start = 0
    while start < len(clean):
        end = min(len(clean), start + max_chars)
        if end < len(clean):
            split_at = clean.rfind("\n\n", start, end)
            if split_at > start + 400:
                end = split_at
        chunk = clean[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(clean):
            break
        start = max(0, end - CHUNK_OVERLAP)
    return chunks


def _title_for_chunk(source_path: str, chunk: str, index: int) -> str:
    for line in chunk.splitlines():
        stripped = line.strip()
        if stripped.startswith("#"):
            return stripped.strip("# ").strip()[:120] or f"{source_path} chunk {index + 1}"
        if stripped and not stripped.startswith("{"):
            return stripped[:120]
    return f"{source_path} chunk {index + 1}"


def _json_catalog_chunks() -> list[RetrievalChunk]:
    chunks: list[RetrievalChunk] = []
    knowledge_dir = PROJECT_ROOT / "data" / "knowledge"
    for path in sorted(knowledge_dir.glob("*.json")):
        raw = _read_text(path)
        if not raw:
            continue
        try:
            payload = json.loads(raw)
        except json.JSONDecodeError:
            payload = {"raw": raw}
        if isinstance(payload, dict):
            for key in ["fields", "formulas", "models", "stages", "sources"]:
                items = payload.get(key)
                if isinstance(items, list):
                    for idx, item in enumerate(items):
                        text = json.dumps(item, ensure_ascii=True, indent=2, default=str)
                        chunks.append(
                            RetrievalChunk(
                                chunk_id=f"{path.name}:{key}:{idx}",
                                source_path=str(path.relative_to(PROJECT_ROOT)),
                                title=str(item.get("display_name") or item.get("name") or item.get("field") or item.get("formula_id") or item.get("model_id") or item.get("stage_id") or item.get("source_id") or f"{key} {idx}"),
                                text=text,
                                metadata={"catalog": path.name, "catalog_key": key},
                            )
                        )
        chunks.append(
            RetrievalChunk(
                chunk_id=f"{path.name}:full",
                source_path=str(path.relative_to(PROJECT_ROOT)),
                title=path.name,
                text=json.dumps(payload, ensure_ascii=True, indent=2, default=str)[:MAX_CHARS_PER_CHUNK],
                metadata={"catalog": path.name, "catalog_key": "full"},
            )
        )
    return chunks


@lru_cache(maxsize=1)
def build_local_retrieval_index() -> RetrievalIndex:
    """Build the in-memory local project retrieval index."""
    chunks: list[RetrievalChunk] = []
    chunks.extend(_json_catalog_chunks())
    for relative in CURATED_PROJECT_FILES:
        path = PROJECT_ROOT / relative
        text = _read_text(path)
        for idx, chunk in enumerate(_chunk_text(text)):
            chunks.append(
                RetrievalChunk(
                    chunk_id=f"{relative}:{idx}",
                    source_path=relative,
                    title=_title_for_chunk(relative, chunk, idx),
                    text=chunk,
                    metadata={"file": relative, "chunk_index": idx},
                )
            )

    if not chunks:
        chunks.append(
            RetrievalChunk(
                chunk_id="empty",
                source_path="none",
                title="No local retrieval context",
                text="No local project retrieval documents were available.",
                metadata={},
            )
        )

    vectorizer = TfidfVectorizer(
        lowercase=True,
        stop_words="english",
        ngram_range=(1, 2),
        max_features=30000,
    )
    matrix = vectorizer.fit_transform([chunk.text for chunk in chunks])
    return RetrievalIndex(chunks=chunks, vectorizer=vectorizer, matrix=matrix)


def reload_local_retrieval_index() -> RetrievalIndex:
    """Clear and rebuild the local retrieval index."""
    build_local_retrieval_index.cache_clear()
    return build_local_retrieval_index()


def retrieval_status() -> dict[str, Any]:
    """Return readiness information for local retrieval."""
    index = build_local_retrieval_index()
    sources = sorted({chunk.source_path for chunk in index.chunks})
    return {
        "status": "ready",
        "retriever": "local_tfidf",
        "chunk_count": len(index.chunks),
        "source_count": len(sources),
        "sources": sources[:60],
        "uses_paid_resources": False,
        "requires_network": False,
    }


def retrieve_project_context(query: str, *, limit: int = 6) -> list[dict[str, Any]]:
    """Return the most relevant local project chunks for a question."""
    index = build_local_retrieval_index()
    query_vector = index.vectorizer.transform([query])
    scores = cosine_similarity(query_vector, index.matrix).ravel()
    ranked = sorted(enumerate(scores), key=lambda item: item[1], reverse=True)
    results: list[dict[str, Any]] = []
    for idx, score in ranked:
        if score <= 0 and results:
            break
        chunk = index.chunks[idx]
        results.append(
            {
                "score": float(score),
                "source_path": chunk.source_path,
                "title": chunk.title,
                "text": chunk.text,
                "metadata": chunk.metadata,
            }
        )
        if len(results) >= limit:
            break
    return results


def retrieve_context_by_source(source_needles: list[str], *, limit: int = 4) -> list[dict[str, Any]]:
    """Return representative chunks whose source path matches any requested needle."""
    index = build_local_retrieval_index()
    needles = [needle.lower().replace("\\", "/") for needle in source_needles if needle]
    results: list[dict[str, Any]] = []
    seen: set[str] = set()
    for chunk in index.chunks:
        source = chunk.source_path.replace("\\", "/")
        source_lower = source.lower()
        if not any(needle in source_lower for needle in needles):
            continue
        if source in seen:
            continue
        seen.add(source)
        results.append(
            {
                "score": 1.0,
                "source_path": chunk.source_path,
                "title": chunk.title,
                "text": chunk.text,
                "metadata": {**chunk.metadata, "forced_by_source": True},
            }
        )
        if len(results) >= limit:
            break
    return results


def format_retrieval_context(results: list[dict[str, Any]]) -> str:
    """Format retrieval results for a grounded LLM prompt."""
    if not results:
        return "No local project retrieval context matched the question."
    lines = ["LOCAL PROJECT RETRIEVAL CONTEXT"]
    for idx, result in enumerate(results, start=1):
        lines.append(
            f"\n[{idx}] Source: {result['source_path']} | Title: {result['title']} | Score: {result['score']:.4f}\n{result['text']}"
        )
    return "\n".join(lines)
