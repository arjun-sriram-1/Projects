"""Evaluation harness for the project-aware copilot.

The evaluator is intentionally deterministic by default. It uses the same
backend query path as the UI, but with ``use_llm=False`` unless a caller
explicitly opts into local Ollama. This makes it suitable for regression tests
and demos without paid APIs or network access.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from api.copilot.grounded_llm import answer_project_question
from api.core.config import PROJECT_ROOT


EVAL_QUESTIONS_PATH = PROJECT_ROOT / "data" / "knowledge" / "copilot_eval_questions.json"


def load_eval_questions(path: Path = EVAL_QUESTIONS_PATH) -> dict[str, Any]:
    """Load the copilot evaluation question set."""
    return json.loads(path.read_text(encoding="utf-8"))


def _contains_all(text: str, expected: list[str]) -> tuple[bool, list[str]]:
    lower = text.lower()
    missing = [item for item in expected if item.lower() not in lower]
    return not missing, missing


def _sources_contain(sources: list[str], expected: list[str]) -> tuple[bool, list[str]]:
    joined = " ".join(str(source).replace("\\", "/") for source in sources).lower()
    missing = [item for item in expected if item.lower() not in joined]
    return not missing, missing


def _answer_corpus(response: dict[str, Any]) -> str:
    trace = response.get("trace") or {}
    market_trace = response.get("market_trace") or {}
    retrieved_text = " ".join(
        str(item.get("text") or "") for item in response.get("retrieved_context") or []
    )
    parts = [
        str(response.get("answer") or ""),
        str(trace.get("formula") or ""),
        str(trace.get("plain_english") or ""),
        " ".join(str(item) for item in trace.get("notes") or []),
        str(market_trace.get("summary") or ""),
        " ".join(str(item) for item in market_trace.get("formulas") or []),
        retrieved_text,
    ]
    return "\n".join(parts)


def _source_corpus(response: dict[str, Any]) -> list[str]:
    trace = response.get("trace") or {}
    market_trace = response.get("market_trace") or {}
    sources = list(response.get("sources") or [])
    sources.extend(trace.get("source_files") or [])
    sources.extend(market_trace.get("sources") or [])
    return sources


def _nearly_equal(actual: Any, expected: Any) -> bool:
    if isinstance(expected, (int, float)):
        try:
            return abs(float(actual) - float(expected)) <= max(1e-6, abs(float(expected)) * 1e-6)
        except (TypeError, ValueError):
            return False
    return actual == expected


def evaluate_answer(case: dict[str, Any], response: dict[str, Any]) -> dict[str, Any]:
    """Evaluate one answer against its expected route/trace/source checks."""
    expected = case.get("expect") or {}
    checks: list[dict[str, Any]] = []

    def add(name: str, passed: bool, detail: Any = None) -> None:
        checks.append({"name": name, "passed": bool(passed), "detail": detail})

    if "route_intent" in expected:
        actual = (response.get("route") or {}).get("intent")
        add("route_intent", actual == expected["route_intent"], {"expected": expected["route_intent"], "actual": actual})

    if "style" in expected:
        add("style", response.get("style") == expected["style"], {"expected": expected["style"], "actual": response.get("style")})

    trace = response.get("trace") or {}
    if "trace_formula_id" in expected:
        add(
            "trace_formula_id",
            trace.get("formula_id") == expected["trace_formula_id"],
            {"expected": expected["trace_formula_id"], "actual": trace.get("formula_id")},
        )

    if "trace_result" in expected:
        add(
            "trace_result",
            _nearly_equal(trace.get("result"), expected["trace_result"]),
            {"expected": expected["trace_result"], "actual": trace.get("result")},
        )

    if expected.get("market_trace_required"):
        add("market_trace_required", bool(response.get("market_trace")), response.get("market_trace"))

    if expected.get("answer_contains"):
        passed, missing = _contains_all(_answer_corpus(response), expected["answer_contains"])
        add("answer_contains", passed, {"missing": missing, "expected": expected["answer_contains"]})

    if expected.get("source_contains"):
        actual_sources = _source_corpus(response)
        passed, missing = _sources_contain(actual_sources, expected["source_contains"])
        add("source_contains", passed, {"missing": missing, "expected": expected["source_contains"], "actual": actual_sources})

    passed = all(check["passed"] for check in checks)
    return {
        "id": case.get("id"),
        "question": case.get("question"),
        "passed": passed,
        "checks": checks,
        "response_summary": {
            "mode": response.get("mode"),
            "style": response.get("style"),
            "route": response.get("route"),
            "sources": response.get("sources"),
            "trace": response.get("trace"),
            "has_market_trace": bool(response.get("market_trace")),
        },
    }


def run_copilot_evaluation(
    *,
    use_llm: bool | None = False,
    case_ids: list[str] | None = None,
    retrieval_limit: int = 7,
) -> dict[str, Any]:
    """Run the copilot evaluation set through the backend query path."""
    payload = load_eval_questions()
    selected = set(case_ids or [])
    cases = [
        case for case in payload.get("cases", [])
        if not selected or case.get("id") in selected
    ]
    results = []
    for case in cases:
        response = answer_project_question(
            case["question"],
            style=case.get("style", "casual_precise"),
            use_llm=use_llm,
            values=case.get("values") or {},
            retrieval_limit=retrieval_limit,
        )
        results.append(evaluate_answer(case, response))

    passed_count = sum(1 for result in results if result["passed"])
    return {
        "version": payload.get("version"),
        "status": "passed" if passed_count == len(results) else "failed",
        "use_llm": use_llm,
        "total": len(results),
        "passed": passed_count,
        "failed": len(results) - passed_count,
        "results": results,
        "uses_paid_resources": False,
    }
