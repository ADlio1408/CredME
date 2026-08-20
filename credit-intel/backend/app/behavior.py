"""
Alternative-data / behavioral signal engine.

This is the "thin-file" lever: for applicants with sparse or no bureau
history, transaction-level behavior (velocity, balance stability, login
anomalies, channel mix) gives a secondary, real-time trust signal that
can support or temper the bureau-based score.

Honesty note: bank_transactions_data_2.csv and Loan.csv do not share a
customer key in this dataset, so in this prototype behavioral scoring is
computed per AccountID and exposed as an independent lookup + fusion
input. In production this would join on a single Customer/Party ID from
the core banking system.
"""
import os
from functools import lru_cache

import numpy as np
import pandas as pd

THIS_DIR = os.path.dirname(os.path.abspath(__file__))
TX_PATH = os.path.join(THIS_DIR, "..", "data", "bank_transactions_data_2.csv")


@lru_cache(maxsize=1)
def _load_tx() -> pd.DataFrame:
    df = pd.read_csv(TX_PATH, parse_dates=["TransactionDate", "PreviousTransactionDate"])
    return df


def list_accounts() -> list[str]:
    df = _load_tx()
    return sorted(df["AccountID"].unique().tolist())


def get_behavior_profile(account_id: str) -> dict:
    """
    Computes a 0-100 BehavioralTrustScore for an account from its
    transaction history, plus the underlying signals so the score is
    explainable rather than a black box.
    """
    df = _load_tx()
    acct = df[df["AccountID"] == account_id]
    if acct.empty:
        return None

    n_tx = len(acct)
    avg_balance = float(acct["AccountBalance"].mean())
    balance_volatility = float(acct["AccountBalance"].std(ddof=0)) if n_tx > 1 else 0.0
    balance_stability = 1.0 - min(balance_volatility / max(avg_balance, 1.0), 1.0)

    avg_login_attempts = float(acct["LoginAttempts"].mean())
    login_anomaly_rate = float((acct["LoginAttempts"] > 1).mean())

    channel_mix = acct["Channel"].value_counts(normalize=True).to_dict()
    online_share = float(channel_mix.get("Online", 0.0))

    tx_dates = acct["TransactionDate"].sort_values()
    if n_tx > 2:
        gaps_days = tx_dates.diff().dt.total_seconds().dropna() / 86400
        mean_gap = gaps_days.mean()
        std_gap = gaps_days.std(ddof=0)  # ddof=0: defined even with few samples
        tx_regularity = 1.0 - min(float(std_gap / mean_gap), 1.0) if mean_gap else 0.5
    else:
        # Not enough gaps to judge a pattern - neutral prior rather than
        # letting a single-gap sample (std undefined) poison the score.
        tx_regularity = 0.5

    debit_ratio = float((acct["TransactionType"] == "Debit").mean())
    avg_tx_amount = float(acct["TransactionAmount"].mean())

    # Weighted composite -> 0-100. Weights are illustrative and should be
    # calibrated against real outcome data (e.g. downstream default rates)
    # before production use.
    score = (
        0.30 * balance_stability
        + 0.25 * (1 - login_anomaly_rate)
        + 0.20 * tx_regularity
        + 0.15 * min(avg_balance / 10000, 1.0)
        + 0.10 * (1 - min(online_share, 1.0) * 0.3)  # slight caution on all-online activity, not punitive
    ) * 100

    score = float(np.clip(score, 0, 100))

    return {
        "account_id": account_id,
        "behavioral_trust_score": round(score, 1),
        "signals": {
            "transaction_count": n_tx,
            "avg_account_balance": round(avg_balance, 2),
            "balance_stability_index": round(balance_stability, 3),
            "avg_login_attempts": round(avg_login_attempts, 2),
            "login_anomaly_rate": round(login_anomaly_rate, 3),
            "transaction_regularity_index": round(tx_regularity, 3),
            "online_channel_share": round(online_share, 3),
            "debit_ratio": round(debit_ratio, 3),
            "avg_transaction_amount": round(avg_tx_amount, 2),
        },
    }
