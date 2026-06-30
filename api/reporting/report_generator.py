import pandas as pd

from api.rag.data_access import (
    load_counterparties,
    load_predictions,
    load_portfolio,
    load_simulations,
    load_scenarios
)


def generate_report_data(company_name=None):

    cp = load_counterparties()

    pred = load_predictions()

    portfolio = load_portfolio()

    simulations = load_simulations()

    scenarios = load_scenarios()

    empty_report = {
        "total_exposure": 0.0,
        "total_expected_loss": 0.0,
        "avg_pd": 0.0,
        "avg_lgd": 0.0,
        "var95": 0.0,
        "var99": 0.0,
        "es95": 0.0,
        "es99": 0.0,
        "top_risk": pd.DataFrame(),
        "stress": scenarios
    }

    if portfolio.empty or pred.empty or cp.empty:

        return empty_report

    df = portfolio.merge(
        pred,
        on="counterparty_id",
        how="left"
    )

    df = df.merge(
        cp,
        on="counterparty_id",
        how="left"
    )

    if "company_name" not in df.columns:

        if "company_name_x" in df.columns:
            df["company_name"] = df["company_name_x"]

        elif "company_name_y" in df.columns:
            df["company_name"] = df["company_name_y"]

    if "exposure" not in df.columns:

        if "exposure_x" in df.columns:
            df["exposure"] = df["exposure_x"]

        elif "exposure_y" in df.columns:
            df["exposure"] = df["exposure_y"]

    if company_name and "company_name" in df.columns:

        df = df[
            df["company_name"] == company_name
        ]

    required_columns = [
        "exposure",
        "expected_loss",
        "pd",
        "lgd"
    ]

    if df.empty or any(
        col not in df.columns
        for col in required_columns
    ):

        return empty_report

    total_exposure = float(
        df["exposure"].sum()
    )

    total_expected_loss = float(
        df["expected_loss"].sum()
    )

    avg_pd = float(
        df["pd"].mean()
    )

    avg_lgd = float(
        df["lgd"].mean()
    )

    top_risk = df.sort_values(
        "expected_loss",
        ascending=False
    ).head(10)

    if simulations.empty:

        latest_sim = {
            "var_95": 0.0,
            "var_99": 0.0,
            "expected_shortfall_95": 0.0,
            "expected_shortfall_99": 0.0
        }

    else:

        latest_sim = simulations.sort_values(
            "created_at",
            ascending=False
        ).iloc[0]

    return {

        "total_exposure":
        total_exposure,

        "total_expected_loss":
        total_expected_loss,

        "avg_pd":
        avg_pd,

        "avg_lgd":
        avg_lgd,

        "var95":
        latest_sim.get("var_95", 0.0),

        "var99":
        latest_sim.get("var_99", 0.0),

        "es95":
        latest_sim.get(
            "expected_shortfall_95",
            latest_sim.get("expected_shortfall", 0.0)
        ),

        "es99":
        latest_sim.get("expected_shortfall_99", 0.0),

        "top_risk":
        top_risk,

        "stress":
        scenarios,

        "company_name":
        company_name
    }

