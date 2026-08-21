"""
Core regression tests for the CredMe decisioning API.

Focus: the behaviors the project's pitch depends on —
thin-file applicants are never auto-declined, the unified
decision endpoint returns a coherent shape, and each risk
tier maps to the expected decision family.
"""

import pytest
from fastapi.testclient import TestClient

from backend.api import CREDME_API_KEY_ADMIN, CREDME_API_KEY_APPLICANT, app

client = TestClient(app)

AUTH_HEADERS = {"X-API-Key": CREDME_API_KEY_APPLICANT}
ADMIN_HEADERS = {"X-API-Key": CREDME_API_KEY_ADMIN}


def base_application(**overrides):
    application = {
        "Age": 32,
        "AnnualIncome": 75000,
        "CreditScore": 680,
        "EmploymentStatus": "Employed",
        "EducationLevel": "Bachelor",
        "Experience": 8,
        "LoanAmount": 20000,
        "LoanDuration": 36,
        "MaritalStatus": "Single",
        "NumberOfDependents": 1,
        "HomeOwnershipStatus": "Rent",
        "MonthlyDebtPayments": 800,
        "TotalDebtToIncomeRatio": 0.30,
        "CreditCardUtilizationRate": 0.25,
        "NumberOfOpenCreditLines": 4,
        "NumberOfCreditInquiries": 1,
        "DebtToIncomeRatio": 0.22,
        "BankruptcyHistory": 0,
        "LoanPurpose": "Education",
        "PreviousLoanDefaults": 0,
        "PaymentHistory": 28,
        "LengthOfCreditHistory": 10,
        "SavingsAccountBalance": 15000,
        "CheckingAccountBalance": 5000,
        "TotalAssets": 50000,
        "TotalLiabilities": 20000,
        "MonthlyIncome": 6250,
        "UtilityBillsPaymentHistory": 0.95,
        "JobTenure": 5,
        "NetWorth": 30000,
    }
    application.update(overrides)
    return application


def base_transaction(**overrides):
    transaction = {
        "TransactionAmount": 150,
        "TransactionDuration": 60,
        "LoginAttempts": 1,
        "AccountBalance": 8000,
        "CustomerAge": 32,
        "TransactionType": "Debit",
        "Location": "San Diego",
        "Channel": "Online",
        "AccountID": "AC00128",
        "DeviceID": "D000380",
    }
    transaction.update(overrides)
    return transaction


def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "healthy"
    assert body["credit_model_loaded"] is True
    assert body["behavior_model_loaded"] is True


def test_predict_returns_expected_shape():
    response = client.post(
        "/predict", json=base_application(), headers=AUTH_HEADERS
    )
    assert response.status_code == 200
    body = response.json()
    assert body["decision"] in {"APPROVE", "REVIEW", "DECLINE"}
    assert body["risk_level"] in {"LOW", "MEDIUM", "HIGH", "THIN_FILE"}
    assert 0.0 <= body["approval_probability"] <= 1.0
    assert len(body["reasons"]) <= 5


