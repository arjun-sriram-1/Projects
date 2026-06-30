MISSING_RETRIEVAL_CONTEXT = (
    "No retrieved context is available for this question. "
    "Do not invent financial numbers, credit limits, risk grades, or policy claims. "
    "State that the supporting data is missing."
)


def build_context(documents):
    context = """

==============================
RETRIEVED CREDIT RISK CONTEXT
==============================

"""

    clean_documents = [str(doc).strip() for doc in documents if str(doc).strip()]

    if not clean_documents:
        context += MISSING_RETRIEVAL_CONTEXT
    else:
        for doc in clean_documents:
            context += "\n\n"
            context += doc

    context += """

==============================
END OF CONTEXT
==============================

Only use the retrieved information
to answer the user's question.
"""

    return context
