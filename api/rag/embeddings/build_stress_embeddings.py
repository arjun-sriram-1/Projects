import psycopg2

from sentence_transformers import (
    SentenceTransformer
)

from api.rag.config import DB_CONFIG

from api.rag.vector_store.faiss_manager import (
    create_index,
    add_embeddings,
    save_index
)

from api.rag.vector_store.metadata_manager import (
    save_metadata
)

def get_connection():

    return psycopg2.connect(
        **DB_CONFIG
    )
    
def main():

    model = SentenceTransformer(
        "all-MiniLM-L6-v2"
    )

    conn = get_connection()

    cur = conn.cursor()

    cur.execute(
        """
        SELECT
        id,
        content

        FROM rag_documents

        WHERE document_type='stress'
        """
    )

    rows = cur.fetchall()
    ids = []

    documents = []

    for row in rows:

        ids.append(row[0])

        documents.append(
            row[1]
        )
        embeddings = model.encode(
        documents,
        show_progress_bar=True
    )
        index = create_index(
        embeddings.shape[1]
    )

    index = add_embeddings(
        index,
        embeddings
    )
    save_index(
        index,
        "data/vector_store/stress_index.faiss"
    )
    metadata = {

        "ids": ids,

        "documents": documents
    }

    save_metadata(
        metadata,
        "data/vector_store/stress_metadata.pkl"
    )
    print(
        "Stress index created."
    )

if __name__ == "__main__":
    main()

