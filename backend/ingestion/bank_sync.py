"""
Deterministic Mock Bank Sync Engine for FinSight.

Simulates financial institution synchronization with deterministic transactions,
sign normalization, and duplicate prevention.
"""

from decimal import Decimal
from datetime import datetime
from typing import Dict, Any, List, Optional
from sqlalchemy.orm import Session

from backend.models import User, Account, Transaction
from backend.ingestion.normalizer import normalize_transaction_input
from backend.ingestion.deduplicator import is_duplicate_transaction


def get_deterministic_mock_bank_feed() -> List[Dict[str, Any]]:
    """
    Returns a deterministic batch of raw mock bank feed items for synchronization.
    """
    return [
        {
            "amount": Decimal("450.00"),
            "transaction_type": "expense",
            "category": "Food",
            "merchant_name": "Swiggy",
            "description": "Lunch delivery order",
            "transaction_date": datetime(2026, 8, 27, 13, 30, 0),
            "reference_id": "MOCK-HDFC-20260827-01",
        },
        {
            "amount": Decimal("320.00"),
            "transaction_type": "expense",
            "category": "Transport",
            "merchant_name": "Uber India",
            "description": "Cab ride to office",
            "transaction_date": datetime(2026, 8, 27, 18, 45, 0),
            "reference_id": "MOCK-HDFC-20260827-02",
        },
        {
            "amount": Decimal("1299.00"),
            "transaction_type": "expense",
            "category": "Shopping",
            "merchant_name": "Amazon India",
            "description": "Wireless earbuds purchase",
            "transaction_date": datetime(2026, 8, 27, 20, 15, 0),
            "reference_id": "MOCK-HDFC-20260827-03",
        },
        {
            "amount": Decimal("15000.00"),
            "transaction_type": "income",
            "category": "Other",
            "merchant_name": "Tech Solutions Consulting",
            "description": "Freelance consulting payout",
            "transaction_date": datetime(2026, 8, 27, 11, 0, 0),
            "reference_id": "MOCK-HDFC-20260827-04",
        },
    ]


def sync_mock_bank_transactions(
    user_id: int,
    db: Session,
    account_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Synchronizes mock bank transactions into the user's account.

    Guarantees:
    - Validates user existence and account ownership.
    - Runs deterministic deduplication against existing database transactions.
    - Inserts only un-imported transactions with source='bank'.
    - Repeated calls skip all already-imported items.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise ValueError(f"User with id {user_id} does not exist.")

    # Locate account with ownership verification
    if account_id:
        account = db.query(Account).filter(Account.id == account_id, Account.user_id == user_id).first()
        if not account:
            raise ValueError(f"Account with id {account_id} not found or does not belong to user {user_id}.")
    else:
        account = db.query(Account).filter(Account.user_id == user_id, Account.is_active == True).first()
        if not account:
            raise ValueError(f"No active account found for user {user_id}.")

    raw_feed = get_deterministic_mock_bank_feed()
    imported_txs: List[Transaction] = []
    skipped_items: List[Dict[str, Any]] = []

    for item in raw_feed:
        normalized = normalize_transaction_input(
            amount=item["amount"],
            transaction_type=item["transaction_type"],
            category=item["category"],
            merchant_name=item["merchant_name"],
            description=item["description"],
            transaction_date=item["transaction_date"],
            source="bank",
            reference_id=item["reference_id"],
        )

        is_dup, dup_id, dup_reason = is_duplicate_transaction(
            db=db,
            account_id=account.id,
            user_id=user_id,
            amount=normalized["amount"],
            transaction_date=normalized["transaction_date"],
            merchant_name=normalized["merchant_name"],
            reference_id=normalized["reference_id"],
        )

        if is_dup:
            skipped_items.append({
                "reference_id": normalized["reference_id"],
                "merchant_name": normalized["merchant_name"],
                "amount": str(normalized["amount"]),
                "reason": dup_reason,
                "existing_transaction_id": dup_id,
            })
        else:
            new_tx = Transaction(
                account_id=account.id,
                user_id=user_id,
                amount=normalized["amount"],
                currency="INR",
                transaction_type=normalized["transaction_type"],
                category=normalized["category"],
                merchant_name=normalized["merchant_name"],
                description=normalized["description"],
                source="bank",
                reference_id=normalized["reference_id"],
                transaction_date=normalized["transaction_date"],
                is_suspicious=False,
            )
            db.add(new_tx)
            db.flush()
            imported_txs.append(new_tx)

    db.commit()

    for tx in imported_txs:
        db.refresh(tx)

    return {
        "status": "success",
        "user_id": user_id,
        "account_id": account.id,
        "imported_count": len(imported_txs),
        "duplicate_count": len(skipped_items),
        "skipped_count": len(skipped_items),
        "imported_transactions": imported_txs,
        "skipped_transactions": skipped_items,
    }
