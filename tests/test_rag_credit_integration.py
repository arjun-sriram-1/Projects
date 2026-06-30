"""RAG credit decision and memo integration tests for V2 Phase 11C."""

from api.rag.agents import credit_committee_agent, credit_decision_agent, credit_memo_agent, decision_rules
from api.rag.agents import master_router
from api.rag.agents.prompts import CREDIT_DECISION_PROMPT, MEMO_PROMPT
from api.rag.llm.prompt_templates import CREDIT_RISK_PROMPT


class DummySession:
    def __enter__(self):
        return "db-session"

    def __exit__(self, exc_type, exc, tb):
        return False


def stored_recommendation():
    return {
        "approval_status": "CONDITIONAL APPROVAL",
        "key_risk_drivers": ["High fuel-price sensitivity", "Moderate liquidity buffer"],
        "recommended_credit_limit": 750000.0,
        "recommended_tenor_days": 45,
        "recommended_security": "Standby LC",
        "risk_grade": "BB",
        "run_id": "rec-123",
    }


def test_decision_rules_reads_latest_stored_recommendation_only(monkeypatch):
    monkeypatch.setattr(decision_rules, "SessionLocal", lambda: DummySession())
    monkeypatch.setattr(
        decision_rules,
        "get_latest_credit_recommendation_by_name",
        lambda db, company: stored_recommendation(),
    )

    decision = decision_rules.make_decision("Acme Fuel")

    assert decision["decision"] == "CONDITIONAL APPROVAL"
    assert decision["recommended_credit_limit"] == 750000.0
    assert decision["recommended_tenor_days"] == 45
    assert decision["recommended_security"] == "Standby LC"
    assert decision["risk_grade"] == "BB"
    assert decision["run_id"] == "rec-123"


def test_decision_agent_explains_stored_output_without_recomputing(monkeypatch):
    monkeypatch.setattr(credit_decision_agent, "extract_company", lambda question: "Acme Fuel")
    monkeypatch.setattr(
        credit_decision_agent,
        "make_decision",
        lambda company: {
            "decision": "APPROVED",
            "risk_grade": "BBB",
            "recommended_credit_limit": 1000000.0,
            "recommended_tenor_days": 60,
            "recommended_security": "Existing collateral acceptable",
            "reasons": ["Low PD", "Strong collateral"],
            "run_id": "rec-456",
        },
    )

    response = credit_decision_agent.run_credit_decision_agent("Should we approve Acme Fuel?")

    assert "Stored Credit Decision for Acme Fuel" in response
    assert "Approval Status: APPROVED" in response
    assert "Recommended Credit Limit: 1,000,000.00" in response
    assert "Recommendation Run ID: rec-456" in response
    assert "based only on the latest stored credit_recommendations record" in response


def test_decision_agent_requires_stored_recommendation(monkeypatch):
    monkeypatch.setattr(credit_decision_agent, "extract_company", lambda question: "Missing Co")
    monkeypatch.setattr(
        credit_decision_agent,
        "make_decision",
        lambda company: {
            "decision": "UNKNOWN",
            "reason": "No stored credit recommendation found. Run the credit decision engine first.",
            "reasons": ["No stored credit recommendation found."],
        },
    )

    response = credit_decision_agent.run_credit_decision_agent("Should we approve Missing Co?")

    assert response == "No stored credit recommendation found. Run the credit decision engine first."


def test_credit_committee_agent_wraps_stored_decision_not_policy_calculator(monkeypatch):
    monkeypatch.setattr(
        credit_committee_agent,
        "make_decision",
        lambda company: {
            "decision": "REJECT / PREPAYMENT ONLY",
            "reason": "No unsecured open credit.",
            "reasons": ["High PD"],
        },
    )

    result = credit_committee_agent.evaluate_credit_request("Weak Fuel", 900000, 90)

    assert result["decision"] == "REJECT / PREPAYMENT ONLY"
    assert result["source"] == "latest stored credit_recommendations record"
    assert "does not create an independent credit decision" in result["note"]
    assert result["requested_exposure"] == 900000
    assert result["tenor_days"] == 90


def test_credit_memo_agent_uses_grounded_service_only(monkeypatch):
    monkeypatch.setattr(credit_memo_agent, "SessionLocal", lambda: DummySession())
    calls = []

    def fake_build_memo(db, company, persist=True):
        calls.append((db, company, persist))
        return "Memo from stored SQL/model outputs only."

    monkeypatch.setattr(credit_memo_agent, "build_grounded_credit_memo", fake_build_memo)

    memo = credit_memo_agent.generate_credit_memo("Acme Fuel")

    assert memo == "Memo from stored SQL/model outputs only."
    assert calls == [("db-session", "Acme Fuel", True)]


def test_master_router_routes_decision_and_memo_to_stored_agents(monkeypatch):
    monkeypatch.setattr(master_router, "classify_query", lambda query: "decision")
    monkeypatch.setattr(master_router, "run_credit_decision_agent", lambda query: "stored decision")
    assert master_router.route_query("approve Acme Fuel?") == "stored decision"

    monkeypatch.setattr(master_router, "classify_query", lambda query: "memo")
    monkeypatch.setattr(master_router, "extract_company", lambda query: "Acme Fuel")
    monkeypatch.setattr(master_router, "generate_credit_memo", lambda company: f"memo {company}")
    assert master_router.route_query("generate memo for Acme Fuel") == "memo Acme Fuel"


def test_rag_prompts_forbid_independent_credit_decisions():
    combined = "\n".join([CREDIT_RISK_PROMPT, CREDIT_DECISION_PROMPT, MEMO_PROMPT]).lower()

    assert "do not create independent" in combined or "must not create independent" in combined
    assert "stored credit_recommendations" in combined
    assert "do not invent" in combined
    assert "if stored decision data is missing" in combined
