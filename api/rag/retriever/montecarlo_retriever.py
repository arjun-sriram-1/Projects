from api.rag.retriever.lazy_faiss import search_index


def search_montecarlo(query, k=3):
    return search_index(
        query,
        "montecarlo_index.faiss",
        "montecarlo_metadata.pkl",
        k,
    )
