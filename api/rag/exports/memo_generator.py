from api.rag.agents.credit_memo_agent import (
    generate_credit_memo
)


def build_credit_memo(question):

    memo_text = generate_credit_memo(
        question
    )

    return memo_text

