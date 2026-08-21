import { useState } from "react";
import "./App.css";

const API_KEY = import.meta.env.VITE_API_KEY || "credme-dev-applicant-key";

const initialApplication = {
  Age: 32,
  AnnualIncome: 75000,
  CreditScore: 680,
  EmploymentStatus: "Employed",
  EducationLevel: "Bachelor",
  Experience: 8,
  LoanAmount: 20000,
  LoanDuration: 36,
  MaritalStatus: "Single",
  NumberOfDependents: 1,
  HomeOwnershipStatus: "Rent",
  MonthlyDebtPayments: 800,
  TotalDebtToIncomeRatio: 0.30,
  CreditCardUtilizationRate: 0.25,
  NumberOfOpenCreditLines: 4,
  NumberOfCreditInquiries: 1,
  DebtToIncomeRatio: 0.22,
  BankruptcyHistory: 0,
  LoanPurpose: "Education",
  PreviousLoanDefaults: 0,
  PaymentHistory: 28,
  LengthOfCreditHistory: 10,
  SavingsAccountBalance: 15000,
  CheckingAccountBalance: 5000,
  TotalAssets: 50000,
  TotalLiabilities: 20000,
  MonthlyIncome: 6250,
  UtilityBillsPaymentHistory: 0.95,
  JobTenure: 5,
  NetWorth: 30000,
  RentPaymentConsistency: 0.9,
};

const initialTransaction = {
  TransactionAmount: 150,
  TransactionDuration: 60,
  LoginAttempts: 1,
  AccountBalance: 8000,
  CustomerAge: 32,
  TransactionType: "Debit",
  Location: "San Diego",
  Channel: "Online",
  AccountID: "AC00128",
  DeviceID: "D000380",
};

