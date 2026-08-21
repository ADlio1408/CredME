import { useState, useMemo } from "react";
import "./App.css";

const API_KEY = import.meta.env.VITE_API_KEY || "credme-dev-applicant-key";

const initialApplication = {
  Age: 32,
  AnnualIncome: 750000,
  CreditScore: 0,
  EmploymentStatus: "Employed",
  EducationLevel: "Bachelor",
  Experience: 8,
  LoanAmount: 200000,
  LoanDuration: 36,
  MaritalStatus: "Single",
  NumberOfDependents: 1,
  HomeOwnershipStatus: "Rent",
  MonthlyDebtPayments: 8000,
  TotalDebtToIncomeRatio: 0.128,
  CreditCardUtilizationRate: 25,
  NumberOfOpenCreditLines: 4,
  NumberOfCreditInquiries: 1,
  DebtToIncomeRatio: 0.128,
  BankruptcyHistory: 0,
  LoanPurpose: "Education",
  PreviousLoanDefaults: 0,
  PaymentHistory: 28,
  LengthOfCreditHistory: 10,
  SavingsAccountBalance: 150000,
  CheckingAccountBalance: 50000,
  TotalAssets: 500000,
  TotalLiabilities: 200000,
  MonthlyIncome: 62500,
  UtilityBillsPaymentHistory: 0.95,
  JobTenure: 5,
  NetWorth: 300000,
  RentPaymentConsistency: 90,
};

const initialTransaction = {
  TransactionAmount: 75000,
  TransactionDuration: 60,
  LoginAttempts: 1,
  AccountBalance: 50000,
  CustomerAge: 32,
  TransactionType: "Debit",
  Location: "San Diego",
  Channel: "Online",
  AccountID: "AC00128",
  DeviceID: "D000380",
};

function calculateDTI(appState) {
  const debt = parseFloat(appState.MonthlyDebtPayments) || 0;
  let income = parseFloat(appState.MonthlyIncome);
  if (!income || income <= 0) {
    const annual = parseFloat(appState.AnnualIncome);
    if (annual && annual > 0) {
      income = annual / 12;
    }
  }
  if (!income || income <= 0) return 0;
  return parseFloat((debt / income).toFixed(4));
}

