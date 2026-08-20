"""
Loads the trained model and turns a validated application into a score
plus a ranked, human-readable list of contributing factors.

Explainability approach: we use feature_importances_ weighted by each
feature's standardized deviation from the training-population mean as a
fast, dependency-light approximation of per-prediction attribution
(similar in spirit to SHAP but without the extra dependency, which is
unavailable in this offline environment). For a production system,
swap this for a proper SHAP TreeExplainer (see README "Next steps") -
the interface (`explain(application_row)`) is designed so that swap is
a one-file change.
"""
import json
import os

import joblib
import numpy as np
import pandas as pd

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
ARTIFACT_DIR = os.path.join(THIS_DIR, "artifacts")
DATA_PATH = os.path.join(THIS_DIR, "..", "..", "data", "Loan.csv")

MODEL_VERSION = "credit-intel-gbc-v1"

_model = None
_scaler = None
_feature_names = None
_feature_importances = None
_train_means = None
_train_stds = None

CATEGORICAL_COLS = [
    "EmploymentStatus",
    "EducationLevel",
    "MaritalStatus",
    "HomeOwnershipStatus",
    "LoanPurpose",
]

# camelCase Loan.csv column <- snake_case API field
FIELD_MAP = {
    "age": "Age",
    "annual_income": "AnnualIncome",
    "credit_score": "CreditScore",
    "employment_status": "EmploymentStatus",
    "education_level": "EducationLevel",
    "experience": "Experience",
    "loan_amount": "LoanAmount",
    "loan_duration": "LoanDuration",
    "marital_status": "MaritalStatus",
    "number_of_dependents": "NumberOfDependents",
    "home_ownership_status": "HomeOwnershipStatus",
    "monthly_debt_payments": "MonthlyDebtPayments",
    "credit_card_utilization_rate": "CreditCardUtilizationRate",
    "number_of_open_credit_lines": "NumberOfOpenCreditLines",
    "number_of_credit_inquiries": "NumberOfCreditInquiries",
    "debt_to_income_ratio": "DebtToIncomeRatio",
    "bankruptcy_history": "BankruptcyHistory",
    "loan_purpose": "LoanPurpose",
    "previous_loan_defaults": "PreviousLoanDefaults",
    "payment_history": "PaymentHistory",
    "length_of_credit_history": "LengthOfCreditHistory",
    "savings_account_balance": "SavingsAccountBalance",
    "checking_account_balance": "CheckingAccountBalance",
    "total_assets": "TotalAssets",
    "total_liabilities": "TotalLiabilities",
    "monthly_income": "MonthlyIncome",
    "utility_bills_payment_history": "UtilityBillsPaymentHistory",
    "job_tenure": "JobTenure",
    "net_worth": "NetWorth",
    "base_interest_rate": "BaseInterestRate",
    "interest_rate": "InterestRate",
    "monthly_loan_payment": "MonthlyLoanPayment",
    "total_debt_to_income_ratio": "TotalDebtToIncomeRatio",
}


def _ensure_loaded():
    global _model, _scaler, _feature_names, _feature_importances, _train_means, _train_stds
    if _model is not None:
        return
    if not os.path.exists(os.path.join(ARTIFACT_DIR, "model.pkl")):
        raise RuntimeError(
            "Model artifacts not found. Run `python -m app.ml.train_model` first."
        )
    _model = joblib.load(os.path.join(ARTIFACT_DIR, "model.pkl"))
    _scaler = joblib.load(os.path.join(ARTIFACT_DIR, "scaler.pkl"))
    with open(os.path.join(ARTIFACT_DIR, "feature_names.json")) as f:
        _feature_names = json.load(f)
    with open(os.path.join(ARTIFACT_DIR, "feature_importances.json")) as f:
        _feature_importances = json.load(f)

    # training-population stats, used to compute how far a given
    # applicant deviates from "typical" on each feature (for explanations)
    df = pd.read_csv(DATA_PATH)
    X = df.drop(columns=["ApplicationDate", "LoanApproved", "RiskScore"])
    X = pd.get_dummies(X, columns=CATEGORICAL_COLS, drop_first=False)
    X = X.reindex(columns=_feature_names, fill_value=0)
    _train_means = X.mean()
    _train_stds = X.std(ddof=0).replace(0, 1)


def _application_to_row(app_dict: dict) -> pd.DataFrame:
    """Converts an API application (snake_case) into the one-hot-encoded
    row shape the model expects."""
    raw = {FIELD_MAP[k]: v for k, v in app_dict.items() if k in FIELD_MAP}
    row = pd.DataFrame([raw])
    row = pd.get_dummies(row, columns=CATEGORICAL_COLS, drop_first=False)
    row = row.reindex(columns=_feature_names, fill_value=0)
    return row


def score_application(app_dict: dict) -> dict:
    _ensure_loaded()
    row = _application_to_row(app_dict)
    row_scaled = _scaler.transform(row)

    proba_approve = float(_model.predict_proba(row_scaled)[0, 1])
    credit_intel_score = round(proba_approve * 100, 1)

    if proba_approve >= 0.70:
        decision = "APPROVE"
    elif proba_approve >= 0.40:
        decision = "REFER"  # send to human underwriter / request more data
    else:
        decision = "DECLINE"

    # Approximate per-applicant attribution: importance * z-score of the
    # applicant's value vs. the training population, so the sign tells us
    # whether this applicant's value pushes them above/below "typical".
    z = (row.iloc[0] - _train_means) / _train_stds
    contributions = []
    for feat, importance in _feature_importances.items():
        if importance <= 0:
            continue
        raw_contribution = importance * z.get(feat, 0.0)
        contributions.append((feat, raw_contribution))

    contributions.sort(key=lambda t: -abs(t[1]))
    top = contributions[:6]

    # Sign convention: features positively correlated with approval in this
    # dataset (income, assets, payment history, credit score) reduce risk
    # when the applicant is above-average; debt/utilization/defaults do
    # the opposite. We approximate direction from correlation sign learned
    # implicitly via z * importance, framed in risk language for the UI.
    risk_reducing_hint = {"TotalDebtToIncomeRatio", "DebtToIncomeRatio", "CreditCardUtilizationRate",
                           "PreviousLoanDefaults", "BankruptcyHistory", "NumberOfCreditInquiries",
                           "MonthlyDebtPayments", "TotalLiabilities", "InterestRate", "BaseInterestRate"}
    top_factors = []
    for feat, contrib in top:
        is_risk_feature = feat in risk_reducing_hint
        # if it's a "bad" feature and applicant is above average (z>0) -> increases risk
        # if it's a "good" feature and applicant is below average (z<0) -> increases risk
        z_val = z.get(feat, 0.0)
        increases_risk = (is_risk_feature and z_val > 0) or (not is_risk_feature and z_val < 0)
        top_factors.append({
            "feature": feat,
            "contribution": round(abs(contrib), 4),
            "direction": "increases_risk" if increases_risk else "decreases_risk",
        })

    return {
        "decision": decision,
        "approval_probability": round(proba_approve, 4),
        "credit_intel_score": credit_intel_score,
        "top_factors": top_factors,
    }