function App() {
  const [application, setApplication] = useState(initialApplication);
  const [transaction, setTransaction] = useState(initialTransaction);

  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const updateApplication = (field, value) => {
    setApplication((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  const updateTransaction = (field, value) => {
    setTransaction((prev) => ({
      ...prev,
      [field]: value,
    }));
  };

  const assessCredit = async () => {
    setLoading(true);
    setError("");
    setResult(null);

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
            AnnualIncome: Number(application.AnnualIncome),
            CreditScore: Number(application.CreditScore),
            Experience: Number(application.Experience),
            LoanAmount: Number(application.LoanAmount),
            LoanDuration: Number(application.LoanDuration),
            NumberOfDependents: Number(application.NumberOfDependents),
            MonthlyDebtPayments: Number(application.MonthlyDebtPayments),
            TotalDebtToIncomeRatio: Number(
              application.TotalDebtToIncomeRatio
            ),
            CreditCardUtilizationRate: Number(
              application.CreditCardUtilizationRate
            ),
            NumberOfOpenCreditLines: Number(
              application.NumberOfOpenCreditLines
            ),
            NumberOfCreditInquiries: Number(
              application.NumberOfCreditInquiries
            ),
            DebtToIncomeRatio: Number(application.DebtToIncomeRatio),
            BankruptcyHistory: Number(application.BankruptcyHistory),
            PreviousLoanDefaults: Number(application.PreviousLoanDefaults),
            PaymentHistory: Number(application.PaymentHistory),
            LengthOfCreditHistory: Number(
              application.LengthOfCreditHistory
            ),
            SavingsAccountBalance: Number(
              application.SavingsAccountBalance
            ),
            CheckingAccountBalance: Number(
              application.CheckingAccountBalance
            ),
            TotalAssets: Number(application.TotalAssets),
            TotalLiabilities: Number(application.TotalLiabilities),
            MonthlyIncome: Number(application.MonthlyIncome),
            UtilityBillsPaymentHistory: Number(
              application.UtilityBillsPaymentHistory
            ),
            JobTenure: Number(application.JobTenure),
            NetWorth: Number(application.NetWorth),
            RentPaymentConsistency: Number(
              application.RentPaymentConsistency
            ),
          },

          transaction: {
            ...transaction,
            TransactionAmount: Number(transaction.TransactionAmount),
            TransactionDuration: Number(transaction.TransactionDuration),
            LoginAttempts: Number(transaction.LoginAttempts),
            AccountBalance: Number(transaction.AccountBalance),
            CustomerAge: Number(transaction.CustomerAge),
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
        "Unable to connect to CredMe API. Make sure the FastAPI server is running on port 4000."
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
              onChange={(v) => updateApplication("Age", v)}
            />

            <Field
              label="Annual Income"
              prefix="₹"
              value={application.AnnualIncome}
              onChange={(v) => updateApplication("AnnualIncome", v)}
            />

            <Field
              label="Credit Score"
              value={application.CreditScore}
              onChange={(v) => updateApplication("CreditScore", v)}
            />

            <Field
              label="Rent Payment Consistency (alt. data, thin-file only)"
              value={application.RentPaymentConsistency}
              suffix="%"
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
              onChange={(v) => updateApplication("LoanAmount", v)}
            />

            <Field
              label="Loan Duration"
              suffix="months"
              value={application.LoanDuration}
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
              onChange={(v) =>
                updateApplication("MonthlyIncome", v)
              }
            />

            <Field
              label="Monthly Debt Payments"
              prefix="₹"
              value={application.MonthlyDebtPayments}
              onChange={(v) =>
                updateApplication("MonthlyDebtPayments", v)
              }
            />

            <Field
              label="Debt-to-Income Ratio"
              value={application.DebtToIncomeRatio}
              suffix="%"
              onChange={(v) =>
                updateApplication("DebtToIncomeRatio", v)
              }
            />

            <Field
              label="Credit Utilization"
              value={application.CreditCardUtilizationRate}
              suffix="%"
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
              onChange={(v) =>
                updateApplication("TotalAssets", v)
              }
            />

            <Field
              label="Total Liabilities"
              prefix="₹"
              value={application.TotalLiabilities}
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
              <p>Real-time transaction and fraud signals</p>
            </div>
          </div>

          <div className="form-grid">
            <Field
              label="Transaction Amount"
              prefix="₹"
              value={transaction.TransactionAmount}
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
            CredMe evaluates creditworthiness and behavioral risk
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
                <span>Credit Confidence</span>

                <strong>
                  {result.credit_confidence}%
                </strong>

                <small>
                  {result.credit_strength}
                </small>
              </div>
            </div>

            {/* RISK CARDS */}

            <div className="result-grid">
              <div className="result-card">
                <div className="result-card-top">
                  <span>Credit Intelligence</span>

                  <span className="result-number">
                    {result.credit_confidence}%
                  </span>
                </div>

                <div className="progress">
                  <div
                    className="progress-fill credit"
                    style={{
                      width: `${Math.min(
                        result.credit_confidence,
                        100
                      )}%`,
                    }}
                  ></div>
                </div>

                <div className="result-footer">
                  <span>Credit Strength</span>
                  <strong>
                    {result.credit_strength}
                  </strong>
                </div>
              </div>

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
                    {result.behavioral_anomaly_score}
                  </strong>

                  <span>
                    behavioral anomaly score
                  </span>
                </div>

                <div className="result-footer">
                  <span>Anomaly Detection</span>

                  <strong>
                    {result.anomaly_detected
                      ? "DETECTED"
                      : "NORMAL"}
                  </strong>
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
                    Explainable AI assessment
                  </p>
                </div>
              </div>

              <p className="reasoning-text">
                {result.reasoning}
              </p>

              <div className="signal-section">
                <h4>Risk Signals</h4>

                {result.high_risk_signals?.length > 0 && (
                  <div className="signals">
                    {result.high_risk_signals.map(
                      (signal, index) => (
                        <div
                          className="signal high"
                          key={index}
                        >
                          <span>!</span>
                          {signal}
                        </div>
                      )
                    )}
                  </div>
                )}

                {result.medium_risk_signals?.length > 0 && (
                  <div className="signals">
                    {result.medium_risk_signals.map(
                      (signal, index) => (
                        <div
                          className="signal medium"
                          key={index}
                        >
                          <span>!</span>
                          {signal}
                        </div>
                      )
                    )}
                  </div>
                )}

                {result.high_risk_signals?.length === 0 &&
                  result.medium_risk_signals?.length === 0 && (
                    <div className="signal normal">
                      <span>✓</span>
                      No significant behavioral risk signals
                      detected.
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
                    Key factors influencing the model prediction
                  </p>
                </div>

                <span>SHAP</span>
              </div>

              <div className="drivers-list">
                {result.reasons?.map((reason, index) => (
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
                          {reason.effect}
                        </small>
                      </div>
                    </div>

                    <div
                      className={
                        reason.impact >= 0
                          ? "impact positive"
                          : "impact negative"
                      }
                    >
                      {reason.impact >= 0 ? "+" : ""}
                      {reason.impact}%
                    </div>
                  </div>
                ))}
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
}) {
  return (
    <label className="field">
      <span>{label}</span>

      <div className="input-wrapper">
        {prefix && (
          <span className="input-prefix">
            {prefix}
          </span>
        )}

        <input
          type="text"
          value={value}
          onChange={(e) =>
            onChange(e.target.value)
          }
        />

        {suffix && (
          <span className="input-suffix">
            {suffix}
          </span>
        )}
      </div>
    </label>
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