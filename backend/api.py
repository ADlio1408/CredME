from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import os
import re
import joblib
import shap
import numpy as np
import pandas as pd


# ============================================================
# CREDME API
# REAL-TIME CREDIT INTELLIGENCE PLATFORM
# ============================================================

BASE_DIR = os.path.dirname(
    os.path.dirname(
        os.path.abspath(__file__)
    )
)

MODELS_DIR = os.path.join(
    BASE_DIR,
    "models"
)

DATA_DIR = os.path.join(
    BASE_DIR,
    "data"
)


app = FastAPI(
    title="CredMe API",
    description="Real-Time Credit Intelligence Platform",
    version="1.0.0",
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# MODEL PATHS
# ============================================================

CREDIT_MODEL_PATH = os.path.join(
    MODELS_DIR,
    "credit_model.joblib"
)

CREDIT_METADATA_PATH = os.path.join(
    MODELS_DIR,
    "credit_model_metadata.joblib"
)

BEHAVIOR_MODEL_PATH = os.path.join(
    MODELS_DIR,
    "behavior_model.joblib"
)

BEHAVIOR_SCALER_PATH = os.path.join(
    MODELS_DIR,
    "behavior_scaler.joblib"
)

BEHAVIOR_FEATURES_PATH = os.path.join(
    MODELS_DIR,
    "behavior_features.joblib"
)

BEHAVIOR_MEDIANS_PATH = os.path.join(
    MODELS_DIR,
    "behavior_feature_medians.joblib"
)

TRANSACTION_DATA_PATH = os.path.join(
    DATA_DIR,
    "bank_transactions_data_2.csv"
)


# ============================================================
# LOAD CREDIT MODEL
# ============================================================

print("=" * 70)
print("CREDME API — LOADING MODELS")
print("=" * 70)

credit_model = joblib.load(
    CREDIT_MODEL_PATH
)

credit_preprocessor = (
    credit_model
    .named_steps["preprocessor"]
)

credit_xgb_model = (
    credit_model
    .named_steps["model"]
)

print("Credit model loaded.")


# ============================================================
# LOAD CREDIT MODEL METADATA
# ============================================================

try:

    credit_model_metadata = joblib.load(
        CREDIT_METADATA_PATH
    )

except FileNotFoundError:

    credit_model_metadata = {}

    print(
        "WARNING: credit_model_metadata.joblib "
        "not found."
    )


# ============================================================
# LOAD BEHAVIORAL MODEL
# ============================================================

behavior_model = joblib.load(
    BEHAVIOR_MODEL_PATH
)

behavior_scaler = joblib.load(
    BEHAVIOR_SCALER_PATH
)

behavior_features = joblib.load(
    BEHAVIOR_FEATURES_PATH
)

print("Behavior model loaded.")

print(
    f"Behavior features: {len(behavior_features)}"
)


# ============================================================
# LOAD BEHAVIOR FEATURE MEDIANS
# ============================================================

try:

    behavior_feature_medians = joblib.load(
        BEHAVIOR_MEDIANS_PATH
    )

except FileNotFoundError:

    behavior_feature_medians = None

    print(
        "WARNING: behavior_feature_medians.joblib "
        "not found."
    )


# ============================================================
# LOAD TRANSACTION HISTORY
# ============================================================
#
# IMPORTANT:
#
# The previous API used hard-coded behavioral values:
#
#     TimeSincePreviousTransaction = 24
#     TransactionHour = 14
#     TransactionDayOfWeek = 2
#     AccountTransactionCount = 1
#     ChannelFrequency = 1
#     DeviceFrequency = 1
#     LocationFrequency = 1
#
# This caused the behavioral model to see nearly every
# frontend transaction through the same artificial profile.
#
# We now use the real transaction dataset to construct
# historical behavioral baselines.
#
# ============================================================

transaction_history = pd.read_csv(
    TRANSACTION_DATA_PATH
)

transaction_history[
    "TransactionDate"
] = pd.to_datetime(
    transaction_history["TransactionDate"],
    errors="coerce"
)

transaction_history[
    "PreviousTransactionDate"
] = pd.to_datetime(
    transaction_history["PreviousTransactionDate"],
    errors="coerce"
)


print(
    f"Transaction history loaded: "
    f"{len(transaction_history)} records"
)

print(
    f"Historical accounts: "
    f"{transaction_history['AccountID'].nunique()}"
)


# ============================================================
# PREPARE HISTORICAL BEHAVIORAL BASELINES
# ============================================================

account_transaction_counts = (
    transaction_history
    .groupby("AccountID")
    .size()
    .to_dict()
)


account_mean_amounts = (
    transaction_history
    .groupby("AccountID")["TransactionAmount"]
    .mean()
    .to_dict()
)


account_std_amounts = (
    transaction_history
    .groupby("AccountID")["TransactionAmount"]
    .std()
    .to_dict()
)


account_last_transaction = (
    transaction_history
    .groupby("AccountID")["TransactionDate"]
    .max()
    .to_dict()
)


account_channel_counts = (
    transaction_history
    .groupby(
        ["AccountID", "Channel"]
    )
    .size()
    .to_dict()
)


account_device_counts = (
    transaction_history
    .groupby(
        ["AccountID", "DeviceID"]
    )
    .size()
    .to_dict()
)


account_location_counts = (
    transaction_history
    .groupby(
        ["AccountID", "Location"]
    )
    .size()
    .to_dict()
)


# ============================================================
# POPULATION FALLBACKS
# ============================================================

population_mean_amount = (
    transaction_history[
        "TransactionAmount"
    ].mean()
)

population_std_amount = (
    transaction_history[
        "TransactionAmount"
    ].std()
)

population_median_amount = (
    transaction_history[
        "TransactionAmount"
    ].median()
)

population_median_balance = (
    transaction_history[
        "AccountBalance"
    ].median()
)


# ============================================================
# LOAN APPLICATION INPUT
# ============================================================

class LoanApplication(BaseModel):

    Age: int

    AnnualIncome: float

    CreditScore: float

    EmploymentStatus: str

    EducationLevel: str

    Experience: int

    LoanAmount: float

    LoanDuration: int

    MaritalStatus: str

    NumberOfDependents: int

    HomeOwnershipStatus: str

    MonthlyDebtPayments: float

    TotalDebtToIncomeRatio: float

    CreditCardUtilizationRate: float

    NumberOfOpenCreditLines: int

    NumberOfCreditInquiries: int

    DebtToIncomeRatio: float

    BankruptcyHistory: int

    LoanPurpose: str

    PreviousLoanDefaults: int

    PaymentHistory: float

    LengthOfCreditHistory: int

    SavingsAccountBalance: float

    CheckingAccountBalance: float

    TotalAssets: float

    TotalLiabilities: float

    MonthlyIncome: float

    UtilityBillsPaymentHistory: float

    JobTenure: int

    NetWorth: float


# ============================================================
# TRANSACTION INPUT
# ============================================================

class TransactionInput(BaseModel):

    TransactionAmount: float

    TransactionDuration: float

    LoginAttempts: int

    AccountBalance: float

    CustomerAge: int

    TransactionType: str

    Location: str

    Channel: str

    AccountID: str

    DeviceID: str


# ============================================================
# UNIFIED DECISION INPUT
# ============================================================

class DecisionRequest(BaseModel):

    application: LoanApplication

    transaction: TransactionInput


# ============================================================
# CREDIT DATA PREPARATION
# ============================================================

def prepare_credit_dataframe(
    application: LoanApplication
):

    data = application.model_dump()

    df = pd.DataFrame(
        [data]
    )

    # --------------------------------------------------------
    # THIN-FILE HANDLING
    # --------------------------------------------------------
    #
    # CreditScore = 0 means NO traditional credit history.
    #
    # It is NOT a bad credit score.
    #
    # The supervised dataset contains no thin-file examples,
    # therefore the model prediction is used only as an
    # available credit signal. Final decision logic explicitly
    # prevents thin-file status from causing a decline.
    #
    # --------------------------------------------------------

    df["CreditScore"] = (
        df["CreditScore"]
        .replace(
            0,
            np.nan
        )
    )

    # --------------------------------------------------------
    # Application date features
    # --------------------------------------------------------

    today = pd.Timestamp.today()

    df["ApplicationYear"] = (
        today.year
    )

    df["ApplicationMonth"] = (
        today.month
    )

    df["ApplicationDayOfWeek"] = (
        today.dayofweek
    )

    return df


# ============================================================
# HUMAN READABLE FEATURE NAME
# ============================================================

def clean_feature_name(
    feature
):

    clean_name = feature.replace(
        "numeric__",
        ""
    )

    clean_name = clean_name.replace(
        "categorical__",
        ""
    )

    if "_" in clean_name:

        parts = clean_name.split("_")

        if len(parts) > 1:

            clean_name = (
                parts[0]
                + " - "
                + " ".join(
                    parts[1:]
                )
            )

    clean_name = clean_name.replace(
        "_",
        " "
    )

    clean_name = re.sub(
        r"(?<!^)(?=[A-Z])",
        " ",
        clean_name
    )

    return (
        clean_name
        .strip()
        .title()
    )


# ============================================================
# SHAP CREDIT REASONS
# ============================================================

def get_credit_reasons(
    credit_df
):

    transformed = (
        credit_preprocessor
        .transform(
            credit_df
        )
    )

    feature_names = (
        credit_preprocessor
        .get_feature_names_out()
    )

    explainer = shap.TreeExplainer(
        credit_xgb_model
    )

    shap_values = (
        explainer
        .shap_values(
            transformed
        )
    )

    # --------------------------------------------------------
    # Handle different SHAP output formats
    # --------------------------------------------------------

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

    if len(
        shap_values.shape
    ) == 3:

        shap_values = (
            shap_values[:, :, -1]
        )

    if len(
        shap_values.shape
    ) > 1:

        shap_values = (
            shap_values[0]
        )

    feature_impact = pd.DataFrame(
        {
            "feature": feature_names,
            "impact": shap_values,
        }
    )

    feature_impact[
        "abs_impact"
    ] = (
        feature_impact["impact"]
        .abs()
    )

    top_features = (
        feature_impact
        .sort_values(
            "abs_impact",
            ascending=False
        )
        .head(5)
    )

    reasons = []

    for _, row in (
        top_features.iterrows()
    ):

        feature = row["feature"]

        impact = float(
            row["impact"]
        )

        clean_name = (
            clean_feature_name(
                feature
            )
        )

        if impact > 0:

            effect = (
                "increased approval confidence"
            )

        else:

            effect = (
                "reduced approval confidence"
            )

        reasons.append(
            {
                "feature": clean_name,
                "impact": round(
                    impact,
                    4
                ),
                "effect": effect,
            }
        )

    return reasons


# ============================================================
# HEALTH CHECK
# ============================================================

@app.get("/health")
def health():

    return {
        "status": "healthy",
        "service": "CredMe API",
        "version": "1.0.0",
        "credit_model_loaded": True,
        "behavior_model_loaded": True,
        "transaction_history_loaded": True,
    }


# ============================================================
# CREDIT PREDICTION
# ============================================================

@app.post("/predict")
def predict(
    application: LoanApplication
):

    df = prepare_credit_dataframe(
        application
    )

    probability = (
        credit_model
        .predict_proba(
            df
        )[0][1]
    )

    probability = float(
        probability
    )

    credit_confidence = round(
        probability * 100,
        2
    )

    is_thin_file = (
        float(
            application.CreditScore
        ) == 0
    )

    if is_thin_file:

        decision = "REVIEW"

        risk = "THIN_FILE"

    elif probability >= 0.70:

        decision = "APPROVE"

        risk = "LOW"

    elif probability >= 0.40:

        decision = "REVIEW"

        risk = "MEDIUM"

    else:

        decision = "DECLINE"

        risk = "HIGH"

    reasons = get_credit_reasons(
        df
    )

    return {

        "approval_probability":
            round(
                probability,
                4
            ),

        "credit_confidence":
            credit_confidence,

        "decision":
            decision,

        "risk_level":
            risk,

        "thin_file":
            is_thin_file,

        "reasons":
            reasons,
    }


# ============================================================
# BEHAVIORAL FEATURE PREPARATION
# ============================================================

def prepare_behavior_dataframe(
    transaction: TransactionInput
):

    data = transaction.model_dump()

    df = pd.DataFrame(
        [data]
    )

    account_id = (
        transaction.AccountID
    )

    channel = (
        transaction.Channel
    )

    device_id = (
        transaction.DeviceID
    )

    location = (
        transaction.Location
    )

    # ========================================================
    # ACCOUNT HISTORY
    # ========================================================

    account_count = (
        account_transaction_counts
        .get(
            account_id,
            0
        )
    )

    # ========================================================
    # TIME SINCE PREVIOUS TRANSACTION
    # ========================================================

    last_transaction = (
        account_last_transaction
        .get(
            account_id
        )
    )

    if pd.notna(
        last_transaction
    ):

        current_time = pd.Timestamp.now()

        time_since_previous = (
            current_time
            - last_transaction
        ).total_seconds() / 3600

        # Prevent unrealistic negative values.
        time_since_previous = max(
            0.01,
            time_since_previous
        )

    else:

        # Unknown account:
        # use training median if available.
        time_since_previous = np.nan

    df[
        "TimeSincePreviousTransaction"
    ] = time_since_previous

    # ========================================================
    # CURRENT TIME FEATURES
    # ========================================================

    now = pd.Timestamp.now()

    df[
        "TransactionHour"
    ] = now.hour

    df[
        "TransactionDayOfWeek"
    ] = now.dayofweek

    # ========================================================
    # AMOUNT / BALANCE RATIO
    # ========================================================

    df[
        "AmountToBalanceRatio"
    ] = (
        df[
            "TransactionAmount"
        ]
        /
        (
            df[
                "AccountBalance"
            ]
            + 1
        )
    )

    # ========================================================
    # ACCOUNT AMOUNT DEVIATION
    # ========================================================

    account_mean = (
        account_mean_amounts
        .get(
            account_id,
            population_mean_amount
        )
    )

    account_std = (
        account_std_amounts
        .get(
            account_id,
            population_std_amount
        )
    )

    if pd.isna(
        account_std
    ):

        account_std = (
            population_std_amount
        )

    df[
        "AmountDeviation"
    ] = (
        (
            df[
                "TransactionAmount"
            ]
            - account_mean
        )
        /
        (
            account_std
            + 1
        )
    )

    # ========================================================
    # ACCOUNT TRANSACTION COUNT
    # ========================================================
    #
    # Add the current transaction to the historical count.
    #
    # ========================================================

    df[
        "AccountTransactionCount"
    ] = (
        account_count + 1
    )

    # ========================================================
    # CHANNEL FREQUENCY
    # ========================================================

    historical_channel_count = (
        account_channel_counts
        .get(
            (
                account_id,
                channel
            ),
            0
        )
    )

    df[
        "AccountChannelFrequency"
    ] = (
        historical_channel_count + 1
    ) / (
        account_count + 1
    )

    # ========================================================
    # DEVICE FREQUENCY
    # ========================================================

    historical_device_count = (
        account_device_counts
        .get(
            (
                account_id,
                device_id
            ),
            0
        )
    )

    df[
        "AccountDeviceFrequency"
    ] = (
        historical_device_count + 1
    ) / (
        account_count + 1
    )

    # ========================================================
    # LOCATION FREQUENCY
    # ========================================================

    historical_location_count = (
        account_location_counts
        .get(
            (
                account_id,
                location
            ),
            0
        )
    )

    df[
        "AccountLocationFrequency"
    ] = (
        historical_location_count + 1
    ) / (
        account_count + 1
    )

    # ========================================================
    # SELECT TRAINED FEATURES
    # ========================================================

    X = df[
        behavior_features
    ].copy()

    # ========================================================
    # CLEAN INVALID VALUES
    # ========================================================

    X = X.replace(
        [
            np.inf,
            -np.inf
        ],
        np.nan
    )

    # ========================================================
    # TRAINING MEDIAN IMPUTATION
    # ========================================================

    if (
        behavior_feature_medians
        is not None
    ):

        X = X.fillna(
            behavior_feature_medians
        )

    else:

        X = X.fillna(
            X.median(
                numeric_only=True
            )
        )

    # Final safety fallback

    X = X.fillna(
        0
    )

    return X


# ============================================================
# BEHAVIORAL SIGNAL GENERATION
# ============================================================

def generate_behavior_signals(
    transaction,
    anomaly_detected
):

    signals = []

    amount = float(
        transaction.TransactionAmount
    )

    balance = float(
        transaction.AccountBalance
    )

    # ========================================================
    # TRANSACTION AMOUNT
    # ========================================================

    if amount > balance:

        signals.append(
            {
                "signal":
                    "Transaction exceeds account balance",
                "severity":
                    "HIGH",
            }
        )

    elif amount > balance * 0.50:

        signals.append(
            {
                "signal":
                    "Large transaction relative to balance",
                "severity":
                    "MEDIUM",
            }
        )

    else:

        signals.append(
            {
                "signal":
                    "Transaction amount within balance range",
                "severity":
                    "LOW",
            }
        )

    # ========================================================
    # LOGIN ATTEMPTS
    # ========================================================

    if transaction.LoginAttempts >= 4:

        signals.append(
            {
                "signal":
                    "Unusually high login attempts",
                "severity":
                    "HIGH",
            }
        )

    elif transaction.LoginAttempts >= 2:

        signals.append(
            {
                "signal":
                    "Elevated login attempts",
                "severity":
                    "MEDIUM",
            }
        )

    else:

        signals.append(
            {
                "signal":
                    "Normal login activity",
                "severity":
                    "LOW",
            }
        )

    # ========================================================
    # TRANSACTION DURATION
    # ========================================================

    if (
        transaction.TransactionDuration
        >= 180
    ):

        signals.append(
            {
                "signal":
                    "Unusually long transaction duration",
                "severity":
                    "MEDIUM",
            }
        )

    else:

        signals.append(
            {
                "signal":
                    "Normal transaction duration",
                "severity":
                    "LOW",
            }
        )

    # ========================================================
    # ML ANOMALY
    # ========================================================

    if anomaly_detected:

        signals.append(
            {
                "signal":
                    "ML model detected unusual behavior",
                "severity":
                    "MEDIUM",
            }
        )

    else:

        signals.append(
            {
                "signal":
                    "Behavior consistent with baseline",
                "severity":
                    "LOW",
            }
        )

    return signals


# ============================================================
# BEHAVIORAL RISK CHECK
# ============================================================

@app.post("/behavior/check")
def check_behavior(
    transaction: TransactionInput
):

    X = prepare_behavior_dataframe(
        transaction
    )

    X_scaled = (
        behavior_scaler
        .transform(
            X
        )
    )

    prediction = (
        behavior_model
        .predict(
            X_scaled
        )[0]
    )

    raw_score = (
        behavior_model
        .decision_function(
            X_scaled
        )[0]
    )

    anomaly_detected = bool(
        prediction == -1
    )

    # ========================================================
    # CONVERT RAW SCORE TO 0–100
    # ========================================================

    anomaly_score = max(
        0,
        min(
            100,
            round(
                float(
                    (
                        0.5
                        - raw_score
                    )
                    * 100
                ),
                2
            )
        )
    )

    signals = (
        generate_behavior_signals(
            transaction,
            anomaly_detected
        )
    )

    high_signals = sum(
        1
        for signal in signals
        if signal["severity"] == "HIGH"
    )

    medium_signals = sum(
        1
        for signal in signals
        if signal["severity"] == "MEDIUM"
    )

    # ========================================================
    # CALIBRATED BEHAVIORAL RISK
    # ========================================================

    if high_signals >= 2:

        behavioral_risk = "HIGH"

    elif (
        high_signals >= 1
        and anomaly_detected
    ):

        behavioral_risk = "HIGH"

    elif (
        high_signals >= 1
        or anomaly_detected
        or medium_signals >= 1
    ):

        behavioral_risk = "MEDIUM"

    else:

        behavioral_risk = "LOW"

    return {

        "behavioral_anomaly_score":
            float(
                anomaly_score
            ),

        "behavioral_risk":
            behavioral_risk,

        "anomaly_detected":
            anomaly_detected,

        "raw_anomaly_score":
            round(
                float(
                    raw_score
                ),
                4
            ),

        "signals":
            signals,
    }


# ============================================================
# UNIFIED CREDME DECISION
# ============================================================

@app.post("/decision")
def decision(
    request: DecisionRequest
):

    application = (
        request.application
    )

    transaction = (
        request.transaction
    )

    # ========================================================
    # 1. CREDIT ASSESSMENT
    # ========================================================

    credit_df = (
        prepare_credit_dataframe(
            application
        )
    )

    # ========================================================
    # THIN-FILE DETECTION
    # ========================================================

    is_thin_file = (
        float(
            application.CreditScore
        ) == 0
    )

    # ========================================================
    # CREDIT PROBABILITY
    # ========================================================

    credit_probability = (
        credit_model
        .predict_proba(
            credit_df
        )[0][1]
    )

    credit_probability = float(
        credit_probability
    )

    credit_confidence = round(
        credit_probability * 100,
        2
    )

    # ========================================================
    # CREDIT SHAP
    # ========================================================

    credit_reasons = (
        get_credit_reasons(
            credit_df
        )
    )

    # ========================================================
    # 2. BEHAVIORAL ASSESSMENT
    # ========================================================

    behavior_X = (
        prepare_behavior_dataframe(
            transaction
        )
    )

    behavior_scaled = (
        behavior_scaler
        .transform(
            behavior_X
        )
    )

    behavior_prediction = (
        behavior_model
        .predict(
            behavior_scaled
        )[0]
    )

    behavior_raw_score = (
        behavior_model
        .decision_function(
            behavior_scaled
        )[0]
    )

    anomaly_detected = bool(
        behavior_prediction == -1
    )

    behavioral_anomaly_score = max(
        0,
        min(
            100,
            round(
                float(
                    (
                        0.5
                        - behavior_raw_score
                    )
                    * 100
                ),
                2
            )
        )
    )

    # ========================================================
    # 3. BEHAVIORAL SIGNAL ANALYSIS
    # ========================================================

    high_signals = []

    medium_signals = []

    amount = float(
        transaction.TransactionAmount
    )

    balance = float(
        transaction.AccountBalance
    )

    # --------------------------------------------------------
    # Transaction amount
    # --------------------------------------------------------

    if amount > balance:

        high_signals.append(
            "Transaction exceeds account balance"
        )

    elif amount > balance * 0.50:

        medium_signals.append(
            "Transaction is large relative to account balance"
        )

    # --------------------------------------------------------
    # Login attempts
    # --------------------------------------------------------

    if transaction.LoginAttempts >= 4:

        high_signals.append(
            "Unusually high login attempts"
        )

    elif transaction.LoginAttempts >= 2:

        medium_signals.append(
            "Elevated login attempts"
        )

    # --------------------------------------------------------
    # Transaction duration
    # --------------------------------------------------------

    if (
        transaction.TransactionDuration
        >= 180
    ):

        medium_signals.append(
            "Unusually long transaction duration"
        )

    # --------------------------------------------------------
    # ML anomaly
    # --------------------------------------------------------

    if anomaly_detected:

        medium_signals.append(
            "ML model detected unusual behavior"
        )

    # ========================================================
    # 4. CALIBRATED BEHAVIORAL RISK
    # ========================================================

    if len(high_signals) >= 2:

        behavioral_risk = "HIGH"

    elif (
        len(high_signals) >= 1
        and anomaly_detected
    ):

        behavioral_risk = "HIGH"

    elif (
        len(high_signals) >= 1
        or anomaly_detected
        or len(medium_signals) >= 1
    ):

        behavioral_risk = "MEDIUM"

    else:

        behavioral_risk = "LOW"

    # ========================================================
    # 5. CREDIT STRENGTH
    # ========================================================

    if is_thin_file:

        credit_strength = "THIN_FILE"

    elif credit_confidence >= 70:

        credit_strength = "STRONG"

    elif credit_confidence >= 40:

        credit_strength = "BORDERLINE"

    else:

        credit_strength = "WEAK"

    # ========================================================
    # 6. FINANCIAL RISK SCREEN
    # ========================================================

    financial_concerns = []

    # --------------------------------------------------------
    # Debt burden
    # --------------------------------------------------------

    if (
        application.TotalDebtToIncomeRatio
        >= 0.60
    ):

        financial_concerns.append(
            "High total debt-to-income ratio"
        )

    # --------------------------------------------------------
    # Credit utilization
    # --------------------------------------------------------

    if (
        application.CreditCardUtilizationRate
        >= 0.80
    ):

        financial_concerns.append(
            "High credit utilization"
        )

    # --------------------------------------------------------
    # Previous defaults
    # --------------------------------------------------------

    if (
        application.PreviousLoanDefaults
        > 0
    ):

        financial_concerns.append(
            "Previous loan defaults reported"
        )

    # --------------------------------------------------------
    # Bankruptcy
    # --------------------------------------------------------

    if (
        application.BankruptcyHistory
        > 0
    ):

        financial_concerns.append(
            "Previous bankruptcy history reported"
        )

    # --------------------------------------------------------
    # Payment history
    # --------------------------------------------------------
    #
    # PaymentHistory is NOT a 0-1 ratio. In the training data
    # (data/Loan.csv) it ranges ~8-45, with a 10th percentile
    # of ~18. The previous "< 0.70" threshold assumed a 0-1
    # scale and therefore never fired for any real applicant.
    #
    # --------------------------------------------------------

    if (
        application.PaymentHistory
        < 18
    ):

        financial_concerns.append(
            "Weak payment history"
        )

    # ========================================================
    # 7. FINAL CREDME DECISION
    # ========================================================
    #
    # IMPORTANT:
    #
    # THIN-FILE STATUS ALONE CAN NEVER CAUSE DECLINE.
    #
    # Behavioral anomaly alone also does not automatically
    # cause a decline.
    #
    # ========================================================

    if is_thin_file:

        severe_financial_risk = (
            (
                application.TotalDebtToIncomeRatio
                >= 0.85
            )
            or
            (
                application.CreditCardUtilizationRate
                >= 0.95
            )
            or
            (
                application.PreviousLoanDefaults
                >= 2
            )
            or
            (
                application.BankruptcyHistory
                >= 1
            )
        )

        if severe_financial_risk:

            final_decision = "REVIEW"

        elif (
            behavioral_risk == "HIGH"
            or len(financial_concerns) >= 2
        ):

            final_decision = "REVIEW"

        elif (
            behavioral_risk == "MEDIUM"
            or len(financial_concerns) == 1
        ):

            final_decision = "REVIEW"

        else:

            final_decision = "APPROVE"

    else:

        # ----------------------------------------------------
        # Strong credit
        # ----------------------------------------------------

        if (
            credit_strength == "STRONG"
            and behavioral_risk == "LOW"
            and len(financial_concerns) == 0
        ):

            final_decision = "APPROVE"

        # ----------------------------------------------------
        # Strong credit + behavioral concern
        # ----------------------------------------------------

        elif (
            credit_strength == "STRONG"
            and behavioral_risk
            in [
                "MEDIUM",
                "HIGH"
            ]
        ):

            final_decision = "REVIEW"

        # ----------------------------------------------------
        # Strong credit + significant financial concern
        # ----------------------------------------------------

        elif (
            credit_strength == "STRONG"
            and len(financial_concerns) >= 2
        ):

            final_decision = "REVIEW"

        # ----------------------------------------------------
        # Weak credit
        # ----------------------------------------------------

        elif (
            credit_strength == "WEAK"
        ):

            final_decision = "DECLINE"

        # ----------------------------------------------------
        # Borderline credit
        # ----------------------------------------------------

        elif (
            credit_strength == "BORDERLINE"
        ):

            final_decision = "REVIEW"

        else:

            final_decision = "REVIEW"

    # ========================================================
    # 8. FINAL REASONING
    # ========================================================

    if is_thin_file:

        if final_decision == "APPROVE":

            reasoning = (
                "Applicant has no traditional credit history. "
                "The missing credit score was not treated as a "
                "negative signal. Available financial capacity "
                "and behavioral activity appear acceptable."
            )

        else:

            if (
                behavioral_risk == "HIGH"
                and len(financial_concerns) > 0
            ):

                reasoning = (
                    "Applicant has no traditional credit history. "
                    "The missing credit score was not treated as "
                    "negative; however, financial and behavioral "
                    "risk signals require additional review."
                )

            elif (
                behavioral_risk == "HIGH"
            ):

                reasoning = (
                    "Applicant has no traditional credit history. "
                    "The missing credit score was not treated as "
                    "negative; however, multiple behavioral risk "
                    "signals require additional review."
                )

            elif (
                len(financial_concerns) > 0
            ):

                reasoning = (
                    "Applicant has no traditional credit history. "
                    "The missing credit score was not treated as "
                    "negative, but available financial indicators "
                    "require additional review."
                )

            else:

                reasoning = (
                    "Applicant has no traditional credit history. "
                    "Alternative financial and behavioral signals "
                    "require additional review before lending."
                )

    elif final_decision == "APPROVE":

        reasoning = (
            f"Strong credit profile with "
            f"{credit_confidence}% credit confidence "
            f"and no significant behavioral or financial "
            f"concerns."
        )

    elif final_decision == "DECLINE":

        reasoning = (
            f"Credit confidence is low at "
            f"{credit_confidence}%, indicating a weak "
            f"credit profile that does not meet the "
            f"automatic approval threshold."
        )

    else:

        if (
            behavioral_risk == "HIGH"
            and len(financial_concerns) > 0
        ):

            reasoning = (
                "Credit profile requires additional review "
                "because significant financial and behavioral "
                "risk signals were detected."
            )

        elif (
            behavioral_risk == "HIGH"
        ):

            reasoning = (
                "Credit profile requires additional review "
                "because significant behavioral risk signals "
                "were detected."
            )

        elif (
            behavioral_risk == "MEDIUM"
        ):

            reasoning = (
                f"Credit profile is "
                f"{credit_strength.lower()} with behavioral "
                f"activity that warrants additional review."
            )

        elif (
            len(financial_concerns) > 0
        ):

            reasoning = (
                f"Credit profile is "
                f"{credit_strength.lower()}, but available "
                f"financial indicators warrant additional review."
            )

        else:

            reasoning = (
                f"Credit profile is "
                f"{credit_strength.lower()} and the available "
                f"evidence does not provide enough confidence "
                f"for automatic approval."
            )

    # ========================================================
    # 9. SUMMARY
    # ========================================================

    if is_thin_file:

        credit_summary = (
            "THIN-FILE — no traditional credit history"
        )

    else:

        credit_summary = (
            f"{credit_confidence}% confidence"
        )

    # ========================================================
    # 10. REMOVE DUPLICATES
    # ========================================================

    high_signals = list(
        dict.fromkeys(
            high_signals
        )
    )

    medium_signals = list(
        dict.fromkeys(
            medium_signals
        )
    )

    # ========================================================
    # 11. FINAL RESPONSE
    # ========================================================

    return {

        "final_decision":
            final_decision,

        "reasoning":
            reasoning,

        "credit_confidence":
            credit_confidence,

        "credit_strength":
            credit_strength,

        "thin_file":
            is_thin_file,

        "credit_score_used":
            (
                None
                if is_thin_file
                else application.CreditScore
            ),

        "reasons":
            credit_reasons,

        "behavioral_anomaly_score":
            float(
                behavioral_anomaly_score
            ),

        "behavioral_risk":
            behavioral_risk,

        "anomaly_detected":
            anomaly_detected,

        "high_risk_signals":
            high_signals,

        "medium_risk_signals":
            medium_signals,

        "financial_concerns":
            financial_concerns,

        "thin_file_financial_concerns":
            (
                financial_concerns
                if is_thin_file
                else []
            ),

        "summary": {

            "credit":
                credit_summary,

            "behavior":
                f"{behavioral_risk} behavioral risk",

            "recommendation":
                final_decision,
        },
    }


# ============================================================
# STARTUP MESSAGE
# ============================================================

print("=" * 70)
print("CREDME API READY")
print("=" * 70)

print(
    f"Credit model      : {CREDIT_MODEL_PATH}"
)

print(
    f"Behavior model    : {BEHAVIOR_MODEL_PATH}"
)

print(
    f"Transaction data  : {TRANSACTION_DATA_PATH}"
)

print(
    f"Behavior features : {behavior_features}"
)

print("=" * 70)