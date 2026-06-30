"""
Financial Ratio Engine

Business purpose:
Convert extracted financial statement values into liquidity, leverage, coverage,
and profitability ratios used by PD models, credit policy, and analyst memos.

Inputs:
Structured Phase 2 financial metrics such as revenue, EBITDA, EBIT, cash,
receivables, inventory, current assets/liabilities, debt, equity, and assets.

Outputs:
FinancialRatioResult with formula-versioned ratios, missing input warnings,
currency/unit preservation, and an input data reference for auditability.

Method:
Ratios are deterministic financial formulas. Divide-by-zero and missing critical
inputs return None rather than fabricated values.

Assumptions:
Values are already normalized to one reporting currency by Phase 2 extraction.
If total_debt is unavailable, short-term/current/long-term debt components may
be summed as a documented proxy.

Limitations:
The engine calculates historical ratios only. It does not forecast, score, or
recommend credit limits by itself.
"""

from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from decimal import Decimal
from typing import Any, Dict, Optional


FORMULA_VERSION = "financial_ratios_v1.0"


@dataclass
class FinancialRatioResult:
    """Formula-versioned financial ratios for one fiscal period."""

    counterparty_id: Optional[int] = None
    uploaded_document_id: Optional[int] = None
    financial_metrics_id: Optional[int] = None
    fiscal_year: Optional[int] = None
    fiscal_period: Optional[str] = None
    currency: Optional[str] = None

    current_ratio: Optional[float] = None
    quick_ratio: Optional[float] = None
    cash_ratio: Optional[float] = None
    working_capital: Optional[float] = None
    debt_to_equity: Optional[float] = None
    debt_to_ebitda: Optional[float] = None
    liabilities_to_assets: Optional[float] = None
    interest_coverage: Optional[float] = None
    operating_margin: Optional[float] = None
    net_margin: Optional[float] = None
    return_on_assets: Optional[float] = None
    return_on_equity: Optional[float] = None

    formula_version: str = FORMULA_VERSION
    calculation_date: datetime = field(default_factory=lambda: datetime.now(timezone.utc))
    input_data_reference: Optional[str] = None
    missing_inputs: Dict[str, list[str]] = field(default_factory=dict)
    calculation_warnings: list[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Return a serializable dict for API and persistence layers."""
        result = asdict(self)
        result["calculation_date"] = self.calculation_date.isoformat()
        return result


def _to_float(value: Any) -> Optional[float]:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _get(source: Any, field_name: str) -> Optional[float]:
    if isinstance(source, dict):
        return _to_float(source.get(field_name))
    return _to_float(getattr(source, field_name, None))


def _safe_divide(
    numerator: Optional[float],
    denominator: Optional[float],
    ratio_name: str,
    missing_inputs: Dict[str, list[str]],
    numerator_name: str,
    denominator_name: str,
) -> Optional[float]:
    missing = []
    if numerator is None:
        missing.append(numerator_name)
    if denominator is None:
        missing.append(denominator_name)
    if denominator == 0:
        missing.append(f"{denominator_name}_zero")
    if missing:
        missing_inputs[ratio_name] = missing
        return None
    return numerator / denominator


def _derive_total_debt(financials: Any, warnings: list[str]) -> Optional[float]:
    total_debt = _get(financials, "total_debt")
    if total_debt is not None:
        return total_debt

    debt_parts = [
        _get(financials, "short_term_debt"),
        _get(financials, "current_portion_long_term_debt"),
        _get(financials, "long_term_debt"),
    ]
    if any(value is not None for value in debt_parts):
        warnings.append(
            "total_debt was derived from short-term, current portion, and long-term debt."
        )
        return sum(value or 0.0 for value in debt_parts)
    return None


def calculate_financial_ratios(financials: Any) -> FinancialRatioResult:
    """Calculate all required credit-analysis ratios from extracted financials."""
    warnings: list[str] = []
    missing_inputs: Dict[str, list[str]] = {}
    total_debt = _derive_total_debt(financials, warnings)

    counterparty_id = getattr(financials, "counterparty_id", None)
    uploaded_document_id = getattr(financials, "uploaded_document_id", None)
    financial_metrics_id = getattr(financials, "id", None)
    fiscal_year = getattr(financials, "fiscal_year", None)
    fiscal_period = getattr(financials, "fiscal_period", None)
    currency = getattr(financials, "currency", None)

    if isinstance(financials, dict):
        counterparty_id = financials.get("counterparty_id")
        uploaded_document_id = financials.get("uploaded_document_id")
        financial_metrics_id = financials.get("id")
        fiscal_year = financials.get("fiscal_year")
        fiscal_period = financials.get("fiscal_period")
        currency = financials.get("currency")

    current_assets = _get(financials, "current_assets")
    current_liabilities = _get(financials, "current_liabilities")
    cash = _get(financials, "cash_and_equivalents")
    accounts_receivable = _get(financials, "accounts_receivable")
    inventory = _get(financials, "inventory")
    equity = _get(financials, "shareholders_equity")
    ebitda = _get(financials, "ebitda")
    ebit = _get(financials, "ebit")
    interest_expense = _get(financials, "interest_expense")
    revenue = _get(financials, "revenue")
    net_income = _get(financials, "net_income")
    total_assets = _get(financials, "total_assets")
    total_liabilities = _get(financials, "total_liabilities")

    quick_assets = None
    if cash is not None and accounts_receivable is not None:
        quick_assets = cash + accounts_receivable
    elif current_assets is not None and inventory is not None:
        quick_assets = current_assets - inventory
        warnings.append(
            "quick_assets were derived from current_assets minus inventory because cash/receivables were incomplete."
        )

    working_capital = None
    if current_assets is None or current_liabilities is None:
        missing_inputs["working_capital"] = [
            name
            for name, value in {
                "current_assets": current_assets,
                "current_liabilities": current_liabilities,
            }.items()
            if value is None
        ]
    else:
        working_capital = current_assets - current_liabilities

    result = FinancialRatioResult(
        counterparty_id=counterparty_id,
        uploaded_document_id=uploaded_document_id,
        financial_metrics_id=financial_metrics_id,
        fiscal_year=fiscal_year,
        fiscal_period=fiscal_period,
        currency=currency,
        current_ratio=_safe_divide(
            current_assets,
            current_liabilities,
            "current_ratio",
            missing_inputs,
            "current_assets",
            "current_liabilities",
        ),
        quick_ratio=_safe_divide(
            quick_assets,
            current_liabilities,
            "quick_ratio",
            missing_inputs,
            "cash_and_equivalents_plus_accounts_receivable",
            "current_liabilities",
        ),
        cash_ratio=_safe_divide(
            cash,
            current_liabilities,
            "cash_ratio",
            missing_inputs,
            "cash_and_equivalents",
            "current_liabilities",
        ),
        working_capital=working_capital,
        debt_to_equity=_safe_divide(
            total_debt,
            equity,
            "debt_to_equity",
            missing_inputs,
            "total_debt",
            "shareholders_equity",
        ),
        debt_to_ebitda=_safe_divide(
            total_debt,
            ebitda,
            "debt_to_ebitda",
            missing_inputs,
            "total_debt",
            "ebitda",
        ),
        liabilities_to_assets=_safe_divide(
            total_liabilities,
            total_assets,
            "liabilities_to_assets",
            missing_inputs,
            "total_liabilities",
            "total_assets",
        ),
        interest_coverage=_safe_divide(
            ebit,
            interest_expense,
            "interest_coverage",
            missing_inputs,
            "ebit",
            "interest_expense",
        ),
        operating_margin=_safe_divide(
            ebit,
            revenue,
            "operating_margin",
            missing_inputs,
            "ebit",
            "revenue",
        ),
        net_margin=_safe_divide(
            net_income,
            revenue,
            "net_margin",
            missing_inputs,
            "net_income",
            "revenue",
        ),
        return_on_assets=_safe_divide(
            net_income,
            total_assets,
            "return_on_assets",
            missing_inputs,
            "net_income",
            "total_assets",
        ),
        return_on_equity=_safe_divide(
            net_income,
            equity,
            "return_on_equity",
            missing_inputs,
            "net_income",
            "shareholders_equity",
        ),
        input_data_reference=(
            f"financial_metrics_extracted:{financial_metrics_id}"
            if financial_metrics_id is not None
            else None
        ),
        missing_inputs=missing_inputs,
        calculation_warnings=warnings,
    )

    return result
