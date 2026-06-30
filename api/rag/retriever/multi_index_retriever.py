from api.rag.retriever.intent_router import (
    detect_intent
)

from api.rag.retriever.counterparty_retriever import (
    search_counterparty
)

from api.rag.retriever.stress_retriever import (
    search_stress
)

from api.rag.retriever.montecarlo_retriever import (
    search_montecarlo
)

from api.rag.retriever.policy_retriever import (
    search_policy
)

from api.rag.retriever.context_builder import (
    build_context
)


def retrieve_context(question):

    intent = detect_intent(
        question
    )

    docs = []

    if intent == "counterparty":

        docs.extend(
            search_counterparty(question)
        )

    elif intent == "stress":

        docs.extend(
            search_stress(question)
        )

    elif intent == "montecarlo":

        docs.extend(
            search_montecarlo(question)
        )

    elif intent == "policy":

        docs.extend(
            search_policy(question)
        )

    elif intent == "credit_decision":

        docs.extend(
            search_counterparty(question)
        )

        docs.extend(
            search_policy(question)
        )

    else:

        docs.extend(
            search_counterparty(question)
        )

        docs.extend(
            search_policy(question)
        )

    return build_context(
        docs
    )

