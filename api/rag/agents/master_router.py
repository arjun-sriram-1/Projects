from api.rag.agents.intent_classifier import (
    classify_query
)

from api.rag.agents.counterparty_agent import (
    run_counterparty_agent
)

from api.rag.agents.stress_agent import (
    run_stress_agent
)

from api.rag.agents.portfolio_agent import (
    run_portfolio_agent
)
from api.rag.agents.credit_decision_agent import (
    run_credit_decision_agent
)

from api.rag.agents.credit_memo_agent import (
    generate_credit_memo
)
from api.rag.agents.comparison_agent import (
    compare_companies
)
from api.rag.utils.company_extractor import (
    extract_company,
    extract_two_companies
)
from api.core.config import settings
from api.rag.grounded_context import (
    GroundedCopilotContext,
    build_grounded_fallback_answer,
)
from api.rag.llm.ollama_client import generate_response
from api.rag.retriever.multi_index_retriever import retrieve_context
from api.rag.agents.prompts import COUNTERPARTY_PROMPT


def _grounded_prompt(
    query: str,
    grounded_context: GroundedCopilotContext,
    retrieved_context: str,
) -> str:
    return COUNTERPARTY_PROMPT.format(
        context=f"{grounded_context.to_prompt_context()}\n\n{retrieved_context}",
        question=query,
    )


def route_query(query, grounded_context: GroundedCopilotContext | None = None):
    if grounded_context is not None:
        if not settings.copilot_use_llm:
            return build_grounded_fallback_answer(query, grounded_context)
        try:
            retrieved_context = retrieve_context(query)
            prompt = _grounded_prompt(query, grounded_context, retrieved_context)
            return generate_response(prompt)
        except Exception:
            return build_grounded_fallback_answer(query, grounded_context)

    intent = classify_query(query)

    if intent == "stress":
        return run_stress_agent(query)

    elif intent == "portfolio":
        return run_portfolio_agent(query)

    elif intent == "memo":

        company = extract_company(query)

        if company is None:
            company = (
                query.replace("generate", "")
                .replace("credit", "")
                .replace("memo", "")
                .replace("for", "")
                .strip()
            )

        return generate_credit_memo(company)
    
    elif intent == "compare":

        companies = extract_two_companies(query)

        if companies is None:
            return (
            "Please specify two valid "
            "counterparties to compare."
        )

        return compare_companies(
            companies[0],
            companies[1]
        )

    elif intent == "decision":

        return run_credit_decision_agent(query)

    else:
        return run_counterparty_agent(query)


