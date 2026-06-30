"""Grounded SQL context and fallback answers for the credit copilot."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from typing import Any, Iterable, Optional

from sqlalchemy import text
from sqlalchemy.orm import Session

from api.credit_decision.service import load_credit_decision_input
from api.credit_decision.engine import recommend_credit_terms
from api.financials.service import get_financial_trend_features
from api.financials.trends import calculate_trend_risk_overlay
from api.market_data.assets import CORE_MARKET_ASSETS, sql_asset_list


def _json_safe(value: Any) -> Any:
    if isinstance(value, Decimal):
        return float(value)
    if isinstance(value, (datetime, date)):
        return value.isoformat()
    if isinstance(value, dict):
        return {key: _json_safe(item) for key, item in value.items()}
    if isinstance(value, list):
        return [_json_safe(item) for item in value]
    return value


def _safe_float(value: Any) -> Optional[float]:
    try:
        if value is None:
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _fmt_money(value: Any) -> str:
    number = _safe_float(value)
    if number is None:
        return "missing"
    return f"${number:,.0f}"


def _fmt_pct(value: Any) -> str:
    number = _safe_float(value)
    if number is None:
        return "missing"
    return f"{number * 100:.2f}%"


def _fmt_ratio(value: Any) -> str:
    number = _safe_float(value)
    if number is None:
        return "missing"
    return f"{number:.2f}x"


def _row_to_dict(row: Any) -> dict[str, Any]:
    if row is None:
        return {}
    return {key: _json_safe(value) for key, value in dict(row).items()}


def _query_one(db: Session, sql: str, params: dict[str, Any]) -> dict[str, Any]:
    try:
        row = db.execute(text(sql), params).mappings().first()
        return _row_to_dict(row)
    except Exception as exc:
        db.rollback()
        return {"_error": str(exc)}


def _query_all(db: Session, sql: str, params: dict[str, Any]) -> list[dict[str, Any]]:
    try:
        rows = db.execute(text(sql), params).mappings().all()
        return [_row_to_dict(row) for row in rows]
    except Exception as exc:
        db.rollback()
        return [{"_error": str(exc)}]


def _compact_json(value: Any) -> str:
    return json.dumps(_json_safe(value), ensure_ascii=True, default=str)


def _compute_unsaved_recommendation(db: Session, counterparty_id: int) -> dict[str, Any]:
    try:
        inputs = load_credit_decision_input(db, counterparty_id)
        result = recommend_credit_terms(inputs).to_dict()
        result["_computed_not_persisted"] = True
        return _json_safe(result)
    except Exception as exc:
        return {"_error": str(exc), "_computed_not_persisted": True}


@dataclass
class GroundedCopilotContext:
    counterparty: dict[str, Any] = field(default_factory=dict)
    financials: dict[str, Any] = field(default_factory=dict)
    ratios: dict[str, Any] = field(default_factory=dict)
    financial_trends: dict[str, Any] = field(default_factory=dict)
    pd: dict[str, Any] = field(default_factory=dict)
    loss: dict[str, Any] = field(default_factory=dict)
    trade_exposure: dict[str, Any] = field(default_factory=dict)
    recommendation: dict[str, Any] = field(default_factory=dict)
    scenario: dict[str, Any] = field(default_factory=dict)
    simulation: dict[str, Any] = field(default_factory=dict)
    stress: dict[str, Any] = field(default_factory=dict)
    regime: dict[str, Any] = field(default_factory=dict)
    market_prices: list[dict[str, Any]] = field(default_factory=list)
    documents: list[dict[str, Any]] = field(default_factory=list)
    visible_metrics: dict[str, Any] = field(default_factory=dict)
    page: Optional[str] = None
    source_notes: list[str] = field(default_factory=list)

    def has_counterparty(self) -> bool:
        return bool(self.counterparty.get("id"))

    def to_prompt_context(self) -> str:
        sections = [
            ("Selected Counterparty", self.counterparty),
            ("Latest Financials", self.financials),
            ("Latest Financial Ratios", self.ratios),
            ("Financial History Trend Features", self.financial_trends),
            ("Latest PD Model Output", self.pd),
            ("Latest LGD/EAD/Loss Output", self.loss),
            ("Latest Trade Exposure / Requested Terms", self.trade_exposure),
            ("Latest Credit Recommendation", self.recommendation),
            ("Latest Scenario Result", self.scenario),
            ("Latest Monte Carlo Simulation", self.simulation),
            ("Latest Market Stress", self.stress),
            ("Latest Market Regime", self.regime),
            ("Latest Market Prices", self.market_prices),
            ("Recent Documents", self.documents),
            ("Visible Frontend Metrics", self.visible_metrics),
        ]
        lines = [
            "==============================",
            "GROUNDED SQL / UI CONTEXT",
            "==============================",
            "Rules: use only this context and retrieved context. If a value is missing, say it is missing.",
            f"Current page: {self.page or 'not supplied'}",
        ]
        for title, payload in sections:
            if payload:
                lines.append(f"\n{title}:\n{_compact_json(payload)}")
            else:
                lines.append(f"\n{title}: missing")
        if self.source_notes:
            lines.append("\nSource Notes:")
            lines.extend(f"- {note}" for note in self.source_notes)
        lines.append("==============================")
        return "\n".join(lines)


def _lookup_counterparty(
    db: Session,
    counterparty_id: Optional[int],
    counterparty_name: Optional[str],
) -> dict[str, Any]:
    if counterparty_id:
        return _query_one(
            db,
            """
            SELECT id, counterparty_name, counterparty_type, country, created_at
            FROM counterparties_master
            WHERE id = :counterparty_id
            """,
            {"counterparty_id": counterparty_id},
        )
    if counterparty_name:
        return _query_one(
            db,
            """
            SELECT id, counterparty_name, counterparty_type, country, created_at
            FROM counterparties_master
            WHERE LOWER(counterparty_name) = LOWER(:counterparty_name)
            ORDER BY created_at DESC, id DESC
            LIMIT 1
            """,
            {"counterparty_name": counterparty_name},
        )
    return {}


def build_grounded_copilot_context(
    db: Session,
    *,
    counterparty_id: Optional[int] = None,
    counterparty_name: Optional[str] = None,
    page: Optional[str] = None,
    visible_metrics: Optional[dict[str, Any]] = None,
) -> GroundedCopilotContext:
    """Load latest stored V2 outputs for the selected counterparty."""
    context = GroundedCopilotContext(page=page, visible_metrics=visible_metrics or {})
    context.counterparty = _lookup_counterparty(db, counterparty_id, counterparty_name)

    resolved_id = context.counterparty.get("id")
    if not resolved_id:
        context.source_notes.append("No selected counterparty was resolved from request context.")
        return context

    params = {"counterparty_id": resolved_id}
    context.documents = _query_all(
        db,
        """
        SELECT id, filename, document_type, extraction_status, uploaded_at, processed_at, extraction_error
        FROM uploaded_documents
        WHERE counterparty_id = :counterparty_id
        ORDER BY uploaded_at DESC, id DESC
        LIMIT 5
        """,
        params,
    )
    context.financials = _query_one(
        db,
        """
        SELECT id, uploaded_document_id, fiscal_year, currency, revenue, ebitda, ebit,
               net_income, cash_and_equivalents, current_assets, total_assets,
               current_liabilities, total_debt, total_liabilities, shareholders_equity,
               interest_expense, operating_cash_flow, free_cash_flow,
               extraction_confidence, missing_critical_fields, extraction_warnings, created_at
        FROM financial_metrics_extracted
        WHERE counterparty_id = :counterparty_id
        ORDER BY fiscal_year DESC NULLS LAST, created_at DESC, id DESC
        LIMIT 1
        """,
        params,
    )
    context.ratios = _query_one(
        db,
        """
        SELECT id, financial_metrics_id, fiscal_year, current_ratio, quick_ratio, cash_ratio,
               working_capital, debt_to_equity, debt_to_ebitda, liabilities_to_assets,
               interest_coverage, operating_margin, net_margin, return_on_assets,
               return_on_equity, missing_inputs, calculation_warnings, created_at
        FROM financial_ratios
        WHERE counterparty_id = :counterparty_id
        ORDER BY fiscal_year DESC NULLS LAST, calculation_date DESC, id DESC
        LIMIT 1
        """,
        params,
    )
    try:
        trend_features = get_financial_trend_features(db, int(resolved_id))
        context.financial_trends = _json_safe(
            {
                **trend_features,
                "model_overlay": calculate_trend_risk_overlay(trend_features),
            }
        )
    except Exception as exc:
        db.rollback()
        context.financial_trends = {"_error": str(exc)}
    context.pd = _query_one(
        db,
        """
        SELECT id, run_id, financial_ratios_id, structural_pd, ml_pd, final_pd,
               distance_to_default, model_disagreement, market_stress_index,
               market_regime, classification_label, feature_contributions,
               warnings, created_at
        FROM pd_model_predictions
        WHERE counterparty_id = :counterparty_id
        ORDER BY created_at DESC, id DESC
        LIMIT 1
        """,
        params,
    )
    context.loss = _query_one(
        db,
        """
        SELECT id, run_id, pd_prediction_id, trade_exposure_id, probability_of_default,
               predicted_lgd, exposure_at_default, expected_loss, collateral_strength,
               liquidity_score, ead_cap_applied, expected_drawdown, invoice_exposure,
               model_assumptions, warnings, created_at
        FROM loss_estimates
        WHERE counterparty_id = :counterparty_id
        ORDER BY created_at DESC, id DESC
        LIMIT 1
        """,
        params,
    )
    context.trade_exposure = _query_one(
        db,
        """
        SELECT id, requested_credit_limit, approved_credit_limit, outstanding_receivables,
               payment_tenor_days, utilization_rate, collateral_type, letter_of_credit_flag,
               guarantee_flag, deposit_percentage, invoice_amount, fuel_volume, fuel_price,
               created_at
        FROM trade_exposures
        WHERE counterparty_id = :counterparty_id
        ORDER BY created_at DESC, id DESC
        LIMIT 1
        """,
        params,
    )
    context.recommendation = _query_one(
        db,
        """
        SELECT id, run_id, probability_of_default, loss_given_default, exposure_at_default,
               expected_loss, scenario_expected_loss, credit_var_95, expected_shortfall_95,
               recommended_credit_limit, recommended_tenor_days, recommended_security,
               risk_grade, approval_status, policy_score, limit_haircut,
               key_risk_drivers, mitigating_factors, warnings, input_data_reference, created_at
        FROM credit_recommendations
        WHERE counterparty_id = :counterparty_id
        ORDER BY created_at DESC, id DESC
        LIMIT 1
        """,
        params,
    )
    if not context.recommendation or context.recommendation.get("_error"):
        computed_recommendation = _compute_unsaved_recommendation(db, int(resolved_id))
        if computed_recommendation and not computed_recommendation.get("_error"):
            context.recommendation = computed_recommendation
            context.source_notes.append(
                "No persisted credit_recommendations row was found; recommendation values were computed from stored PD/LGD/EAD/trade exposure using the credit decision engine and were not saved by the copilot."
            )
        elif computed_recommendation.get("_error"):
            context.source_notes.append(
                f"Credit recommendation fallback unavailable: {computed_recommendation['_error']}"
            )
    context.scenario = _query_one(
        db,
        """
        SELECT id, run_id, scenario_name, scenario_type, scenario_impacts, created_at
        FROM scenario_results
        WHERE CAST(scenario_impacts AS TEXT) LIKE :counterparty_marker
        ORDER BY created_at DESC, id DESC
        LIMIT 1
        """,
        {"counterparty_marker": f'%"{resolved_id}"%'},
    )
    context.simulation = _query_one(
        db,
        """
        SELECT id, run_id, scenario, expected_loss, unexpected_loss, var_95, var_99,
               expected_shortfall_95, expected_shortfall_99, worst_case_loss,
               distribution_summary, created_at
        FROM simulation_results
        ORDER BY created_at DESC, id DESC
        LIMIT 1
        """,
        {},
    )
    context.stress = _query_one(
        db,
        """
        SELECT id, date, stress_index, stress_level, pc1_score, explained_variance_ratio,
               pca_loadings, top_positive_drivers, top_negative_drivers, component_values,
               available_components, missing_components, model_version, data_source, created_at
        FROM stress_index_history
        ORDER BY date DESC, created_at DESC, id DESC
        LIMIT 1
        """,
        {},
    )
    context.regime = _query_one(
        db,
        """
        SELECT id, date, regime_id, regime_label, regime_probability, regime_characteristics,
               feature_values, model_version, data_source, created_at
        FROM market_regime_history
        ORDER BY date DESC, created_at DESC, id DESC
        LIMIT 1
        """,
        {},
    )
    context.market_prices = _query_all(
        db,
        f"""
        SELECT DISTINCT ON (asset)
               id, date, asset, asset_name, ticker, price, return, rolling_volatility,
               data_source, units, created_at
        FROM market_prices
        WHERE asset IN (
            {sql_asset_list(CORE_MARKET_ASSETS)}
        )
        ORDER BY asset, date DESC, id DESC
        """,
        {},
    )
    context.source_notes.extend(
        [
            "Counterparty, financials, ratios, PD, loss, and recommendation facts are loaded from V2 SQL tables.",
            "Financial trend features are calculated from stored multi-period financial_metrics_extracted and financial_ratios rows; they are an overlay, not a replacement for the latest snapshot.",
            "Market stress and regime are global context, not counterparty-specific model outputs.",
        ]
    )
    return context


def _extract_list(value: Any) -> list[str]:
    if value is None:
        return []
    if isinstance(value, list):
        clean_items = []
        for item in value:
            if isinstance(item, dict):
                description = item.get("description") or item.get("component") or item.get("label")
                loading = _safe_float(item.get("loading") or item.get("score") or item.get("value"))
                if description and loading is not None:
                    clean_items.append(f"{description} ({loading:+.2f})")
                elif description:
                    clean_items.append(str(description))
                else:
                    clean_items.append(_compact_json(item))
            else:
                clean_items.append(str(item))
        return clean_items
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return [str(item) for item in parsed]
        except Exception:
            pass
        return [value]
    return [str(value)]


def _number(value: Any, default: float = 0.0) -> float:
    parsed = _safe_float(value)
    return default if parsed is None else parsed


def _first_value(*values: Any) -> Any:
    for value in values:
        if value is not None and value != "":
            return value
    return None


def _drivers_from_dict(value: Any, limit: int = 4) -> list[str]:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except Exception:
            return []
    if not isinstance(value, dict):
        return []
    rows = []
    for key, item in value.items():
        numeric = _safe_float(item)
        if numeric is not None:
            rows.append((str(key).replace("_", " "), numeric))
    rows.sort(key=lambda row: abs(row[1]), reverse=True)
    return [f"{name} ({score:+.2f})" for name, score in rows[:limit]]


def _market_price_lookup(context: GroundedCopilotContext) -> dict[str, dict[str, Any]]:
    lookup: dict[str, dict[str, Any]] = {}
    for row in context.market_prices or []:
        if row and not row.get("_error"):
            lookup[str(row.get("asset"))] = row
    return lookup


def _fmt_market_price(row: Optional[dict[str, Any]]) -> str:
    if not row:
        return "not available"
    label = row.get("asset_name") or row.get("asset") or "market indicator"
    price = row.get("price")
    units = row.get("units") or ""
    date_value = row.get("date") or "latest"
    move = _safe_float(row.get("return"))
    move_text = f", latest return {_fmt_pct(move)}" if move is not None else ""
    return f"{label}: {_fmt_ratio(price).replace('x', '')} {units} on {date_value}{move_text}".strip()


def _human_label(value: Any) -> str:
    return str(value or "missing").replace("_", " ").strip()


def _assessment_from_ratio(label: str, value: Any) -> str:
    numeric = _safe_float(value)
    if numeric is None:
        return f"{label} is missing, so I would treat that part of the assessment cautiously"
    if "current" in label.lower() or "quick" in label.lower():
        if numeric >= 1.5:
            return f"{label} is strong at {_fmt_ratio(numeric)}"
        if numeric >= 1.0:
            return f"{label} is adequate at {_fmt_ratio(numeric)}"
        return f"{label} is weak at {_fmt_ratio(numeric)}"
    if "debt/ebitda" in label.lower():
        if numeric <= 2.5:
            return f"Debt/EBITDA is comfortable at {_fmt_ratio(numeric)}"
        if numeric <= 4.5:
            return f"Debt/EBITDA is moderate at {_fmt_ratio(numeric)}"
        return f"Debt/EBITDA is high at {_fmt_ratio(numeric)}"
    if "interest" in label.lower():
        if numeric >= 4:
            return f"interest coverage is strong at {_fmt_ratio(numeric)}"
        if numeric >= 2:
            return f"interest coverage is acceptable at {_fmt_ratio(numeric)}"
        return f"interest coverage is weak at {_fmt_ratio(numeric)}"
    return f"{label} is {_fmt_ratio(numeric)}"


def build_grounded_fallback_answer(question: str, context: GroundedCopilotContext) -> str:
    """Return a human-readable grounded analyst answer without inventing facts."""
    cp = context.counterparty
    name = cp.get("counterparty_name") or "the selected counterparty"
    if not context.has_counterparty():
        return (
            "I do not have a selected counterparty in the copilot request. "
            "Select a counterparty first, then ask again so I can ground the answer in stored SQL/model outputs."
        )

    q = question.lower()
    rec = context.recommendation
    loss = context.loss
    trade = context.trade_exposure
    pd = context.pd
    ratios = context.ratios
    trends = context.financial_trends
    fin = context.financials
    stress = context.stress
    regime = context.regime
    prices = _market_price_lookup(context)

    final_pd = _first_value(pd.get("final_pd"), loss.get("probability_of_default"), rec.get("probability_of_default"))
    lgd = _first_value(loss.get("predicted_lgd"), rec.get("loss_given_default"))
    ead = _first_value(loss.get("exposure_at_default"), rec.get("exposure_at_default"))
    expected_loss = _first_value(loss.get("expected_loss"), rec.get("expected_loss"))
    var95 = _first_value(rec.get("credit_var_95"), context.simulation.get("var_95"))
    es95 = _first_value(rec.get("expected_shortfall_95"), context.simulation.get("expected_shortfall_95"))
    decision = rec.get("approval_status") or "not stored"
    risk_grade = rec.get("risk_grade") or pd.get("classification_label") or "not stored"
    recommended_limit = rec.get("recommended_credit_limit")
    tenor = rec.get("recommended_tenor_days")
    security = rec.get("recommended_security")
    requested_limit = trade.get("requested_credit_limit")
    requested_tenor = trade.get("payment_tenor_days")
    requested_security = trade.get("collateral_type")
    stress_index = _first_value(stress.get("stress_index"), pd.get("market_stress_index"))
    regime_label = _first_value(regime.get("regime_label"), pd.get("market_regime"), "not available")
    drivers = _extract_list(rec.get("key_risk_drivers"))
    mitigants = _extract_list(rec.get("mitigating_factors"))
    pd_drivers = _drivers_from_dict(pd.get("feature_contributions"))

    paragraphs: list[str] = []
    bullets: list[str] = []

    intro = (
        f"For {name}, I would read the current credit picture as {decision.lower()} with "
        f"internal risk grade {risk_grade}. The stored model shows PD of {_fmt_pct(final_pd)}, "
        f"LGD of {_fmt_pct(lgd)}, EAD of {_fmt_money(ead)}, and expected loss of {_fmt_money(expected_loss)}."
    )
    if recommended_limit is not None or tenor is not None or security:
        intro += (
            f" In practical credit terms, that translates to a recommended limit of "
            f"{_fmt_money(recommended_limit)}, tenor of {tenor if tenor is not None else 'missing'} days, "
            f"and security of {security or 'missing'}."
        )
    paragraphs.append(intro)

    wants_market = any(term in q for term in ["market", "stress", "oil", "fuel", "usd", "dxy", "macro", "commodity", "interconnected", "affect", "pmi", "iata", "opec", "inventory", "inventories", "crack spread", "brent", "wti"])
    wants_math = any(term in q for term in ["math", "mathematical", "pd", "lgd", "ead", "expected loss", "var", "shortfall", "monte", "default"])
    wants_terms = any(term in q for term in ["limit", "reduced", "recommend", "approve", "decision", "tenor", "lc", "security", "terms"])
    wants_financial = any(term in q for term in ["financial", "liquidity", "leverage", "coverage", "ratio", "cash", "debt"])
    wants_scenario = any(term in q for term in ["scenario", "adverse", "forecast", "future", "severe"])
    if not any([wants_market, wants_math, wants_terms, wants_financial, wants_scenario]):
        wants_market = wants_math = wants_terms = wants_financial = True

    if wants_financial:
        financial_sentence = (
            "Financially, the main repayment question is whether short-term liquidity and operating cash flow are strong enough "
            "to support fuel receivables through the requested tenor. "
            f"{_assessment_from_ratio('Current ratio', ratios.get('current_ratio'))}, "
            f"{_assessment_from_ratio('Debt/EBITDA', ratios.get('debt_to_ebitda'))}, and "
            f"{_assessment_from_ratio('interest coverage', ratios.get('interest_coverage'))}. "
            f"The annual-report extraction confidence is {_fmt_pct(fin.get('extraction_confidence'))} for fiscal year {fin.get('fiscal_year', 'missing')}."
        )
        paragraphs.append(financial_sentence)
        if trends and not trends.get("_error"):
            overlay = trends.get("model_overlay") or {}
            paragraphs.append(
                "The history layer checks whether the latest snapshot is part of an improving or deteriorating pattern. "
                f"It has {trends.get('period_count', 0)} stored period(s), trend status {trends.get('history_status', 'missing')}, "
                f"and direction {overlay.get('direction', 'neutral')}. "
                f"Revenue CAGR is {_fmt_pct(trends.get('revenue_cagr'))}, latest revenue growth is {_fmt_pct(trends.get('latest_revenue_growth'))}, "
                f"current-ratio trend is {_fmt_ratio(trends.get('current_ratio_trend'))}, and the PD trend multiplier is {_fmt_ratio(overlay.get('pd_multiplier'))}."
            )

    if wants_market:
        market_sentence = (
            f"Externally, the relevant backdrop is {regime_label} with a stress index of {_fmt_ratio(stress_index).replace('x', ' / 100')}. "
            "For a fuel-credit counterparty, commodity prices, crack spread, inventories, OPEC supply, USD strength, volatility, PMI, and passenger or trade activity are interconnected: "
            "fuel prices and crack spread pressure margins and working capital, inventories and OPEC production shape supply tightness, USD strength can raise non-USD cost burdens, "
            "volatility lowers credit appetite, and weaker PMI/IATA/freight signals reduce demand visibility. "
            f"Latest stored indicators include {_fmt_market_price(prices.get('brent_oil'))}, "
            f"{_fmt_market_price(prices.get('jet_fuel_proxy'))}, {_fmt_market_price(prices.get('jet_crack_spread'))}, "
            f"{_fmt_market_price(prices.get('eia_crude_inventories'))}, {_fmt_market_price(prices.get('opec_production'))}, "
            f"{_fmt_market_price(prices.get('global_pmi') or prices.get('pmi'))}, {_fmt_market_price(prices.get('iata_passenger_traffic'))}, "
            f"{_fmt_market_price(prices.get('dxy'))}, and {_fmt_market_price(prices.get('vix'))}."
        )
        paragraphs.append(market_sentence)
        top_positive = _extract_list(stress.get("top_positive_drivers"))
        if top_positive:
            bullets.append("Market stress drivers: " + "; ".join(top_positive[:4]) + ".")

    if wants_math:
        math_sentence = (
            "Mathematically, the credit engine separates default likelihood, recovery severity, and exposure size. "
            f"PD estimates the chance of default ({_fmt_pct(final_pd)}), LGD estimates the loss if default happens ({_fmt_pct(lgd)}), "
            f"and EAD estimates the amount exposed at default ({_fmt_money(ead)}). Expected loss is therefore PD x LGD x EAD, "
            f"which is {_fmt_money(expected_loss)} for the stored run. "
            f"The structural model distance to default is {_fmt_ratio(pd.get('distance_to_default'))}; a lower distance means the firm is closer to its debt barrier. "
            f"Monte Carlo tail risk is represented by VaR 95 of {_fmt_money(var95)} and expected shortfall 95 of {_fmt_money(es95)}, "
            "which describe downside outcomes beyond the average expected loss."
        )
        paragraphs.append(math_sentence)
        if trends and not trends.get("_error"):
            overlay = trends.get("model_overlay") or {}
            paragraphs.append(
                "Financial history feeds the models as a capped overlay, not as a replacement for the core formulas. "
                "Deteriorating revenue, margins, leverage, coverage, liquidity, cash, or fuel-cost trends can raise the ML PD cross-check, "
                "nudge the Merton asset-volatility proxy, and increase LGD through weaker liquidity. "
                f"For this counterparty the overlay direction is {overlay.get('direction', 'neutral')} with risk score {_fmt_ratio(overlay.get('risk_score'))}."
            )
        if pd_drivers:
            bullets.append("Important PD model drivers: " + "; ".join(pd_drivers) + ".")

    if wants_terms:
        terms_sentence = (
            "For credit terms, the engine does not look at the requested line in isolation. It asks whether the requested limit and tenor are appropriate "
            "given PD, LGD, exposure, liquidity, leverage, collateral, and external market stress. "
        )
        if requested_limit is not None:
            terms_sentence += f"The requested line was {_fmt_money(requested_limit)}"
            if requested_tenor is not None:
                terms_sentence += f" for {requested_tenor} days"
            if requested_security:
                terms_sentence += f" with {_human_label(requested_security)} security"
            terms_sentence += ". "
        if recommended_limit is not None:
            terms_sentence += f"The recommended limit of {_fmt_money(recommended_limit)} is the model's risk-adjusted comfort level. "
            if requested_limit is not None:
                reduction = _number(requested_limit) - _number(recommended_limit)
                if reduction > 0:
                    terms_sentence += f"That is a reduction of {_fmt_money(reduction)} versus the requested line, reflecting model and policy risk controls. "
        if tenor is not None:
            terms_sentence += f"The {tenor}-day tenor limits receivable build-up and keeps exposure closer to observable repayment capacity. "
        if security:
            terms_sentence += f"The security requirement ({security}) is there to reduce loss severity if payment performance deteriorates. "
        if drivers:
            terms_sentence += "The main reasons are " + "; ".join(drivers[:3]) + "."
        paragraphs.append(terms_sentence)
        if mitigants:
            bullets.append("Mitigating factors: " + "; ".join(mitigants[:4]) + ".")

    if wants_scenario:
        scenario_sentence = (
            "Under adverse or severe scenarios, the same counterparty can become riskier even if its latest financial statements have not changed, "
            "because higher fuel costs, USD strength, volatility, or weaker trade activity can compress margins and increase drawdown on the credit line. "
        )
        if context.scenario:
            scenario_sentence += (
                f"The latest stored scenario is {context.scenario.get('scenario_name', 'missing')} "
                f"({context.scenario.get('scenario_type', 'missing')}). "
            )
        scenario_sentence += "That is why scenario and Monte Carlo outputs are used as overlays rather than replacements for the core PD/LGD/EAD calculation."
        paragraphs.append(scenario_sentence)

    if bullets:
        paragraphs.append("Key grounded takeaways:\n" + "\n".join(f"- {item}" for item in bullets[:4]))

    paragraphs.append(
        "I am not creating a new approval outside the model; I am explaining the stored SQL/model outputs and how those outputs connect to the credit decision."
    )
    return "\n\n".join(paragraphs)


def summarize_context_sources(context: GroundedCopilotContext) -> list[str]:
    sources: list[str] = []
    mapping: Iterable[tuple[str, dict[str, Any]]] = [
        ("counterparties_master", context.counterparty),
        ("financial_metrics_extracted", context.financials),
        ("financial_ratios", context.ratios),
        ("financial_trend_features", context.financial_trends),
        ("pd_model_predictions", context.pd),
        ("loss_estimates", context.loss),
        ("trade_exposures", context.trade_exposure),
        ("credit_recommendations", context.recommendation),
        ("scenario_results", context.scenario),
        ("simulation_results", context.simulation),
        ("stress_index_history", context.stress),
        ("market_regime_history", context.regime),
    ]
    for table, payload in mapping:
        if payload and not payload.get("_error"):
            if table == "credit_recommendations" and payload.get("_computed_not_persisted"):
                sources.append("credit_decision_engine_computed_from_sql_inputs")
                continue
            suffix = f" id={payload['id']}" if payload.get("id") is not None else ""
            sources.append(f"{table}{suffix}")
    if context.documents:
        sources.append("uploaded_documents")
    if context.market_prices and not context.market_prices[0].get("_error"):
        sources.append("market_prices latest rows")
    return sources
