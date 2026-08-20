from typing import Optional

from pydantic import BaseModel, Field, field_validator


class LoanApplication(BaseModel):
    """Input contract for a credit application. Ranges are validated so
    obviously malformed or out-of-domain input never reaches the model."""

    age: int = Field(..., ge=18, le=100)
    annual_income: float = Field(..., ge=0, le=10_000_000)
    credit_score: int = Field(..., ge=300, le=850)
    employment_status: str
    education_level: str
    experience: int = Field(..., ge=0, le=60)
    loan_amount: float = Field(..., gt=0, le=5_000_000)
    loan_duration: int = Field(..., ge=1, le=480)
    marital_status: str
    number_of_dependents: int = Field(..., ge=0, le=20)
    home_ownership_status: str
    monthly_debt_payments: float = Field(..., ge=0)
    credit_card_utilization_rate: float = Field(..., ge=0, le=1)
    number_of_open_credit_lines: int = Field(..., ge=0, le=100)
    number_of_credit_inquiries: int = Field(..., ge=0, le=100)
    debt_to_income_ratio: float = Field(..., ge=0, le=5)
    bankruptcy_history: int = Field(..., ge=0, le=1)
    loan_purpose: str
    previous_loan_defaults: int = Field(..., ge=0, le=1)
    payment_history: int = Field(..., ge=0, le=100)
    length_of_credit_history: int = Field(..., ge=0, le=80)
    savings_account_balance: float = Field(..., ge=0)
    checking_account_balance: float = Field(..., ge=0)
    total_assets: float = Field(..., ge=0)
    total_liabilities: float = Field(..., ge=0)
    monthly_income: float = Field(..., ge=0)
    utility_bills_payment_history: float = Field(..., ge=0, le=1)
    job_tenure: int = Field(..., ge=0, le=60)
    net_worth: float
    base_interest_rate: float = Field(..., ge=0, le=1)
    interest_rate: float = Field(..., ge=0, le=1)
    monthly_loan_payment: float = Field(..., ge=0)
    total_debt_to_income_ratio: float = Field(..., ge=0, le=5)

    # Optional: link to a bank account for alt-data/behavioral fusion.
    account_id: Optional[str] = Field(default=None, max_length=32)

    @field_validator("employment_status", "education_level", "marital_status",
                      "home_ownership_status", "loan_purpose")
    @classmethod
    def strip_and_check(cls, v: str) -> str:
        v = v.strip()
        if not v:
            raise ValueError("must not be empty")
        return v


class FeatureContribution(BaseModel):
    feature: str
    contribution: float
    direction: str  # "increases_risk" | "decreases_risk"


class ScoreResponse(BaseModel):
    decision: str  # "APPROVE" | "REFER" | "DECLINE"
    approval_probability: float
    credit_intel_score: float  # 0-100
    top_factors: list[FeatureContribution]
    behavioral_trust_score: Optional[float] = None
    behavioral_signals: Optional[dict] = None
    fused_score: Optional[float] = None
    explanation: str
    model_version: str
