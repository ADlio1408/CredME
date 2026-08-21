"""
Core regression tests for the CredMe decisioning API.

Focus: the behaviors the project's pitch depends on —
thin-file applicants are never auto-declined, the unified
decision endpoint returns a coherent shape, and each risk
tier maps to the expected decision family.
"""

import pytest
from fastapi.testclient import TestClient

from backend.api import CREDME_API_KEY_APPLICANT, app

client = TestClient(app)

AUTH_HEADERS = {"X-API-Key": CREDME_API_KEY_APPLICANT}


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


def test_health_does_not_require_api_key():
    assert client.get("/health").status_code == 200


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


def test_thin_file_with_weak_rent_history_flagged():
    """
    RentPaymentConsistency is an illustrative alternative-data
    signal, only meaningful for thin-file applicants (that's
    exactly the population traditional credit data can't speak
    to). Low consistency should surface as a concern.
    """
    application = base_application(
        CreditScore=0,
        RentPaymentConsistency=0.40,
    )
    transaction = base_transaction()

    response = client.post(
        "/decision",
        json={"application": application, "transaction": transaction},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert (
        "Inconsistent alternative payment history (rent)"
        in body["financial_concerns"]
    )


def test_rent_history_ignored_for_non_thin_file_applicants():
    application = base_application(RentPaymentConsistency=0.10)
    transaction = base_transaction()

    response = client.post(
        "/decision",
        json={"application": application, "transaction": transaction},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert (
        "Inconsistent alternative payment history (rent)"
        not in body["financial_concerns"]
    )


def test_decision_rejects_age_zero():
    application = base_application(Age=0)
    transaction = base_transaction()

    response = client.post(
        "/decision",
        json={"application": application, "transaction": transaction},
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 422


def test_decision_rejects_customer_age_zero():
    application = base_application()
    transaction = base_transaction(CustomerAge=0)

    response = client.post(
        "/decision",
        json={"application": application, "transaction": transaction},
        headers=AUTH_HEADERS,
    )
    assert response.status_code == 422


def test_exact_user_scenario_evaluation():
    """
    Test the exact audit test case:
    Age: 32, AnnualIncome: 78, MonthlyIncome: 7, Debt: 800, CreditScore: 0,
    Loan: 20000, Txn: 150 vs Balance: 80.
    """
    application = base_application(
        Age=32,
        AnnualIncome=78,
        MonthlyIncome=7,
        CreditScore=0,
        LoanAmount=20000,
        LoanDuration=36,
        MonthlyDebtPayments=800,
        TotalDebtToIncomeRatio=114.2857,
        DebtToIncomeRatio=114.2857,
        CreditCardUtilizationRate=0.25,
        PreviousLoanDefaults=0,
        BankruptcyHistory=0,
        RentPaymentConsistency=0.10,
    )
    transaction = base_transaction(
        TransactionAmount=150,
        AccountBalance=80,
        TransactionDuration=60,
        LoginAttempts=1,
        CustomerAge=32,
    )

    response = client.post(
        "/decision",
        json={"application": application, "transaction": transaction},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()

    # Core Decision Checks
    assert body["final_decision"] == "REVIEW"
    assert body["thin_file"] is True
    assert body["credit_strength"] == "THIN_FILE"

    # Layer 1: Credit Intelligence
    assert "credit_intelligence" in body
    assert body["credit_intelligence"]["is_thin_file"] is True
    assert body["credit_intelligence"]["credit_score_used"] is None

    # Layer 2: Financial Intelligence
    assert "financial_intelligence" in body
    assert body["financial_intelligence"]["financial_risk_level"] == "CRITICAL"
    assert body["financial_intelligence"]["dti_status"] == "CRITICAL"
    assert body["financial_intelligence"]["debt_to_income_ratio"] is not None
    assert round(body["financial_intelligence"]["debt_to_income_ratio"], 1) == 114.3

    # Layer 3: Behavioral Intelligence
    assert "behavioral_intelligence" in body
    # Txn 150 > Balance 80 is flagged as a rule check warning
    assert any(
        "exceeds available account balance" in flag
        for flag in body["behavioral_intelligence"]["rule_checks_flagged"]
    )
    assert body["behavioral_risk"] in {"MEDIUM", "HIGH"}

    # Dynamic Reasoning checks: mentions debt/income affordability and transaction overdraft
    assert "Thin-file status alone did not cause the review" in body["reasoning"]


def test_thin_file_healthy_approves():
    """
    A healthy thin-file applicant with good income, low debt, clean behavioral signals
    should be APPROVED.
    """
    application = base_application(
        Age=28,
        AnnualIncome=720000,
        MonthlyIncome=60000,
        CreditScore=0,
        LoanAmount=40000,
        LoanDuration=12,
        MonthlyDebtPayments=2000,
        TotalDebtToIncomeRatio=0.033,
        DebtToIncomeRatio=0.033,
        CreditCardUtilizationRate=0.10,
        PreviousLoanDefaults=0,
        BankruptcyHistory=0,
        PaymentHistory=30,
        RentPaymentConsistency=1.0,
    )
    transaction = base_transaction(
        TransactionAmount=500,
        AccountBalance=50000,
        TransactionDuration=45,
        LoginAttempts=1,
        CustomerAge=28,
    )

    response = client.post(
        "/decision",
        json={"application": application, "transaction": transaction},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["thin_file"] is True
    assert body["final_decision"] == "APPROVE"
    assert body["financial_intelligence"]["financial_risk_level"] == "LOW"


def test_zero_income_safety():
    """
    Test that 0 monthly income with positive debt obligations does not crash with ZeroDivisionError
    and is flagged safely.
    """
    application = base_application(
        MonthlyIncome=0,
        AnnualIncome=0,
        MonthlyDebtPayments=500,
    )
    transaction = base_transaction()

    response = client.post(
        "/decision",
        json={"application": application, "transaction": transaction},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["financial_intelligence"]["dti_status"] == "CRITICAL"
    assert any("Zero reported income" in c for c in body["financial_concerns"])


def test_rent_and_utilization_api_handling():
    """
    Test that decimal representations for RentPaymentConsistency (0.90) and CreditCardUtilizationRate (0.25)
    are handled correctly by the Decision and Financial engines.
    """
    application = base_application(
        RentPaymentConsistency=0.90,
        CreditCardUtilizationRate=0.25,
        CreditScore=0,
    )
    transaction = base_transaction()

    response = client.post(
        "/decision",
        json={"application": application, "transaction": transaction},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert any("Rent Payment Consistency: 90%" in ctx for ctx in body["thin_file_context"])
    # 25% utilization is low and should not generate high utilization warning
    assert not any("High credit utilization" in c for c in body["financial_concerns"])


def test_transaction_exceeds_balance_flagged_without_claiming_fraud():
    """
    Test that transaction amount exceeding account balance is cleanly flagged as an account rule check,
    without claiming fraud or asserting an ML anomaly if Isolation Forest is normal.
    """
    application = base_application()
    transaction = base_transaction(
        TransactionAmount=75000,
        AccountBalance=50000,
    )

    response = client.post(
        "/decision",
        json={"application": application, "transaction": transaction},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    rule_checks = body["behavioral_intelligence"]["transaction_rule_checks"]
    assert any("Transaction amount (₹75,000) exceeds available account balance (₹50,000)." in r for r in rule_checks)
    # Ensure no false claim of fraud in output reasoning or summary
    assert "fraud" not in body["reasoning"].lower()


def test_new_default_demo_profile_evaluation():
    """
    Test evaluation of the realistic new default demo profile:
    Age 32, Annual ₹7,50,000, Monthly ₹62,500, Debt ₹8,000 (DTI 12.8%),
    CreditScore 0 (Thin-file), Loan ₹2,00,000 (36 mo), Rent 90%, Txn ₹75,000 vs Bal ₹50,000.
    """
    application = base_application(
        Age=32,
        AnnualIncome=750000,
        MonthlyIncome=62500,
        MonthlyDebtPayments=8000,
        TotalDebtToIncomeRatio=0.128,
        DebtToIncomeRatio=0.128,
        LoanAmount=200000,
        LoanDuration=36,
        CreditScore=0,
        RentPaymentConsistency=0.90,
        CreditCardUtilizationRate=0.25,
        SavingsAccountBalance=150000,
        CheckingAccountBalance=50000,
        TotalAssets=500000,
        TotalLiabilities=200000,
        NetWorth=300000,
    )
    transaction = base_transaction(
        TransactionAmount=75000,
        AccountBalance=50000,
        TransactionDuration=60,
        LoginAttempts=1,
        CustomerAge=32,
    )

    response = client.post(
        "/decision",
        json={"application": application, "transaction": transaction},
        headers=AUTH_HEADERS,
    )

    assert response.status_code == 200
    body = response.json()
    assert body["thin_file"] is True
    assert body["financial_intelligence"]["financial_risk_level"] == "LOW"
    assert body["financial_intelligence"]["debt_to_income_ratio"] == 0.128
    assert len(body["behavioral_intelligence"]["transaction_rule_checks"]) == 1
    assert "Transaction amount (₹75,000) exceeds available account balance (₹50,000)." in body["behavioral_intelligence"]["transaction_rule_checks"][0]
    # Because of the transaction rule check (₹75,000 > ₹50,000), thin-file routes to REVIEW
    assert body["final_decision"] == "REVIEW"




