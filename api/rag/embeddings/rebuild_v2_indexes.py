"""Rebuild V2 RAG documents and FAISS indexes from current project tables.

This utility replaces stale V1-style RAG documents with grounded V2 documents
that match the fuel credit-line workflow: requested terms, financial strength,
PD/LGD/EAD, expected loss, market/scenario context, and final recommendation.
"""

from __future__ import annotations

import json
import pickle
from decimal import Decimal
from pathlib import Path
from typing import Any

import faiss
import numpy as np
from sentence_transformers import SentenceTransformer
from sqlalchemy import text

from api.core.config import settings
from api.db.session import engine


DOCUMENT_TYPES = ["counterparty", "policy", "stress", "monte_carlo"]
INDEX_FILES = {
    "counterparty": ("counterparty_index.faiss", "counterparty_metadata.pkl"),
    "policy": ("policy_index.faiss", "policy_metadata.pkl"),
    "stress": ("stress_index.faiss", "stress_metadata.pkl"),
    "monte_carlo": ("montecarlo_index.faiss", "montecarlo_metadata.pkl"),
}


def _json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    return value


def _money(value: Any) -> str:
    try:
        if value is None:
            return "missing"
        return f"${float(value):,.0f}"
    except (TypeError, ValueError):
        return "missing"


def _pct(value: Any) -> str:
    try:
        if value is None:
            return "missing"
        return f"{float(value) * 100:.2f}%"
    except (TypeError, ValueError):
        return "missing"


def _ratio(value: Any) -> str:
    try:
        if value is None:
            return "missing"
        return f"{float(value):.2f}x"
    except (TypeError, ValueError):
        return "missing"


def _list_text(value: Any) -> str:
    if not value:
        return "None stored"
    if isinstance(value, list):
        return "; ".join(str(item) for item in value)
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return "; ".join(str(item) for item in parsed)
        except Exception:
            pass
        return value
    return json.dumps(value, default=str)


def _dict_text(value: Any) -> str:
    if not value:
        return "None stored"
    if isinstance(value, str):
        return value
    return json.dumps(value, default=str)


def _fetch_all(sql: str) -> list[dict[str, Any]]:
    with engine.connect() as connection:
        return [dict(row) for row in connection.execute(text(sql)).mappings().all()]


