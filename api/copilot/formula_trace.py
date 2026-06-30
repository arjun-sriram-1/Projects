"""Deterministic formula tracing for copilot explanations."""

from __future__ import annotations

from math import erf, sqrt
from typing import Any

from api.copilot.knowledge import get_field, get_formula


def _safe_float(value: Any) -> float | None:
    try:
        if value is None or value == "":
            return None
        return float(value)
    except (TypeError, ValueError):
        return None


def _normal_cdf(value: float) -> float:
    return 0.5 * (1.0 + erf(value / sqrt(2.0)))


def _resolve_target(target: str) -> tuple[str, dict[str, Any] | None]:
    formula = get_formula(target)
    if formula:
        return str(formula["formula_id"]), formula
    field = get_field(target)
    if field and field.get("formula_id"):
        formula = get_formula(str(field["formula_id"]))
        if formula:
            return str(formula["formula_id"]), formula
    return target, None


def _with_input_status(inputs: list[str], values: dict[str, Any]) -> dict[str, Any]:
    return {
        name: {
            "value": values.get(name),
            "provided": name in values,
        }
        for name in inputs
    }


def trace_formula(target: str, values: dict[str, Any] | None = None) -> dict[str, Any]:
    """Trace a known formula with optional numeric calculation.

    The trace is intentionally deterministic and grounded in the JSON formula
    catalog. If enough numeric inputs are supplied, it calculates the result.
    Otherwise it returns the formula, required inputs, and missing inputs.
    """
    values = values or {}
    formula_id, formula = _resolve_target(target)
    if not formula:
        return {
            "target": target,
            "matched": False,
            "message": "No formula catalog entry matched the requested target.",
            "available_hint": "Try fields like final_pd, expected_loss, stress_index, risk_grade, or recommended_credit_limit.",
        }

    inputs = [str(item) for item in formula.get("inputs", [])]
    trace: dict[str, Any] = {
        "target": target,
        "matched": True,
        "formula_id": formula_id,
        "name": formula.get("name"),
        "formula": formula.get("formula"),
        "inputs": _with_input_status(inputs, values),
        "output": formula.get("output"),
        "plain_english": formula.get("plain_english"),
        "source_files": formula.get("source_files", []),
        "calculation": None,
        "result": None,
        "missing_inputs": [name for name in inputs if name not in values],
        "notes": [],
    }

    calculator = _CALCULATORS.get(formula_id)
    if calculator:
        trace.update(calculator(values))
    else:
        trace["notes"].append("No numeric calculator is registered yet; returning catalog trace only.")
    return trace


def _trace_expected_loss(values: dict[str, Any]) -> dict[str, Any]:
    pd = _safe_float(
        values.get("probability_of_default")
        if "probability_of_default" in values
        else values.get("pd")
        if "pd" in values
        else values.get("final_pd")
    )
    lgd = _safe_float(
        values.get("loss_given_default")
        if "loss_given_default" in values
        else values.get("lgd")
        if "lgd" in values
        else values.get("predicted_lgd")
    )
    ead = _safe_float(
        values.get("exposure_at_default")
        if "exposure_at_default" in values
        else values.get("ead")
    )
    missing = []
    if pd is None:
        missing.append("probability_of_default")
    if lgd is None:
        missing.append("loss_given_default")
    if ead is None:
        missing.append("exposure_at_default")
    if missing:
        return {
            "missing_inputs": missing,
            "notes": ["Provide PD, LGD, and EAD to calculate expected loss."],
        }
    result = pd * lgd * ead
    return {
        "calculation": f"{pd:.6f} * {lgd:.6f} * {ead:.2f}",
        "result": result,
        "missing_inputs": [],
        "notes": [
            "Expected loss rises one-for-one with PD, LGD, or EAD if the other two stay constant."
        ],
    }


def _trace_final_pd(values: dict[str, Any]) -> dict[str, Any]:
    structural_pd = _safe_float(values.get("structural_pd"))
    ml_pd = _safe_float(values.get("ml_pd"))
    structural_weight = _safe_float(values.get("structural_weight"))
    ml_weight = _safe_float(values.get("ml_weight"))
    if structural_weight is None:
        structural_weight = 0.4
    if ml_weight is None:
        ml_weight = 0.6
    missing = []
    if structural_pd is None:
        missing.append("structural_pd")
    if ml_pd is None:
        missing.append("ml_pd")
    if missing:
        return {
            "missing_inputs": missing,
            "notes": [
                "Current catalog default blend weights are 0.40 structural and 0.60 ML.",
                "Provide structural_pd and ml_pd to calculate final_pd.",
            ],
        }
    total = structural_weight + ml_weight
    if total <= 0:
        structural_weight, ml_weight = 0.4, 0.6
        total = 1.0
    structural_weight = structural_weight / total
    ml_weight = ml_weight / total
    result = structural_weight * structural_pd + ml_weight * ml_pd
    return {
        "calculation": (
            f"{structural_weight:.4f} * {structural_pd:.6f} + "
            f"{ml_weight:.4f} * {ml_pd:.6f}"
        ),
        "result": result,
        "missing_inputs": [],
        "notes": [
            "This is the final PD used downstream by LGD/EAD expected loss and credit decision logic.",
            "The current trained config uses 40% structural PD and 60% ML PD unless overridden in the request.",
        ],
    }


