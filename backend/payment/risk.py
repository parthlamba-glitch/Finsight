"""
Deterministic Payment Risk Evaluation for FinSight.

Evaluates transaction safety and anomaly signals using strictly deterministic
rules against the user's historical ledger. Zero stochastic or LLM models.
"""

from decimal import Decimal
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from backend.models import User, Account, Transaction
from backend.engine import get_balance


def evaluate_payment_risk(
    user_id: int,
    amount: Decimal,
    recipient_name: str,
    db: Session,
) -> Dict[str, Any]:
    """
    Deterministically evaluates payment risk based on historical spending baselines
    and account balance ratios.

    Deterministic Rules:
    1. Balance Ratio: If payment > 50% of authoritative balance, flag warning.
    2. Velocity/Spike: If payment > 3x average historical expense or > 2x max single expense.
    3. First-time Recipient: If recipient has never been paid before and amount >= ₹5,000.
    4. New Account / No History: If user has no historical expenses and amount >= ₹10,000.

    Args:
        user_id: ID of the user initiating the payment.
        amount: Proposed payment amount (Decimal, positive).
        recipient_name: Payee/Recipient name.
        db: SQLAlchemy database session.

    Returns:
        Dict:
        {
            "fraud_warning": bool,
            "risk_level": "low" | "medium" | "high",
            "risk_reasons": List[str],
        }
    """
    if not isinstance(amount, Decimal):
        amount = Decimal(str(amount))

    # 1. Fetch authoritative balance
    balance_info = get_balance(user_id, db)
    current_balance: Decimal = balance_info["balance"]

    # 2. Fetch past expense transactions
    transactions = (
        db.query(Transaction)
        .join(Account, Transaction.account_id == Account.id)
        .filter(
            Account.user_id == user_id,
            Transaction.user_id == user_id,
            Transaction.amount < Decimal("0.00"),
        )
        .all()
    )

    risk_reasons: List[str] = []
    is_high_risk = False

    # Check recipient history
    cleaned_recipient = recipient_name.strip().lower() if recipient_name else ""
    known_recipients = {
        (t.merchant_name or "").strip().lower()
        for t in transactions
        if t.merchant_name
    }

    if transactions:
        expenses = [abs(t.amount) for t in transactions]
        max_expense = max(expenses)
        avg_expense = sum(expenses, Decimal("0.00")) / Decimal(len(expenses))

        # Check 1: Exceeds historical spending patterns
        if max_expense > Decimal("0.00") and amount > (max_expense * Decimal("2.0")):
            is_high_risk = True
            risk_reasons.append(
                f"Payment amount (₹{amount:.2f}) is significantly above the user's maximum past single expense (₹{max_expense:.2f})."
            )
        elif avg_expense > Decimal("0.00") and amount > (avg_expense * Decimal("3.0")):
            is_high_risk = True
            risk_reasons.append(
                f"Payment amount (₹{amount:.2f}) is over 3 times the user's average historical expense (₹{avg_expense:.2f})."
            )

        # Check 2: First-time recipient for significant amount
        if cleaned_recipient and cleaned_recipient not in known_recipients and amount >= Decimal("5000.00"):
            risk_reasons.append(
                f"Recipient '{recipient_name.strip()}' has no previous payment history with this account."
            )
    else:
        # No prior transaction history
        if amount >= Decimal("10000.00"):
            is_high_risk = True
            risk_reasons.append(
                f"Large payment amount (₹{amount:.2f}) on an account with no prior expense history."
            )

    # Check 3: Large portion of authoritative balance
    if current_balance > Decimal("0.00") and amount > (current_balance * Decimal("0.50")):
        is_high_risk = True
        risk_reasons.append(
            f"Payment amount (₹{amount:.2f}) represents more than 50% of the total account balance (₹{current_balance:.2f})."
        )

    # Determine final risk_level and fraud_warning flag
    if is_high_risk:
        risk_level = "high"
        fraud_warning = True
    elif risk_reasons:
        risk_level = "medium"
        fraud_warning = False
    else:
        risk_level = "low"
        fraud_warning = False

    return {
        "fraud_warning": fraud_warning,
        "risk_level": risk_level,
        "risk_reasons": risk_reasons,
    }
