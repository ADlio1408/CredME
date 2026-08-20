"""
Trains the traditional credit-risk model on Loan.csv.

Design notes
------------
- GradientBoosting/RandomForest chosen over a black-box net: for a lending
  use case, feature_importances_ + per-feature contribution give us
  explainability out of the box, which regulated credit decisions require.
- We predict LoanApproved (binary) with predict_proba, then derive a
  0-100 "CreditIntelScore" from the probability. RiskScore in the source
  data is kept only as a validation signal, not as a training feature
  (it would leak the label).
- Artifacts (model, scaler, feature list, feature importances) are written
  to backend/app/ml/artifacts/ so the API can load them without retraining.

Run:
    python -m app.ml.train_model
"""
import json
import os

import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import GradientBoostingClassifier
from sklearn.metrics import classification_report, roc_auc_score
from sklearn.model_selection import train_test_split
from sklearn.preprocessing import StandardScaler

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
ARTIFACT_DIR = os.path.join(THIS_DIR, "artifacts")
DATA_PATH = os.path.join(THIS_DIR, "..", "..", "data", "Loan.csv")

# Columns that would leak the label or are pure metadata -> excluded from training
DROP_COLS = ["ApplicationDate", "LoanApproved", "RiskScore"]
CATEGORICAL_COLS = [
    "EmploymentStatus",
    "EducationLevel",
    "MaritalStatus",
    "HomeOwnershipStatus",
    "LoanPurpose",
]


def load_and_prepare():
    df = pd.read_csv(DATA_PATH)
    y = df["LoanApproved"].astype(int)

    X = df.drop(columns=DROP_COLS)
    X = pd.get_dummies(X, columns=CATEGORICAL_COLS, drop_first=False)

    feature_names = list(X.columns)
    return X, y, feature_names


def train():
    os.makedirs(ARTIFACT_DIR, exist_ok=True)
    X, y, feature_names = load_and_prepare()

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42, stratify=y
    )

    scaler = StandardScaler()
    X_train_scaled = scaler.fit_transform(X_train)
    X_test_scaled = scaler.transform(X_test)

    clf = GradientBoostingClassifier(
        n_estimators=200,
        max_depth=3,
        learning_rate=0.08,
        random_state=42,
    )
    clf.fit(X_train_scaled, y_train)

    y_pred = clf.predict(X_test_scaled)
    y_proba = clf.predict_proba(X_test_scaled)[:, 1]

    print(classification_report(y_test, y_pred, target_names=["Denied", "Approved"]))
    auc = roc_auc_score(y_test, y_proba)
    print(f"ROC-AUC: {auc:.4f}")

    importances = dict(zip(feature_names, clf.feature_importances_.tolist()))
    importances = dict(sorted(importances.items(), key=lambda kv: -kv[1]))

    joblib.dump(clf, os.path.join(ARTIFACT_DIR, "model.pkl"))
    joblib.dump(scaler, os.path.join(ARTIFACT_DIR, "scaler.pkl"))
    with open(os.path.join(ARTIFACT_DIR, "feature_names.json"), "w") as f:
        json.dump(feature_names, f, indent=2)
    with open(os.path.join(ARTIFACT_DIR, "feature_importances.json"), "w") as f:
        json.dump(importances, f, indent=2)
    with open(os.path.join(ARTIFACT_DIR, "metrics.json"), "w") as f:
        json.dump({"roc_auc": auc, "n_train": len(X_train), "n_test": len(X_test)}, f, indent=2)

    print(f"Artifacts written to {ARTIFACT_DIR}")


if __name__ == "__main__":
    train()
