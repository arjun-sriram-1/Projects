import psycopg2
import json

from api.rag.config import DB_CONFIG

from api.rag.document_utils import (
    create_metadata,
    format_currency
)


def get_connection():

    return psycopg2.connect(**DB_CONFIG)


QUERY = """
SELECT *

FROM scenario_results
"""


def build_document(row):

    return f"""
STRESS TEST SCENARIO

Scenario:
{row["scenario_name"]}

Expected Loss:
{format_currency(row["expected_loss"])}

VaR 95:
{format_currency(row["var_95"])}

Expected Shortfall:
{format_currency(row["expected_shortfall"])}

Unexpected Loss:
{format_currency(row["unexpected_loss"])}

Maximum Loss:
{format_currency(row["max_loss"])}
"""


def main():

    conn = get_connection()

    cur = conn.cursor()

    cur.execute(QUERY)

    columns = [desc[0] for desc in cur.description]

    rows = cur.fetchall()

    for r in rows:

        row = dict(zip(columns, r))

        content = build_document(row)

        metadata = {

            "scenario": row["scenario_name"],

            "document_type": "stress"
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
                "stress",
                "scenario_results",
                row["scenario_id"],
                row["scenario_name"],
                content,
                json.dumps(metadata)
            )
        )

    conn.commit()

    cur.close()

    conn.close()

    print("Stress documents created.")


if __name__ == "__main__":
    main()

