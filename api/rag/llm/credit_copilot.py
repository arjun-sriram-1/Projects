from api.rag.retriever.multi_index_retriever import (
    retrieve_context
)

from api.rag.llm.prompt_templates import (
    CREDIT_RISK_PROMPT
)

from api.rag.llm.ollama_client import (
    generate_response
)


DEBUG = True


def ask_credit_copilot(question):

    context = retrieve_context(
        question
    )

    if DEBUG:

        print("\n")
        print("=" * 100)
        print("RETRIEVED CONTEXT")
        print("=" * 100)
        print(context)
        print("=" * 100)
        print("\n")

    prompt = CREDIT_RISK_PROMPT.format(

        question=question,

        context=context
    )

    response = generate_response(
        prompt
    )

    return response

