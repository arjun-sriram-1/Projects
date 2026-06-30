"""Inspect key V2 database tables.

This script requires a valid `DB_URL` in `.env` and a reachable PostgreSQL
database. It does not create or modify tables.
"""

from __future__ import annotations

from sqlalchemy import inspect

from api.db.session import SessionLocal


TABLES_TO_CHECK = [
    "counterparties_master",
    "uploaded_documents",
    "financial_metrics_extracted",
    "financial_ratios",
    "pd_model_predictions",
    "loss_estimates",
    "scenario_results",
    "simulation_results",
    "credit_recommendations",
]


def describe_tables() -> dict[str, list[str]]:
    """Return table names mapped to their column names."""
    with SessionLocal() as db:
        inspector = inspect(db.get_bind())
        result: dict[str, list[str]] = {}
        for table_name in TABLES_TO_CHECK:
            result[table_name] = [
                column["name"] for column in inspector.get_columns(table_name)
            ]
        return result


def main() -> None:
    """Print a compact schema summary for manual verification."""
    print("\n=== V2 CREDIT RISK SCHEMA CHECK ===\n")
    for table_name, columns in describe_tables().items():
        print(f"{table_name}:")
        for column_name in columns[:8]:
            print(f"  {column_name}")
        if len(columns) > 8:
            print(f"  ... and {len(columns) - 8} more columns")
        print()
    print("Schema verification complete.")


if __name__ == "__main__":
    main()

