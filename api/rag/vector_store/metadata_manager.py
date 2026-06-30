import pickle


def save_metadata(
        metadata,
        filepath
):

    with open(
        filepath,
        "wb"
    ) as f:

        pickle.dump(
            metadata,
            f
        )


def load_metadata(
        filepath
):

    with open(
        filepath,
        "rb"
    ) as f:

        return pickle.load(f)

