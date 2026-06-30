import faiss
import numpy as np


def create_index(dimension):

    return faiss.IndexFlatL2(
        dimension
    )


def add_embeddings(
        index,
        embeddings
):

    embeddings = np.array(
        embeddings,
        dtype="float32"
    )

    index.add(
        embeddings
    )

    return index


def save_index(
        index,
        path
):

    faiss.write_index(
        index,
        path
    )


def load_index(path):

    return faiss.read_index(
        path
    )

