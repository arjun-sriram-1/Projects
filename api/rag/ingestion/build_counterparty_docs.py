import psycopg2
import json

from api.rag.config import DB_CONFIG

from api.rag.document_utils import (
    create_metadata,
    format_currency,
    format_percentage,
    format_anomaly
)


QUERY = """
SELECT

c.counterparty_id,
c.company_name,
c.sector,
c.country,
c.region,
c.revenue,
c.debt,
c.fleet_size,
c.fuel_dependency,
c.fx_exposure,
c.profit_margin,
c.exposure,
c.security,

m.pd,
m.lgd,
m.expected_loss,
m.risk_segment,
m.anomaly_status

FROM counterparties_master c

JOIN model_predictions m
ON c.counterparty_id = m.counterparty_id

ORDER BY c.counterparty_id
"""


def get_connection():
    return psycopg2.connect(**DB_CONFIG)


def build_document(row):

    return f"""
COUNTERPARTY CREDIT PROFILE

Company:
{row["company_name"]}

Counterparty ID:
{row["counterparty_id"]}

Sector:
{row["sector"]}

Country:
{row["country"]}

Region:
{row["region"]}

Revenue:
{format_currency(row["revenue"])}

Debt:
{format_currency(row["debt"])}

Fleet Size:
{row["fleet_size"]}

Fuel Dependency:
{row["fuel_dependency"]}

FX Exposure:
{row["fx_exposure"]}

Profit Margin:
{row["profit_margin"]}

Exposure:
{format_currency(row["exposure"])}

Security:
{row["security"]}

Predicted PD:
{format_percentage(row["pd"])}

Predicted LGD:
{format_percentage(row["lgd"])}

Expected Loss:
{format_currency(row["expected_loss"])}

Risk Segment:
{row["risk_segment"]}

Anomaly Details:
{format_anomaly(row["anomaly_status"])}
"""


def main():

    conn = get_connection()
    cur = conn.cursor()

    print("Deleting old counterparty docs...")

    cur.execute("""
        DELETE FROM rag_documents
        WHERE document_type='counterparty'
    """)

    conn.commit()

    print("Loading counterparties...")

    cur.execute(QUERY)

    columns = [d[0] for d in cur.description]
    rows = cur.fetchall()

    print(f"Rows fetched = {len(rows)}")

    inserted = 0

    for r in rows:

        row = dict(zip(columns, r))

        content = build_document(row)

        metadata = create_metadata(
            counterparty_id=row["counterparty_id"],
            sector=row["sector"],
            risk_segment=row["risk_segment"],
            document_type="counterparty"
        )

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
            VALUES (%s,%s,%s,%s,%s,%s)
            """,
            (
                "counterparty",
                "counterparties_master",
                row["counterparty_id"],
                row["company_name"],
                content,
                json.dumps(metadata)
            )
        )

        inserted += 1

    conn.commit()

    print(f"Inserted {inserted} documents")

    cur.close()
    conn.close()

    print("Done")


if __name__ == "__main__":
    main()

