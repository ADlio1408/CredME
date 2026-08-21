import os
import joblib
import pandas as pd

from sklearn.ensemble import IsolationForest
from sklearn.preprocessing import StandardScaler


# ============================================================
# CREDME — BEHAVIORAL INTELLIGENCE ENGINE
# ============================================================

print("=" * 70)
print("CREDME — TRAINING BEHAVIORAL INTELLIGENCE MODEL")
print("=" * 70)


# ============================================================
# 1. LOAD TRANSACTION DATA
# ============================================================

df = pd.read_csv(
    "data/bank_transactions_data_2.csv"
)

print(
    f"\nTransaction records: {len(df)}"
)

print(
    f"Unique accounts: "
    f"{df['AccountID'].nunique()}"
)


# ============================================================
# 2. DATE FEATURES
# ============================================================

df["TransactionDate"] = pd.to_datetime(
    df["TransactionDate"]
)

df["PreviousTransactionDate"] = pd.to_datetime(
    df["PreviousTransactionDate"]
)


df["TimeSincePreviousTransaction"] = (
    df["TransactionDate"]
    - df["PreviousTransactionDate"]
).dt.total_seconds() / 3600


df["TransactionHour"] = (
    df["TransactionDate"].dt.hour
)


df["TransactionDayOfWeek"] = (
    df["TransactionDate"].dt.dayofweek
)


# ============================================================
# 3. BEHAVIORAL FEATURES
# ============================================================

# ------------------------------------------------------------
# Transaction amount relative to account balance
# ------------------------------------------------------------

df["AmountToBalanceRatio"] = (
    df["TransactionAmount"]
    /
    (df["AccountBalance"] + 1)
)


# ------------------------------------------------------------
# Amount relative to customer's normal behavior
# ------------------------------------------------------------

account_mean_amount = (
    df.groupby("AccountID")[
        "TransactionAmount"
    ]
    .transform("mean")
)


account_std_amount = (
    df.groupby("AccountID")[
        "TransactionAmount"
    ]
    .transform("std")
)


df["AmountDeviation"] = (
    (
        df["TransactionAmount"]
        - account_mean_amount
    )
    /
    (account_std_amount + 1)
)


# ------------------------------------------------------------
# Transaction frequency
# ------------------------------------------------------------

account_transaction_count = (
    df.groupby("AccountID")[
        "TransactionID"
    ]
    .transform("count")
)


df["AccountTransactionCount"] = (
    account_transaction_count
)


# ------------------------------------------------------------
# Channel frequency
# ------------------------------------------------------------

channel_counts = (
    df.groupby(
        [
            "AccountID",
            "Channel",
        ]
    )["TransactionID"]
    .transform("count")
)


df["AccountChannelFrequency"] = (
    channel_counts
    /
    account_transaction_count
)


# ------------------------------------------------------------
# Device frequency
# ------------------------------------------------------------

device_counts = (
    df.groupby(
        [
            "AccountID",
            "DeviceID",
        ]
    )["TransactionID"]
    .transform("count")
)


df["AccountDeviceFrequency"] = (
    device_counts
    /
    account_transaction_count
)


# ------------------------------------------------------------
# Location frequency
# ------------------------------------------------------------

location_counts = (
    df.groupby(
        [
            "AccountID",
            "Location",
        ]
    )["TransactionID"]
    .transform("count")
)


df["AccountLocationFrequency"] = (
    location_counts
    /
    account_transaction_count
)


# ============================================================
# 4. NUMERIC FEATURES FOR ANOMALY MODEL
# ============================================================

behavior_features = [
    "TransactionAmount",
    "TransactionDuration",
    "LoginAttempts",
    "AccountBalance",
    "CustomerAge",
    "TimeSincePreviousTransaction",
    "TransactionHour",
    "TransactionDayOfWeek",
    "AmountToBalanceRatio",
    "AmountDeviation",
    "AccountTransactionCount",
    "AccountChannelFrequency",
    "AccountDeviceFrequency",
    "AccountLocationFrequency",
]


print(
    "\nBehavioral features:"
)

for feature in behavior_features:

    print(
        f"  - {feature}"
    )


X = df[
    behavior_features
].copy()


# ============================================================
# 5. CLEAN DATA
# ============================================================

X = X.replace(
    [
        float("inf"),
        float("-inf"),
    ],
    pd.NA
)


# ------------------------------------------------------------
# Calculate training medians
# ------------------------------------------------------------
#
# These medians will later be saved and used by the API
# whenever historical behavioral information is unavailable.
#
# ------------------------------------------------------------

