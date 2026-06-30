"""Grounded local-LLM wrapper for project-aware copilot answers."""

from __future__ import annotations

from typing import Any

from api.copilot.answer_composer import (
    AnswerMode,
    compose_copilot_answer,
    determine_answer_mode,
)
from api.copilot.formula_trace import trace_formula
from api.copilot.knowledge import describe_field, search_knowledge
from api.copilot.local_retriever import (
    format_retrieval_context,
    retrieve_context_by_source,
    retrieve_project_context,
)
from api.copilot.market_trace import explain_market_factor
from api.copilot.question_router import classify_project_question, route_to_dict
from api.core.config import settings
from api.rag.llm.ollama_client import generate_response


def _compact_sources(retrieved: list[dict[str, Any]]) -> list[str]:
    seen: set[str] = set()
    sources: list[str] = []
    for item in retrieved:
        source = str(item.get("source_path") or "")
        if source and source not in seen:
            seen.add(source)
            sources.append(source)
    return sources


def _infer_trace_target(question: str) -> str | None:
    q = question.lower()
    ordered = [
        ("expected_loss", ["expected loss", " el ", "loss calculated"]),
        ("final_pd", ["final pd", "probability of default", " pd ", "default probability"]),
        ("stress_index", ["stress index", "market stress"]),
        ("pc1_score", ["pc1", "pca"]),
        ("risk_grade", ["risk grade", "rating", "grade"]),
        ("recommended_credit_limit", ["recommended limit", "credit limit", "approved limit"]),
        ("structural_pd", ["structural pd", "merton"]),
    ]
    padded = f" {q} "
    for target, needles in ordered:
        if any(needle in padded for needle in needles):
            return target
    return None


def _clean_copilot_answer(answer: str) -> str:
    """Remove internal retrieval/source artifacts from user-facing answers."""
    blocked_prefixes = (
        "sources:",
        "source:",
        "sources used:",
        "the closest project source i found",
        "closest project source",
        "retrieved context:",
    )
    cleaned_lines: list[str] = []
    dropping_json = False
    for raw_line in str(answer or "").splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        lowered = stripped.lower()
        if any(lowered.startswith(prefix) for prefix in blocked_prefixes):
            continue
        if "`data\\" in stripped or "`data/" in stripped or "api/rag/" in stripped or "source_files" in stripped:
            continue
        if stripped.startswith("{") and any(token in stripped for token in ('"field"', '"source_files"', '"source_tables"')):
            dropping_json = True
            continue
        if dropping_json:
            if stripped.endswith("}") or stripped.endswith("},"):
                dropping_json = False
            continue
        cleaned_lines.append(line)

    cleaned = "\n".join(cleaned_lines).strip()
    while "\n\n\n" in cleaned:
        cleaned = cleaned.replace("\n\n\n", "\n\n")
    return cleaned or "I could not produce a clean answer from the current project context."


def _wants_formula_details(question: str) -> bool:
    q = f" {question.lower()} "
    return any(
        token in q
        for token in [
            " formula",
            " calculate",
            " calculated",
            " calculation",
            " math",
            " derive",
            " step by step",
            " show me",
            " exact",
            " equation",
            " pca loading",
            " pc1",
        ]
    )


