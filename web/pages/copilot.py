"""AI credit analyst page."""

from __future__ import annotations

from html import escape
from typing import Any

import streamlit as st

from web.api_client import ApiClient
from web.components.formatting import money, number, pct, text
from web.components.layout import render_technical_json
from web.components.terminal import (
    action_grid,
    evidence_panel,
    render_terminal_kpi_strip,
    terminal_panel,
)


SUGGESTIONS = [
    "Why is the recommended limit constrained?",
    "What financial metrics are weakest?",
    "How does market stress affect this name?",
    "What should credit committee watch next?",
]


def _date_only(value: Any) -> str:
    raw = text(value)
    return raw if raw == "-" else raw.split("T")[0]


def _latest_context(client: ApiClient, counterparty_id: int) -> dict[str, dict]:
    pd_result = client.latest_pd(counterparty_id)
    loss_result = client.latest_loss(counterparty_id)
    stress_result = client.latest_market_stress()
    decision_result = client.latest_recommendation(counterparty_id)
    ratios_result = client.latest_ratios(counterparty_id)
    return {
        "pd": pd_result.data if pd_result.ok and pd_result.data else {},
        "loss": loss_result.data if loss_result.ok and loss_result.data else {},
        "stress": stress_result.data if stress_result.ok and stress_result.data else {},
        "decision": decision_result.data if decision_result.ok and decision_result.data else {},
        "ratios": ratios_result.data if ratios_result.ok and ratios_result.data else {},
    }


def _context_kpis(payload: dict[str, dict]) -> list[tuple[str, str, str, str]]:
    pd_data = payload["pd"]
    loss = payload["loss"]
    stress = payload["stress"]
    decision = payload["decision"]
    return [
        ("Approval", text(decision.get("approval_status")), "Latest recommendation", "info"),
        ("Risk Grade", text(decision.get("risk_grade")), "Decision output", "watch"),
        ("Final PD", pct(pd_data.get("final_pd")), text(pd_data.get("classification_label")), "risk"),
        ("Expected Loss", money(loss.get("expected_loss")), "Loss engine", "watch"),
        ("Stress Index", number(stress.get("stress_index"), 2), text(stress.get("stress_level")), "info"),
    ]


def _context_panel(payload: dict[str, dict], context: dict) -> str:
    decision = payload["decision"]
    pd_data = payload["pd"]
    loss = payload["loss"]
    ratios = payload["ratios"]
    rows = [
        ("Counterparty", text(context.get("counterparty")), "Selected workspace"),
        ("Requested limit", money(context.get("requested_limit")), "Header context"),
        ("Recommended limit", money(decision.get("recommended_credit_limit")), "Credit recommendation"),
        ("Recommended security", text(decision.get("recommended_security")), "Credit recommendation"),
        ("Final PD", pct(pd_data.get("final_pd")), "Quant model"),
        ("LGD / EAD", f"{pct(loss.get('predicted_lgd'))} / {money(loss.get('exposure_at_default'))}", "Loss model"),
        ("Debt / EBITDA", number(ratios.get("debt_to_ebitda"), 4), "Financial ratios"),
        ("Current ratio", number(ratios.get("current_ratio"), 4), "Financial ratios"),
    ]
    return terminal_panel("Analyst Context", evidence_panel(rows), "Current backend outputs available to the credit workflow")


def _data_used(payload: dict[str, dict]) -> list[tuple[str, str, str | None]]:
    return [
        ("Financial ratios", _date_or_latest(payload["ratios"].get("created_at") or payload["ratios"].get("fiscal_year")), "Financial statement and ratio context"),
        ("PD model output", _date_only(payload["pd"].get("created_at")), "Default probability explanation"),
        ("LGD / EAD / expected loss", _date_only(payload["loss"].get("created_at")), "Loss and exposure explanation"),
        ("Market stress components", text(payload["stress"].get("date")), "Market context"),
        ("Credit recommendation", _date_only(payload["decision"].get("created_at")), "Decision explanation"),
    ]


