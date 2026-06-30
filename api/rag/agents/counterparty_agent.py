from api.rag.retriever.multi_index_retriever import (
    retrieve_context
)

from api.rag.llm.ollama_client import (
    generate_response
)

from api.rag.agents.prompts import (
    COUNTERPARTY_PROMPT
)


def run_counterparty_agent(question):

    context = retrieve_context(question)

    prompt = COUNTERPARTY_PROMPT.format(
        context=context,
        question=question
    )

    return generate_response(prompt)

