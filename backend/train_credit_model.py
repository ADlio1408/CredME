import os
import joblib
import pandas as pd

from sklearn.model_selection import train_test_split
from sklearn.compose import ColumnTransformer
from sklearn.pipeline import Pipeline
from sklearn.preprocessing import OneHotEncoder
from sklearn.impute import SimpleImputer
from sklearn.metrics import (
    accuracy_score,
    precision_score,
    recall_score,
    f1_score,
    roc_auc_score,
    brier_score_loss,
    confusion_matrix,
)

from xgboost import XGBClassifier


# ============================================================
# CREDME — CREDIT DECISION MODEL
# ============================================================

print("=" * 70)
print("CREDME — TRAINING CREDIT DECISION MODEL")
print("=" * 70)


# ============================================================
# 1. LOAD DATA
# ============================================================

df = pd.read_csv(
    "data/Loan.csv"
)

print(
    f"\nDataset shape: {df.shape}"
)


# ============================================================
# 2. TARGET
# ============================================================

TARGET = "LoanApproved"

y = df[TARGET]


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
# 4. THIN-FILE / CREDIT SCORE HANDLING
# ============================================================
#
# CredMe must NOT interpret:
#
#     CreditScore = 0
#
# as:
#
#     "Very poor credit"
#
# Instead:
#
#     CreditScore = 0
#
# means:
#
#     "No traditional credit history / thin file"
#
# Therefore:
#
#     0 -> missing value
#
# The preprocessing pipeline will replace the missing score
# with the median CreditScore from applicants who have a score.
#
# This gives a neutral baseline rather than assigning the
# applicant a terrible credit score.
#
# IMPORTANT:
#
# The current Loan.csv dataset contains no CreditScore = 0
# applicants. Therefore the model cannot learn a dedicated
# thin-file pattern from training data.
#
# Thin-file handling will be performed explicitly during
# inference / decision fusion in the API.
#
# ============================================================

if "CreditScore" in X.columns:

    thin_file_count = (
        X["CreditScore"] == 0
    ).sum()

    credit_history_count = (
        X["CreditScore"] > 0
    ).sum()

    print(
        f"\nThin-file applicants "
        f"(CreditScore = 0): {thin_file_count}"
    )

    print(
        f"Applicants with credit history: "
        f"{credit_history_count}"
    )

    print(
        f"Thin-file percentage: "
        f"{thin_file_count / len(X) * 100:.2f}%"
    )

    if thin_file_count == 0:

        print(
            "\nWARNING:"
        )

        print(
            "Loan.csv contains no thin-file applicants."
        )

        print(
            "The credit model will therefore learn from "
            "traditional-credit applicants only."
        )

        print(
            "Thin-file applicants will be handled as a "
            "separate inference condition rather than "
            "being treated as bad-credit applicants."
        )

    # --------------------------------------------------------
    # Convert artificial zero to missing
    # --------------------------------------------------------

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
# 6. IDENTIFY FEATURE TYPES
# ============================================================

numeric_features = X.select_dtypes(
    include=[
        "int64",
        "float64",
        "int32",
        "float32",
    ]
).columns.tolist()

categorical_features = X.select_dtypes(
    include=[
        "object",
        "str",
        "category",
    ]
).columns.tolist()


print(
    f"\nNumeric features: "
    f"{len(numeric_features)}"
)

print(
    f"Categorical features: "
    f"{len(categorical_features)}"
)

print(
    "\nCategorical columns:"
)

print(
    categorical_features
)

print(
    "\nNumeric columns:"
)

print(
    numeric_features
)


# ============================================================
# 7. TRAIN / TEST SPLIT
# ============================================================

X_train, X_test, y_train, y_test = train_test_split(
    X,
    y,
    test_size=0.20,
    random_state=42,
    stratify=y,
)

print(
    f"\nTraining samples: "
    f"{len(X_train)}"
)

print(
    f"Testing samples:  "
    f"{len(X_test)}"
)


# ============================================================
# 8. PREPROCESSING
# ============================================================

