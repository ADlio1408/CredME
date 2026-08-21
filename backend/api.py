from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import APIKeyHeader
from pydantic import BaseModel, Field as PydanticField, field_validator

import os
import re


import joblib
import shap  # pyright: ignore[reportMissingImports] # type: ignore
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
# API KEY AUTH — ROLE / SCOPE BASED
# ============================================================
#
# Two roles, each a distinct API key mapped to an explicit set
# of scopes:
#
#   - "applicant" — the public-facing role the frontend uses.
#     Can request assessments, nothing else.
#
#   - "admin"     — internal/reviewer role. Everything the
#     applicant role can do, plus operator-only endpoints
#     (live transaction ingestion, LLM narrative generation).
#
# Keys are read from environment variables — never hardcoded.
# If unset, the API falls back to published, clearly-labeled
# development keys so the prototype still runs out of the box
# locally; these fallbacks are NOT suitable for any shared or
# public deployment.
#
# ============================================================

API_KEY_HEADER_NAME = "X-API-Key"

DEV_FALLBACK_APPLICANT_KEY = "credme-dev-applicant-key"

DEV_FALLBACK_ADMIN_KEY = "credme-dev-admin-key"

APPLICANT_SCOPES = {"decision"}

ADMIN_SCOPES = APPLICANT_SCOPES

CREDME_API_KEY_APPLICANT = os.environ.get(
    "CREDME_API_KEY_APPLICANT",
    DEV_FALLBACK_APPLICANT_KEY,
)

CREDME_API_KEY_ADMIN = os.environ.get(
    "CREDME_API_KEY_ADMIN",
    DEV_FALLBACK_ADMIN_KEY,
)

if CREDME_API_KEY_APPLICANT == DEV_FALLBACK_APPLICANT_KEY:

    print(
        "WARNING: CREDME_API_KEY_APPLICANT is not set. Using "
        "the published development fallback key."
    )

if CREDME_API_KEY_ADMIN == DEV_FALLBACK_ADMIN_KEY:

    print(
        "WARNING: CREDME_API_KEY_ADMIN is not set. Using the "
        "published development fallback key."
    )

API_KEY_SCOPES = {
    CREDME_API_KEY_APPLICANT: APPLICANT_SCOPES,
    CREDME_API_KEY_ADMIN: ADMIN_SCOPES,
}

_api_key_header = APIKeyHeader(
    name=API_KEY_HEADER_NAME,
    auto_error=False,
)