def _plain_market_answer(question: str) -> str:
    q = question.lower()
    if any(token in q for token in ["fuel", "oil", "brent", "crude", "jet"]):
        return (
            "Fuel prices affect the credit recommendation because they directly influence an airline's operating cost and cash-flow pressure.\n"
            "When fuel becomes expensive, margins can tighten and the company may need more working capital to buy the same volume of fuel.\n"
            "That can make the counterparty look riskier, especially if liquidity or profitability is already weak.\n"
            "In the recommendation, this can show up as a lower approved limit, shorter credit days, or stronger security such as a guarantee or letter of credit.\n"
            "If the company has strong cash, good margins, and low leverage, the effect is usually more moderate."
        )
    if any(token in q for token in ["usd", "fx", "currency", "dxy", "inr"]):
        return (
            "FX movements matter because fuel is often linked to USD pricing while many airlines earn a large part of revenue in local currency.\n"
            "If the local currency weakens, fuel and dollar-linked obligations become more expensive in local terms.\n"
            "That can pressure margins, liquidity, and repayment capacity.\n"
            "The credit recommendation may therefore become more conservative through a lower limit, tighter tenor, or extra security.\n"
            "The impact is smaller when the company has natural USD revenue, hedging, or strong cash reserves."
        )
    if any(token in q for token in ["stress", "market", "vix", "regime", "macro"]):
        return (
            "Market stress affects the recommendation because it tells the model whether the external environment is calm or risky.\n"
            "When stress is high, companies are more exposed to sudden cost increases, weaker demand, and tighter funding conditions.\n"
            "For a fuel buyer or airline, that can increase default risk even if the latest financial statement still looks acceptable.\n"
            "The system may respond by reducing the recommended limit, shortening tenor, or asking for stronger credit support.\n"
            "In simple terms, good company financials matter, but the market backdrop can still make the recommendation more cautious."
        )
    return (
        "This market factor affects the recommendation by changing the external risk around the counterparty.\n"
        "If the factor makes costs higher, demand weaker, or funding conditions tighter, the credit view becomes more cautious.\n"
        "That can influence the recommended limit, tenor, security requirement, and overall approval status.\n"
        "The effect is strongest when the company already has weak liquidity, high leverage, or thin margins.\n"
        "If the company is financially strong, the same market move may only have a moderate impact."
    )