# ------------------------------------------------------------
# Numeric features
# ------------------------------------------------------------
#
# Median imputation is particularly important for CreditScore.
#
# If a thin-file applicant enters:
#
#     CreditScore = 0
#
# it is converted to missing before the pipeline.
#
# The median therefore provides a neutral reference point.
#
# ------------------------------------------------------------

numeric_pipeline = Pipeline(
    steps=[
        (
            "imputer",
            SimpleImputer(
                strategy="median"
            ),
        ),
    ]
)


# ------------------------------------------------------------
# Categorical features
# ------------------------------------------------------------

categorical_pipeline = Pipeline(
    steps=[
        (
            "imputer",
            SimpleImputer(
                strategy="most_frequent"
            ),
        ),
        (
            "encoder",
            OneHotEncoder(
                handle_unknown="ignore",
                sparse_output=False,
            ),
        ),
    ]
)


# ------------------------------------------------------------
# Combined preprocessor
# ------------------------------------------------------------

preprocessor = ColumnTransformer(
    transformers=[
        (
            "numeric",
            numeric_pipeline,
            numeric_features,
        ),
        (
            "categorical",
            categorical_pipeline,
            categorical_features,
        ),
    ]
)


# ============================================================
# 9. XGBOOST CREDIT MODEL
# ============================================================

model = XGBClassifier(
    n_estimators=400,
    max_depth=5,
    learning_rate=0.05,
    subsample=0.85,
    colsample_bytree=0.85,
    objective="binary:logistic",
    eval_metric="logloss",
    random_state=42,
    n_jobs=-1,
)


# ============================================================
# 10. COMPLETE PIPELINE
# ============================================================

pipeline = Pipeline(
    steps=[
        (
            "preprocessor",
            preprocessor,
        ),
        (
            "model",
            model,
        ),
    ]
)


# ============================================================
# 11. TRAIN
# ============================================================

print(
    "\nTraining XGBoost..."
)

pipeline.fit(
    X_train,
    y_train,
)

print(
    "Training complete."
)


# ============================================================
# 12. PREDICTIONS
# ============================================================

predictions = pipeline.predict(
    X_test
)

probabilities = (
    pipeline
    .predict_proba(X_test)[:, 1]
)


# ============================================================
# 13. EVALUATION
# ============================================================

accuracy = accuracy_score(
    y_test,
    predictions,
)

precision = precision_score(
    y_test,
    predictions,
    zero_division=0,
)

recall = recall_score(
    y_test,
    predictions,
    zero_division=0,
)

f1 = f1_score(
    y_test,
    predictions,
    zero_division=0,
)

roc_auc = roc_auc_score(
    y_test,
    probabilities,
)

brier = brier_score_loss(
    y_test,
    probabilities,
)

cm = confusion_matrix(
    y_test,
    predictions,
)


# ============================================================
# 14. DISPLAY MODEL PERFORMANCE
# ============================================================

print(
    "\n" + "=" * 70
)

print(
    "CREDME MODEL PERFORMANCE"
)

print(
    "=" * 70
)

print(
    f"\nAccuracy  : {accuracy:.4f}"
)

print(
    f"Precision : {precision:.4f}"
)

print(
    f"Recall    : {recall:.4f}"
)

print(
    f"F1 Score  : {f1:.4f}"
)

print(
    f"ROC-AUC   : {roc_auc:.4f}"
)

print(
    f"Brier     : {brier:.4f}"
)

print(
    "\nConfusion Matrix:"
)

print(
    cm
)


# ============================================================
# 15. THIN-FILE TEST CHECK
# ============================================================
#
# This section checks whether the test set contains genuine
# thin-file applicants.
#
# Since Loan.csv currently contains zero such applicants,
# this will normally report zero.
#
# This is intentional and transparent.
#
# ============================================================

original_test_credit_scores = df.loc[
    X_test.index,
    "CreditScore"
]

thin_file_test_mask = (
    original_test_credit_scores == 0
)

thin_file_test_count = (
    thin_file_test_mask.sum()
)


