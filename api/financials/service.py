"""Persistence service for Phase 3 financial ratio calculations."""

from datetime import datetime
from decimal import Decimal

from sqlalchemy.orm import Session

from api.db.models import (
    CounterpartyMaster,
    FinancialMetricsExtracted,
    FinancialRatios,
    UploadedDocument,
)
from api.financials.schemas import ManualFinancialMetricsBatchCreate, ManualFinancialMetricsCreate
from api.financials.trends import calculate_financial_trend_features, calculate_trend_risk_overlay
from api.shared.financial_ratios import FinancialRatioResult, calculate_financial_ratios


CRITICAL_MANUAL_FIELDS = [
    "revenue",
    "ebitda",
    "ebit",
    "net_income",
    "cash_and_equivalents",
    "accounts_receivable",
    "inventory",
    "current_assets",
    "current_liabilities",
    "total_assets",
    "total_debt",
    "total_liabilities",
    "shareholders_equity",
    "interest_expense",
]

MODEL_READY_FIELDS = [
    "revenue",
    "ebitda",
    "ebit",
    "interest_expense",
    "net_income",
    "cash_and_equivalents",
    "accounts_receivable",
    "inventory",
    "current_assets",
    "current_liabilities",
    "total_assets",
    "total_debt",
    "total_liabilities",
    "shareholders_equity",
]


def _decimal_or_none(value: float | None) -> Decimal | None:
    if value is None:
        return None
    return Decimal(str(value))


def _manual_missing_fields(payload: ManualFinancialMetricsCreate) -> list[str]:
    return [
        field_name
        for field_name in CRITICAL_MANUAL_FIELDS
        if getattr(payload, field_name) is None
    ]


def _period_label(payload: ManualFinancialMetricsCreate) -> str:
    if payload.period_label:
        return payload.period_label
    if payload.fiscal_period:
        return payload.fiscal_period
    return "FY" if payload.period_type == "annual" else "Q1"


def _period_sort_key(metrics: FinancialMetricsExtracted) -> tuple[int, int, int]:
    quarter_order = {"FY": 5, "Q4": 4, "Q3": 3, "Q2": 2, "Q1": 1}
    fiscal_period = str(metrics.fiscal_period or "FY").upper()
    return (
        int(metrics.fiscal_year or 0),
        quarter_order.get(fiscal_period, 0),
        int(metrics.id or 0),
    )


def _metadata(metrics: FinancialMetricsExtracted) -> dict:
    return metrics.original_text_references if isinstance(metrics.original_text_references, dict) else {}


def _is_latest(metrics: FinancialMetricsExtracted) -> bool:
    return bool(_metadata(metrics).get("is_latest_snapshot"))


def _model_ready_score(metrics: FinancialMetricsExtracted) -> int:
    return sum(1 for field_name in MODEL_READY_FIELDS if getattr(metrics, field_name, None) is not None)


def _model_ready_missing(metrics: FinancialMetricsExtracted) -> list[str]:
    return [
        field_name
        for field_name in MODEL_READY_FIELDS
        if getattr(metrics, field_name, None) is None
    ]


def _with_latest_flag(metrics: FinancialMetricsExtracted, is_latest: bool) -> None:
    refs = dict(_metadata(metrics))
    refs["is_latest_snapshot"] = bool(is_latest)
    if "period_type" not in refs:
        refs["period_type"] = metrics.period_type
    if "period_label" not in refs:
        refs["period_label"] = metrics.period_label
    metrics.original_text_references = refs


def get_financial_metrics_history(
    db: Session,
    counterparty_id: int,
) -> list[FinancialMetricsExtracted]:
    """Return all stored financial metric periods for a counterparty."""
    rows = (
        db.query(FinancialMetricsExtracted)
        .filter(FinancialMetricsExtracted.counterparty_id == counterparty_id)
        .all()
    )
    return sorted(rows, key=_period_sort_key, reverse=True)


def get_latest_financial_metrics_for_counterparty(
    db: Session,
    counterparty_id: int,
) -> FinancialMetricsExtracted | None:
    """Return the best model-ready latest snapshot, falling back to newest period.

    Analysts can mark a period as latest, but the model should not silently use a
    stale or incomplete period when a newer, materially more complete period is
    available for the same counterparty.
    """
    rows = get_financial_metrics_history(db, counterparty_id)
    if not rows:
        return None
    explicit = [row for row in rows if _is_latest(row)]
    selected = sorted(explicit, key=_period_sort_key, reverse=True)[0] if explicit else rows[0]
    selected_key = _period_sort_key(selected)
    selected_score = _model_ready_score(selected)
    best = max(rows, key=lambda row: (_model_ready_score(row), *_period_sort_key(row)))
    best_score = _model_ready_score(best)
    best_key = _period_sort_key(best)
    if best.id != selected.id and best_score >= selected_score + 3 and best_key >= selected_key:
        return best
    return selected


