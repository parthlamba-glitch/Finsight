"""
Deterministic Deduplication Engine for FinSight.

Enforces deterministic duplicate prevention across bank syncs, statement imports,
and manual/voice transaction candidate ingestion.
"""

from decimal import Decimal
from datetime import datetime
from typing import Optional, Tuple
from sqlalchemy.orm import Session
from sqlalchemy import extract

from backend.models import Transaction
from backend.ingestion.normalizer import normalize_merchant_name


def is_duplicate_transaction(
    db: Session,
    account_id: int,
    user_id: int,
    amount: Decimal,
    transaction_date: datetime,
    merchant_name: Optional[str] = None,
    reference_id: Optional[str] = None,
) -> Tuple[bool, Optional[int], Optional[str]]:
    """
    Checks if a candidate transaction already exists in the database.

    Deterministic Check Order:
    1. Exact reference_id match within the account/user.
    2. Exact match on (account_id, user_id, amount, calendar_date, normalized_merchant).

    Args:
        db: SQLAlchemy session.
        account_id: Account ID to check.
        user_id: User ID to check.
        amount: Signed Decimal transaction amount.
        transaction_date: Datetime of the candidate transaction.
        merchant_name: Raw or cleaned merchant name string.
        reference_id: Optional external/bank/statement unique reference.

    Returns:
        (is_duplicate, existing_transaction_id, duplicate_reason)
    """
    # 1. Exact reference_id check
    if reference_id and reference_id.strip():
        clean_ref = reference_id.strip()
        existing_by_ref = (
            db.query(Transaction)
            .filter(
                Transaction.user_id == user_id,
                Transaction.account_id == account_id,
                Transaction.reference_id == clean_ref,
            )
            .first()
        )
        if existing_by_ref:
            return (
                True,
                existing_by_ref.id,
                f"Duplicate transaction reference '{clean_ref}' (Existing ID: {existing_by_ref.id})",
            )

    # 2. Content-tuple check on (account, user, amount, calendar date, normalized merchant)
    _, canonical_merchant = normalize_merchant_name(merchant_name)
    if not canonical_merchant:
        # Missing/empty merchant on candidate: insufficient information for secondary tuple duplicate detection
        return (False, None, None)

    same_day_txs = (
        db.query(Transaction)
        .filter(
            Transaction.user_id == user_id,
            Transaction.account_id == account_id,
            Transaction.amount == amount,
            extract("year", Transaction.transaction_date) == transaction_date.year,
            extract("month", Transaction.transaction_date) == transaction_date.month,
            extract("day", Transaction.transaction_date) == transaction_date.day,
        )
        .all()
    )

    for existing_tx in same_day_txs:
        _, existing_canonical = normalize_merchant_name(existing_tx.merchant_name)
        if existing_canonical and existing_canonical == canonical_merchant:
            return (
                True,
                existing_tx.id,
                f"Duplicate transaction on {transaction_date.strftime('%Y-%m-%d')} for amount {amount} with merchant '{merchant_name}'",
            )

    return (False, None, None)