def build_counterparty_documents() -> list[dict[str, Any]]:
    rows = _fetch_all(
        """
        SELECT
            cp.id AS counterparty_id,
            cp.counterparty_name,
            cp.counterparty_type,
            cp.country,
            fm.fiscal_year,
            fm.currency,
            fm.revenue,
            fm.ebitda,
            fm.ebit,
            fm.net_income,
            fm.cash_and_equivalents,
            fm.accounts_receivable,
            fm.inventory,
            fm.total_debt,
            fm.shareholders_equity,
            fm.extraction_confidence,
            fr.current_ratio,
            fr.quick_ratio,
            fr.debt_to_ebitda,
            fr.debt_to_equity,
            fr.interest_coverage,
            fr.operating_margin,
            pd.final_pd,
            pd.structural_pd,
            pd.ml_pd,
            pd.distance_to_default,
            pd.market_regime,
            pd.market_stress_index,
            pd.feature_contributions,
            le.predicted_lgd,
            le.exposure_at_default,
            le.expected_loss AS loss_expected_loss,
            le.collateral_strength,
            te.requested_credit_limit,
            te.approved_credit_limit,
            te.payment_tenor_days,
            te.collateral_type,
            te.utilization_rate,
            cr.approval_status,
            cr.risk_grade,
            cr.recommended_credit_limit,
            cr.recommended_tenor_days,
            cr.recommended_security,
            cr.expected_loss AS recommendation_expected_loss,
            cr.scenario_expected_loss,
            cr.credit_var_95,
            cr.expected_shortfall_95,
            cr.policy_score,
            cr.key_risk_drivers,
            cr.mitigating_factors,
            cr.warnings
        FROM counterparties_master cp
        LEFT JOIN LATERAL (
            SELECT *
            FROM financial_metrics_extracted
            WHERE counterparty_id = cp.id
            ORDER BY fiscal_year DESC NULLS LAST, created_at DESC, id DESC
            LIMIT 1
        ) fm ON TRUE
        LEFT JOIN LATERAL (
            SELECT *
            FROM financial_ratios
            WHERE counterparty_id = cp.id
            ORDER BY fiscal_year DESC NULLS LAST, calculation_date DESC, id DESC
            LIMIT 1
        ) fr ON TRUE
        LEFT JOIN LATERAL (
            SELECT *
            FROM pd_model_predictions
            WHERE counterparty_id = cp.id
            ORDER BY created_at DESC, id DESC
            LIMIT 1
        ) pd ON TRUE
        LEFT JOIN LATERAL (
            SELECT *
            FROM loss_estimates
            WHERE counterparty_id = cp.id
            ORDER BY created_at DESC, id DESC
            LIMIT 1
        ) le ON TRUE
        LEFT JOIN LATERAL (
            SELECT *
            FROM trade_exposures
            WHERE counterparty_id = cp.id
            ORDER BY created_at DESC, id DESC
            LIMIT 1
        ) te ON TRUE
        LEFT JOIN LATERAL (
            SELECT *
            FROM credit_recommendations
            WHERE counterparty_id = cp.id
            ORDER BY created_at DESC, id DESC
            LIMIT 1
        ) cr ON TRUE
        WHERE fm.id IS NOT NULL
           OR fr.id IS NOT NULL
           OR pd.id IS NOT NULL
           OR le.id IS NOT NULL
           OR te.id IS NOT NULL
           OR cr.id IS NOT NULL
        ORDER BY cp.id
        """
    )

    documents: list[dict[str, Any]] = []
    for row in rows:
        content = f"""
COUNTERPARTY CREDIT LINE ANALYSIS

Counterparty: {row.get("counterparty_name")}
Counterparty ID: {row.get("counterparty_id")}
Type: {row.get("counterparty_type") or "missing"}
Country: {row.get("country") or "missing"}

REQUESTED CREDIT TERMS
Requested Credit Line: {_money(row.get("requested_credit_limit"))}
Approved / Current Line: {_money(row.get("approved_credit_limit"))}
Requested Tenor: {row.get("payment_tenor_days") or "missing"} days
Requested Security / Collateral Type: {row.get("collateral_type") or "missing"}
Utilization Rate: {_pct(row.get("utilization_rate"))}

FINANCIAL STRENGTH
Fiscal Year: {row.get("fiscal_year") or "missing"}
Currency: {row.get("currency") or "missing"}
Revenue: {_money(row.get("revenue"))}
EBITDA: {_money(row.get("ebitda"))}
EBIT / Operating Profit: {_money(row.get("ebit"))}
Net Income: {_money(row.get("net_income"))}
Cash: {_money(row.get("cash_and_equivalents"))}
Accounts Receivable: {_money(row.get("accounts_receivable"))}
Inventory: {_money(row.get("inventory"))}
Total Debt: {_money(row.get("total_debt"))}
Equity: {_money(row.get("shareholders_equity"))}
Current Ratio: {_ratio(row.get("current_ratio"))}
Quick Ratio: {_ratio(row.get("quick_ratio"))}
Debt / EBITDA: {_ratio(row.get("debt_to_ebitda"))}
Debt / Equity: {_ratio(row.get("debt_to_equity"))}
Interest Coverage: {_ratio(row.get("interest_coverage"))}
Operating Margin: {_pct(row.get("operating_margin"))}
Extraction Confidence: {_pct(row.get("extraction_confidence"))}

MODEL OUTPUTS
Final PD: {_pct(row.get("final_pd"))}
Structural PD: {_pct(row.get("structural_pd"))}
ML PD: {_pct(row.get("ml_pd"))}
Distance To Default: {_ratio(row.get("distance_to_default"))}
LGD: {_pct(row.get("predicted_lgd"))}
EAD: {_money(row.get("exposure_at_default"))}
Expected Loss: {_money(row.get("loss_expected_loss"))}
Collateral Strength: {_ratio(row.get("collateral_strength"))}
Market Regime: {row.get("market_regime") or "missing"}
Market Stress Index: {row.get("market_stress_index") or "missing"}
PD Feature Contributions: {_dict_text(row.get("feature_contributions"))}

FINAL CREDIT RECOMMENDATION
Approval Status: {row.get("approval_status") or "missing"}
Risk Grade: {row.get("risk_grade") or "missing"}
Recommended Credit Line: {_money(row.get("recommended_credit_limit"))}
Recommended Tenor: {row.get("recommended_tenor_days") or "missing"} days
Recommended Security: {row.get("recommended_security") or "missing"}
Recommendation Expected Loss: {_money(row.get("recommendation_expected_loss"))}
Scenario Expected Loss: {_money(row.get("scenario_expected_loss"))}
Credit VaR 95: {_money(row.get("credit_var_95"))}
Expected Shortfall 95: {_money(row.get("expected_shortfall_95"))}
Policy Score: {_ratio(row.get("policy_score"))}
Key Risk Drivers: {_list_text(row.get("key_risk_drivers"))}
Mitigating Factors: {_list_text(row.get("mitigating_factors"))}
Warnings: {_list_text(row.get("warnings"))}

SOURCE TABLES
counterparties_master, financial_metrics_extracted, financial_ratios,
pd_model_predictions, loss_estimates, trade_exposures, credit_recommendations.
"""
        documents.append(
            {
                "document_type": "counterparty",
                "source_table": "counterparties_master",
                "source_id": str(row.get("counterparty_id")),
                "title": row.get("counterparty_name") or f"Counterparty {row.get('counterparty_id')}",
                "content": content.strip(),
                "metadata": {
                    "counterparty_id": row.get("counterparty_id"),
                    "document_type": "counterparty",
                    "workflow": "credit_line_analysis",
                },
            }
        )
    return documents