function App() {
  const [application, setApplication] = useState(initialApplication);
  const [transaction, setTransaction] = useState(initialTransaction);

  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const updateApplication = (field, value) => {
    setApplication((prev) => {
      let finalValue = value;
      // Clamp percentage fields between 0 and 100
      if ((field === "RentPaymentConsistency" || field === "CreditCardUtilizationRate") && value !== "") {
        const num = parseFloat(value);
        if (!isNaN(num)) {
          finalValue = Math.max(0, Math.min(100, num));
        }
      }

      const next = {
        ...prev,
        [field]: finalValue,
      };

      // Keep transaction.CustomerAge synced with applicant Age
      if (field === "Age") {
        setTransaction((tPrev) => ({
          ...tPrev,
          CustomerAge: finalValue,
        }));
      }

      // Automatically update DebtToIncomeRatio and TotalDebtToIncomeRatio in state
      const computedDti = calculateDTI(next);
      next.DebtToIncomeRatio = computedDti;
      next.TotalDebtToIncomeRatio = computedDti;

      return next;
    });
  };

  const updateTransaction = (field, value) => {
    setTransaction((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  const isAgeInvalid = application.Age === "" || Number(application.Age) <= 0;
  const calculatedDti = calculateDTI(application);

  // Data Quality & Consistency Warnings (non-blocking)
  const incomeInconsistencyWarning = useMemo(() => {
    const annual = parseFloat(application.AnnualIncome);
    const monthly = parseFloat(application.MonthlyIncome);
    if (!isNaN(annual) && annual > 0 && !isNaN(monthly) && monthly > 0) {
      const expectedAnnual = monthly * 12;
      const diff = Math.abs(annual - expectedAnnual);
      // Sensible numerical tolerance: accounts for monthly rounding (up to ₹12/yr or 1% of annual income)
      const tolerance = Math.max(12, annual * 0.01);
      if (diff > tolerance) {
        return `⚠️ Input Consistency Note: Reported annual income (₹${annual.toLocaleString()}/yr) differs from 12 × monthly income (₹${monthly.toLocaleString()}/mo = ₹${expectedAnnual.toLocaleString()}/yr). Underwriting evaluates both values exactly as entered.`;
      }
    }
    return null;
  }, [application.AnnualIncome, application.MonthlyIncome]);

  const loanExposureWarning = useMemo(() => {
    const annual = parseFloat(application.AnnualIncome);
    const loan = parseFloat(application.LoanAmount);
    if (!isNaN(annual) && annual > 0 && !isNaN(loan) && loan > annual * 2) {
      return `⚠️ High Exposure Note: Requested loan amount (₹${loan.toLocaleString()}) is ${(loan / annual).toFixed(1)}x total reported annual income (₹${annual.toLocaleString()}).`;
    }
    return null;
  }, [application.AnnualIncome, application.LoanAmount]);

  const transactionOverdraftWarning = useMemo(() => {
    const txn = parseFloat(transaction.TransactionAmount);
    const bal = parseFloat(transaction.AccountBalance);
    if (!isNaN(txn) && !isNaN(bal) && txn > bal) {
      return `⚠️ Account Balance Note: Transaction amount (₹${txn.toLocaleString()}) exceeds available account balance (₹${bal.toLocaleString()}). This will be evaluated as a rule-based behavioral check.`;
    }
    return null;
  }, [transaction.TransactionAmount, transaction.AccountBalance]);

  const getDtiDisplay = () => {
    const monthlyIncome = parseFloat(application.MonthlyIncome) || (parseFloat(application.AnnualIncome) ? parseFloat(application.AnnualIncome) / 12 : 0);
    const monthlyDebt = parseFloat(application.MonthlyDebtPayments) || 0;

    if (monthlyIncome <= 0 && monthlyDebt > 0) {
      return {
        value: "Undefined (Zero Income)",
        badge: "⚠️ Undefined DTI",
        helper: `⚠️ Monthly debt payments of ₹${monthlyDebt.toLocaleString()} reported with ₹0 monthly income.`,
      };
    }
    if (calculatedDti <= 0) {
      return {
        value: "0.0% (0.00)",
        badge: "Auto-Calculated",
        helper: "Computed: Monthly Debt ÷ Monthly Income",
      };
    }
    if (calculatedDti >= 1.0) {
      return {
        value: `${(calculatedDti * 100).toFixed(1)}% (${calculatedDti.toFixed(1)}x Income)`,
        badge: "⚠️ Critical Affordability Risk",
        helper: `⚠️ Severe debt burden: Existing debt (₹${monthlyDebt.toLocaleString()}/mo) exceeds monthly income (₹${monthlyIncome.toLocaleString()}/mo) by ${calculatedDti.toFixed(1)}x. Debt obligations exceed 100% of income.`,
      };
    }
    if (calculatedDti >= 0.50) {
      return {
        value: `${(calculatedDti * 100).toFixed(1)}%`,
        badge: "High DTI",
        helper: `Elevated debt load: Monthly debt obligations consume ${(calculatedDti * 100).toFixed(0)}% of monthly income.`,
      };
    }
    return {
      value: `${(calculatedDti * 100).toFixed(1)}%`,
      badge: "Auto-Calculated",
      helper: `Monthly Debt (₹${monthlyDebt.toLocaleString()}) ÷ Monthly Income (₹${monthlyIncome.toLocaleString()})`,
    };
  };

  const dtiDisplay = getDtiDisplay();

  const assessCredit = async () => {
    setError("");
    setResult(null);

    // Validation: Age cannot be 0 or invalid
    const ageNum = Number(application.Age);
    if (!application.Age || isNaN(ageNum) || ageNum <= 0) {
      setError("Invalid Age: Applicant age cannot be 0 or empty. Please enter a valid age.");
      return;
    }

    const customerAgeNum = Number(transaction.CustomerAge);
    if (!transaction.CustomerAge || isNaN(customerAgeNum) || customerAgeNum <= 0) {
      setError("Invalid Age: Transaction customer age cannot be 0 or empty. Please enter a valid age.");
      return;
    }

    const currentDti = calculateDTI(application);

    setLoading(true);

    try {
      const response = await fetch("http://127.0.0.1:4000/decision", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "X-API-Key": API_KEY,
        },
        body: JSON.stringify({
          application: {
            ...application,
            Age: Number(application.Age),
            AnnualIncome: Number(application.AnnualIncome || 0),
            CreditScore: Number(application.CreditScore || 0),
            Experience: Number(application.Experience || 0),
            LoanAmount: Number(application.LoanAmount || 0),
            LoanDuration: Number(application.LoanDuration || 0),
            NumberOfDependents: Number(application.NumberOfDependents || 0),
            MonthlyDebtPayments: Number(application.MonthlyDebtPayments || 0),
            TotalDebtToIncomeRatio: currentDti,
            CreditCardUtilizationRate: Number(
              application.CreditCardUtilizationRate || 0
            ) / 100,
            NumberOfOpenCreditLines: Number(
              application.NumberOfOpenCreditLines || 0
            ),
            NumberOfCreditInquiries: Number(
              application.NumberOfCreditInquiries || 0
            ),
            DebtToIncomeRatio: currentDti,
            BankruptcyHistory: Number(application.BankruptcyHistory || 0),
            PreviousLoanDefaults: Number(application.PreviousLoanDefaults || 0),
            PaymentHistory: Number(application.PaymentHistory || 0),
            LengthOfCreditHistory: Number(
              application.LengthOfCreditHistory || 0
            ),
            SavingsAccountBalance: Number(
              application.SavingsAccountBalance || 0
            ),
            CheckingAccountBalance: Number(
              application.CheckingAccountBalance || 0
            ),
            TotalAssets: Number(application.TotalAssets || 0),
            TotalLiabilities: Number(application.TotalLiabilities || 0),
            MonthlyIncome: Number(application.MonthlyIncome || 0),
            UtilityBillsPaymentHistory: Number(
              application.UtilityBillsPaymentHistory || 0
            ),
            JobTenure: Number(application.JobTenure || 0),
            NetWorth: Number(application.NetWorth || 0),
            RentPaymentConsistency: Number(
              application.RentPaymentConsistency || 0
            ) / 100,
          },

          transaction: {
            ...transaction,
            TransactionAmount: Number(transaction.TransactionAmount || 0),
            TransactionDuration: Number(transaction.TransactionDuration || 0),
            LoginAttempts: Number(transaction.LoginAttempts || 0),
            AccountBalance: Number(transaction.AccountBalance || 0),
            CustomerAge: Number(transaction.CustomerAge || 0),
          },
        }),
      });

      if (!response.ok) {
        const message = await response.text();
        throw new Error(message || "Unable to assess application.");
      }

      const data = await response.json();

      setResult(data);
    } catch (err) {
      console.error(err);

      setError(
        err.message?.includes("detail")
          ? err.message
          : "Unable to connect to CredMe API. Make sure the FastAPI server is running on port 4000."
      );
    } finally {
      setLoading(false);
    }
  };

  const getDecisionClass = () => {
    if (!result) return "";

    if (result.final_decision === "APPROVE") return "approve";
    if (result.final_decision === "DECLINE") return "decline";

    return "review";
  };

  const getRiskClass = (risk) => {
    if (risk === "LOW") return "risk-low";
    if (risk === "HIGH") return "risk-high";

    return "risk-medium";
  };

  return (
    <div className="app">
      {/* =====================================================
          HEADER
      ====================================================== */}

      <header className="topbar">
        <div className="brand">
          <div className="brand-mark">C</div>

          <div>
            <h1>CredMe</h1>
            <span>Real-Time Credit Intelligence</span>
          </div>
        </div>

        <div className="system-status">
          <span className="status-dot"></span>
          Intelligence Engine Online
        </div>
      </header>

      {/* =====================================================
          HERO
      ====================================================== */}

      <main className="container">
        <section className="hero-section">
          <div>
            <p className="eyebrow">NEXT-GEN UNDERWRITING</p>

            <h2>
              Make smarter credit decisions
              <br />
              <span>with real-time intelligence.</span>
            </h2>

            <p className="hero-description">
              CredMe combines creditworthiness, financial health and
              behavioral signals to provide an explainable lending
              recommendation.
            </p>
          </div>

          <div className="hero-stat">
            <div className="stat-label">AI DECISION ENGINE</div>
            <div className="stat-value">LIVE</div>
            <div className="stat-description">
              XGBoost + SHAP + Behavioral AI
            </div>
          </div>
        </section>

        {/* =====================================================
            APPLICANT INFORMATION
        ====================================================== */}

        <section className="card">
          <div className="section-heading">
            <div className="section-icon">01</div>

            <div>
              <h3>Applicant Profile</h3>
              <p>Core identity and employment information</p>
            </div>
          </div>

          <div className="form-grid">
            <Field
              label="Age"
              value={application.Age}
              isNumeric={true}
              integerOnly={true}
              hasError={isAgeInvalid}
              errorMessage={isAgeInvalid ? "Age cannot be 0. Enter a valid age." : ""}
              onChange={(v) => updateApplication("Age", v)}
            />

            <Field
              label="Annual Income"
              prefix="₹"
              value={application.AnnualIncome}
              isNumeric={true}
              onChange={(v) => updateApplication("AnnualIncome", v)}
            />

            <Field
              label="Credit Score"
              value={application.CreditScore}
              isNumeric={true}
              integerOnly={true}
              helperText="Set 0 for thin-file / New-to-Credit"
              onChange={(v) => updateApplication("CreditScore", v)}
            />

            <Field
              label="Rent Payment Consistency (alt. data, thin-file only)"
              value={application.RentPaymentConsistency}
              suffix="%"
              isNumeric={true}
              onChange={(v) =>
                updateApplication("RentPaymentConsistency", v)
              }
            />

            <SelectField
              label="Employment Status"
              value={application.EmploymentStatus}
              options={[
                "Employed",
                "Self-Employed",
                "Unemployed",
                "Retired",
              ]}
              onChange={(v) =>
                updateApplication("EmploymentStatus", v)
              }
            />

            <SelectField
              label="Education Level"
              value={application.EducationLevel}
              options={[
                "High School",
                "Associate",
                "Bachelor",
                "Master",
                "Doctorate",
              ]}
              onChange={(v) =>
                updateApplication("EducationLevel", v)
              }
            />

            <Field
              label="Years of Experience"
              value={application.Experience}
              isNumeric={true}
              integerOnly={true}
              suffix="yrs"
              onChange={(v) => updateApplication("Experience", v)}
            />

            <SelectField
              label="Marital Status"
              value={application.MaritalStatus}
              options={["Single", "Married", "Divorced", "Widowed"]}
              onChange={(v) =>
                updateApplication("MaritalStatus", v)
              }
            />

            <SelectField
              label="Home Ownership"
              value={application.HomeOwnershipStatus}
              options={["Rent", "Own", "Mortgage"]}
              onChange={(v) =>
                updateApplication("HomeOwnershipStatus", v)
              }
            />
          </div>
        </section>

        {/* =====================================================
            LOAN DETAILS
        ====================================================== */}

        <section className="card">
          <div className="section-heading">
            <div className="section-icon">02</div>

            <div>
              <h3>Loan & Financial Profile</h3>
              <p>Credit exposure and repayment capacity</p>
            </div>
          </div>

          <div className="form-grid">
            <Field
              label="Loan Amount"
              prefix="₹"
              value={application.LoanAmount}
              isNumeric={true}
              onChange={(v) => updateApplication("LoanAmount", v)}
            />

            <Field
              label="Loan Duration"
              suffix="months"
              value={application.LoanDuration}
              isNumeric={true}
              integerOnly={true}
              onChange={(v) =>
                updateApplication("LoanDuration", v)
              }
            />

            <SelectField
              label="Loan Purpose"
              value={application.LoanPurpose}
              options={[
                "Education",
                "Home",
                "Auto",
                "Debt Consolidation",
                "Personal",
                "Business",
              ]}
              onChange={(v) =>
                updateApplication("LoanPurpose", v)
              }
            />

            <Field
              label="Monthly Income"
              prefix="₹"
              value={application.MonthlyIncome}
              isNumeric={true}
              onChange={(v) =>
                updateApplication("MonthlyIncome", v)
              }
            />

            <Field
              label="Monthly Debt Payments"
              prefix="₹"
              value={application.MonthlyDebtPayments}
              isNumeric={true}
              onChange={(v) =>
                updateApplication("MonthlyDebtPayments", v)
              }
            />

            <Field
              label="Debt-to-Income Ratio"
              value={dtiDisplay.value}
              readOnly={true}
              isCalculated={true}
              badge={dtiDisplay.badge}
              helperText={dtiDisplay.helper}
            />

            <Field
              label="Credit Utilization"
              value={application.CreditCardUtilizationRate}
              suffix="%"
              isNumeric={true}
              onChange={(v) =>
                updateApplication(
                  "CreditCardUtilizationRate",
                  v
                )
              }
            />

            <Field
              label="Savings Balance"
              prefix="₹"
              value={application.SavingsAccountBalance}
              isNumeric={true}
              onChange={(v) =>
                updateApplication(
                  "SavingsAccountBalance",
                  v
                )
              }
            />

            <Field
              label="Checking Balance"
              prefix="₹"
              value={application.CheckingAccountBalance}
              isNumeric={true}
              onChange={(v) =>
                updateApplication(
                  "CheckingAccountBalance",
                  v
                )
              }
            />

            <Field
              label="Total Assets"
              prefix="₹"
              value={application.TotalAssets}
              isNumeric={true}
              onChange={(v) =>
                updateApplication("TotalAssets", v)
              }
            />

            <Field
              label="Total Liabilities"
              prefix="₹"
              value={application.TotalLiabilities}
              isNumeric={true}
              onChange={(v) =>
                updateApplication(
                  "TotalLiabilities",
                  v
                )
              }
            />

            <Field
              label="Net Worth"
              prefix="₹"
              value={application.NetWorth}
              isNumeric={true}
              allowNegative={true}
              onChange={(v) =>
                updateApplication("NetWorth", v)
              }
            />
          </div>
        </section>

        {/* =====================================================
            BEHAVIORAL INFORMATION
        ====================================================== */}

        <section className="card">
          <div className="section-heading">
            <div className="section-icon">03</div>

            <div>
              <h3>Behavioral Intelligence</h3>
              <p>Real-time transaction & behavioral risk signals</p>
            </div>
          </div>

          <div className="form-grid">
            <Field
              label="Transaction Amount"
              prefix="₹"
              value={transaction.TransactionAmount}
              isNumeric={true}
              onChange={(v) =>
                updateTransaction(
                  "TransactionAmount",
                  v
                )
              }
            />

            <Field
              label="Account Balance"
              prefix="₹"
              value={transaction.AccountBalance}
              isNumeric={true}
              onChange={(v) =>
                updateTransaction(
                  "AccountBalance",
                  v
                )
              }
            />

            <Field
              label="Transaction Duration"
              suffix="sec"
              value={transaction.TransactionDuration}
              isNumeric={true}
              onChange={(v) =>
                updateTransaction(
                  "TransactionDuration",
                  v
                )
              }
            />

            <Field
              label="Login Attempts"
              value={transaction.LoginAttempts}
              isNumeric={true}
              integerOnly={true}
              onChange={(v) =>
                updateTransaction(
                  "LoginAttempts",
                  v
                )
              }
            />

            <SelectField
              label="Transaction Type"
              value={transaction.TransactionType}
              options={["Debit", "Credit"]}
              onChange={(v) =>
                updateTransaction(
                  "TransactionType",
                  v
                )
              }
            />

            <SelectField
              label="Channel"
              value={transaction.Channel}
              options={["Online", "ATM", "Branch"]}
              onChange={(v) =>
                updateTransaction(
                  "Channel",
                  v
                )
              }
            />

            <Field
              label="Location"
              value={transaction.Location}
              onChange={(v) =>
                updateTransaction(
                  "Location",
                  v
                )
              }
            />

            <Field
              label="Account ID"
              value={transaction.AccountID}
              onChange={(v) =>
                updateTransaction(
                  "AccountID",
                  v
                )
              }
            />

            <Field
              label="Device ID"
              value={transaction.DeviceID}
              onChange={(v) =>
                updateTransaction(
                  "DeviceID",
                  v
                )
              }
            />
          </div>
        </section>

        {/* =====================================================
            DATA QUALITY & CONSISTENCY WARNINGS
        ====================================================== */}

        {(incomeInconsistencyWarning || loanExposureWarning || transactionOverdraftWarning) && (
          <div style={{ marginTop: "16px", marginBottom: "8px" }}>
            {incomeInconsistencyWarning && (
              <div className="data-quality-banner">
                <span>ℹ️</span>
                <div>{incomeInconsistencyWarning}</div>
              </div>
            )}
            {loanExposureWarning && (
              <div className="data-quality-banner">
                <span>ℹ️</span>
                <div>{loanExposureWarning}</div>
              </div>
            )}
            {transactionOverdraftWarning && (
              <div className="data-quality-banner">
                <span>ℹ️</span>
                <div>{transactionOverdraftWarning}</div>
              </div>
            )}
          </div>
        )}

        {/* =====================================================
            ASSESS BUTTON
        ====================================================== */}

        <div className="assessment-area">
          <button
            className="assess-button"
            onClick={assessCredit}
            disabled={loading}
          >
            {loading ? (
              <>
                <span className="spinner"></span>
                ANALYZING APPLICATION...
              </>
            ) : (
              <>
                ASSESS CREDIT
                <span className="arrow">→</span>
              </>
            )}
          </button>

          <p>
            CredMe evaluates creditworthiness, financial affordability and behavioral risk
            before generating a recommendation.
          </p>
        </div>

        {/* =====================================================
            ERROR
        ====================================================== */}

        {error && (
          <div className="error-box">
            <strong>Connection Error</strong>
            <span>{error}</span>
          </div>
        )}

        {/* =====================================================
            RESULTS
        ====================================================== */}

        {result && (
          <section className="results">
            <div className="results-header">
              <div>
                <p className="eyebrow">CREDME ASSESSMENT</p>
                <h2>Decision Intelligence</h2>
              </div>

              <div className="analysis-complete">
                ✓ Analysis Complete
              </div>
            </div>

            {/* FINAL DECISION */}

            <div
              className={`decision-banner ${getDecisionClass()}`}
            >
              <div>
                <span className="decision-label">
                  RECOMMENDATION
                </span>

                <h2>{result.final_decision}</h2>

                <p>{result.reasoning}</p>
              </div>

              <div className="decision-score">
                <span>Predicted Approval Probability</span>

                <strong>
                  {result.predicted_approval_probability ?? result.credit_confidence}%
                </strong>

                <small>
                  {result.credit_strength}
                </small>
              </div>
            </div>

            {/* THREE INTELLIGENCE CARDS */}

            <div className="result-grid">
              {/* Layer 1: Credit Intelligence */}
              <div className="result-card">
                <div className="result-card-top">
                  <span>Credit Intelligence</span>

                  <span className="result-number">
                    {result.predicted_approval_probability ?? result.credit_confidence}%
                  </span>
                </div>

                <div className="progress">
                  <div
                    className="progress-fill credit"
                    style={{
                      width: `${Math.min(
                        result.predicted_approval_probability ?? result.credit_confidence ?? 0,
                        100
                      )}%`,
                    }}
                  ></div>
                </div>

                <div className="result-footer">
                  <span>Credit Strength</span>
                  <span
                    className={`risk-pill ${
                      result.credit_strength === "THIN_FILE"
                        ? "risk-thin"
                        : result.credit_strength === "STRONG"
                        ? "risk-low"
                        : result.credit_strength === "BORDERLINE"
                        ? "risk-medium"
                        : "risk-high"
                    }`}
                  >
                    {result.credit_strength}
                  </span>
                </div>

                <p style={{ fontSize: "11px", color: "var(--muted)", margin: "10px 0 0", lineHeight: 1.4 }}>
                  {result.credit_intelligence?.credit_history_note ??
                    (result.thin_file
                      ? "No traditional bureau history (New-to-Credit). Missing bureau score represented using baseline population median (~650); thin-file status evaluated in policy context."
                      : "Traditional bureau credit score available.")}
                </p>
              </div>

              {/* Layer 2: Financial Risk Analysis */}
              <div className="result-card">
                <div className="result-card-top">
                  <span>Financial Risk Engine</span>

                  <span
                    className={`risk-pill ${
                      (result.financial_intelligence?.financial_risk_level || "LOW") === "CRITICAL"
                        ? "risk-critical"
                        : getRiskClass(result.financial_intelligence?.financial_risk_level || "LOW")
                    }`}
                  >
                    {result.financial_intelligence?.financial_risk_level || "LOW"}
                  </span>
                </div>

                <div className="behavior-score">
                  <strong>
                    {result.financial_intelligence?.dti_percentage !== null &&
                    result.financial_intelligence?.dti_percentage !== undefined
                      ? `${result.financial_intelligence.dti_percentage.toLocaleString()}%`
                      : result.debt_to_income_ratio
                      ? `${(result.debt_to_income_ratio * 100).toFixed(1)}%`
                      : "N/A"}
                  </strong>

                  <span>DTI ratio</span>
                </div>

                <div className="result-footer">
                  <span>Monthly Cash Flow</span>
                  <strong>
                    {result.financial_intelligence?.monthly_cash_flow !== undefined
                      ? result.financial_intelligence.monthly_cash_flow >= 0
                        ? `+₹${result.financial_intelligence.monthly_cash_flow.toLocaleString()}/mo`
                        : `-₹${Math.abs(result.financial_intelligence.monthly_cash_flow).toLocaleString()}/mo`
                      : "N/A"}
                  </strong>
                </div>
              </div>

              {/* Layer 3: Behavioral Intelligence */}
              <div className="result-card">
                <div className="result-card-top">
                  <span>Behavioral Intelligence</span>

                  <span
                    className={`risk-pill ${getRiskClass(
                      result.behavioral_risk
                    )}`}
                  >
                    {result.behavioral_risk}
                  </span>
                </div>

                <div className="behavior-score">
                  <strong>
                    {result.normalized_anomaly_score ?? result.behavioral_anomaly_score}
                  </strong>

                  <span>
                    Normalized Anomaly Score
                  </span>
                </div>

                <div className="result-footer">
                  <span>Model: <strong>{result.behavioral_intelligence?.model_status ?? (result.anomaly_detected ? "ANOMALOUS" : "NORMAL")}</strong></span>
                  <span>Rules: <strong>{result.transaction_rule_checks?.length ?? result.rule_checks_flagged?.length ?? 0} flagged</strong></span>
                </div>
              </div>
            </div>

            {/* REASONING */}

            <div className="reasoning-card">
              <div className="reasoning-heading">
                <div className="reasoning-icon">✦</div>

                <div>
                  <h3>Decision Reasoning</h3>
                  <p>
                    Explainable AI multi-factor synthesis
                  </p>
                </div>
              </div>

              <p className="reasoning-text">
                {result.reasoning}
              </p>

              <div className="signal-section">
                <h4>Categorized Risk Signals & Evidence</h4>

                {/* Financial Concerns */}
                {result.financial_concerns?.length > 0 && (
                  <div className="signals" style={{ marginBottom: "14px" }}>
                    <div style={{ fontSize: "11px", fontWeight: "700", color: "#9f1239", marginBottom: "2px" }}>
                      FINANCIAL CAPACITY & DEBT CONCERNS
                    </div>
                    {result.financial_concerns.map((concern, index) => (
                      <div className="signal financial" key={`fin-${index}`}>
                        <span>!</span>
                        {concern}
                      </div>
                    ))}
                  </div>
                )}

                {/* Thin-File Context (Bureau status only, NO financial duplicates) */}
                {result.thin_file && result.thin_file_context?.length > 0 && (
                  <div className="signals" style={{ marginBottom: "14px" }}>
                    <div style={{ fontSize: "11px", fontWeight: "700", color: "#5b21b6", marginBottom: "2px" }}>
                      CREDIT HISTORY & THIN-FILE STATUS
                    </div>
                    {result.thin_file_context.map((note, index) => (
                      <div className="signal thin-file" key={`thin-ctx-${index}`}>
                        <span>ℹ</span>
                        {note}
                      </div>
                    ))}
                  </div>
                )}

                {/* Behavioral Rule Flags & Anomalies */}
                {(result.high_risk_signals?.length > 0 ||
                  result.medium_risk_signals?.length > 0 ||
                  result.rule_checks_flagged?.length > 0 ||
                  result.anomaly_detected) && (
                  <div className="signals">
                    <div style={{ fontSize: "11px", fontWeight: "700", color: "#655a72", marginBottom: "2px" }}>
                      BEHAVIORAL SIGNALS & ACCOUNT CHECKS
                    </div>
                    {result.rule_checks_flagged?.map((flag, index) => (
                      <div className="signal medium" key={`rule-${index}`}>
                        <span>!</span>
                        {flag}
                      </div>
                    ))}
                    {result.anomaly_detected && (
                      <div className="signal high" key="ml-anom">
                        <span>!</span>
                        ML Anomaly Model flagged unusual transaction signature.
                      </div>
                    )}
                    {!result.anomaly_detected && (!result.rule_checks_flagged || result.rule_checks_flagged.length === 0) && (
                      <div className="signal normal">
                        <span>✓</span>
                        Behavioral model: NORMAL — No anomalous transaction signals detected.
                      </div>
                    )}
                  </div>
                )}

                {(!result.financial_concerns || result.financial_concerns.length === 0) &&
                  (!result.rule_checks_flagged || result.rule_checks_flagged.length === 0) &&
                  !result.anomaly_detected && (
                    <div className="signal normal">
                      <span>✓</span>
                      All financial and behavioral risk screens passed cleanly.
                    </div>
                  )}
              </div>
            </div>

            {/* CREDIT DRIVERS */}

            <div className="drivers-card">
              <div className="drivers-header">
                <div>
                  <h3>Credit Decision Drivers</h3>
                  <p>
                    Top 5 model drivers — Relative SHAP Contribution
                  </p>
                </div>

                <span>SHAP</span>
              </div>

              <div className="drivers-list">
                {result.reasons?.map((reason, index) => {
                  const isPositive = reason.impact >= 0;
                  const contributionPct = reason.relative_contribution_pct ?? Math.abs(reason.impact);
                  const directionText = reason.direction ?? reason.effect ?? (isPositive ? "Increases approval likelihood" : "Decreases approval likelihood");

                  return (
                    <div
                      className="driver"
                      key={index}
                    >
                      <div className="driver-info">
                        <span className="driver-rank">
                          {String(index + 1).padStart(2, "0")}
                        </span>

                        <div>
                          <strong>
                            {reason.feature}
                          </strong>

                          <small>
                            {directionText}
                          </small>
                        </div>
                      </div>

                      <div
                        className={
                          isPositive
                            ? "impact positive"
                            : "impact negative"
                        }
                      >
                        {isPositive ? "▲ +" : "▼ -"}
                        {contributionPct}%
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* RESPONSIBLE AI */}

            <div className="responsible-ai">
              <span>RESPONSIBLE AI</span>

              <p>
                CredMe provides a decision recommendation rather
                than an autonomous lending decision. High-risk
                cases are routed for human review, with key
                decision factors exposed for transparency.
              </p>
            </div>
          </section>
        )}
      </main>

      <footer>
        <span>CredMe © 2026</span>
        <span>Real-Time Credit Intelligence Platform</span>
      </footer>
    </div>
  );
}


/* ============================================================
   REUSABLE FORM FIELD
============================================================ */

function Field({
  label,
  value,
  onChange,
  prefix,
  suffix,
  isNumeric = false,
  integerOnly = false,
  allowNegative = false,
  readOnly = false,
  isCalculated = false,
  badge = null,
  hasError = false,
  errorMessage = "",
  helperText = "",
  placeholder = "",
}) {
  const handleInputChange = (e) => {
    if (readOnly) return;
    const rawVal = e.target.value;

    if (!isNumeric) {
      if (onChange) onChange(rawVal);
      return;
    }

    // Allow empty string to allow clearing the field
    if (rawVal === "") {
      if (onChange) onChange("");
      return;
    }

    if (integerOnly) {
      if (/^\d+$/.test(rawVal)) {
        if (onChange) onChange(rawVal);
      }
    } else if (allowNegative) {
      if (/^-?\d*\.?\d*$/.test(rawVal)) {
        if (onChange) onChange(rawVal);
      }
    } else {
      if (/^\d*\.?\d*$/.test(rawVal)) {
        if (onChange) onChange(rawVal);
      }
    }
  };

  const fieldClasses = [
    "field",
    readOnly || isCalculated ? "is-readonly" : "",
    hasError ? "has-error" : "",
  ]
    .filter(Boolean)
    .join(" ");

  return (
    <div className={fieldClasses}>
      <div className="field-header">
        <span className="field-label">{label}</span>
        {badge && <span className="field-badge">{badge}</span>}
      </div>

      <div className="input-wrapper">
        {prefix && (
          <span className="input-prefix">
            {prefix}
          </span>
        )}

        <input
          type="text"
          inputMode={
            isNumeric ? (integerOnly ? "numeric" : "decimal") : "text"
          }
          value={value ?? ""}
          onChange={handleInputChange}
          readOnly={readOnly}
          placeholder={placeholder}
          aria-invalid={hasError}
        />

        {suffix && (
          <span className="input-suffix">
            {suffix}
          </span>
        )}
      </div>

      {hasError && errorMessage && (
        <span className="field-error-msg">⚠️ {errorMessage}</span>
      )}

      {!hasError && helperText && (
        <span className="field-helper">{helperText}</span>
      )}
    </div>
  );
}


/* ============================================================
   SELECT FIELD
============================================================ */

function SelectField({
  label,
  value,
  options,
  onChange,
}) {
  return (
    <label className="field">
      <span>{label}</span>

      <select
        value={value}
        onChange={(e) =>
          onChange(e.target.value)
        }
      >
        {options.map((option) => (
          <option
            value={option}
            key={option}
          >
            {option}
          </option>
        ))}
      </select>
    </label>
  );
}


export default App;