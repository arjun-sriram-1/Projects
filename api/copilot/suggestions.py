"""Prompt suggestions for the project-aware copilot."""

from __future__ import annotations


DEFAULT_SUGGESTIONS = [
    {
        "label": "Trace expected loss",
        "question": "Trace expected loss using PD, LGD, and EAD.",
        "intent": "formula_trace",
    },
    {
        "label": "Explain final PD",
        "question": "How is final PD calculated from structural PD and ML PD?",
        "intent": "formula_trace",
    },
    {
        "label": "PCA to decision",
        "question": "How does PCA market stress flow into PD and the final credit decision?",
        "intent": "market_pca_explanation",
    },
    {
        "label": "Interview version",
        "question": "Explain this project to an interviewer from data input to final recommendation.",
        "intent": "interview_explanation",
    },
]


PAGE_SUGGESTIONS = {
    "counterparty": [
        {
            "label": "Company snapshot",
            "question": "Give me a casual counterparty analysis without repeating dashboard metrics.",
            "intent": "field_definition",
        },
        {
            "label": "Data lineage",
            "question": "Where do this counterparty's financial data points come from?",
            "intent": "data_lineage",
        },
    ],
    "financials": [
        {
            "label": "Ratio meaning",
            "question": "Explain the key financial ratios and how they affect credit risk.",
            "intent": "field_definition",
        },
        {
            "label": "Weakest metric",
            "question": "Which financial metric is weakest and how does it affect PD?",
            "intent": "model_explanation",
        },
    ],
    "market": [
        {
            "label": "PCA stress",
            "question": "Explain how market data is converted into PCA stress index.",
            "intent": "market_pca_explanation",
        },
        {
            "label": "Oil impact",
            "question": "How does Brent or jet fuel pressure affect the final risk output?",
            "intent": "market_factor_explanation",
        },
    ],
    "scenario": [
        {
            "label": "Stress scenario",
            "question": "How do scenario multipliers connect stress to PD, LGD, EAD, and losses?",
            "intent": "market_factor_explanation",
        },
        {
            "label": "Tail risk",
            "question": "Explain VaR and expected shortfall compared with expected loss.",
            "intent": "formula_trace",
        },
    ],
    "models": [
        {
            "label": "Model realism",
            "question": "Which models use real, proxy, synthetic, or calibrated data?",
            "intent": "model_explanation",
        },
        {
            "label": "PD blend",
            "question": "Trace final PD and explain the calibrated blend weights.",
            "intent": "formula_trace",
        },
    ],
    "decision": [
        {
            "label": "Limit trace",
            "question": "Explain how the recommended credit limit is calculated.",
            "intent": "credit_decision_explanation",
        },
        {
            "label": "Approval logic",
            "question": "Explain the approval status, risk grade, tenor, and security condition.",
            "intent": "credit_decision_explanation",
        },
    ],
}


def get_suggestions(page: str | None = None) -> dict:
    """Return default and page-specific copilot suggestions."""
    page_key = (page or "").lower().strip()
    return {
        "page": page_key or None,
        "default": DEFAULT_SUGGESTIONS,
        "page_specific": PAGE_SUGGESTIONS.get(page_key, []),
        "uses_paid_resources": False,
    }
