import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

import pytest

from app.ml import score as ml_score
from app import behavior


GOOD_APPLICANT = {
    "age": 40, "annual_income": 120000, "credit_score": 780,
    "employment_status": "Employed", "education_level": "Master",
    "experience": 15, "loan_amount": 15000, "loan_duration": 36,
    "marital_status": "Married", "number_of_dependents": 1,
    "home_ownership_status": "Own", "monthly_debt_payments": 300,
    "credit_card_utilization_rate": 0.1, "number_of_open_credit_lines": 3,
    "number_of_credit_inquiries": 0, "debt_to_income_ratio": 0.08,
    "bankruptcy_history": 0, "loan_purpose": "Home",
    "previous_loan_defaults": 0, "payment_history": 5,
    "length_of_credit_history": 20, "savings_account_balance": 40000,
    "checking_account_balance": 15000, "total_assets": 300000,
    "total_liabilities": 20000, "monthly_income": 10000,
    "utility_bills_payment_history": 0.98, "job_tenure": 10,
    "net_worth": 280000, "base_interest_rate": 0.05, "interest_rate": 0.06,
    "monthly_loan_payment": 450, "total_debt_to_income_ratio": 0.1,
}

RISKY_APPLICANT = {
    **GOOD_APPLICANT,
    "annual_income": 22000, "credit_score": 520,
    "debt_to_income_ratio": 0.75, "total_debt_to_income_ratio": 0.8,
    "credit_card_utilization_rate": 0.95, "previous_loan_defaults": 1,
    "bankruptcy_history": 1, "savings_account_balance": 200,
    "checking_account_balance": 50, "net_worth": -5000,
}


def test_good_applicant_scores_higher_than_risky():
    good = ml_score.score_application(GOOD_APPLICANT)
    risky = ml_score.score_application(RISKY_APPLICANT)
    assert good["approval_probability"] > risky["approval_probability"]
    assert good["credit_intel_score"] > risky["credit_intel_score"]


def test_decision_bucketing_matches_thresholds():
    result = ml_score.score_application(GOOD_APPLICANT)
    assert result["decision"] in {"APPROVE", "REFER", "DECLINE"}
    if result["approval_probability"] >= 0.70:
        assert result["decision"] == "APPROVE"


def test_top_factors_are_ranked_and_bounded():
    result = ml_score.score_application(GOOD_APPLICANT)
    factors = result["top_factors"]
    assert 0 < len(factors) <= 6
    contributions = [f["contribution"] for f in factors]
    assert contributions == sorted(contributions, reverse=True)
    for f in factors:
        assert f["direction"] in {"increases_risk", "decreases_risk"}


def test_behavior_unknown_account_returns_none():
    assert behavior.get_behavior_profile("NOT_A_REAL_ACCOUNT") is None


def test_behavior_known_account_has_bounded_score():
    accounts = behavior.list_accounts()
    profile = behavior.get_behavior_profile(accounts[0])
    assert profile is not None
    assert 0 <= profile["behavioral_trust_score"] <= 100
    assert profile["signals"]["transaction_count"] >= 1


def test_score_application_is_deterministic():
    r1 = ml_score.score_application(GOOD_APPLICANT)
    r2 = ml_score.score_application(GOOD_APPLICANT)
    assert r1["approval_probability"] == r2["approval_probability"]