def build_policy_documents() -> list[dict[str, Any]]:
    policy_dir = settings.data_dir / "rag_documents" / "policy"
    documents: list[dict[str, Any]] = []
    for source_id, path in enumerate(sorted(policy_dir.glob("*.txt")), start=1):
        content = path.read_text(encoding="utf-8").strip()
        documents.append(
            {
                "document_type": "policy",
                "source_table": "data/rag_documents/policy",
                "source_id": str(source_id),
                "title": path.stem.replace("_", " ").title(),
                "content": content,
                "metadata": {
                    "filename": path.name,
                    "document_type": "policy",
                    "workflow": "credit_line_policy",
                },
            }
        )
    return documents


def build_stress_documents() -> list[dict[str, Any]]:
    rows = _fetch_all(
        """
        SELECT scenario_id, run_id, scenario_name, scenario_type, expected_loss,
               var_95, var_99, expected_shortfall_95, expected_shortfall_99,
               unexpected_loss, max_loss, scenario_inputs, scenario_impacts,
               assumptions_reference, number_of_counterparties,
               number_of_simulations, created_at
        FROM scenario_results
        ORDER BY created_at DESC, scenario_id DESC
        LIMIT 80
        """
    )
    documents = []
    for row in rows:
        content = f"""
SCENARIO AND STRESS RESULT

Scenario: {row.get("scenario_name") or row.get("scenario_type") or "missing"}
Scenario Type: {row.get("scenario_type") or "missing"}
Run ID: {row.get("run_id") or "missing"}
Counterparties Included: {row.get("number_of_counterparties") or "missing"}
Simulations: {row.get("number_of_simulations") or "missing"}

Expected Loss: {_money(row.get("expected_loss"))}
VaR 95: {_money(row.get("var_95"))}
VaR 99: {_money(row.get("var_99"))}
Expected Shortfall 95: {_money(row.get("expected_shortfall_95"))}
Expected Shortfall 99: {_money(row.get("expected_shortfall_99"))}
Unexpected Loss: {_money(row.get("unexpected_loss"))}
Maximum Loss: {_money(row.get("max_loss"))}

Scenario Inputs: {_dict_text(row.get("scenario_inputs"))}
Scenario Impacts: {_dict_text(row.get("scenario_impacts"))}
Assumptions: {_dict_text(row.get("assumptions_reference"))}

Use this document to explain how future market conditions may affect expected
loss, tail loss, liquidity pressure, and recommended credit terms.
"""
        documents.append(
            {
                "document_type": "stress",
                "source_table": "scenario_results",
                "source_id": str(row.get("scenario_id")),
                "title": row.get("scenario_name") or f"Scenario {row.get('scenario_id')}",
                "content": content.strip(),
                "metadata": {
                    "scenario_id": row.get("scenario_id"),
                    "run_id": row.get("run_id"),
                    "document_type": "stress",
                },
            }
        )
    return documents