def mark_financial_metrics_as_latest(
    db: Session,
    financial_metrics_id: int,
) -> FinancialMetricsExtracted:
    """Mark one metrics row as the selected latest snapshot for its counterparty."""
    selected = (
        db.query(FinancialMetricsExtracted)
        .filter(FinancialMetricsExtracted.id == financial_metrics_id)
        .first()
    )
    if selected is None:
        raise ValueError(f"Financial metrics record {financial_metrics_id} not found")
    rows = (
        db.query(FinancialMetricsExtracted)
        .filter(FinancialMetricsExtracted.counterparty_id == selected.counterparty_id)
        .all()
    )
    for row in rows:
        _with_latest_flag(row, row.id == selected.id)
    db.commit()
    db.refresh(selected)
    return selected


def create_manual_financial_metrics(
    db: Session,
    payload: ManualFinancialMetricsCreate,
) -> FinancialMetricsExtracted:
    """Store analyst-entered financial metrics with a manual source document."""
    counterparty = (
        db.query(CounterpartyMaster)
        .filter(CounterpartyMaster.id == payload.counterparty_id)
        .first()
    )
    if counterparty is None:
        raise ValueError(f"Counterparty {payload.counterparty_id} not found")

    timestamp = datetime.utcnow()
    timestamp_key = timestamp.strftime("%Y%m%d%H%M%S%f")
    fiscal_label = payload.fiscal_year or "unknown_year"
    document = UploadedDocument(
        counterparty_id=payload.counterparty_id,
        filename=f"manual_financials_{fiscal_label}_{timestamp_key}.json",
        file_path=f"manual://financial-metrics/{payload.counterparty_id}/{timestamp_key}",
        document_type="manual_financial_statement",
        file_size_bytes=0,
        extraction_status="completed",
        processed_at=timestamp,
        created_by=payload.created_by,
    )
    db.add(document)
    db.flush()

    warnings = ["manual_entry_no_pdf_source"]
    ebit = payload.ebit
    if (
        ebit is None
        and payload.revenue is not None
        and payload.operating_margin_percent is not None
    ):
        ebit = payload.revenue * (payload.operating_margin_percent / 100)
        warnings.append("ebit_derived_from_operating_margin")

    missing_fields = _manual_missing_fields(payload)
    if ebit is not None and "ebit" in missing_fields:
        missing_fields.remove("ebit")
    period_label = _period_label(payload)
    model_missing_fields = [
        field_name
        for field_name in CRITICAL_MANUAL_FIELDS
        if field_name != "ebit" and getattr(payload, field_name) is None
    ]
    if ebit is None:
        model_missing_fields.append("ebit")
    metrics = FinancialMetricsExtracted(
        uploaded_document_id=document.id,
        source_document_id=document.id,
        counterparty_id=payload.counterparty_id,
        fiscal_year=payload.fiscal_year,
        fiscal_period=period_label,
        currency=payload.currency,
        extraction_confidence=Decimal("1.00") if not model_missing_fields else Decimal("0.80"),
        missing_critical_fields=model_missing_fields,
        original_text_references={
            "source": "manual analyst entry",
            "period_type": payload.period_type,
            "period_label": period_label,
            "is_latest_snapshot": bool(payload.is_latest_snapshot),
            "model_ready_missing_fields": model_missing_fields,
        },
        extraction_warnings=warnings,
        revenue=_decimal_or_none(payload.revenue),
        ebitda=_decimal_or_none(payload.ebitda),
        ebit=_decimal_or_none(ebit),
        interest_expense=_decimal_or_none(payload.interest_expense),
        net_income=_decimal_or_none(payload.net_income),
        cash_and_equivalents=_decimal_or_none(payload.cash_and_equivalents),
        accounts_receivable=_decimal_or_none(payload.accounts_receivable),
        inventory=_decimal_or_none(payload.inventory),
        current_assets=_decimal_or_none(payload.current_assets),
        total_assets=_decimal_or_none(payload.total_assets),
        current_liabilities=_decimal_or_none(payload.current_liabilities),
        total_debt=_decimal_or_none(payload.total_debt),
        total_liabilities=_decimal_or_none(payload.total_liabilities),
        shareholders_equity=_decimal_or_none(payload.shareholders_equity),
    )
    db.add(metrics)
    db.commit()
    db.refresh(metrics)
    if payload.is_latest_snapshot:
        metrics = mark_financial_metrics_as_latest(db, metrics.id)
    return metrics


