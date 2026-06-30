"""Load and query the structured copilot knowledge catalogs.

The catalogs live in ``data/knowledge`` and are intentionally plain JSON so
they can be used by the API, tests, retrieval jobs, and future UI tooling.
"""

from __future__ import annotations

import json
from functools import lru_cache
from pathlib import Path
from typing import Any

from api.core.config import PROJECT_ROOT


KNOWLEDGE_DIR = PROJECT_ROOT / "data" / "knowledge"


class KnowledgeCatalogError(RuntimeError):
    """Raised when a required knowledge catalog is missing or malformed."""


def _load_json(filename: str) -> dict[str, Any]:
    path = KNOWLEDGE_DIR / filename
    if not path.exists():
        raise KnowledgeCatalogError(f"Knowledge catalog missing: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise KnowledgeCatalogError(f"Knowledge catalog is invalid JSON: {path}") from exc


@lru_cache(maxsize=1)
def load_knowledge_catalogs() -> dict[str, dict[str, Any]]:
    """Return all copilot knowledge catalogs keyed by catalog name."""
    return {
        "fields": _load_json("field_catalog.json"),
        "formulas": _load_json("formula_catalog.json"),
        "models": _load_json("model_catalog.json"),
        "pipeline": _load_json("pipeline_graph.json"),
        "sources": _load_json("source_catalog.json"),
        "tone": _load_json("tone_profile.json"),
    }


def reload_knowledge_catalogs() -> dict[str, dict[str, Any]]:
    """Clear the in-process cache and reload catalogs from disk."""
    load_knowledge_catalogs.cache_clear()
    return load_knowledge_catalogs()


def _normalize(value: str) -> str:
    return value.lower().strip().replace("-", "_").replace(" ", "_")


def _items(catalog_name: str, key: str) -> list[dict[str, Any]]:
    catalog = load_knowledge_catalogs()[catalog_name]
    items = catalog.get(key)
    if not isinstance(items, list):
        raise KnowledgeCatalogError(f"Catalog {catalog_name} does not contain list key {key}")
    return items


def get_catalog_status() -> dict[str, Any]:
    """Return readiness and counts for the knowledge layer."""
    catalogs = load_knowledge_catalogs()
    return {
        "status": "ready",
        "knowledge_dir": str(KNOWLEDGE_DIR),
        "catalog_versions": {
            name: payload.get("version") for name, payload in catalogs.items()
        },
        "counts": {
            "fields": len(catalogs["fields"].get("fields", [])),
            "formulas": len(catalogs["formulas"].get("formulas", [])),
            "models": len(catalogs["models"].get("models", [])),
            "pipeline_stages": len(catalogs["pipeline"].get("stages", [])),
            "sources": len(catalogs["sources"].get("sources", [])),
            "tone_styles": len(catalogs["tone"].get("styles", {})),
        },
    }


def list_fields() -> list[dict[str, Any]]:
    """Return all field catalog entries."""
    return _items("fields", "fields")


def list_formulas() -> list[dict[str, Any]]:
    """Return all formula catalog entries."""
    return _items("formulas", "formulas")


def list_models() -> list[dict[str, Any]]:
    """Return all model catalog entries."""
    return _items("models", "models")


def list_pipeline_stages() -> list[dict[str, Any]]:
    """Return all pipeline stage entries."""
    return _items("pipeline", "stages")


def list_sources() -> list[dict[str, Any]]:
    """Return all source catalog entries."""
    return _items("sources", "sources")


def get_field(field_name: str) -> dict[str, Any] | None:
    """Find a field by canonical field name or display name."""
    target = _normalize(field_name)
    for item in _items("fields", "fields"):
        aliases = [
            item.get("field", ""),
            item.get("display_name", ""),
            item.get("formula_id", ""),
        ]
        if target in {_normalize(str(alias)) for alias in aliases if alias}:
            return item
    return None


def get_formula(formula_id: str) -> dict[str, Any] | None:
    """Find a formula by formula ID, name, or output field."""
    target = _normalize(formula_id)
    for item in _items("formulas", "formulas"):
        aliases = [
            item.get("formula_id", ""),
            item.get("name", ""),
            item.get("output", ""),
        ]
        if target in {_normalize(str(alias)) for alias in aliases if alias}:
            return item
    field = get_field(formula_id)
    if field and field.get("formula_id"):
        return get_formula(str(field["formula_id"]))
    return None


def get_model(model_id: str) -> dict[str, Any] | None:
    """Find a model by model ID or display name."""
    target = _normalize(model_id)
    for item in _items("models", "models"):
        aliases = [item.get("model_id", ""), item.get("display_name", "")]
        if target in {_normalize(str(alias)) for alias in aliases if alias}:
            return item
    return None


def get_pipeline_stage(stage_id: str) -> dict[str, Any] | None:
    """Find a pipeline stage by stage ID or name."""
    target = _normalize(stage_id)
    for item in _items("pipeline", "stages"):
        aliases = [item.get("stage_id", ""), item.get("name", "")]
        if target in {_normalize(str(alias)) for alias in aliases if alias}:
            return item
    return None


def get_source(source_id: str) -> dict[str, Any] | None:
    """Find a source by source ID or path."""
    target = _normalize(source_id)
    for item in _items("sources", "sources"):
        aliases = [item.get("source_id", ""), item.get("path", "")]
        if target in {_normalize(str(alias)) for alias in aliases if alias}:
            return item
    return None


def search_knowledge(query: str, *, limit: int = 10) -> list[dict[str, Any]]:
    """Simple exact-token search across catalogs.

    This is deliberately small and dependency-free. Later retrieval phases can
    layer vector search or BM25 on top of this.
    """
    target_tokens = {
        token for token in _normalize(query).split("_") if len(token) >= 2
    }
    if not target_tokens:
        return []

    results: list[dict[str, Any]] = []
    catalogs = [
        ("field", _items("fields", "fields")),
        ("formula", _items("formulas", "formulas")),
        ("model", _items("models", "models")),
        ("pipeline_stage", _items("pipeline", "stages")),
        ("source", _items("sources", "sources")),
    ]
    for kind, items in catalogs:
        for item in items:
            searchable = _normalize(json.dumps(item, ensure_ascii=True, default=str))
            score = sum(1 for token in target_tokens if token in searchable)
            if score:
                results.append({"kind": kind, "score": score, "item": item})

    results.sort(key=lambda row: row["score"], reverse=True)
    return results[: max(1, limit)]


def describe_field(field_name: str) -> dict[str, Any] | None:
    """Return field metadata plus linked formula/model/source context."""
    field = get_field(field_name)
    if not field:
        return None
    formula = get_formula(str(field.get("formula_id", ""))) if field.get("formula_id") else None
    sources = [
        get_source(str(source))
        for source in field.get("source_tables", [])
        if get_source(str(source))
    ]
    models = [
        model
        for model in _items("models", "models")
        if field.get("field") in model.get("output_fields", [])
    ]
    return {
        "field": field,
        "formula": formula,
        "models": models,
        "sources": sources,
    }
