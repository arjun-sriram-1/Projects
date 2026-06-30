"""API client for dashboard-to-backend calls.

The dashboard must not connect directly to Postgres or recalculate backend model
logic. All data should come through FastAPI endpoints.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Optional

import requests

from web.config import config


@dataclass
class ApiResult:
    ok: bool
    data: Optional[Any] = None
    error: Optional[str] = None
    status_code: Optional[int] = None


class ApiClient:
    def __init__(self, base_url: str | None = None, timeout: int = 20, upload_timeout: int = 300):
        self.base_url = (base_url or config.api_base_url).rstrip("/")
        self.timeout = timeout
        self.upload_timeout = upload_timeout

    def request(self, method: str, path: str, *, json: Optional[dict[str, Any]] = None, params: Optional[dict[str, Any]] = None) -> ApiResult:
        try:
            response = requests.request(
                method=method.upper(),
                url=f"{self.base_url}{path}",
                json=json,
                params=params,
                timeout=self.timeout,
            )
            if response.status_code >= 400:
                return ApiResult(False, error=response.text, status_code=response.status_code)
            return ApiResult(True, data=response.json(), status_code=response.status_code)
        except requests.RequestException as exc:
            return ApiResult(False, error=str(exc))

    def get(self, path: str, *, params: Optional[dict[str, Any]] = None) -> ApiResult:
        return self.request("GET", path, params=params)

    def post(self, path: str, *, json: Optional[dict[str, Any]] = None, params: Optional[dict[str, Any]] = None) -> ApiResult:
        return self.request("POST", path, json=json, params=params)

    def health(self) -> ApiResult:
        return self.get("/health")

    def counterparties(self, search: str | None = None, limit: int = 50) -> ApiResult:
        params: dict[str, Any] = {"limit": limit}
        if search:
            params["search"] = search
        return self.get("/api/v1/documents/counterparties", params=params)

    def latest_alerts(self) -> ApiResult:
        return self.get("/api/v1/monitoring/alerts/latest")

    def latest_market_stress(self) -> ApiResult:
        return self.get("/api/v1/market-intelligence/stress/latest")

    def latest_market_regime(self) -> ApiResult:
        return self.get("/api/v1/market-intelligence/regime/latest")

    def counterparty_documents(self, counterparty_id: int) -> ApiResult:
        return self.get(f"/api/v1/documents/counterparty/{counterparty_id}")

    def latest_ratios(self, counterparty_id: int) -> ApiResult:
        return self.get(f"/api/v1/financial-analysis/counterparty/{counterparty_id}/latest-ratios")

    def latest_pd(self, counterparty_id: int) -> ApiResult:
        return self.get(f"/api/v1/credit-risk/counterparty/{counterparty_id}/latest-pd")

    def calculate_pd(self, financial_metrics_id: int, time_horizon_years: float = 1.0) -> ApiResult:
        return self.post(
            f"/api/v1/credit-risk/pd/calculate/{financial_metrics_id}",
            json={"time_horizon_years": time_horizon_years},
        )

    def latest_loss(self, counterparty_id: int) -> ApiResult:
        return self.get(f"/api/v1/credit-risk/counterparty/{counterparty_id}/latest-loss")

    def calculate_loss(self, payload: dict[str, Any]) -> ApiResult:
        return self.post("/api/v1/credit-risk/loss/calculate", json=payload)

    def latest_recommendation(self, counterparty_id: int) -> ApiResult:
        return self.get(f"/api/v1/credit-decision/counterparty/{counterparty_id}/latest")

    def calculate_recommendation(self, counterparty_id: int) -> ApiResult:
        return self.post(f"/api/v1/credit-decision/counterparty/{counterparty_id}/recommend")

    def document_status(self, document_id: int) -> ApiResult:
        return self.get(f"/api/v1/documents/status/{document_id}")

    def calculate_ratios(self, financial_metrics_id: int) -> ApiResult:
        return self.post(f"/api/v1/financial-analysis/ratios/calculate/{financial_metrics_id}")

    def create_manual_financial_metrics(self, payload: dict[str, Any]) -> ApiResult:
        return self.post("/api/v1/financial-analysis/metrics/manual", json=payload)

    def upload_document(self, file_obj, filename: str, counterparty_id: int | None = None, counterparty_name: str | None = None, document_type: str = "annual_report", created_by: str = "dashboard") -> ApiResult:
        params = {"document_type": document_type, "created_by": created_by}
        if counterparty_id:
            params["counterparty_id"] = counterparty_id
        elif counterparty_name:
            params["counterparty_name"] = counterparty_name
        files = {"file": (filename, file_obj, "application/pdf")}
        try:
            response = requests.post(f"{self.base_url}/api/v1/documents/upload", params=params, files=files, timeout=max(self.timeout, self.upload_timeout))
            if response.status_code >= 400:
                return ApiResult(False, error=response.text, status_code=response.status_code)
            return ApiResult(True, data=response.json(), status_code=response.status_code)
        except requests.RequestException as exc:
            return ApiResult(False, error=str(exc))

    def recent_market_prices(self, assets: list[str], limit_per_asset: int = 180) -> ApiResult:
        return self.get("/api/v1/market-intelligence/prices/recent", params={"assets": ",".join(assets), "limit_per_asset": limit_per_asset})

    def market_forecast(self, model_type: str, assets: list[str], market_prices: list[dict], horizon: int = 10) -> ApiResult:
        return self.post("/api/v1/market-intelligence/forecast", json={"model_type": model_type, "assets": assets, "horizon": horizon, "market_prices": market_prices})

    def commodity_factors(self, assets: list[str], market_prices: list[dict], rolling_window: int = 30) -> ApiResult:
        return self.post("/api/v1/market-intelligence/commodity-factors/analyze", json={"assets": assets, "rolling_window": rolling_window, "market_prices": market_prices})

    def scenario_list(self, target_regime: str | None = None) -> ApiResult:
        params = {"target_regime": target_regime} if target_regime else None
        return self.get("/api/v1/scenario-analysis/scenarios", params=params)

    def latest_monte_carlo(self) -> ApiResult:
        return self.get("/api/v1/scenario-analysis/monte-carlo/latest")

    def run_monte_carlo(self, payload: dict[str, Any]) -> ApiResult:
        return self.post("/api/v1/scenario-analysis/monte-carlo/run", json=payload)

    def hedge_sensitivity(self, payload: dict[str, Any]) -> ApiResult:
        return self.post("/api/v1/scenario-analysis/hedging/sensitivity", json=payload)
    def analyze_alerts(self, payload: dict[str, Any]) -> ApiResult:
        return self.post("/api/v1/monitoring/alerts/analyze", json=payload)

    def copilot(self, question: str) -> ApiResult:
        return self.post("/api/copilot", json={"question": question})

    def rag_memo(self, company_name: str) -> ApiResult:
        return self.post("/api/memo", json={"company_name": company_name})

    def export_memo(self, question: str) -> ApiResult:
        return self.post("/api/v1/reporting/memo/export", json={"question": question})

    def export_risk_report(self, company_name: str | None = None, output_file: str | None = None) -> ApiResult:
        params: dict[str, Any] = {}
        if company_name:
            params["company_name"] = company_name
        if output_file:
            params["output_file"] = output_file
        return self.get("/api/v1/reporting/risk-report/export", params=params or None)

    def model_validation_report(self, payload: dict[str, Any] | None = None) -> ApiResult:
        return self.post("/api/v1/reporting/model-validation/report", json=payload or {})





