import json
import os

import joblib
import numpy as np
import pandas as pd

from sklearn.model_selection import train_test_split


# ============================================================
# CREDME — FAIRNESS / DISPARATE IMPACT AUDIT
# ============================================================
#
# Checks the trained credit model's approval decisions for
# disparate impact across two ECOA-protected bases present in
# the training data: Age and MaritalStatus.
#
# Method: four-fifths rule (a.k.a. 80% rule) — a group's
# approval rate should be at least 80% of the highest-approval
# group's rate. This is a standard adverse-impact screen used
# in US fair-lending / EEOC analysis. It is a screen, not a
# legal conclusion — a failing ratio flags the model for
# further review, it does not by itself prove discrimination.
#
# Uses the SAME train/test split as train_credit_model.py
# (random_state=42, test_size=0.20, stratify=y) so results are
# reproducible against the shipped model.
#
# ============================================================

print("=" * 70)
print("CREDME — FAIRNESS / DISPARATE IMPACT AUDIT")
print("=" * 70)

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ROOT_DIR = os.path.dirname(BASE_DIR)

df = pd.read_csv(os.path.join(ROOT_DIR, "data", "Loan.csv"))

TARGET = "LoanApproved"
y = df[TARGET]

features_to_remove = [
    "LoanApproved",
    "RiskScore",
    "BaseInterestRate",
    "InterestRate",
    "MonthlyLoanPayment",
    "ApplicationDate",
]

X = df.drop(columns=features_to_remove)

if "CreditScore" in X.columns:
    X["CreditScore"] = X["CreditScore"].replace(0, pd.NA)

date = pd.to_datetime(df["ApplicationDate"])
X["ApplicationYear"] = date.dt.year
X["ApplicationMonth"] = date.dt.month
X["ApplicationDayOfWeek"] = date.dt.dayofweek

X_train, X_test, y_train, y_test = train_test_split(
    X, y, test_size=0.20, random_state=42, stratify=y,
)

print(f"\nTest set size: {len(X_test)}")

# ============================================================
# LOAD TRAINED MODEL
# ============================================================

model_path = os.path.join(ROOT_DIR, "models", "credit_model.joblib")
credit_model = joblib.load(model_path)

predictions = credit_model.predict(X_test)
probabilities = credit_model.predict_proba(X_test)[:, 1]

results = X_test.copy()
results["predicted_approved"] = predictions
results["approval_probability"] = probabilities
results["actual_approved"] = y_test.values


def age_bucket(age):
    if age < 25:
        return "<25"
    if age < 40:
        return "25-39"
    if age < 60:
        return "40-59"
    return "60+"


results["AgeGroup"] = results["Age"].apply(age_bucket)


def four_fifths_audit(df_results, group_column):
    group_stats = (
        df_results.groupby(group_column)
        .agg(
            n=("predicted_approved", "size"),
            predicted_approval_rate=("predicted_approved", "mean"),
            actual_approval_rate=("actual_approved", "mean"),
            avg_approval_probability=("approval_probability", "mean"),
        )
        .reset_index()
    )

    max_rate = group_stats["predicted_approval_rate"].max()

    group_stats["disparate_impact_ratio"] = (
        group_stats["predicted_approval_rate"] / max_rate
        if max_rate > 0
        else 0.0
    )

    group_stats["passes_four_fifths_rule"] = (
        group_stats["disparate_impact_ratio"] >= 0.80
    )

    return group_stats


def print_group_stats(title, group_stats, group_column):
    print("\n" + "-" * 70)
    print(title)
    print("-" * 70)

    for _, row in group_stats.iterrows():
        flag = "OK" if row["passes_four_fifths_rule"] else "FLAGGED"

        print(
            f"{row[group_column]:<15} "
            f"n={int(row['n']):<6} "
            f"predicted_approval={row['predicted_approval_rate'] * 100:6.2f}%  "
            f"actual_approval={row['actual_approval_rate'] * 100:6.2f}%  "
            f"disparate_impact_ratio={row['disparate_impact_ratio']:.3f}  "
            f"[{flag}]"
        )


age_stats = four_fifths_audit(results, "AgeGroup")
print_group_stats("APPROVAL RATE BY AGE GROUP", age_stats, "AgeGroup")

marital_stats = four_fifths_audit(results, "MaritalStatus")
print_group_stats(
    "APPROVAL RATE BY MARITAL STATUS", marital_stats, "MaritalStatus"
)

# ============================================================
# SAVE REPORT
# ============================================================

report = {
    "method": "four_fifths_rule",
    "description": (
        "Screens the trained credit model's approval decisions "
        "for disparate impact across Age and Marital Status "
        "(ECOA-protected bases present in the training data). "
        "A group's disparate_impact_ratio should be >= 0.80; "
        "below that, the group is flagged for review. This is "
        "a screen, not a legal determination."
    ),
    "test_set_size": int(len(X_test)),
    "by_age_group": json.loads(
        age_stats.to_json(orient="records")
    ),
    "by_marital_status": json.loads(
        marital_stats.to_json(orient="records")
    ),
    "any_group_flagged": bool(
        (~age_stats["passes_four_fifths_rule"]).any()
        or (~marital_stats["passes_four_fifths_rule"]).any()
    ),
}

report_path = os.path.join(ROOT_DIR, "models", "fairness_report.json")

with open(report_path, "w") as f:
    json.dump(report, f, indent=2)

print("\n" + "=" * 70)
print(f"Fairness report saved to: {report_path}")
print("=" * 70)