def create_manual_financial_metrics_batch(
    db: Session,
    payload: ManualFinancialMetricsBatchCreate,
) -> tuple[list[FinancialMetricsExtracted], FinancialMetricsExtracted]:
    """Store multiple analyst-entered periods and return the selected latest snapshot."""
    if not payload.periods:
        raise ValueError("At least one financial period is required")

    created: list[FinancialMetricsExtracted] = []
    latest_requested = [period for period in payload.periods if period.is_latest_snapshot]
    selected_latest = latest_requested[-1] if latest_requested else max(
        payload.periods,
        key=lambda item: (
            int(item.fiscal_year or 0),
            {"FY": 5, "Q4": 4, "Q3": 3, "Q2": 2, "Q1": 1}.get(_period_label(item), 0),
        ),
    )

    for period in payload.periods:
        item = period.model_copy(
            update={
                "counterparty_id": payload.counterparty_id,
                "is_latest_snapshot": period is selected_latest,
            }
        )
        created.append(create_manual_financial_metrics(db, item))

    latest = max(
        (item for item in created if item.is_latest_snapshot),
        key=_period_sort_key,
        default=max(created, key=_period_sort_key),
    )
    return created, latest


def calculate_ratios_for_metrics(
    db: Session,
    financial_metrics_id: int,
) -> FinancialRatioResult:
    """Load Phase 2 extracted financials and calculate formula-versioned ratios."""
    financials = (
        db.query(FinancialMetricsExtracted)
        .filter(FinancialMetricsExtracted.id == financial_metrics_id)
        .first()
    )
    if financials is None:
        raise ValueError(f"Financial metrics record {financial_metrics_id} not found")
    return calculate_financial_ratios(financials)


def save_financial_ratios(
    db: Session,
    ratios: FinancialRatioResult,
) -> FinancialRatios:
    """Upsert financial ratios for one extracted financial statement record."""
    existing = (
        db.query(FinancialRatios)
        .filter(FinancialRatios.financial_metrics_id == ratios.financial_metrics_id)
        .first()
    )
    record = existing or FinancialRatios()

    for field_name, value in ratios.__dict__.items():
        if hasattr(record, field_name):
            setattr(record, field_name, value)

    if existing is None:
        db.add(record)
    db.commit()
    db.refresh(record)
    return record


def calculate_and_store_ratios(
    db: Session,
    financial_metrics_id: int,
) -> FinancialRatios:
    """Calculate ratios from Phase 2 financials and store them for downstream models."""
    ratios = calculate_ratios_for_metrics(db, financial_metrics_id)
    return save_financial_ratios(db, ratios)


def get_latest_ratios_for_counterparty(
    db: Session,
    counterparty_id: int,
) -> FinancialRatios | None:
    """Return ratios for the selected latest snapshot, with newest-period fallback."""
    latest_metrics = get_latest_financial_metrics_for_counterparty(db, counterparty_id)
    if latest_metrics is not None:
        selected_ratio = (
            db.query(FinancialRatios)
            .filter(FinancialRatios.financial_metrics_id == latest_metrics.id)
            .first()
        )
        if selected_ratio is not None:
            return selected_ratio
    return (
        db.query(FinancialRatios)
        .filter(FinancialRatios.counterparty_id == counterparty_id)
        .order_by(FinancialRatios.fiscal_year.desc(), FinancialRatios.calculation_date.desc())
        .first()
    )


def get_financial_trend_features(
    db: Session,
    counterparty_id: int,
) -> dict:
    """Calculate trend features from all stored periods for a counterparty."""
    metrics_rows = get_financial_metrics_history(db, counterparty_id)
    ratio_rows = (
        db.query(FinancialRatios)
        .filter(FinancialRatios.counterparty_id == counterparty_id)
        .all()
    )
    features = calculate_financial_trend_features(counterparty_id, metrics_rows, ratio_rows)
    features["model_overlay"] = calculate_trend_risk_overlay(features)
    return features