feature_medians = (
    X.median(
        numeric_only=True
    )
)


# Fill missing values in model input

X = X.fillna(
    feature_medians
)


# ------------------------------------------------------------
# Also clean the original dataframe used for reporting
# ------------------------------------------------------------
#
# Some accounts have only one transaction, which causes
# standard deviation to become NaN. The model input above
# is already fixed, but we also fix the displayed dataframe
# so the anomaly table does not show NaN.
#
# ------------------------------------------------------------

if "AmountDeviation" in feature_medians.index:

    df["AmountDeviation"] = (
        df["AmountDeviation"]
        .fillna(
            feature_medians[
                "AmountDeviation"
            ]
        )
    )


# ============================================================
# 6. SCALE FEATURES
# ============================================================

print(
    "\nScaling behavioral features..."
)


scaler = StandardScaler()


X_scaled = scaler.fit_transform(
    X
)


# ============================================================
# 7. TRAIN ISOLATION FOREST
# ============================================================

print(
    "\nTraining Isolation Forest..."
)


model = IsolationForest(
    n_estimators=300,

    # Approximately 5% of training observations
    # are expected to be anomalous.
    contamination=0.05,

    random_state=42,

    n_jobs=-1,
)


model.fit(
    X_scaled
)


print(
    "Training complete."
)


# ============================================================
# 8. GENERATE ANOMALY SCORES
# ============================================================

predictions = model.predict(
    X_scaled
)


raw_scores = model.decision_function(
    X_scaled
)


df["BehaviorLabel"] = (
    predictions
)


df["AnomalyScore"] = (
    -raw_scores
)


# ============================================================
# 9. RESULTS
# ============================================================

normal_count = (
    df["BehaviorLabel"] == 1
).sum()


anomaly_count = (
    df["BehaviorLabel"] == -1
).sum()


anomaly_rate = (
    anomaly_count
    /
    len(df)
    *
    100
)


print(
    "\n" + "=" * 70
)

print(
    "BEHAVIORAL MODEL RESULTS"
)

print(
    "=" * 70
)


print(
    f"\nNormal transactions   : "
    f"{normal_count}"
)


print(
    f"Anomalous transactions: "
    f"{anomaly_count}"
)


print(
    f"\nAnomaly rate: "
    f"{anomaly_rate:.2f}%"
)


# ============================================================
# 10. TOP ANOMALIES
# ============================================================

print(
    "\nTOP 10 BEHAVIORAL ANOMALIES"
)

print(
    "-" * 70
)


top_anomalies = (
    df.sort_values(
        "AnomalyScore",
        ascending=False
    )
    [
        [
            "TransactionID",
            "AccountID",
            "TransactionAmount",
            "TransactionType",
            "Location",
            "Channel",
            "DeviceID",
            "LoginAttempts",
            "AccountBalance",
            "AmountDeviation",
            "AnomalyScore",
        ]
    ]
    .head(10)
)


print(
    top_anomalies.to_string(
        index=False
    )
)


# ============================================================
# 11. SAVE MODELS
# ============================================================

os.makedirs(
    "models",
    exist_ok=True
)


# ------------------------------------------------------------
# Isolation Forest
# ------------------------------------------------------------

joblib.dump(
    model,
    "models/behavior_model.joblib"
)


# ------------------------------------------------------------
# StandardScaler
# ------------------------------------------------------------

joblib.dump(
    scaler,
    "models/behavior_scaler.joblib"
)


# ------------------------------------------------------------
# Feature list
# ------------------------------------------------------------

joblib.dump(
    behavior_features,
    "models/behavior_features.joblib"
)


# ------------------------------------------------------------
# Training medians
# ------------------------------------------------------------

joblib.dump(
    feature_medians,
    "models/behavior_feature_medians.joblib"
)


# ============================================================
# 12. DISPLAY SAVED FILES
# ============================================================

print(
    "\n" + "=" * 70
)

print(
    "BEHAVIOR MODEL SAVED"
)

print(
    "=" * 70
)


print(
    "\nmodels/behavior_model.joblib"
)

print(
    "models/behavior_scaler.joblib"
)

print(
    "models/behavior_features.joblib"
)

print(
    "models/behavior_feature_medians.joblib"
)


# ============================================================
# 13. COMPLETE
# ============================================================

print(
    "\n" + "=" * 70
)

print(
    "CREDME BEHAVIORAL MODEL COMPLETE"
)

print(
    "=" * 70
)