def _trace_risk_grade(values: dict[str, Any]) -> dict[str, Any]:
    pd = _safe_float(
        values.get("probability_of_default")
        if "probability_of_default" in values
        else values.get("pd")
        if "pd" in values
        else values.get("final_pd")
    )
    if pd is None:
        return {
            "missing_inputs": ["probability_of_default"],
            "notes": ["Provide PD/final_pd to map the internal proxy risk grade."],
        }
    if pd < 0.01:
        grade = "A"
    elif pd < 0.03:
        grade = "BBB"
    elif pd < 0.07:
        grade = "BB"
    elif pd < 0.15:
        grade = "B"
    else:
        grade = "CCC"
    return {
        "calculation": f"PD {pd:.6f} mapped to internal grade band",
        "result": grade,
        "missing_inputs": [],
        "notes": ["This is an internal proxy grade, not an external agency rating."],
    }


def _trace_recommended_limit(values: dict[str, Any]) -> dict[str, Any]:
    base_limit = _safe_float(
        values.get("base_limit")
        if "base_limit" in values
        else values.get("requested_credit_limit")
        if "requested_credit_limit" in values
        else values.get("approved_credit_limit")
        if "approved_credit_limit" in values
        else values.get("exposure_at_default")
    )
    haircut = _safe_float(values.get("limit_haircut"))
    missing = []
    if base_limit is None:
        missing.append("base_limit")
    if haircut is None:
        missing.append("limit_haircut")
    if missing:
        return {
            "missing_inputs": missing,
            "notes": [
                "The credit engine first determines a base limit, then applies the risk haircut."
            ],
        }
    haircut = min(max(haircut, 0.0), 1.0)
    result = base_limit * (1.0 - haircut)
    return {
        "calculation": f"{base_limit:.2f} * (1 - {haircut:.6f})",
        "result": result,
        "missing_inputs": [],
        "notes": ["Higher policy haircuts reduce the recommended limit."],
    }


def _trace_structural_pd(values: dict[str, Any]) -> dict[str, Any]:
    dd = _safe_float(values.get("distance_to_default"))
    if dd is None:
        return {
            "missing_inputs": ["distance_to_default"],
            "notes": ["Provide distance_to_default to calculate structural PD as N(-DD)."],
        }
    result = _normal_cdf(-dd)
    return {
        "calculation": f"N(-{dd:.6f})",
        "result": result,
        "missing_inputs": [],
        "notes": ["Lower distance to default produces higher structural PD."],
    }


def _trace_pca_stress(values: dict[str, Any]) -> dict[str, Any]:
    pc1 = _safe_float(values.get("pc1_score"))
    if pc1 is None:
        return {
            "missing_inputs": ["pc1_score"],
            "notes": [
                "PCA stress needs the PC1 score and historical distribution to calculate the percentile-scaled 0-100 stress index.",
                "The live project calculates this in api/market_data/stress_index.py rather than from a single point alone.",
            ],
        }
    return {
        "calculation": "percentile_scale(pc1_score) using the historical PC1 distribution",
        "result": None,
        "missing_inputs": ["historical_pc1_distribution"],
        "notes": [
            "A single PC1 value is not enough to reproduce the exact 0-100 stress index without the historical PC1 distribution.",
            "Positive PCA loadings show which market components push the combined stress factor upward.",
        ],
    }


def _trace_pc1(values: dict[str, Any]) -> dict[str, Any]:
    loadings = values.get("pca_loadings")
    components = values.get("component_values")
    if not isinstance(loadings, dict) or not isinstance(components, dict):
        return {
            "missing_inputs": ["pca_loadings", "component_values"],
            "notes": [
                "PC1 is the dot product of standardized component values and PCA loadings.",
                "The project normally computes PCA directly from the component matrix in api/market_data/stress_index.py.",
            ],
        }
    shared = [key for key in loadings if key in components]
    missing = [key for key in loadings if key not in components]
    result = 0.0
    terms = []
    for key in shared:
        loading = _safe_float(loadings.get(key))
        component = _safe_float(components.get(key))
        if loading is None or component is None:
            missing.append(key)
            continue
        result += loading * component
        terms.append(f"{loading:.6f}*{component:.6f}")
    if not terms:
        return {
            "missing_inputs": ["numeric_pca_loadings", "numeric_component_values"],
            "notes": ["No overlapping numeric PCA loading/component pairs were supplied."],
        }
    return {
        "calculation": " + ".join(terms),
        "result": result,
        "missing_inputs": missing,
        "notes": ["This manual trace assumes supplied component values are already standardized."],
    }


_CALCULATORS = {
    "expected_loss": _trace_expected_loss,
    "final_pd_blend": _trace_final_pd,
    "risk_grade_mapping": _trace_risk_grade,
    "recommended_limit": _trace_recommended_limit,
    "merton_structural_pd": _trace_structural_pd,
    "pca_stress_index": _trace_pca_stress,
    "pca_pc1": _trace_pc1,
}

