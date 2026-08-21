"""
Core regression tests for the CredMe decisioning API.

Focus: the behaviors the project's pitch depends on —
thin-file applicants are never auto-declined, the unified
decision endpoint returns a coherent shape, and each risk
tier maps to the expected decision family.
"""

import pytest
from fastapi.testclient import TestClient

from backend.api import app

client = TestClient(app)


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
    response = client.post("/predict", json=base_application())
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
    )

    assert response.status_code == 200
    body = response.json()
    assert body["credit_strength"] in {"WEAK", "BORDERLINE"}
    assert body["final_decision"] in {"DECLINE", "REVIEW"}


def test_behavior_check_flags_amount_exceeding_balance():
    transaction = base_transaction(TransactionAmount=9000, AccountBalance=1000)

    response = client.post("/behavior/check", json=transaction)

    assert response.status_code == 200
    body = response.json()
    signal_texts = [s["signal"] for s in body["signals"]]
    assert "Transaction exceeds account balance" in signal_texts
    assert body["behavioral_risk"] in {"MEDIUM", "HIGH"}


def test_behavior_check_high_login_attempts_flagged():
    transaction = base_transaction(LoginAttempts=6)

    response = client.post("/behavior/check", json=transaction)

    assert response.status_code == 200
    body = response.json()
    signal_texts = [s["signal"] for s in body["signals"]]
    assert "Unusually high login attempts" in signal_texts


def test_decision_rejects_invalid_payload():
    response = client.post(
        "/decision",
        json={"application": {}, "transaction": base_transaction()},
    )
    assert response.status_code == 422
