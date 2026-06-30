from api.rag.retriever.lazy_faiss import search_index


def search_policy(query, k=2):
    return search_index(
        query,
        "policy_index.faiss",
        "policy_metadata.pkl",
        k,
    )
