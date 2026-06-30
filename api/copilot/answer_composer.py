"""Natural answer composition for the project copilot.

This module is the last mile between grounded project evidence and the text the
user sees. Retrieval, formula traces, and market traces stay available for
accuracy, but the default answer should read like a concise analyst explanation,
not like a dump of internal context.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AnswerMode:
    name: str
    include_formulas: bool = False
    include_sources: bool = False
    include_technical_details: bool = False


FORMULA_WORDS = (
    "formula",
    "calculate",
    "calculated",
    "calculation",
    "math",
    "derive",
    "equation",
    "step by step",
    "show working",
    "show me the working",
)

SOURCE_WORDS = (
    "source",
    "sources",
    "where from",
    "which file",
    "which table",
    "table name",
    "lineage",
)

TECHNICAL_WORDS = (
    "implementation",
    "code",
    "backend",
    "api",
    "database",
    "schema",
    "artifact",
    "debug",
    "trace",
)

DIAGNOSTIC_WORDS = (
    "wrong",
    "mismatch",
    "not accurate",
    "error",
    "bug",
    "why is",
    "difference between",
)


def _has_any(question: str, words: tuple[str, ...]) -> bool:
    q = f" {question.lower()} "
    return any(word in q for word in words)


def determine_answer_mode(question: str, route_intent: str | None, style: str | None) -> AnswerMode:
    """Decide how much detail the answer should expose."""
    if style == "interview" or route_intent == "interview_explanation":
        return AnswerMode("interview")
    if _has_any(question, SOURCE_WORDS):
        return AnswerMode("technical", include_sources=True, include_technical_details=True)
    if _has_any(question, FORMULA_WORDS) or route_intent == "formula_trace":
        return AnswerMode("calculation", include_formulas=True)
    if _has_any(question, TECHNICAL_WORDS):
        return AnswerMode("technical", include_formulas=True, include_sources=True, include_technical_details=True)
    if _has_any(question, DIAGNOSTIC_WORDS):
        return AnswerMode("diagnostic")
    if route_intent == "market_pca_explanation":
        return AnswerMode("pca_explanation")
    return AnswerMode("simple_explanation")


def _field_name(field_context: dict[str, Any] | None) -> str | None:
    field = (field_context or {}).get("field") or {}
    return field.get("field")


def _field_display(field_context: dict[str, Any] | None) -> str:
    field = (field_context or {}).get("field") or {}
    return str(field.get("display_name") or field.get("field") or "This field")


def _field_meaning(field_context: dict[str, Any] | None) -> str | None:
    field = (field_context or {}).get("field") or {}
    meaning = field.get("meaning")
    return str(meaning).rstrip(".") if meaning else None


def _value(values: dict[str, Any] | None, *keys: str) -> Any:
    values = values or {}
    for key in keys:
        if key in values and values[key] not in (None, ""):
            return values[key]
    return None


def _fmt_money(value: Any) -> str | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    sign = "-" if number < 0 else ""
    number = abs(number)
    if number >= 1_000_000_000:
        return f"{sign}${number / 1_000_000_000:.1f}B"
    if number >= 1_000_000:
        return f"{sign}${number / 1_000_000:.1f}M"
    if number >= 1_000:
        return f"{sign}${number / 1_000:.1f}K"
    return f"{sign}${number:,.0f}"


def _fmt_pct(value: Any) -> str | None:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    if abs(number) <= 1:
        number *= 100
    return f"{number:.1f}%"


def _limit_sentence(values: dict[str, Any] | None) -> str | None:
    requested = _fmt_money(_value(values, "requested_limit", "base_limit"))
    recommended = _fmt_money(_value(values, "recommended_limit", "recommended_credit_limit"))
    if requested and recommended:
        return f"Here, the requested limit is {requested} and the recommended limit is {recommended}, so the engine is applying a risk adjustment."
    if recommended:
        return f"In the current case, the recommended limit shown to the user is {recommended}."
    return None


def _join(lines: list[str], *, max_lines: int = 9) -> str:
    cleaned: list[str] = []
    seen: set[str] = set()
    for line in lines:
        compact = " ".join(str(line or "").split())
        if not compact:
            continue
        key = compact.lower()
        if key in seen:
            continue
        seen.add(key)
        cleaned.append(compact)
        if len(cleaned) >= max_lines:
            break
    return "\n".join(cleaned) or "I do not have enough project context to answer that cleanly yet."


def _field_answer(field_context: dict[str, Any], values: dict[str, Any] | None, mode: AnswerMode) -> str:
    field = _field_name(field_context) or ""
    display = _field_display(field_context)
    meaning = _field_meaning(field_context)
    formula = (field_context or {}).get("formula") or {}
    lines: list[str] = []

    if meaning:
        lines.append(f"{display} means {meaning}.")
    else:
        lines.append(f"{display} is one of the inputs the project uses to judge credit strength.")

    if field in {"current_ratio", "quick_ratio", "cash_ratio"}:
        lines.append("It is mainly a liquidity signal: it tells whether the company can meet near-term obligations without relying on future profits.")
        lines.append("A stronger value usually supports cleaner credit terms, while a weak value can push the model toward shorter tenor, lower limits, or added security.")
    elif field in {"debt_to_ebitda", "debt_to_equity", "total_debt", "shareholders_equity"}:
        lines.append("It is mainly a leverage signal: it shows how much balance-sheet pressure sits ahead of supplier repayment.")
        lines.append("Higher leverage usually makes credit terms more conservative unless earnings and cash reserves are strong.")
    elif field in {"interest_coverage", "ebit", "ebitda"}:
        lines.append("It is a repayment-capacity signal because it shows how comfortably operating earnings cover fixed obligations.")
        lines.append("Weak coverage can tighten credit days or require extra security because debt service competes with supplier payments.")
    elif field in {"final_pd", "structural_pd", "ml_pd", "distance_to_default"}:
        lines.append("It feeds the default-risk view, so a higher risk signal usually means tighter credit terms.")
        lines.append("The recommendation uses this alongside loss severity, market stress, and policy rules instead of relying on one model alone.")
    elif field in {"predicted_lgd", "exposure_at_default", "expected_loss"}:
        lines.append("It feeds the loss view: not just whether default may happen, but how painful it would be if it happens.")
        lines.append("Higher loss pressure usually means a lower approved limit, stronger collateral, or manual review.")
    elif field in {"stress_index", "market_regime", "pc1_score", "pca_loadings"}:
        lines.append("It captures the external market backdrop around the counterparty, especially fuel, FX, volatility, and macro pressure.")
        lines.append("A stressed market can make terms more cautious even when the latest company financials look acceptable.")
    elif field in {"accounts_receivable", "inventory"}:
        lines.append("It helps judge quality of short-term assets, not just the headline current asset number.")
        lines.append("Receivables support quick liquidity, while heavy inventory can make liquidity look better than it really is.")
    else:
        lines.append("The project uses it as part of the wider credit picture rather than as a standalone decision rule.")

    limit_line = _limit_sentence(values)
    if limit_line:
        lines.append(limit_line)

    if mode.include_formulas and formula.get("formula"):
        lines.append(f"In this project, the formula is {formula['formula']}.")

    return _join(lines, max_lines=9)


def _market_answer(question: str, values: dict[str, Any] | None, mode: AnswerMode, market_trace: dict[str, Any] | None) -> str:
    q = question.lower()
    stress = _value(values, "stress_index", "market_stress_index")
    pd_text = _fmt_pct(_value(values, "final_pd", "pd"))
    lines: list[str] = []

    if any(token in q for token in ["fuel", "oil", "brent", "crude", "jet"]):
        lines.extend(
            [
                "Fuel prices matter because they are one of the biggest operating costs for an airline or fuel buyer.",
                "When fuel rises, margins get squeezed and the company may need more working capital to buy the same volume of fuel.",
                "That can make the credit recommendation more cautious through a lower limit, shorter credit days, or stronger security.",
                "The effect is strongest when liquidity is weak, leverage is high, or the company cannot pass fuel costs to customers quickly.",
            ]
        )
        if mode.name == "pca_explanation":
            lines.append("In this project, PCA is the compression step that turns several noisy market moves into one market-stress signal used around PD and scenario risk.")
    elif any(token in q for token in ["usd", "fx", "currency", "dxy", "inr"]):
        lines.extend(
            [
                "FX matters because fuel and many aviation costs are linked to USD, while revenue may be earned in local currency.",
                "If the local currency weakens, the same fuel bill becomes more expensive in local terms.",
                "That can reduce margins, pressure cash flow, and make the model more conservative on limits or tenor.",
                "The impact is lower when the company has USD revenue, hedging, or a strong cash buffer.",
            ]
        )
        if mode.name == "pca_explanation":
            lines.append("In this project, PCA helps combine FX with other market drivers so the model reacts to the overall stress backdrop, not one isolated price move.")
    else:
        lines.extend(
            [
                "Market conditions affect the recommendation by changing the outside risk around the counterparty.",
                "Higher stress usually means more pressure from costs, demand, funding, or volatility.",
                "The model uses that context as a caution signal alongside the company financials.",
                "If the company is already weak, market stress can meaningfully tighten the final terms.",
            ]
        )
        if mode.name == "pca_explanation":
            lines.append("In this project, PCA compresses market variables into a stress signal, which then supports PD context, scenario losses, and tighter or looser credit terms.")
            if "pd" in q:
                lines.append("If the compressed stress signal is higher, the credit view becomes more cautious around final PD and the recommendation can tighten.")

    if pd_text:
        lines.append(f"In the selected case, final PD is currently around {pd_text}, so market pressure is interpreted through that credit-risk base.")
    if stress not in (None, ""):
        lines.append(f"The market stress index is {stress}/100, which tells the recommendation how cautious the external overlay should be.")

    if mode.include_formulas and market_trace:
        formulas = market_trace.get("formulas") or []
        if formulas:
            lines.append("Technically, the project compresses market variables through the PCA/stress-index layer before feeding credit outputs.")
            lines.append("Trace: " + " -> ".join(str(item) for item in formulas[:3]) + ".")

    return _join(lines, max_lines=9)


def _calculation_answer(trace: dict[str, Any] | None, field_context: dict[str, Any] | None) -> str:
    if not trace or not trace.get("matched"):
        if field_context:
            return _field_answer(field_context, None, AnswerMode("calculation", include_formulas=True))
        return "I could not match that to a known project formula. Ask using the exact output name, like expected loss, final PD, LGD, EAD, risk grade, or recommended limit."

    name = str(trace.get("name") or trace.get("formula_id") or "This output")
    formula = trace.get("formula")
    plain = trace.get("plain_english")
    lines = [f"{name} is calculated from the project inputs used for that output."]
    if formula:
        lines.append(f"Formula: {formula}.")
    if trace.get("result") is not None:
        result = trace["result"]
        formula_id = str(trace.get("formula_id") or trace.get("output") or "").lower()
        if isinstance(result, (int, float)):
            if any(token in formula_id for token in ["loss", "limit", "ead", "exposure"]):
                formatted = _fmt_money(result) or f"{result:.4f}"
            elif any(token in formula_id for token in ["pd", "lgd", "haircut", "ratio"]):
                formatted = _fmt_pct(result) or f"{result:.4f}"
            else:
                formatted = f"{result:.4f}".rstrip("0").rstrip(".")
        else:
            formatted = str(result)
        lines.append(f"With the supplied values, the result is {formatted}.")
    elif trace.get("missing_inputs"):
        lines.append("I can explain it, but an exact number needs: " + ", ".join(str(item) for item in trace["missing_inputs"]) + ".")
    if plain:
        lines.append(str(plain))
    return _join(lines, max_lines=9)


def _decision_answer(values: dict[str, Any] | None) -> str:
    final_pd = _fmt_pct(_value(values, "final_pd", "pd"))
    lgd = _fmt_pct(_value(values, "lgd", "predicted_lgd"))
    el = _fmt_money(_value(values, "expected_loss"))
    lines = [
        "The credit recommendation is the final business decision built from default risk, loss severity, exposure size, market stress, and policy rules.",
        "A stronger counterparty can keep normal limits and tenor; a weaker one usually gets reduced limits, shorter credit days, or security requirements.",
    ]
    if final_pd:
        lines.append(f"The selected case is using a final PD of about {final_pd}.")
    if lgd:
        lines.append(f"LGD is about {lgd}, so the model also considers how much could be lost if default happens.")
    if el:
        lines.append(f"Expected loss is around {el}, which acts as the dollar risk anchor for the recommendation.")
    limit_line = _limit_sentence(values)
    if limit_line:
        lines.append(limit_line)
    return _join(lines, max_lines=8)


def _security_answer(values: dict[str, Any] | None) -> str:
    final_pd = _fmt_pct(_value(values, "final_pd", "pd"))
    lgd = _fmt_pct(_value(values, "lgd", "predicted_lgd"))
    lines = [
        "The model recommends security when the risk is acceptable only with extra protection.",
        "That usually happens when PD, LGD, leverage, liquidity pressure, market stress, or requested exposure is too high for clean unsecured terms.",
        "Security like a letter of credit, guarantee, deposit, or collateral lowers the loss if the counterparty fails to pay.",
        "So the recommendation is not just saying yes or no; it is saying the deal can work if downside protection is added.",
    ]
    if final_pd:
        lines.append(f"In the selected case, final PD is about {final_pd}, so the security decision is judged against that risk level.")
    if lgd:
        lines.append(f"LGD is about {lgd}, which means the engine also cares about recovery if default happens.")
    return _join(lines, max_lines=8)


def _tail_risk_answer(values: dict[str, Any] | None) -> str:
    el = _fmt_money(_value(values, "expected_loss"))
    var95 = _fmt_money(_value(values, "credit_var_95", "var_95"))
    es95 = _fmt_money(_value(values, "expected_shortfall_95", "es_95"))
    lines = [
        "VaR can be higher than expected loss because they answer different questions.",
        "Expected loss is the average loss the model expects across normal outcomes.",
        "VaR 95% is a downside threshold: it asks how bad losses could get in a stressed 5% tail of simulations.",
        "Expected shortfall goes even further and averages the losses beyond that VaR point.",
        "So EL is the everyday risk anchor, while VaR and expected shortfall are tail-risk measures used for stress and limit discipline.",
    ]
    if el:
        lines.append(f"In the selected case, expected loss is around {el}.")
    if var95:
        lines.append(f"VaR 95% is around {var95}, so it is showing downside exposure rather than average expected loss.")
    if es95:
        lines.append(f"Expected shortfall 95% is around {es95}, which represents the more severe tail beyond VaR.")
    return _join(lines, max_lines=9)


def _model_answer(question: str) -> str:
    q = question.lower()
    if any(token in q for token in ["proxy", "synthetic", "calibrated", "real data", "real, proxy"]):
        return _join(
            [
                "The project mixes real, proxy, synthetic, and calibrated inputs because it is a student credit-risk build, not a production bank data warehouse.",
                "Market indicators can come from real free sources, while some supplier-level behavior is synthetic or proxy because private payment history is not publicly available.",
                "Model coefficients and stress weights may be calibrated from available data where possible, but some assumptions remain transparent fallbacks.",
                "That is acceptable for demonstration as long as the app clearly separates real market data, uploaded company data, trained artifacts, and demo assumptions.",
            ]
        )
    if "structural" in q and "ml" in q:
        return _join(
            [
                "Structural PD and ML PD can differ because they look at risk from different angles.",
                "Structural PD is balance-sheet based: it asks how close the company is to a default barrier using asset value, debt, volatility, and horizon.",
                "ML PD is pattern based: it learns from financial ratios, market stress, and engineered features that resemble risky or safer counterparties.",
                "A large gap does not automatically mean one is wrong; it means the models are seeing different risk signals.",
                "In this project, the final PD blends them so the recommendation is not dependent on only one modelling view.",
            ]
        )
    return _join(
        [
            "The project uses a layered model setup rather than one single score.",
            "Financial ratios describe company strength, market features describe external pressure, and PD/LGD/EAD translate those signals into credit risk.",
            "The ML layer acts as a data-driven cross-check, while structural and policy layers keep the output explainable.",
            "The final recommendation then converts model risk into business terms like limit, tenor, security, and approval status.",
        ]
    )


def _generic_answer(knowledge_hits: list[dict[str, Any]], retrieved: list[dict[str, Any]]) -> str:
    for hit in knowledge_hits:
        item = hit.get("item") or {}
        text = item.get("interview_explanation") or item.get("plain_english") or item.get("explanation") or item.get("meaning")
        if text:
            return _join([str(text)], max_lines=6)
    for item in retrieved:
        text = str(item.get("text") or "").strip()
        if text:
            first = text.splitlines()[0][:400]
            return _join([first], max_lines=6)
    return "I do not have enough project context to answer that confidently yet."


def compose_copilot_answer(
    *,
    question: str,
    route_intent: str | None,
    mode: AnswerMode,
    retrieved: list[dict[str, Any]],
    knowledge_hits: list[dict[str, Any]],
    trace: dict[str, Any] | None,
    field_context: dict[str, Any] | None,
    market_trace: dict[str, Any] | None,
    values: dict[str, Any] | None,
) -> str:
    """Compose the user-facing answer from grounded evidence."""
    lowered = question.lower()
    if mode.include_formulas:
        return _calculation_answer(trace, field_context)

    if "structural pd" in lowered and ("ml pd" in lowered or "machine learning pd" in lowered or "different" in lowered):
        return _model_answer(question)

    if "var" in lowered and ("expected loss" in lowered or "shortfall" in lowered or "higher" in lowered):
        return _tail_risk_answer(values)

    if "security" in lowered and any(token in lowered for token in ["why", "recommend", "required", "ask"]):
        return _security_answer(values)

    if route_intent in {"market_pca_explanation", "market_factor_explanation"}:
        return _market_answer(question, values, mode, market_trace)

    if field_context and field_context.get("field"):
        return _field_answer(field_context, values, mode)

    if route_intent == "credit_decision_explanation":
        return _decision_answer(values)

    if route_intent == "model_explanation":
        return _model_answer(question)

    if route_intent == "interview_explanation":
        return _join(
            [
                "Interview version: this is an end-to-end credit risk platform for jet-fuel trade exposure.",
                "The user uploads or enters company financials, and the system turns them into liquidity, leverage, profitability, and debt-service signals.",
                "Market data adds external pressure from fuel, FX, volatility, and macro conditions.",
                "The model estimates PD, LGD, EAD, expected loss, and scenario risk, then converts that into recommended credit terms.",
                "The final output is explainable: approved limit, tenor, security requirement, risk grade, and the main drivers behind the decision.",
            ],
            max_lines=7,
        )

    return _generic_answer(knowledge_hits, retrieved)
