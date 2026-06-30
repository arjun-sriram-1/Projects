import math


POLICY = {
    "moderate_pd": 0.08,
    "high_pd": 0.15,
    "high_lgd": 0.60,
    "long_tenor_days": 90,
    "large_request": 5_000_000,
    "high_combined_exposure": 10_000_000
}


def calculate_expected_loss_amount(
    exposure,
    pd_value,
    lgd_value
):

    return float(exposure) * float(pd_value) * float(lgd_value)


SECURITY_SCORE_RELIEF = {
    "deposit": 2,
    "lc": 2,
    "letter of credit": 2,
    "guarantee": 1,
    "partial support": 1
}


def _security_relief(security):

    security_key = str(security or "").strip().lower()

    return SECURITY_SCORE_RELIEF.get(security_key, 0)


def evaluate_credit_policy(
    counterparty,
    requested_exposure=None,
    tenor_days=None
):
    """
    Single formal credit decision policy used by committee,
    memo, and credit-decision agents.
    """

    pd_value = float(counterparty.get("pd", 0) or 0)
    lgd_value = float(counterparty.get("lgd", 0) or 0)

    if (
        pd_value <= 0
        or lgd_value <= 0
        or math.isnan(pd_value)
        or math.isnan(lgd_value)
    ):

        return {
            "company": counterparty.get("company_name"),
            "decision": "REJECT",
            "pd": 0.0,
            "lgd": 0.0,
            "expected_loss": 0.0,
            "requested_exposure": requested_exposure or 0.0,
            "current_exposure": counterparty.get("exposure", 0) or 0,
            "combined_exposure": counterparty.get("exposure", 0) or 0,
            "tenor_days": tenor_days or counterparty.get("credit_days", 0) or 0,
            "security": counterparty.get("security"),
            "score": 99,
            "reasons": [
                "Missing or invalid PD/LGD model output"
            ],
            "reason": "Missing or invalid PD/LGD model output"
        }

    current_exposure = float(
        counterparty.get("exposure", 0) or 0
    )

    requested_exposure = float(
        requested_exposure
        if requested_exposure is not None
        else current_exposure
    )

    tenor_days = int(
        tenor_days
        if tenor_days is not None
        else counterparty.get("credit_days", 0) or 0
    )

    combined_exposure = current_exposure + requested_exposure

    expected_loss = calculate_expected_loss_amount(
        requested_exposure,
        pd_value,
        lgd_value
    )

    score = 0
    reasons = []

    if pd_value > POLICY["high_pd"]:
        score += 3
        reasons.append("High probability of default")

    elif pd_value > POLICY["moderate_pd"]:
        score += 2
        reasons.append("Moderate probability of default")

    if lgd_value > POLICY["high_lgd"]:
        score += 2
        reasons.append("High loss given default")

    if tenor_days > POLICY["long_tenor_days"]:
        score += 2
        reasons.append("Long requested credit tenor")

    if requested_exposure > POLICY["large_request"]:
        score += 2
        reasons.append("Large requested exposure")

    if combined_exposure > POLICY["high_combined_exposure"]:
        score += 1
        reasons.append("High combined exposure after request")

    relief = _security_relief(
        counterparty.get("security")
    )

    if relief:
        score = max(0, score - relief)
        reasons.append("Recognized security mitigates credit risk")

    if score <= 2:
        decision = "APPROVE"

    elif score <= 5:
        decision = "CONDITIONAL APPROVAL"

    else:
        decision = "REJECT"

    if not reasons:
        reasons.append("Within configured credit policy thresholds")

    return {
        "company": counterparty.get("company_name"),
        "decision": decision,
        "pd": pd_value,
        "lgd": lgd_value,
        "expected_loss": expected_loss,
        "requested_exposure": requested_exposure,
        "current_exposure": current_exposure,
        "combined_exposure": combined_exposure,
        "tenor_days": tenor_days,
        "security": counterparty.get("security"),
        "score": score,
        "reasons": reasons,
        "reason": "; ".join(reasons)
    }