def build_monte_carlo_documents() -> list[dict[str, Any]]:
    rows = _fetch_all(
        """
        SELECT id, run_id, scenario, expected_loss, unexpected_loss, var_95,
               var_99, expected_shortfall_95, expected_shortfall_99,
               avg_defaults, max_defaults, number_of_simulations,
               loss_distribution_summary, marginal_risk_contribution,
               default_correlation, assumptions_reference, created_at
        FROM simulation_results
        ORDER BY created_at DESC, id DESC
        LIMIT 80
        """
    )
    documents = []
    for row in rows:
        content = f"""
MONTE CARLO CREDIT RISK RESULT

Simulation ID: {row.get("id")}
Run ID: {row.get("run_id") or "missing"}
Scenario: {row.get("scenario") or "missing"}
Number Of Simulations: {row.get("number_of_simulations") or "missing"}

Average / Expected Loss: {_money(row.get("expected_loss"))}
Unexpected Loss: {_money(row.get("unexpected_loss"))}
VaR 95: {_money(row.get("var_95"))}
VaR 99: {_money(row.get("var_99"))}
Expected Shortfall 95: {_money(row.get("expected_shortfall_95"))}
Expected Shortfall 99: {_money(row.get("expected_shortfall_99"))}
Average Defaults: {row.get("avg_defaults") if row.get("avg_defaults") is not None else "missing"}
Maximum Defaults: {row.get("max_defaults") if row.get("max_defaults") is not None else "missing"}
Default Correlation: {_ratio(row.get("default_correlation"))}

Loss Distribution Summary: {_dict_text(row.get("loss_distribution_summary"))}
Marginal Risk Contribution: {_dict_text(row.get("marginal_risk_contribution"))}
Assumptions: {_dict_text(row.get("assumptions_reference"))}

Use this document to explain loss distribution, VaR, expected shortfall, and
tail-risk drivers for credit-line sizing.
"""
        documents.append(
            {
                "document_type": "monte_carlo",
                "source_table": "simulation_results",
                "source_id": str(row.get("id")),
                "title": f"Monte Carlo {row.get('run_id') or row.get('id')}",
                "content": content.strip(),
                "metadata": {
                    "simulation_id": row.get("id"),
                    "run_id": row.get("run_id"),
                    "document_type": "monte_carlo",
                },
            }
        )
    return documents


def replace_rag_documents(documents: list[dict[str, Any]]) -> dict[str, int]:
    counts = {doc_type: 0 for doc_type in DOCUMENT_TYPES}
    with engine.begin() as connection:
        connection.execute(
            text("DELETE FROM rag_documents WHERE document_type = ANY(:document_types)"),
            {"document_types": DOCUMENT_TYPES},
        )
        for doc in documents:
            connection.execute(
                text(
                    """
                    INSERT INTO rag_documents
                        (document_type, source_table, source_id, title, content, metadata)
                    VALUES
                        (:document_type, :source_table, :source_id, :title, :content, CAST(:metadata AS JSONB))
                    """
                ),
                {
                    **doc,
                    "metadata": json.dumps(doc["metadata"], default=_json_safe),
                },
            )
            counts[doc["document_type"]] += 1
    return counts


def _load_documents_for_type(document_type: str) -> tuple[list[int], list[str]]:
    rows = _fetch_all(
        f"""
        SELECT id, content
        FROM rag_documents
        WHERE document_type = '{document_type}'
        ORDER BY id
        """
    )
    return [int(row["id"]) for row in rows], [str(row["content"]) for row in rows]


def rebuild_faiss_indexes() -> dict[str, int]:
    settings.vector_store_dir.mkdir(parents=True, exist_ok=True)
    model = SentenceTransformer(settings.embeddings_model_name, local_files_only=True)
    indexed_counts: dict[str, int] = {}

    for document_type, (index_name, metadata_name) in INDEX_FILES.items():
        ids, documents = _load_documents_for_type(document_type)
        if not documents:
            indexed_counts[document_type] = 0
            continue
        embeddings = model.encode(documents, show_progress_bar=False)
        embeddings = np.asarray(embeddings, dtype="float32")
        index = faiss.IndexFlatL2(embeddings.shape[1])
        index.add(embeddings)
        faiss.write_index(index, str(settings.vector_store_dir / index_name))
        with (settings.vector_store_dir / metadata_name).open("wb") as handle:
            pickle.dump({"ids": ids, "documents": documents}, handle)
        indexed_counts[document_type] = len(documents)
    return indexed_counts


def rebuild_all() -> dict[str, dict[str, int]]:
    documents = (
        build_counterparty_documents()
        + build_policy_documents()
        + build_stress_documents()
        + build_monte_carlo_documents()
    )
    doc_counts = replace_rag_documents(documents)
    index_counts = rebuild_faiss_indexes()
    return {"documents": doc_counts, "indexes": index_counts}


def main() -> None:
    result = rebuild_all()
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