print(
    "\n" + "=" * 70
)

print(
    "THIN-FILE APPLICANT ANALYSIS"
)

print(
    "=" * 70
)

print(
    f"\nThin-file test applicants: "
    f"{thin_file_test_count}"
)


if thin_file_test_count > 0:

    thin_file_predictions = (
        predictions[thin_file_test_mask]
    )

    thin_file_probabilities = (
        probabilities[thin_file_test_mask]
    )

    thin_file_actual = (
        y_test[thin_file_test_mask]
    )

    print(
        f"\nActual approval rate: "
        f"{thin_file_actual.mean() * 100:.2f}%"
    )

    print(
        f"Predicted approval rate: "
        f"{thin_file_predictions.mean() * 100:.2f}%"
    )

    print(
        f"Average predicted approval "
        f"probability: "
        f"{thin_file_probabilities.mean() * 100:.2f}%"
    )

else:

    print(
        "\nNo thin-file applicants were present "
        "in the test set."
    )

    print(
        "\nThis does NOT mean CredMe rejects thin-file "
        "applicants."
    )

    print(
        "It means Loan.csv does not contain historical "
        "thin-file examples for supervised training."
    )


# ============================================================
# 16. FEATURE IMPORTANCE
# ============================================================

print(
    "\n" + "=" * 70
)

print(
    "TOP CREDIT MODEL FEATURES"
)

print(
    "=" * 70
)


try:

    trained_model = (
        pipeline
        .named_steps["model"]
    )

    trained_preprocessor = (
        pipeline
        .named_steps["preprocessor"]
    )

    feature_names = (
        trained_preprocessor
        .get_feature_names_out()
    )

    importances = (
        trained_model
        .feature_importances_
    )

    feature_importance = (
        pd.DataFrame(
            {
                "feature": feature_names,
                "importance": importances,
            }
        )
        .sort_values(
            "importance",
            ascending=False,
        )
    )

    print(
        feature_importance
        .head(20)
        .to_string(index=False)
    )

    # --------------------------------------------------------
    # CreditScore importance
    # --------------------------------------------------------

    credit_score_features = (
        feature_importance[
            feature_importance["feature"]
            .str.contains(
                "CreditScore",
                case=False,
                na=False,
            )
        ]
    )

    print(
        "\nCreditScore feature:"
    )

    if len(credit_score_features) > 0:

        print(
            credit_score_features
            .to_string(index=False)
        )

    else:

        print(
            "CreditScore feature not found."
        )


except Exception as e:

    print(
        "\nCould not display "
        f"feature importance: {e}"
    )


# ============================================================
# 17. SAVE MODEL
# ============================================================

os.makedirs(
    "models",
    exist_ok=True,
)

model_path = (
    "models/credit_model.joblib"
)

joblib.dump(
    pipeline,
    model_path,
)

print(
    f"\nModel saved to: "
    f"{model_path}"
)


# ============================================================
# 18. SAVE MODEL METADATA
# ============================================================
#
# The API can use this metadata to understand how the model
# was trained without hard-coding assumptions.
#
# ============================================================

metadata = {
    "target": TARGET,
    "model_type": "XGBoost",
    "training_rows": int(len(X_train)),
    "testing_rows": int(len(X_test)),
    "thin_file_training_examples": int(
        (df["CreditScore"] == 0).sum()
    ),
    "credit_score_zero_means": (
        "No traditional credit history / thin file"
    ),
    "thin_file_handling": (
        "CreditScore=0 is converted to missing "
        "and median-imputed during preprocessing"
    ),
    "thin_file_is_not_automatic_decline": True,
}

joblib.dump(
    metadata,
    "models/credit_model_metadata.joblib",
)

print(
    "Model metadata saved to: "
    "models/credit_model_metadata.joblib"
)


# ============================================================
# 19. COMPLETE
# ============================================================

print(
    "\n" + "=" * 70
)

print(
    "CREDME CREDIT MODEL COMPLETE"
)

print(
    "=" * 70
)