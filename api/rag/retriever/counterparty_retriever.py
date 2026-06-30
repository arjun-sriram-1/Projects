from api.rag.retriever.lazy_faiss import search_index


def search_counterparty(query, k=2):
    return search_index(
        query,
        "counterparty_index.faiss",
        "counterparty_metadata.pkl",
        k,
    )
