"""Deterministic project-question routing for the copilot."""

from __future__ import annotations

from dataclasses import dataclass


FIELD_ALIASES = {
    "counterparty_name": ["counterparty name", "company name", "borrower name", "customer name"],
    "counterparty_type": ["counterparty type", "company type", "business category", "buyer type"],
    "country": ["country", "jurisdiction"],
    "revenue": ["revenue", "sales", "top line", "top-line"],
    "ebitda": ["ebitda", "cash earnings"],
    "ebit": ["ebit", "operating profit", "operating income"],
    "accounts_receivable": ["accounts receivable", "receivables", "trade receivables"],
    "inventory": ["inventory", "inventories"],
    "total_debt": ["total debt", "debt obligations"],
    "shareholders_equity": ["shareholders equity", "shareholder equity", "book equity", "equity"],
    "current_ratio": ["current ratio", "current_ratio"],
    "quick_ratio": ["quick ratio", "quick_ratio"],
    "cash_ratio": ["cash ratio", "cash_ratio"],
    "debt_to_equity": ["debt to equity", "debt/equity", "debt_to_equity"],
    "debt_to_ebitda": ["debt to ebitda", "debt/ebitda", "debt_to_ebitda"],
    "interest_coverage": ["interest coverage", "interest_coverage"],
    "structural_pd": ["structural pd", "merton pd", "merton model"],
    "ml_pd": ["ml pd", "machine learning pd", "model pd", "proxy pd"],
    "final_pd": ["final pd", "final probability of default"],
    "distance_to_default": ["distance to default", "default distance"],
    "predicted_lgd": ["predicted lgd", "lgd", "loss given default"],
    "exposure_at_default": ["exposure at default", "ead"],
    "expected_loss": ["expected loss"],
    "credit_var_95": ["var", "var 95", "credit var", "value at risk"],
    "expected_shortfall_95": ["expected shortfall", "shortfall", "es 95"],
    "recommended_credit_limit": ["recommended limit", "credit limit", "approved limit"],
    "recommended_tenor_days": ["recommended tenor", "tenor", "credit tenor"],
    "recommended_security": ["recommended security", "required security", "collateral", "guarantee", "deposit"],
    "risk_grade": ["risk grade"],
    "approval_status": ["approval status", "approval decision", "committee decision", "decision"],
    "stress_index": ["stress index", "market stress"],
    "pc1_score": ["pc1 score", "pc1", "principal component"],
    "pca_loadings": ["pca loadings", "loadings"],
    "market_regime": ["market regime", "regime"],
}


@dataclass(frozen=True)
class QuestionRoute:
    intent: str
    trace_target: str | None
    style_hint: str | None
    retrieval_focus: list[str]
    explanation: str


def _contains_any(text: str, words: list[str]) -> bool:
    return any(word in text for word in words)


def infer_field_target(question: str) -> str | None:
    """Return a canonical project field if the question names one directly."""
    q = question.lower().replace("_", " ")
    matches: list[tuple[int, str]] = []
    for field, aliases in FIELD_ALIASES.items():
        for alias in aliases:
            normalized = alias.lower().replace("_", " ")
            if normalized in q:
                matches.append((len(normalized), field))
    if matches:
        return sorted(matches, reverse=True)[0][1]
    return None