def _field_credit_terms_impact(field_name: str) -> str:
    impacts = {
        "current_ratio": (
            "For credit terms, a stronger current ratio usually supports more comfortable limits, normal tenor, and less need for extra security because short-term assets cover short-term liabilities better. "
            "A weak current ratio does the opposite: it can push the engine toward a lower limit, shorter tenor, more collateral, or closer monitoring because repayment liquidity is tighter."
        ),
        "quick_ratio": (
            "For credit terms, quick ratio is a stricter liquidity check. A strong value supports cleaner terms; a weak value can reduce appetite because the company may rely on slower-moving assets to meet short-term obligations."
        ),
        "cash_ratio": (
            "For credit terms, cash ratio tells you how much immediate cash cushion exists. Strong cash coverage helps support unsecured or longer terms, while weak cash coverage can justify tighter limits or security."
        ),
        "debt_to_ebitda": (
            "For credit terms, higher Debt/EBITDA reduces headroom because more cash earnings are already spoken for by debt. That can mean a lower limit, shorter tenor, or stronger security."
        ),
        "debt_to_equity": (
            "For credit terms, higher Debt/Equity signals more leverage and less balance-sheet cushion. That can make the recommendation more conservative."
        ),
        "interest_coverage": (
            "For credit terms, stronger interest coverage supports repayment capacity. Weak coverage can reduce tenor and limit size because debt service is already pressuring cash flow."
        ),
        "final_pd": (
            "For credit terms, higher final PD directly raises default risk. That can lower the recommended limit, shorten tenor, worsen risk grade, and increase security requirements."
        ),
        "expected_loss": (
            "For credit terms, expected loss is the dollar risk anchor. Higher expected loss pushes the recommendation toward lower exposure, tighter tenor, or better collateral."
        ),
        "stress_index": (
            "For credit terms, higher market stress is an external warning signal. It can make the engine more conservative even if the latest financial statement has not changed."
        ),
        "revenue": (
            "For credit terms, revenue gives scale. A larger, stable revenue base can support a bigger requested line; very small or volatile revenue makes the same limit look more aggressive."
        ),
        "ebitda": (
            "For credit terms, EBITDA is the cash-earnings proxy. Strong EBITDA supports repayment capacity, while weak or negative EBITDA pushes the engine toward tighter tenor, lower limits, or more security."
        ),
        "ebit": (
            "For credit terms, EBIT is the operating-profit input behind interest coverage and operating margin. If EBIT is weak or missing, the app cannot confidently assess debt-service capacity, so terms should be treated more cautiously."
        ),
        "accounts_receivable": (
            "For credit terms, accounts receivable helps measure quick liquidity. Strong collectible receivables improve short-term liquidity; missing or weak receivables make quick-ratio analysis less reliable."
        ),
        "inventory": (
            "For credit terms, inventory matters because quick ratio excludes slower-moving stock. Higher inventory inside current assets can make current ratio look better than true liquid coverage."
        ),
        "total_debt": (
            "For credit terms, more debt means more fixed obligations ahead of trade creditors. That usually reduces credit headroom unless earnings and liquidity are strong enough to absorb it."
        ),
        "shareholders_equity": (
            "For credit terms, stronger equity gives a balance-sheet cushion. Thin or negative equity makes the recommendation more conservative because losses can wipe out capital faster."
        ),
        "structural_pd": (
            "For credit terms, structural PD is one of the default-risk anchors. If it rises, the blended final PD usually rises too, which can reduce limit, shorten tenor, or increase security."
        ),
        "ml_pd": (
            "For credit terms, ML PD is the data-driven cross-check. If the ratios and market features look risky, ML PD can pull final PD upward and make terms tighter."
        ),
        "distance_to_default": (
            "For credit terms, a lower distance to default means the company is closer to the modeled default barrier. That increases PD pressure and can tighten the recommendation."
        ),
        "predicted_lgd": (
            "For credit terms, LGD controls severity if default happens. Higher LGD means collateral protection is weaker, so the engine may ask for security or reduce the approved exposure."
        ),
        "exposure_at_default": (
            "For credit terms, EAD is the amount expected to be outstanding at default. Higher EAD increases expected loss and can force a lower limit or tighter usage controls."
        ),
        "recommended_credit_limit": (
            "For credit terms, this is the direct output: the engine starts from the requested/base limit and applies risk haircuts from PD, LGD, stress, leverage, tenor, collateral, and tail risk."
        ),
        "recommended_tenor_days": (
            "For credit terms, tenor controls how long receivables can remain unpaid. Shorter tenor reduces build-up risk when PD, stress, or liquidity pressure is elevated."
        ),
        "recommended_security": (
            "For credit terms, security reduces loss severity. Guarantees, deposits, or letters of credit can make approval possible when unsecured exposure would be too risky."
        ),
        "risk_grade": (
            "For credit terms, risk grade converts PD into a simpler credit label. Weaker grades usually mean smaller limits, shorter tenor, and stronger security."
        ),
        "approval_status": (
            "For credit terms, approval status is the final policy label. It summarizes whether the modeled risk can be accepted as-is, accepted with conditions, or declined."
        ),
        "market_regime": (
            "For credit terms, market regime tells the engine whether the backdrop is normal or stressed. A stressed regime can tighten terms even before company financials deteriorate."
        ),
        "pc1_score": (
            "For credit terms, PC1 is the compressed market stress factor. A higher stress signal feeds the stress index, which can raise PD pressure and tighten the final recommendation."
        ),
        "pca_loadings": (
            "For credit terms, PCA loadings explain which market drivers are behind the stress score. They do not set terms by themselves, but they explain why stress is moving."
        ),
    }
    return impacts.get(
        field_name,
        "For credit terms, this field matters when it changes PD, LGD, EAD, policy score, or the confidence the engine has in repayment capacity.",
    )


