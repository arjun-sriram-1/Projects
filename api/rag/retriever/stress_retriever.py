from api.rag.retriever.lazy_faiss import search_index


def search_stress(query, k=3):
    return search_index(
        query,
        "stress_index.faiss",
        "stress_metadata.pkl",
        k,
    )
