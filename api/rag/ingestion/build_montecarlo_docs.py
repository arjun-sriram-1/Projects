import psycopg2
import json

from api.rag.config import DB_CONFIG

from api.rag.document_utils import (
    format_currency
)


def get_connection():

    return psycopg2.connect(**DB_CONFIG)


QUERY = """
SELECT *

FROM monte_carlo_runs
"""


def build_document(row):

    return f"""
MONTE CARLO SIMULATION RESULTS

Simulation Run:
{row["run_id"]}

Average Loss:
{format_currency(row["avg_loss"])}

Maximum Loss:
{format_currency(row["max_loss"])}

Minimum Loss:
{format_currency(row["min_loss"])}

Average Defaults:
{row["avg_defaults"]}

Anomaly Flags Triggered:
{row["anomaly_flags_triggered"]}

Number Of Simulations:
{row["n_simulations"]}
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

            "run_id": row["run_id"],

            "document_type": "monte_carlo"
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
                "monte_carlo",
                "monte_carlo_runs",
                row["run_id"],
                f"Monte Carlo Run {row['run_id']}",
                content,
                json.dumps(metadata)
            )
        )

    conn.commit()

    cur.close()

    conn.close()

    print("Monte Carlo documents created.")


if __name__ == "__main__":
    main()