def test_thin_file_never_auto_declines():
    """
    CreditScore=0 means no traditional credit history, not bad
    credit. A financially clean thin-file applicant must never
    be auto-declined by /decision — REVIEW or APPROVE only.
    """
    application = base_application(
        CreditScore=0,
        TotalDebtToIncomeRatio=0.20,
        CreditCardUtilizationRate=0.10,
        PreviousLoanDefaults=0,
        BankruptcyHistory=0,
    )
    transaction = base_transaction(LoginAttempts=1)

    response = client.post(
        "/decision",
        json={"application": application, "transaction": transaction},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["thin_file"] is True
    assert body["final_decision"] != "DECLINE"
    assert body["credit_score_used"] is None


def test_thin_file_with_severe_financial_risk_goes_to_review_not_decline():
    application = base_application(
        CreditScore=0,
        TotalDebtToIncomeRatio=0.90,
        BankruptcyHistory=1,
    )
    transaction = base_transaction()

    response = client.post(
        "/decision",
        json={"application": application, "transaction": transaction},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["final_decision"] == "REVIEW"


def test_weak_credit_declines():
    application = base_application(
        CreditScore=350,
        AnnualIncome=15000,
        TotalDebtToIncomeRatio=0.75,
        CreditCardUtilizationRate=0.95,
        PreviousLoanDefaults=2,
        BankruptcyHistory=1,
    )
    transaction = base_transaction()

    response = client.post(
        "/decision",
        json={"application": application, "transaction": transaction},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["credit_strength"] in {"WEAK", "BORDERLINE"}
    assert body["final_decision"] in {"DECLINE", "REVIEW"}


def test_behavior_check_flags_amount_exceeding_balance():
    transaction = base_transaction(TransactionAmount=9000, AccountBalance=1000)

    response = client.post(
        "/behavior/check", json=transaction, headers=AUTH_HEADERS
    )

    assert response.status_code == 200
    body = response.json()
    signal_texts = [s["signal"] for s in body["signals"]]
    assert "Transaction exceeds account balance" in signal_texts
    assert body["behavioral_risk"] in {"MEDIUM", "HIGH"}


def test_behavior_check_high_login_attempts_flagged():
    transaction = base_transaction(LoginAttempts=6)

    response = client.post(
        "/behavior/check", json=transaction, headers=AUTH_HEADERS
    )

    assert response.status_code == 200
    body = response.json()
    signal_texts = [s["signal"] for s in body["signals"]]
    assert "Unusually high login attempts" in signal_texts


def test_weak_payment_history_is_flagged():
    """
    Regression test: PaymentHistory is on an ~8-45 scale in the
    training data, not a 0-1 ratio. A prior bug compared it
    against 0.70, so this concern never fired for any real
    applicant. It must now fire for a genuinely low value.
    """
    application = base_application(PaymentHistory=10)
    transaction = base_transaction()

    response = client.post(
        "/decision",
        json={"application": application, "transaction": transaction},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert "Weak payment history" in body["financial_concerns"]


def test_typical_payment_history_not_flagged():
    application = base_application(PaymentHistory=28)
    transaction = base_transaction()

    response = client.post(
        "/decision",
        json={"application": application, "transaction": transaction},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert "Weak payment history" not in body["financial_concerns"]


def test_fairness_report_available():
    response = client.get("/fairness/report")
    assert response.status_code == 200
    body = response.json()
    assert body["method"] == "four_fifths_rule"
    assert "by_age_group" in body
    assert "by_marital_status" in body


def test_decision_rejects_invalid_payload():
    response = client.post(
        "/decision",
        json={"application": {}, "transaction": base_transaction()},
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 422


def test_decision_requires_api_key():
    response = client.post(
        "/decision",
        json={
            "application": base_application(),
            "transaction": base_transaction(),
        },
    )
    assert response.status_code == 401


def test_decision_rejects_wrong_api_key():
    response = client.post(
        "/decision",
        json={
            "application": base_application(),
            "transaction": base_transaction(),
        },
        headers={"X-API-Key": "not-the-right-key"},
    )
    assert response.status_code == 401


def test_health_and_fairness_report_do_not_require_api_key():
    assert client.get("/health").status_code == 200
    assert client.get("/fairness/report").status_code == 200


def test_applicant_key_cannot_ingest_stream():
    transaction = base_transaction(AccountID="AC-STREAM-RBAC")
    response = client.post(
        "/stream/transaction", json=transaction, headers=AUTH_HEADERS
    )
    assert response.status_code == 403


def test_admin_key_can_ingest_stream_and_baseline_updates_live():
    """
    Real-time claim under test: streamed transactions for the
    SAME new account update that account's baseline in place,
    so repeated events see an incrementing transaction count —
    not a static snapshot recomputed once at startup.
    """
    account_id = "AC-STREAM-LIVE-001"

    first = client.post(
        "/stream/transaction",
        json=base_transaction(AccountID=account_id, TransactionAmount=100),
        headers=ADMIN_HEADERS,
    )
    assert first.status_code == 200
    first_body = first.json()
    assert first_body["account_transaction_count_after_this_event"] == 1

    second = client.post(
        "/stream/transaction",
        json=base_transaction(AccountID=account_id, TransactionAmount=120),
        headers=ADMIN_HEADERS,
    )
    assert second.status_code == 200
    second_body = second.json()
    assert second_body["account_transaction_count_after_this_event"] == 2


def test_live_stream_broadcasts_ingested_transaction():
    url = f"/stream/live?api_key={CREDME_API_KEY_APPLICANT}"
    with client.websocket_connect(url) as websocket:
        response = client.post(
            "/stream/transaction",
            json=base_transaction(AccountID="AC-STREAM-WS-001"),
            headers=ADMIN_HEADERS,
        )
        assert response.status_code == 200

        event = websocket.receive_json()
        assert event["account_id"] == "AC-STREAM-WS-001"


def test_narrative_requires_admin_scope():
    payload = {
        "application": base_application(),
        "transaction": base_transaction(),
    }
    response = client.post(
        "/explain/narrative", json=payload, headers=AUTH_HEADERS
    )
    assert response.status_code == 403


def test_narrative_uses_template_fallback_without_llm_key():
    """
    CREDME_LLM_API_KEY is intentionally unset in this test
    environment. The narrative layer must fall back to the
    deterministic template rather than attempting a live call.
    """
    payload = {
        "application": base_application(),
        "transaction": base_transaction(),
    }
    response = client.post(
        "/explain/narrative", json=payload, headers=ADMIN_HEADERS
    )
    assert response.status_code == 200
    body = response.json()
    narrative = body["narrative_explanation"]
    assert narrative["source"] == "template_fallback"
    assert len(narrative["narrative"]) > 0
    assert narrative["guardrail_violations"] == []


def test_live_stream_rejects_invalid_key():
    from starlette.websockets import WebSocketDisconnect as _WSDisconnect

    with pytest.raises(_WSDisconnect):
        with client.websocket_connect("/stream/live?api_key=not-a-real-key"):
            pass