def require_scope(scope_name):

    def _dependency(
        api_key: str = Depends(_api_key_header)
    ):

        scopes = API_KEY_SCOPES.get(api_key)

        if scopes is None:

            raise HTTPException(
                status_code=401,
                detail=(
                    "Missing or invalid API key. "
                    f"Provide the '{API_KEY_HEADER_NAME}' "
                    "header."
                ),
            )

        if scope_name not in scopes:

            raise HTTPException(
                status_code=403,
                detail=(
                    "This API key does not have the "
                    f"'{scope_name}' scope."
                ),
            )

        return api_key

    return _dependency


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

    Age: int = PydanticField(..., gt=0, description="Applicant age must be greater than 0")

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

    # --------------------------------------------------------
    # ALTERNATIVE DATA (illustrative)
    # --------------------------------------------------------
    #
    # Not sourced from any real bureau/landlord/telecom feed —
    # this field exists to demonstrate how a genuine alternative-
    # data signal would plug into the thin-file decision path,
    # per the "multi-modal" / NTC goal of the problem statement.
    # Optional and additive: omitting it changes nothing.
    #
    # --------------------------------------------------------

    RentPaymentConsistency: float | None = None

    @field_validator("Age")
    @classmethod
    def validate_applicant_age(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Age cannot be 0 or negative. A valid applicant age is required.")
        return v


# ============================================================
# TRANSACTION INPUT
# ============================================================

class TransactionInput(BaseModel):

    TransactionAmount: float

    TransactionDuration: float

    LoginAttempts: int

    AccountBalance: float

    CustomerAge: int = PydanticField(..., gt=0, description="Customer age must be greater than 0")

    TransactionType: str

    Location: str

    Channel: str

    AccountID: str

    DeviceID: str

    @field_validator("CustomerAge")
    @classmethod
    def validate_customer_age(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("CustomerAge cannot be 0 or negative. A valid age is required.")
        return v


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

    total_abs_impact = float(
        top_features["abs_impact"].sum()
    )

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

        if total_abs_impact > 0:

            pct = (
                impact
                / total_abs_impact
            ) * 100.0

        else:

            pct = 0.0

        if impact > 0:

            effect = (
                "Increases approval likelihood"
            )

        else:

            effect = (
                "Decreases approval likelihood"
            )

        reasons.append(
            {
                "feature": clean_name,
                "relative_contribution_pct": round(abs(pct), 1),
                "impact": round(pct, 1),
                "direction": effect,
                "effect": effect,
                "raw_shap_impact": round(impact, 4),
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
# CONFIGURABLE UNDERWRITING POLICY THRESHOLDS
# ============================================================
# Note: These are institution-level risk policy bands (not ML-calibrated cutoffs):
POLICY_APPROVAL_PROBABILITY_THRESHOLD = 70.0  # Min predicted approval prob for approval eligibility
POLICY_DECLINE_PROBABILITY_THRESHOLD = 40.0   # Max predicted approval prob below which traditional credit declines


# ============================================================
# 1. CREDIT INTELLIGENCE ENGINE
# ============================================================

def evaluate_credit_intelligence(application: LoanApplication):
    """
    Evaluates applicant creditworthiness via the XGBoost model and SHAP explainability.
    Distinguishes established credit history from thin-file (New-to-Credit) uncertainty.
    
    Thin-File Imputation Context:
    When CreditScore = 0 (thin file), it is converted to NaN and imputed to the population
    median (~650) as a neutral baseline input representation for XGBoost. Thin-file uncertainty
    is separately preserved as policy context and evaluated in the Decision Engine.
    """
    credit_df = prepare_credit_dataframe(application)
    is_thin_file = bool(float(application.CreditScore) == 0)

    # Raw predicted probability of approval P(Approved=1) from XGBoost
    credit_probability = float(credit_model.predict_proba(credit_df)[0][1])
    predicted_approval_prob = round(credit_probability * 100, 2)

    credit_reasons = get_credit_reasons(credit_df)

    if is_thin_file:
        credit_strength = "THIN_FILE"
        history_note = (
            "Limited traditional credit history on record (New-to-Credit). "
            "Missing bureau score is represented using a baseline population median (~650) for model input, "
            "while thin-file uncertainty is separately retained and evaluated in policy context."
        )
    elif predicted_approval_prob >= POLICY_APPROVAL_PROBABILITY_THRESHOLD:
        credit_strength = "STRONG"
        history_note = "Established credit history with strong predicted loan approval likelihood."
    elif predicted_approval_prob >= POLICY_DECLINE_PROBABILITY_THRESHOLD:
        credit_strength = "BORDERLINE"
        history_note = "Established credit history with borderline repayment indicators."
    else:
        credit_strength = "WEAK"
        history_note = "Established credit history with weak predicted approval probability."

    return {
        "is_thin_file": is_thin_file,
        "predicted_approval_probability": predicted_approval_prob,
        "model_approval_probability": predicted_approval_prob,
        "credit_confidence": predicted_approval_prob,  # Kept for backward compatibility
        "credit_strength": credit_strength,
        "credit_history_status": "THIN_FILE" if is_thin_file else "ESTABLISHED_CREDIT",
        "credit_history_note": history_note,
        "credit_reasons": credit_reasons,
        "credit_score_used": None if is_thin_file else float(application.CreditScore),
    }


# ============================================================
# 2. FINANCIAL RISK ENGINE
# ============================================================

def evaluate_financial_risk(application: LoanApplication, is_thin_file: bool):
    """
    Evaluates affordability, repayment capacity, and debt obligations independently
    from the credit ML model.
    """
    financial_concerns = []

    # 1. Income & DTI calculation (safe against zero/missing income)
    monthly_income = float(application.MonthlyIncome) if application.MonthlyIncome else 0.0
    annual_income = float(application.AnnualIncome) if application.AnnualIncome else 0.0

    if monthly_income <= 0 and annual_income > 0:
        monthly_income = annual_income / 12.0

    monthly_debt = float(application.MonthlyDebtPayments) if application.MonthlyDebtPayments else 0.0
    loan_amount = float(application.LoanAmount) if application.LoanAmount else 0.0

    if monthly_income > 0:
        dti = monthly_debt / monthly_income
    elif monthly_debt > 0:
        dti = float("inf")
    else:
        dti = 0.0

    # 2. Debt burden & affordability tiers
    if dti == float("inf"):
        financial_concerns.append("Zero reported income with ongoing monthly debt obligations (Undefined DTI).")
        dti_status = "CRITICAL"
    elif dti >= 1.0:
        financial_concerns.append(
            f"Critical debt-to-income burden ({dti * 100:,.1f}%): Monthly debt obligations (₹{monthly_debt:,.0f}) "
            f"exceed total monthly income (₹{monthly_income:,.0f}) by {dti:,.1f}x."
        )
        dti_status = "CRITICAL"
    elif dti >= 0.50:
        financial_concerns.append(
            f"High debt-to-income ratio ({dti * 100:,.1f}%): Monthly debt obligations consume over half of monthly income."
        )
        dti_status = "HIGH"
    elif dti >= 0.36:
        dti_status = "MODERATE"
    else:
        dti_status = "HEALTHY"

    # 3. Monthly cash flow solvency
    monthly_cash_flow = monthly_income - monthly_debt
    if monthly_cash_flow < 0 and dti < 1.0:
        financial_concerns.append(
            f"Negative monthly cash flow: Monthly debt obligations of ₹{monthly_debt:,.0f} exceed monthly income of ₹{monthly_income:,.0f}."
        )

    # 4. Income level viability & loan exposure
    if annual_income > 0 and annual_income < 1000:
        financial_concerns.append(
            f"Nominal income profile: Reported annual income (₹{annual_income:,.0f}) is severely insufficient to support requested loan of ₹{loan_amount:,.0f}."
        )
    elif annual_income > 0 and loan_amount > (annual_income * 2):
        financial_concerns.append(
            f"High loan-to-income exposure: Requested loan (₹{loan_amount:,.0f}) is {loan_amount / annual_income:.1f}x total annual income (₹{annual_income:,.0f})."
        )

    # 5. Revolving credit utilization
    utilization = float(application.CreditCardUtilizationRate or 0)
    if utilization >= 0.80:
        financial_concerns.append(f"High credit utilization ({utilization * 100:.0f}%).")

    # 6. Repayment track record
    if int(application.PreviousLoanDefaults or 0) > 0:
        financial_concerns.append(f"Previous loan defaults reported ({application.PreviousLoanDefaults} default(s) on record).")

    if int(application.BankruptcyHistory or 0) > 0:
        financial_concerns.append("Previous bankruptcy history reported.")

    if float(application.PaymentHistory or 0) < 18:
        financial_concerns.append("Weak payment history")

    # 7. Alternative data (Rent payment consistency — evaluated only for thin file)
    if (
        is_thin_file
        and application.RentPaymentConsistency is not None
        and float(application.RentPaymentConsistency) < 0.70
    ):
        financial_concerns.append("Inconsistent alternative payment history (rent)")

    # Deduplicate non-redundantly while preserving order
    financial_concerns = list(dict.fromkeys(financial_concerns))

    # Determine overall financial risk level
    if dti_status == "CRITICAL" or (annual_income > 0 and annual_income < 1000) or int(application.PreviousLoanDefaults or 0) >= 2 or int(application.BankruptcyHistory or 0) >= 1:
        financial_risk_level = "CRITICAL"
    elif dti_status == "HIGH" or utilization >= 0.80 or len(financial_concerns) >= 2:
        financial_risk_level = "HIGH"
    elif dti_status == "MODERATE" or len(financial_concerns) == 1:
        financial_risk_level = "MEDIUM"
    else:
        financial_risk_level = "LOW"

    return {
        "financial_risk_level": financial_risk_level,
        "debt_to_income_ratio": None if dti == float("inf") else round(dti, 4),
        "dti_percentage": None if dti == float("inf") else round(dti * 100, 2),
        "dti_status": dti_status,
        "monthly_cash_flow": monthly_cash_flow,
        "financial_risk_factors": financial_concerns,
    }


# ============================================================
# 3. BEHAVIORAL INTELLIGENCE ENGINE
# ============================================================

def evaluate_behavioral_intelligence(transaction: TransactionInput):
    """
    Evaluates real-time transaction activity.
    Clearly separates ML Anomaly Detection (Isolation Forest) from Deterministic Transaction Rule Checks.

    Isolation Forest Scoring & Classification:
    - IsolationForest.decision_function(X) outputs raw real numbers where values > 0 represent
      normal inliers and values < 0 represent anomalous outliers.
    - IsolationForest.predict(X) outputs +1 for inliers (NORMAL) and -1 for outliers (ANOMALOUS).
    - Custom Linear Normalization:
        Normalized Anomaly Score = clamp((0.5 - decision_function) * 100, 0, 100)
      This maps the typical decision function domain [-0.5 (anomalous), +0.5 (normal)] to a
      0–100 risk scale where 0 is lowest risk and 100 is highest anomaly risk.
    """
    behavior_X = prepare_behavior_dataframe(transaction)
    behavior_scaled = behavior_scaler.transform(behavior_X)

    behavior_prediction = behavior_model.predict(behavior_scaled)[0]
    behavior_raw_score = float(behavior_model.decision_function(behavior_scaled)[0])

    anomaly_detected = bool(behavior_prediction == -1)
    normalized_anomaly_score = max(
        0.0,
        min(
            100.0,
            round(float((0.5 - behavior_raw_score) * 100), 2)
        )
    )
    model_status = "ANOMALOUS" if anomaly_detected else "NORMAL"

    # Deterministic Transaction Rule Checks (separate from ML Isolation Forest)
    transaction_rule_checks = []
    high_signals = []
    medium_signals = []

    amount = float(transaction.TransactionAmount or 0)
    balance = float(transaction.AccountBalance or 0)

    if amount > balance:
        flag = f"Transaction amount (₹{amount:,.0f}) exceeds available account balance (₹{balance:,.0f})."
        transaction_rule_checks.append(flag)
        high_signals.append(flag)
    elif balance > 0 and amount > balance * 0.50:
        flag = f"Transaction is large relative to account balance (₹{amount:,.0f} vs ₹{balance:,.0f})."
        transaction_rule_checks.append(flag)
        medium_signals.append(flag)

    login_attempts = int(transaction.LoginAttempts or 0)
    if login_attempts >= 4:
        flag = f"Unusually high login attempts ({login_attempts} attempts detected)."
        transaction_rule_checks.append(flag)
        high_signals.append(flag)
    elif login_attempts >= 2:
        flag = f"Elevated login attempts ({login_attempts} attempts detected)."
        transaction_rule_checks.append(flag)
        medium_signals.append(flag)

    duration = float(transaction.TransactionDuration or 0)
    if duration >= 180:
        flag = f"Extended transaction duration ({duration:.0f} seconds)."
        transaction_rule_checks.append(flag)
        medium_signals.append(flag)

    if anomaly_detected:
        medium_signals.append("ML anomaly model detected unusual behavioral signature.")

    # Behavioral Risk Level Calibration
    if (amount > balance and anomaly_detected) or (login_attempts >= 4 and anomaly_detected) or len(high_signals) >= 2:
        behavioral_risk_level = "HIGH"
    elif anomaly_detected or len(high_signals) >= 1 or len(medium_signals) >= 2:
        behavioral_risk_level = "MEDIUM"
    elif len(medium_signals) >= 1:
        behavioral_risk_level = "MEDIUM"
    else:
        behavioral_risk_level = "LOW"

    return {
        "model_status": model_status,
        "anomaly_detected": anomaly_detected,
        "raw_decision_function": round(behavior_raw_score, 4),
        "normalized_anomaly_score": normalized_anomaly_score,
        "behavioral_anomaly_score": normalized_anomaly_score,  # Kept for backward compatibility
        "transaction_rule_checks": transaction_rule_checks,
        "rule_checks_flagged": transaction_rule_checks,
        "high_risk_signals": list(dict.fromkeys(high_signals)),
        "medium_risk_signals": list(dict.fromkeys(medium_signals)),
        "behavioral_risk_level": behavioral_risk_level,
    }


# ============================================================
# 4. DECISION ENGINE & DYNAMIC NARRATIVE
# ============================================================

def make_decision(credit_info, financial_info, behavioral_info):
    """
    Fuses Credit Intelligence, Financial Risk, Behavioral Risk, and Thin-File Status
    into a defensible lending recommendation (APPROVE / REVIEW / DECLINE) with dynamic reasoning.
    
    Principles:
    - Thin-file status alone NEVER causes DECLINE.
    - Thin-file status alone NEVER guarantees APPROVE.
    - Thin-file applicants are APPROVED only when the available model probability (>= 70%)
      and financial/transaction health independently support approval.
    - If evidence is insufficient, borderline, or mixed -> REVIEW.
    """
    is_thin_file = credit_info["is_thin_file"]
    pred_prob = credit_info["predicted_approval_probability"]
    credit_strength = credit_info["credit_strength"]

    fin_risk = financial_info["financial_risk_level"]
    fin_factors = financial_info["financial_risk_factors"]

    beh_risk = behavioral_info["behavioral_risk_level"]
    beh_model_status = behavioral_info["model_status"]
    beh_rule_flags = behavioral_info["transaction_rule_checks"]

    primary_drivers = []

    # 1. Decision Hierarchy
    if is_thin_file:
        # Thin-File Policy: Lack of credit score represents limited bureau evidence / uncertainty.
        if fin_risk == "CRITICAL":
            final_decision = "REVIEW"
            primary_drivers.append("Critical financial affordability risk (debt burden / cash flow deficit)")
        elif fin_risk == "HIGH":
            final_decision = "REVIEW"
            primary_drivers.append("Elevated financial risk factors on thin-file profile")
        elif beh_risk in ["MEDIUM", "HIGH"] or len(beh_rule_flags) > 0 or beh_model_status == "ANOMALOUS":
            final_decision = "REVIEW"
            if len(beh_rule_flags) > 0:
                primary_drivers.append("Transaction rule check warning")
            if beh_model_status == "ANOMALOUS":
                primary_drivers.append("Behavioral anomaly detected")
        elif pred_prob >= 70.0 and fin_risk == "LOW" and beh_risk == "LOW" and len(beh_rule_flags) == 0:
            # Independent positive evidence across credit model, financial capacity, and clean transaction behavior
            final_decision = "APPROVE"
            primary_drivers.append(f"Strong independent model prediction ({pred_prob}%) and clean financial capacity")
        else:
            # Limited evidence / borderline model probability (pred_prob < 70) or moderate financial risk
            final_decision = "REVIEW"
            primary_drivers.append("Limited traditional credit history with insufficient independent evidence for auto-approval")

    else:
        # Established Credit Policy
        if fin_risk == "CRITICAL":
            final_decision = "REVIEW" if pred_prob >= 40 else "DECLINE"
            primary_drivers.append("Critical debt-to-income and cash flow risk")
        elif credit_strength == "STRONG" and fin_risk in ["LOW", "MEDIUM"] and beh_risk == "LOW" and len(beh_rule_flags) == 0:
            final_decision = "APPROVE"
            primary_drivers.append(f"Strong predicted approval probability ({pred_prob}%) with clean financial health")
        elif credit_strength == "WEAK" and fin_risk in ["HIGH", "CRITICAL"]:
            final_decision = "DECLINE"
            primary_drivers.append(f"Weak model predicted approval probability ({pred_prob}%) compounded by elevated financial risk")
        elif credit_strength == "WEAK":
            final_decision = "DECLINE"
            primary_drivers.append(f"Low predicted approval probability ({pred_prob}%) below lending threshold")
        elif beh_risk == "HIGH" or beh_model_status == "ANOMALOUS":
            final_decision = "REVIEW"
            primary_drivers.append("Significant behavioral anomaly detected on account")
        elif len(beh_rule_flags) > 0:
            final_decision = "REVIEW"
            primary_drivers.append("Transaction rule check warning")
        elif credit_strength == "BORDERLINE" or fin_risk in ["HIGH", "CRITICAL"]:
            final_decision = "REVIEW"
            primary_drivers.append("Borderline credit indicators requiring manual underwriting review")
        else:
            final_decision = "REVIEW"
            primary_drivers.append("Mixed credit and behavioral profile")

    # 2. Dynamic Explainable Reasoning Construction
    reasoning_parts = []

    if is_thin_file:
        reasoning_parts.append(
            "Applicant has limited traditional credit history (New-to-Credit). "
            "Missing bureau score is represented using baseline population median imputation (~650) for model input, "
            "while thin-file uncertainty is separately evaluated in policy context."
        )
        if final_decision == "APPROVE":
            reasoning_parts.append(
                f"Independent model prediction ({pred_prob}%), financial capacity, and transaction behavior "
                "are all healthy, qualifying this application for approval."
            )
        else:
            specific_reasons = []
            if fin_factors:
                specific_reasons.append(f"Financial risk indicators: {'; '.join(fin_factors)}")
            if beh_rule_flags:
                specific_reasons.append(f"Transaction rule checks: {'; '.join(beh_rule_flags)}")
            if beh_model_status == "ANOMALOUS":
                specific_reasons.append("ML behavioral model flagged transaction anomaly")

            reasons_summary = ". ".join(specific_reasons) if specific_reasons else "Manual underwriting review required due to limited bureau evidence"
            reasoning_parts.append(
                f"This application is routed to REVIEW due to: {reasons_summary}. "
                "Thin-file status alone did not cause the review."
            )
    else:
        if final_decision == "APPROVE":
            reasoning_parts.append(
                f"Strong credit profile with {pred_prob}% predicted approval probability. "
                "Financial capacity and behavioral patterns are healthy."
            )
        elif final_decision == "DECLINE":
            reasons_summary = f" Key financial risk factors: {'; '.join(fin_factors)}." if fin_factors else ""
            reasoning_parts.append(
                f"Predicted approval probability is low ({pred_prob}%), indicating high default risk "
                f"that does not meet automatic approval criteria.{reasons_summary}"
            )
        else:
            specific_reasons = []
            if fin_factors:
                specific_reasons.append(f"Financial factors: {'; '.join(fin_factors)}")
            if beh_rule_flags:
                specific_reasons.append(f"Transaction rule checks: {'; '.join(beh_rule_flags)}")
            if beh_model_status == "ANOMALOUS":
                specific_reasons.append("ML anomaly model flagged anomalous activity")
            reasons_summary = ". ".join(specific_reasons) if specific_reasons else "Mixed profile signals"
            reasoning_parts.append(
                f"Application routed for human underwriter review ({credit_strength.lower()} credit profile). "
                f"Details: {reasons_summary}."
            )

    reasoning = " ".join(reasoning_parts)

    return {
        "final_decision": final_decision,
        "primary_drivers": primary_drivers,
        "reasoning": reasoning,
    }


# ============================================================
# UNIFIED CREDME DECISION ENDPOINT
# ============================================================

@app.post(
    "/decision",
    dependencies=[Depends(require_scope("decision"))],
)
def decision(
    request: DecisionRequest
):
    application = request.application
    transaction = request.transaction

    # 1. Evaluate Credit Intelligence Layer
    credit_info = evaluate_credit_intelligence(application)

    # 2. Evaluate Financial Risk Engine Layer
    financial_info = evaluate_financial_risk(application, credit_info["is_thin_file"])

    # 3. Evaluate Behavioral Intelligence Layer
    behavioral_info = evaluate_behavioral_intelligence(transaction)

    # 4. Run Decision Engine
    decision_result = make_decision(credit_info, financial_info, behavioral_info)

    # Thin-file context (strictly non-duplicated bureau information)
    if credit_info["is_thin_file"]:
        thin_file_context = [
            "Limited traditional credit history on record (New-to-Credit).",
            "Missing credit score is represented using baseline population median imputation (~650) for model input."
        ]
        if application.RentPaymentConsistency is not None:
            thin_file_context.append(
                f"Alternative payment data incorporated (Rent Payment Consistency: {float(application.RentPaymentConsistency)*100:.0f}%)."
            )
    else:
        thin_file_context = []

    # Summary string formatting
    if credit_info["is_thin_file"]:
        credit_summary = "THIN-FILE — no traditional credit history"
    else:
        credit_summary = f"{credit_info['predicted_approval_probability']}% predicted approval probability"

    return {
        # Core Decision Output
        "final_decision": decision_result["final_decision"],
        "reasoning": decision_result["reasoning"],
        "primary_drivers": decision_result["primary_drivers"],

        # Layer 1: Credit Intelligence
        "credit_intelligence": credit_info,
        "predicted_approval_probability": credit_info["predicted_approval_probability"],
        "model_approval_probability": credit_info["model_approval_probability"],
        "credit_confidence": credit_info["credit_confidence"],  # Backward-compatible alias
        "credit_strength": credit_info["credit_strength"],
        "thin_file": credit_info["is_thin_file"],
        "credit_score_used": credit_info["credit_score_used"],
        "reasons": credit_info["credit_reasons"],

        # Layer 2: Financial Risk Analysis
        "financial_intelligence": financial_info,
        "financial_concerns": financial_info["financial_risk_factors"],
        "debt_to_income_ratio": financial_info["debt_to_income_ratio"],
        "dti_percentage": financial_info["dti_percentage"],

        # Layer 3: Behavioral Intelligence
        "behavioral_intelligence": behavioral_info,
        "behavioral_risk": behavioral_info["behavioral_risk_level"],
        "behavioral_anomaly_score": behavioral_info["behavioral_anomaly_score"],
        "anomaly_detected": behavioral_info["anomaly_detected"],
        "model_status": behavioral_info["model_status"],
        "transaction_rule_checks": behavioral_info["transaction_rule_checks"],
        "rule_checks_flagged": behavioral_info["rule_checks_flagged"],
        "high_risk_signals": behavioral_info["high_risk_signals"],
        "medium_risk_signals": behavioral_info["medium_risk_signals"],

        # Thin-file Context (Clean, non-duplicated)
        "thin_file_context": thin_file_context,
        "thin_file_financial_concerns": thin_file_context,

        # High-level Summary
        "summary": {
            "credit": credit_summary,
            "financial": f"{financial_info['financial_risk_level']} financial risk",
            "behavior": f"{behavioral_info['behavioral_risk_level']} behavioral risk",
            "recommendation": decision_result["final_decision"],
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