def _fallback_answer(
    question: str,
    *,
    style: str,
    retrieved: list[dict[str, Any]],
    knowledge_hits: list[dict[str, Any]],
    trace: dict[str, Any] | None,
    field_context: dict[str, Any] | None = None,
    market_trace: dict[str, Any] | None = None,
    include_trace_details: bool = False,
) -> str:
    parts: list[str] = []
    wants_formula_details = _wants_formula_details(question) or include_trace_details
    if field_context and field_context.get("field"):
        field = field_context["field"]
        display = field.get("display_name") or field.get("field")
        meaning = field.get("meaning")
        formula = field_context.get("formula") or {}
        parts.append(f"{display} means {str(meaning).rstrip('.')}.")
        if wants_formula_details and formula.get("formula"):
            parts.append(f"In this project it is calculated as `{formula['formula']}`.")
        parts.append(_field_credit_terms_impact(str(field.get("field") or "")))
        if style == "interview" and field.get("interview_explanation"):
            parts.append(f"Interview way to say it: {field['interview_explanation']}")

    if market_trace:
        if wants_formula_details:
            parts.append(str(market_trace.get("summary") or "This market question is traced through the project PCA/stress layer."))
            formulas = market_trace.get("formulas") or []
            if formulas:
                parts.append("The key chain is: " + " -> ".join(str(item) for item in formulas[:3]) + ".")
            selected = market_trace.get("selected_components") or []
            if selected:
                top = selected[0]
                contribution = top.get("pc1_contribution")
                contribution_text = f", PC1 contribution {contribution:.4f}" if isinstance(contribution, (int, float)) else ""
                parts.append(
                    f"Most relevant PCA component: {top.get('component')} ({top.get('description')}) with loading {top.get('loading')}{contribution_text}."
                )
        else:
            parts.append(_plain_market_answer(question))

    if trace and trace.get("matched") and wants_formula_details and (include_trace_details or not field_context):
        if not field_context:
            parts.append(
                f"Yep, the clean project formula here is `{trace.get('formula')}`."
            )
        if trace.get("result") is not None:
            parts.append(
                f"Using the values supplied, the calculation is `{trace.get('calculation')}`, which gives `{trace.get('result')}`."
            )
        else:
            missing = trace.get("missing_inputs") or []
            if missing:
                parts.append(
                    "I can explain the flow, but I cannot calculate the exact number unless these inputs are supplied: "
                    + ", ".join(str(item) for item in missing)
                    + "."
                )
        if trace.get("plain_english"):
            parts.append(str(trace["plain_english"]))

    if knowledge_hits and not field_context:
        top = knowledge_hits[0]["item"]
        explanation = (
            top.get("interview_explanation")
            or top.get("plain_english")
            or top.get("explanation")
            or top.get("limitations")
        )
        if explanation:
            parts.append(str(explanation))

    if not parts:
        parts.append(
            "I do not have enough project context for that exact question yet. The safe answer is that the supporting data is missing."
        )

    if style == "interview":
        parts.insert(
            0,
            "Interview version: I would explain it as an auditable chain from source data to model output to credit decision.",
        )
    answer = "\n\n".join(parts)
    if not wants_formula_details and style != "technical":
        paragraphs = [part.strip() for part in answer.split("\n\n") if part.strip()]
        compact = "\n".join(paragraphs)
        lines = [line.strip() for line in compact.splitlines() if line.strip()]
        answer = "\n".join(lines[:10])
    return answer


def build_grounded_prompt(
    question: str,
    *,
    style: str,
    answer_mode: AnswerMode,
    retrieval_context: str,
    knowledge_hits: list[dict[str, Any]],
    trace: dict[str, Any] | None,
    market_trace: dict[str, Any] | None = None,
) -> str:
    """Build the prompt used for the local Qwen/Ollama model."""
    tone = {
        "casual_precise": "casual, direct, not stiff, but technically accurate",
        "interview": "clear interview explanation the user can say out loud",
        "technical": "implementation-focused with file/table/formula details",
        "short": "brief and high-signal",
    }.get(style, "casual, direct, not stiff, but technically accurate")

    knowledge_text = "\n".join(
        f"- {hit['kind']} score={hit['score']}: {hit['item']}"
        for hit in knowledge_hits[:6]
    )
    trace_text = str(trace or "No deterministic formula trace matched.")
    market_trace_text = str(market_trace or "No deterministic market/PCA trace matched.")

    return f"""
You are the informal but accurate project copilot for CREDIT_RISK_PROJECT_V2.

Tone: {tone}.
Answer mode: {answer_mode.name}.

Rules:
1. Use only the provided project context for project-specific claims.
2. Do not invent numbers, files, formulas, tables, PCA steps, model metrics, limits, grades, or approval decisions.
3. If a value is missing, say it is missing.
4. If data is proxy, synthetic, calibrated, or not production-grade, say that clearly.
5. Default to a ChatGPT-like explanation in 5 to 10 short lines.
6. Do not show formulas, PCA chains, loadings, source paths, table names, JSON, or implementation details unless Answer mode is calculation or technical.
7. Explain formulas step by step only when Answer mode is calculation.
8. Keep the voice natural. Do not sound like a formal bank memo unless style is interview.
9. Do not include a sources section unless Answer mode is technical and source details were requested.

QUESTION:
{question}

DETERMINISTIC FORMULA TRACE:
{trace_text}

DETERMINISTIC MARKET/PCA TRACE:
{market_trace_text}

KNOWLEDGE CATALOG HITS:
{knowledge_text or "No exact catalog hits."}

{retrieval_context}

Answer the question now without listing source paths.
""".strip()