def _date_or_latest(value: Any) -> str:
    candidate = text(value)
    return "Latest available" if candidate == "-" else candidate


def _suggestion_grid() -> str:
    cards = []
    for question in SUGGESTIONS:
        cards.append(
            "<div class='suggestion-card'>"
            f"<div class='suggestion-title'>{escape(question)}</div>"
            "<div class='suggestion-copy'>Grounded in current credit workflow context.</div>"
            "</div>"
        )
    return "<div class='suggestion-grid'>" + "".join(cards) + "</div>"


def _conversation_panel(messages: list[dict]) -> str:
    if messages:
        body = action_grid(
            [
                ("Conversation active", f"{len(messages)} messages in this session."),
                ("Grounding", "Answers include visible data lineage when returned."),
            ]
        )
    else:
        body = action_grid(
            [
                ("Ready", "Ask a counterparty, model, market, or recommendation question."),
                ("Grounded context", "The surrounding workflow panels show the data currently available."),
            ]
        )
    return terminal_panel("Live Credit Analyst", body, "Session state for this dashboard conversation")


def render(client: ApiClient, context: dict) -> None:
    counterparty_id = int(context["counterparty_id"])
    st.subheader("AI Credit Analyst")
    st.caption("Ask focused credit questions against the current counterparty context.")

    st.session_state.setdefault("copilot_messages", [])
    st.session_state.setdefault("copilot_input", "")

    context_payload = _latest_context(client, counterparty_id)
    render_terminal_kpi_strip(_context_kpis(context_payload))

    context_col, session_col = st.columns([1.2, 0.8])
    with context_col:
        st.markdown(_context_panel(context_payload, context), unsafe_allow_html=True)
    with session_col:
        st.markdown(_conversation_panel(st.session_state.copilot_messages), unsafe_allow_html=True)

    st.markdown(_suggestion_grid(), unsafe_allow_html=True)
    cols = st.columns(len(SUGGESTIONS))
    for col, question in zip(cols, SUGGESTIONS):
        with col:
            if st.button("Ask", key=f"copilot_{question}", use_container_width=True):
                st.session_state.copilot_input = question

    for message in st.session_state.copilot_messages:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])
            if message.get("data_used"):
                with st.expander("Data used", expanded=False):
                    st.markdown(
                        terminal_panel("Answer Grounding", evidence_panel(message["data_used"]), "Backend outputs checked for this answer"),
                        unsafe_allow_html=True,
                    )

    prompt = st.chat_input("Ask about this counterparty or portfolio")
    question = prompt or st.session_state.pop("copilot_input", "")
    if question:
        st.session_state.copilot_messages.append({"role": "user", "content": question})
        with st.chat_message("user"):
            st.markdown(question)
        with st.chat_message("assistant"):
            with st.spinner("Asking backend copilot..."):
                result = client.copilot(question)
            if result.ok:
                answer = result.data.get("answer") if isinstance(result.data, dict) else str(result.data)
                st.markdown(answer)
                data_used = _data_used(context_payload)
                with st.expander("Data used", expanded=False):
                    st.markdown(
                        terminal_panel("Answer Grounding", evidence_panel(data_used), "Backend outputs checked for this answer"),
                        unsafe_allow_html=True,
                    )
                st.session_state.copilot_messages.append(
                    {
                        "role": "assistant",
                        "content": answer,
                        "data_used": data_used,
                    }
                )
                if isinstance(result.data, dict) and result.data.get("sources"):
                    render_technical_json("Retrieved sources", result.data.get("sources"))
            else:
                message = f"Copilot unavailable: {result.error}"
                st.error(message)
                st.session_state.copilot_messages.append({"role": "assistant", "content": message})

    if st.button("Clear chat", use_container_width=False):
        st.session_state.copilot_messages = []
        st.rerun()
