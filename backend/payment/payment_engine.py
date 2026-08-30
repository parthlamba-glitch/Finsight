"""
Deterministic Simulated Payment Engine for FinSight.

ARCHITECTURAL PRINCIPLES:
-------------------------
1. Simulation Only:
   - Zero external payment gateways (no Razorpay, Stripe, UPI, NPCI, or bank APIs).
2. Deterministic Execution:
   - All affordability checks and risk assessments are evaluated deterministically.
   - Zero LLM, NLP, voice, or prompt logic inside the payment engine.
3. Strict Money Conventions:
   - Payments are recorded as negative (-) expense transactions.
   - Authoritative balance is recalculated via SUM(transaction.amount) (Account.balance is never used).
4. User Ownership & Isolation:
   - Payments are strictly debited against user-owned active accounts.
"""

from decimal import Decimal
from datetime import datetime
from typing import Dict, Any, List
from sqlalchemy.orm import Session

from backend.models import User, Account, Transaction
from backend.engine import get_balance, check_affordability


def preview_payment(
    user_id: int,
    amount: Decimal,
    recipient_name: str,
    db: Session
) -> Dict[str, Any]:
    """
    Computes a deterministic pre-payment preview without executing any database writes.

    Evaluates:
    - User existence and input validation (amount > 0, recipient non-empty).
    - Current authoritative balance and upcoming 30-day bill commitments via check_affordability().
    - Risk level categorization ("low", "medium", "high").
    - Structured reasoning facts for accessible narration.

    Args:
        user_id: ID of the paying user.
        amount: Payment amount (Decimal, positive).
        recipient_name: Target payee name.
        db: SQLAlchemy database session.

    Returns:
        Dict:
        {
            "can_proceed": bool,
            "amount": Decimal,
            "recipient_name": str,
            "current_balance": Decimal,
            "balance_after": Decimal,
            "upcoming_bills": Decimal,
            "available_after_commitments": Decimal,
            "risk_level": str,
            "reasoning_facts": List[Dict[str, Any]]
        }

    Raises:
        ValueError: If user does not exist, amount <= 0, or recipient_name is empty.
    """
    if not recipient_name or not recipient_name.strip():
        raise ValueError("Recipient name must be a non-empty string.")

    cleaned_recipient = recipient_name.strip()

    if amount <= Decimal("0.00"):
        raise ValueError(f"Payment amount must be greater than zero, got {amount}.")

    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError(f"User with id {user_id} does not exist.")

    # 1. Authoritative balance from deterministic engine
    balance_info = get_balance(user_id, db)
    current_balance: Decimal = balance_info["balance"]

    # 2. Utilize existing deterministic affordability calculation
    affordability = check_affordability(user_id=user_id, amount=amount, db=db)

    can_proceed: bool = affordability["can_afford"]
    balance_after: Decimal = affordability["balance_after"]
    upcoming_bills: Decimal = affordability["upcoming_bills"]
    available_after_commitments: Decimal = balance_after - upcoming_bills

    # 3. Deterministic risk level evaluation
    if not can_proceed:
        risk_level = "high"
    elif available_after_commitments < Decimal("5000.00") or affordability["savings_goal_impact_months"] > 0:
        risk_level = "medium"
    else:
        risk_level = "low"

    reasoning_facts: List[Dict[str, Any]] = list(affordability["reasoning_facts"])
    reasoning_facts.append({"fact": "recipient_name", "value": cleaned_recipient})
    reasoning_facts.append({"fact": "can_proceed", "value": str(can_proceed)})
    reasoning_facts.append({"fact": "risk_level", "value": risk_level})

    return {
        "can_proceed": can_proceed,
        "amount": amount,
        "recipient_name": cleaned_recipient,
        "current_balance": current_balance,
        "balance_after": balance_after,
        "upcoming_bills": upcoming_bills,
        "available_after_commitments": available_after_commitments,
        "risk_level": risk_level,
        "reasoning_facts": reasoning_facts,
    }


def execute_payment(
    user_id: int,
    amount: Decimal,
    recipient_name: str,
    db: Session
) -> Dict[str, Any]:
    """
    Executes a simulated payment by creating a negative transaction record on the user's active account.

    Execution Flow:
    1. Runs preview_payment() to validate inputs, balance, and commitments.
    2. If preview indicates payment cannot proceed, raises ValueError and writes NO records.
    3. Locates user's active account (enforcing ownership).
    4. Creates a negative expense Transaction (-amount) with merchant_name=recipient_name.
    5. Commits transaction and recalculates authoritative balance via get_balance().

    Args:
        user_id: ID of the paying user.
        amount: Payment amount (Decimal, positive).
        recipient_name: Target payee name.
        db: SQLAlchemy database session.

    Returns:
        Dict:
        {
            "success": True,
            "transaction_id": int,
            "recipient_name": str,
            "amount": Decimal,
            "previous_balance": Decimal,
            "new_balance": Decimal,
            "transaction_type": "expense"
        }

    Raises:
        ValueError: If preview fails, user does not exist, or no active account is found.
    """
    # 1. Run deterministic preview
    preview = preview_payment(user_id=user_id, amount=amount, recipient_name=recipient_name, db=db)

    if not preview["can_proceed"]:
        raise ValueError(
            f"Payment cannot proceed: insufficient funds or commitments for user {user_id} "
            f"(required: ₹{amount}, available after commitments: ₹{preview['available_after_commitments']})."
        )

    # 2. Locate active user account
    account = (
        db.query(Account)
        .filter(Account.user_id == user_id, Account.is_active == True)
        .first()
    )
    if not account:
        raise ValueError(f"No active account found for user {user_id}.")

    # 3. Create negative transaction
    negative_amount = -abs(amount)
    tx = Transaction(
        account_id=account.id,
        user_id=user_id,
        amount=negative_amount,
        currency="INR",
        transaction_type="expense",
        category="Other",
        merchant_name=preview["recipient_name"],
        description=f"Simulated payment to {preview['recipient_name']}",
        source="payment",
        transaction_date=datetime.now(),
        is_suspicious=False,
    )

    db.add(tx)
    db.commit()
    db.refresh(tx)

    # 4. Authoritative balance recalculation (never uses Account.balance)
    updated_balance_info = get_balance(user_id, db)
    new_balance: Decimal = updated_balance_info["balance"]

    return {
        "success": True,
        "transaction_id": tx.id,
        "recipient_name": preview["recipient_name"],
        "amount": amount,
        "previous_balance": preview["current_balance"],
        "new_balance": new_balance,
        "transaction_type": "expense",
    }
