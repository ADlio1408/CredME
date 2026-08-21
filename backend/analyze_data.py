import pandas as pd


# ============================================================
# CREDME — DATA ANALYSIS
# ============================================================

print("=" * 60)
print("CREDME DATA ANALYSIS")
print("=" * 60)


# ============================================================
# LOAD DATASETS
# ============================================================

loan_df = pd.read_csv(
    "data/Loan.csv"
)

transaction_df = pd.read_csv(
    "data/bank_transactions_data_2.csv"
)


# ============================================================
# LOAN DATASET
# ============================================================

print("\nLOAN DATASET")
print("-" * 60)


print(
    f"Rows: {loan_df.shape[0]}"
)

print(
    f"Columns: {loan_df.shape[1]}"
)


# ------------------------------------------------------------
# Loan approval distribution
# ------------------------------------------------------------

print(
    "\nLoan Approval Distribution:"
)

print(
    loan_df[
        "LoanApproved"
    ].value_counts()
)


print(
    "\nLoan Approval Percentage:"
)

print(
    (
        loan_df[
            "LoanApproved"
        ]
        .value_counts(
            normalize=True
        )
        * 100
    )
    .round(2)
)


# ------------------------------------------------------------
# Thin-file / credit history analysis
# ------------------------------------------------------------

print(
    "\nCredit History Analysis:"
)

if "CreditScore" in loan_df.columns:

    thin_file_count = (
        loan_df[
            "CreditScore"
        ] == 0
    ).sum()

    credit_history_count = (
        loan_df[
            "CreditScore"
        ] > 0
    ).sum()

    print(
        f"Thin-file applicants "
        f"(CreditScore = 0): "
        f"{thin_file_count}"
    )

    print(
        f"Applicants with credit "
        f"history: "
        f"{credit_history_count}"
    )

    print(
        f"Thin-file percentage: "
        f"{thin_file_count / len(loan_df) * 100:.2f}%"
    )

else:

    print(
        "CreditScore column not found."
    )


# ------------------------------------------------------------
# HasCreditHistory feature
# ------------------------------------------------------------

if "HasCreditHistory" in loan_df.columns:

    print(
        "\nHasCreditHistory Distribution:"
    )

    print(
        loan_df[
            "HasCreditHistory"
        ].value_counts()
    )

else:

    print(
        "\nHasCreditHistory is not "
        "stored in the raw dataset."
    )

    print(
        "It is generated during "
        "model training from CreditScore."
    )


# ------------------------------------------------------------
# Missing values
# ------------------------------------------------------------

print(
    "\nMissing Values:"
)

missing = (
    loan_df
    .isnull()
    .sum()
)

missing = (
    missing[
        missing > 0
    ]
)

if len(missing) > 0:

    print(
        missing
    )

else:

    print(
        "No missing values."
    )


# ------------------------------------------------------------
# Duplicate rows
# ------------------------------------------------------------

print(
    f"\nDuplicate Rows: "
    f"{loan_df.duplicated().sum()}"
)


# ============================================================
# TRANSACTION DATASET
# ============================================================

print(
    "\nTRANSACTION DATASET"
)

print(
    "-" * 60
)


print(
    f"Rows: "
    f"{transaction_df.shape[0]}"
)

print(
    f"Columns: "
    f"{transaction_df.shape[1]}"
)


# ------------------------------------------------------------
# Number of accounts
# ------------------------------------------------------------

print(
    "\nNumber of Accounts:"
)

print(
    transaction_df[
        "AccountID"
    ].nunique()
)


# ------------------------------------------------------------
# Transaction types
# ------------------------------------------------------------

print(
    "\nTransaction Types:"
)

print(
    transaction_df[
        "TransactionType"
    ].value_counts()
)


# ------------------------------------------------------------
# Channels
# ------------------------------------------------------------

print(
    "\nChannels:"
)

print(
    transaction_df[
        "Channel"
    ].value_counts()
)


# ------------------------------------------------------------
# Transaction amount statistics
# ------------------------------------------------------------

if "TransactionAmount" in transaction_df.columns:

    print(
        "\nTransaction Amount Statistics:"
    )

    print(
        transaction_df[
            "TransactionAmount"
        ]
        .describe()
        .round(2)
    )


# ------------------------------------------------------------
# Login attempt statistics
# ------------------------------------------------------------

if "LoginAttempts" in transaction_df.columns:

    print(
        "\nLogin Attempt Statistics:"
    )

    print(
        transaction_df[
            "LoginAttempts"
        ]
        .describe()
        .round(2)
    )


# ------------------------------------------------------------
# Transaction duration statistics
# ------------------------------------------------------------

if "TransactionDuration" in transaction_df.columns:

    print(
        "\nTransaction Duration Statistics:"
    )

    print(
        transaction_df[
            "TransactionDuration"
        ]
        .describe()
        .round(2)
    )


# ------------------------------------------------------------
# Account balance statistics
# ------------------------------------------------------------

if "AccountBalance" in transaction_df.columns:

    print(
        "\nAccount Balance Statistics:"
    )

    print(
        transaction_df[
            "AccountBalance"
        ]
        .describe()
        .round(2)
    )


# ------------------------------------------------------------
# Missing values
# ------------------------------------------------------------

print(
    "\nMissing Values:"
)

missing = (
    transaction_df
    .isnull()
    .sum()
)

missing = (
    missing[
        missing > 0
    ]
)

if len(missing) > 0:

    print(
        missing
    )

else:

    print(
        "No missing values."
    )


# ------------------------------------------------------------
# Duplicate rows
# ------------------------------------------------------------

print(
    f"\nDuplicate Rows: "
    f"{transaction_df.duplicated().sum()}"
)


# ============================================================
# FINAL SUMMARY
# ============================================================

print(
    "\n" + "=" * 60
)

print(
    "CREDME DATA ANALYSIS COMPLETE"
)

print(
    "=" * 60
)