def classify_project_question(question: str) -> QuestionRoute:
    """Classify a copilot question into a project-specific route.

    This is intentionally rule-based. It avoids another model deciding which
    facts to retrieve before the grounded answer is built.
    """
    q = f" {question.lower().strip()} "
    field_target = infer_field_target(question)

    if _contains_any(q, [" interview", "explain to interviewer", "say in interview", "resume"]):
        return QuestionRoute(
            intent="interview_explanation",
            trace_target=None,
            style_hint="interview",
            retrieval_focus=["PROJECT_INTERVIEW_GUIDE.md", "pipeline_graph", "model_catalog"],
            explanation="User wants a polished explanation they can say out loud.",
        )

    if _contains_any(q, [" pca", "pc1", "principal component", "loadings"]):
        return QuestionRoute(
            intent="market_pca_explanation",
            trace_target="pc1_score" if "pc1" in q or "loading" in q else "stress_index",
            style_hint=None,
            retrieval_focus=["stress_index.py", "pca_stress_index", "market_stress_pca"],
            explanation="Question is about PCA, PC1, loadings, or market stress compression.",
        )

    formula_request = _contains_any(q, [" formula", "calculate", "calculated", "calculation", " math", "derive", "mapped", "mapping"])

    if not formula_request and _contains_any(q, ["structural pd"]) and _contains_any(q, ["ml pd", "machine learning pd", "model pd", "different", "difference"]):
        return QuestionRoute(
            intent="model_explanation",
            trace_target=None,
            style_hint=None,
            retrieval_focus=["model_catalog", "pd_blend", "merton", "ml_pd"],
            explanation="User is comparing structural PD and ML PD.",
        )

    if field_target == "recommended_security" and _contains_any(q, ["why", "recommend", "security", "collateral", "guarantee", "letter of credit", "lc"]):
        return QuestionRoute(
            intent="credit_decision_explanation",
            trace_target="recommended_security",
            style_hint=None,
            retrieval_focus=["credit_decision/engine.py", "credit_recommendations", "policy"],
            explanation="User is asking why security is recommended.",
        )

    if formula_request:
        target = field_target
        if _contains_any(q, ["expected loss", " el "]):
            target = "expected_loss"
        elif _contains_any(q, ["final pd", " pd ", "probability of default"]):
            target = "final_pd"
        elif _contains_any(q, ["lgd", "loss given default"]):
            target = "predicted_lgd"
        elif _contains_any(q, ["ead", "exposure at default"]):
            target = "exposure_at_default"
        elif _contains_any(q, ["risk grade", " grade"]):
            target = "risk_grade"
        elif _contains_any(q, ["limit", "credit limit"]):
            target = "recommended_credit_limit"
        return QuestionRoute(
            intent="formula_trace",
            trace_target=target,
            style_hint=None,
            retrieval_focus=["formula_catalog", "field_catalog"],
            explanation="User is asking how a value is calculated.",
        )

    if field_target and _contains_any(q, [" affect", "impact", "mean", "meaning", "explain", "terms", "limit", "tenor", "security", "tell us"]):
        return QuestionRoute(
            intent="field_definition",
            trace_target=field_target,
            style_hint=None,
            retrieval_focus=["field_catalog", "formula_catalog", "credit_decision/engine.py"],
            explanation="User is asking what a named field means or how it affects credit terms.",
        )

    if _contains_any(q, ["where", "source", "table", "data point", "comes from", "lineage"]):
        return QuestionRoute(
            intent="data_lineage",
            trace_target=None,
            style_hint=None,
            retrieval_focus=["source_catalog", "field_catalog", "pipeline_graph"],
            explanation="User is asking where a value or field comes from.",
        )

    if _contains_any(q, ["model", "accuracy", "auc", "brier", "trained", "artifact", "validation"]):
        return QuestionRoute(
            intent="model_explanation",
            trace_target=None,
            style_hint="technical",
            retrieval_focus=["model_catalog", "training_summary", "validation_report"],
            explanation="User is asking about models, metrics, artifacts, or validation.",
        )

    if _contains_any(q, ["market", "stress", "oil", "brent", "fuel", "vix", "dxy", "usd", "regime"]):
        return QuestionRoute(
            intent="market_factor_explanation",
            trace_target="stress_index" if "stress" in q else None,
            style_hint=None,
            retrieval_focus=["stress_index.py", "market_regime", "scenario_multiplier_config"],
            explanation="User is asking how market factors affect the project outputs.",
        )

    if _contains_any(q, ["decision", "recommend", "approve", "approval", "limit", "tenor", "security", "lc"]):
        return QuestionRoute(
            intent="credit_decision_explanation",
            trace_target="recommended_credit_limit" if "limit" in q else None,
            style_hint=None,
            retrieval_focus=["credit_decision/engine.py", "credit_recommendations", "policy"],
            explanation="User is asking about the final credit decision or terms.",
        )

    if _contains_any(q, ["what is", "meaning", "mean", "define", "explain"]):
        return QuestionRoute(
            intent="field_definition",
            trace_target=field_target,
            style_hint=None,
            retrieval_focus=["field_catalog", "formula_catalog"],
            explanation="User is asking for a definition or explanation.",
        )

    return QuestionRoute(
        intent="general_project_question",
        trace_target=None,
        style_hint=None,
        retrieval_focus=["field_catalog", "formula_catalog", "pipeline_graph"],
        explanation="General project question; use local retrieval and catalogs.",
    )


def route_to_dict(route: QuestionRoute) -> dict:
    return {
        "intent": route.intent,
        "trace_target": route.trace_target,
        "style_hint": route.style_hint,
        "retrieval_focus": route.retrieval_focus,
        "explanation": route.explanation,
    }
