import psycopg2
import json

from pathlib import Path

from api.rag.config import DB_CONFIG


POLICY_FOLDER = "data/rag_documents/policy"


def get_connection():

    return psycopg2.connect(**DB_CONFIG)


def main():

    conn = get_connection()

    cur = conn.cursor()

    for file in Path(POLICY_FOLDER).glob("*.txt"):

        with open(
            file,
            "r",
            encoding="utf-8"
        ) as f:

            content = f.read()

        metadata = {

            "policy_name": file.stem,

            "document_type": "policy"
        }

        cur.execute(
            """
            INSERT INTO rag_documents
            (
            document_type,
            source_table,
            source_id,
            title,
            content,
            metadata
            )

            VALUES
            (%s,%s,%s,%s,%s,%s)
            """,
            (
                "policy",
                "policy_documents",
                0,
                file.stem,
                content,
                json.dumps(metadata)
            )
        )

    conn.commit()

    cur.close()

    conn.close()

    print("Policy documents created.")


if __name__ == "__main__":
    main()