def answer_project_question(
    question: str,
    *,
    style: str = "casual_precise",
    use_llm: bool | None = None,
    values: dict[str, Any] | None = None,
    retrieval_limit: int = 6,
) -> dict[str, Any]:
    """Answer a project question with local retrieval and optional Qwen/Ollama."""
    route = classify_project_question(question)
    effective_style = route.style_hint or style
    retrieval_query = " ".join([question, *route.retrieval_focus])
    retrieved = retrieve_project_context(retrieval_query, limit=retrieval_limit)
    forced_sources = retrieve_context_by_source(route.retrieval_focus, limit=4)
    merged: list[dict[str, Any]] = []
    seen_sources: set[str] = set()
    for item in [*forced_sources, *retrieved]:
        source = item["source_path"]
        if source in seen_sources:
            continue
        seen_sources.add(source)
        merged.append(item)
        if len(merged) >= retrieval_limit:
            break
    retrieved = merged
    knowledge_hits = search_knowledge(question, limit=8)
    trace_target = route.trace_target or _infer_trace_target(question)
    trace = trace_formula(trace_target, values or {}) if trace_target else None
    market_trace = None
    if route.intent in {"market_pca_explanation", "market_factor_explanation"}:
        market_trace = explain_market_factor(
            factor=question,
            stress_record=values or {},
        )

    field_context = None
    if trace_target:
        field_context = describe_field(trace_target)

    should_use_llm = settings.copilot_use_llm if use_llm is None else use_llm
    retrieval_context = format_retrieval_context(retrieved)
    answer_mode = determine_answer_mode(question, route.intent, effective_style)

    if should_use_llm:
        prompt = build_grounded_prompt(
            question,
            style=effective_style,
            answer_mode=answer_mode,
            retrieval_context=retrieval_context,
            knowledge_hits=knowledge_hits,
            trace=trace,
            market_trace=market_trace,
        )
        try:
            answer = _clean_copilot_answer(generate_response(prompt))
            mode = "ollama_grounded_project_context"
        except Exception as exc:
            answer = compose_copilot_answer(
                question=question,
                route_intent=route.intent,
                mode=answer_mode,
                retrieved=retrieved,
                knowledge_hits=knowledge_hits,
                trace=trace,
                field_context=field_context,
                market_trace=market_trace,
                values=values or {},
            )
            answer += f"\n\nLLM note: local Ollama/Qwen was unavailable, so I used deterministic local retrieval instead. Error: {exc}"
            answer = _clean_copilot_answer(answer)
            mode = "local_retrieval_fallback_after_llm_error"
    else:
        answer = compose_copilot_answer(
            question=question,
            route_intent=route.intent,
            mode=answer_mode,
            retrieved=retrieved,
            knowledge_hits=knowledge_hits,
            trace=trace,
            field_context=field_context,
            market_trace=market_trace,
            values=values or {},
        )
        answer = _clean_copilot_answer(answer)
        mode = "local_retrieval_no_llm"

    return {
        "question": question,
        "answer": answer,
        "mode": mode,
        "answer_mode": answer_mode.name,
        "style": effective_style,
        "route": route_to_dict(route),
        "trace": trace,
        "market_trace": market_trace,
        "field_context": field_context,
        "knowledge_hits": knowledge_hits,
        "retrieved_context": retrieved,
        "sources": _compact_sources(retrieved),
        "uses_paid_resources": False,
    }
