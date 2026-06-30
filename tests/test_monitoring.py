"""Monitoring and early warning tests for V2."""

from api.monitoring.router import router as monitoring_router
from api.monitoring.service import generate_alerts_from_records, summarize_alerts


def test_monitoring_alerts_are_explainable_and_threshold_driven():
    alerts, warnings = generate_alerts_from_records(
        predictions=[
            {"counterparty_id": 1, "probability_of_default": 0.18, "market_stress_index": 84},
            {"counterparty_id": 2, "probability_of_default": 0.04, "market_stress_index": 45},
        ],
        loss_estimates=[
            {"counterparty_id": 1, "predicted_lgd": 0.74, "exposure_at_default": 900_000, "expected_loss": 119_880},
            {"counterparty_id": 2, "predicted_lgd": 0.35, "exposure_at_default": 100_000, "expected_loss": 1_400},
        ],
        scenario_results=[{"run_id": "stress-1", "scenario_type": "tail", "expected_loss": 1_500_000}],
        simulations=[{"run_id": "mc-1", "var_95": 650_000}],
        stress_history=[{"stress_index": 88}],
    )

    assert warnings == []
    reasons = {alert.alert_reason for alert in alerts}
    assert "Probability of default exceeds high-risk threshold." in reasons
    assert "LGD exceeds high loss-severity threshold." in reasons
    assert "Scenario expected loss exceeds stress loss threshold." in reasons
    assert all(alert.triggering_metric for alert in alerts)
    assert all(alert.data_source for alert in alerts)
    assert all(alert.model_version == "early_warning_rules_v1.0" for alert in alerts)

    counts = summarize_alerts(alerts)
    assert counts["alert_count"] == len(alerts)
    assert counts["high_count"] >= 3


def test_monitoring_does_not_fabricate_alerts_from_missing_data():
    alerts, warnings = generate_alerts_from_records()

    assert alerts == []
    assert warnings == ["No monitoring source records supplied; no alerts generated."]


def test_monitoring_router_imports_with_v2_path():
    assert monitoring_router.prefix == "/api/v1/monitoring"
    route_paths = {route.path for route in monitoring_router.routes}
    assert "/api/v1/monitoring/alerts/latest" in route_paths
