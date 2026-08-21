import joblib
import pandas as pd
import shap


# ============================================================
# CREDME — MODEL EXPLAINABILITY
# ============================================================

print("=" * 70)
print("CREDME — MODEL EXPLAINABILITY")
print("=" * 70)


# ============================================================
# 1. LOAD DATASET
# ============================================================

df = pd.read_csv(
    "data/Loan.csv"
)


# ============================================================
# 2. TARGET
# ============================================================

target = "LoanApproved"


# ============================================================
# 3. REMOVE TARGET / LEAKAGE FEATURES
# ============================================================

features_to_remove = [
    "LoanApproved",
    "RiskScore",
    "BaseInterestRate",
    "InterestRate",
    "MonthlyLoanPayment",
    "ApplicationDate",
]


X = df.drop(
    columns=features_to_remove
)


# ============================================================
# 4. HANDLE THIN-FILE APPLICANTS
# ============================================================
#
# This MUST match train_credit_model.py.
#
# CreditScore = 0 means:
#
#     No traditional credit history / thin file
#
# It does NOT mean:
#
#     Extremely poor credit
#
# Therefore:
#
# HasCreditHistory = 0
# CreditScore      = missing
#
# ============================================================

if "CreditScore" in X.columns:

    X["HasCreditHistory"] = (
        X["CreditScore"] > 0
    ).astype(int)

    X["CreditScore"] = (
        X["CreditScore"]
        .replace(0, pd.NA)
    )


# ============================================================
# 5. CREATE DATE FEATURES
# ============================================================

date = pd.to_datetime(
    df["ApplicationDate"]
)


X["ApplicationYear"] = (
    date.dt.year
)


X["ApplicationMonth"] = (
    date.dt.month
)


X["ApplicationDayOfWeek"] = (
    date.dt.dayofweek
)


# ============================================================
# 6. LOAD TRAINED CREDIT PIPELINE
# ============================================================

pipeline = joblib.load(
    "models/credit_model.joblib"
)


# ============================================================
# 7. GET PREPROCESSOR + XGBOOST MODEL
# ============================================================

preprocessor = (
    pipeline
    .named_steps["preprocessor"]
)


model = (
    pipeline
    .named_steps["model"]
)


# ============================================================
# 8. TRANSFORM DATA
# ============================================================

X_transformed = (
    preprocessor.transform(X)
)


# ============================================================
# 9. GET PROCESSED FEATURE NAMES
# ============================================================

feature_names = (
    preprocessor
    .get_feature_names_out()
)


print(
    f"\nOriginal features: "
    f"{X.shape[1]}"
)


print(
    f"Processed features: "
    f"{X_transformed.shape[1]}"
)


# ============================================================
# 10. SHAP TREE EXPLAINER
# ============================================================

print(
    "\nCreating SHAP TreeExplainer..."
)


explainer = shap.TreeExplainer(
    model
)


# ============================================================
# 11. EXPLAIN SAMPLE
# ============================================================
#
# We only use 100 rows to keep the explainability analysis
# fast while still providing a useful global overview.
#
# ============================================================

sample = (
    X_transformed[:100]
)


shap_values = (
    explainer.shap_values(
        sample
    )
)


# ============================================================
# 12. HANDLE SHAP OUTPUT
# ============================================================
#
# XGBoost / SHAP versions can return slightly different
# output shapes.
#
# For binary classification we want the SHAP values
# corresponding to the positive class.
#
# ============================================================

if isinstance(
    shap_values,
    list
):

    shap_values = (
        shap_values[-1]
    )


if hasattr(
    shap_values,
    "values"
):

    shap_values = (
        shap_values.values
    )


# If SHAP returns an additional output dimension,
# reduce it to the positive-class explanation.

if len(
    shap_values.shape
) == 3:

    shap_values = (
        shap_values[:, :, -1]
    )


# ============================================================
# 13. GLOBAL FEATURE IMPORTANCE
# ============================================================

importance = pd.DataFrame(
    {
        "feature": feature_names,

        "importance": (
            abs(shap_values)
            .mean(axis=0)
        ),
    }
)


importance = (
    importance
    .sort_values(
        "importance",
        ascending=False,
    )
)


# ============================================================
# 14. DISPLAY TOP FEATURES
# ============================================================

print(
    "\nTOP 20 CREDIT DECISION FEATURES"
)

print(
    "=" * 70
)


print(
    importance
    .head(20)
    .to_string(
        index=False
    )
)


# ============================================================
# 15. CHECK THIN-FILE FEATURE
# ============================================================

print(
    "\n" + "=" * 70
)

print(
    "THIN-FILE FEATURE CHECK"
)

print(
    "=" * 70
)


thin_file_features = (
    importance[
        importance["feature"]
        .str.contains(
            "HasCreditHistory",
            case=False,
            na=False,
        )
    ]
)


if len(
    thin_file_features
) > 0:

    print(
        "\nHasCreditHistory SHAP importance:"
    )

    print(
        thin_file_features
        .to_string(
            index=False
        )
    )

else:

    print(
        "\nHasCreditHistory was not "
        "found in the processed features."
    )


# ============================================================
# 16. CHECK CREDIT SCORE FEATURE
# ============================================================

credit_score_features = (
    importance[
        importance["feature"]
        .str.contains(
            "CreditScore",
            case=False,
            na=False,
        )
    ]
)


print(
    "\nCreditScore-related SHAP features:"
)


if len(
    credit_score_features
) > 0:

    print(
        credit_score_features
        .to_string(
            index=False
        )
    )

else:

    print(
        "No CreditScore feature found."
    )


# ============================================================
# 17. COMPLETE
# ============================================================

print(
    "\n" + "=" * 70
)

print(
    "EXPLAINABILITY ANALYSIS COMPLETE"
)

print(
    "=" * 70
)