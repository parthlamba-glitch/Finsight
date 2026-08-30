"""
Transaction Normalizer for FinSight.

Validates and normalizes raw transaction inputs from any source (bank feed, statement, voice)
into clean, Decimal-safe attributes following the FinSight money sign convention.
"""

from decimal import Decimal
from datetime import datetime, date
from typing import Optional, Dict, Any, Tuple
import re

from backend.models.transaction import VALID_TRANSACTION_TYPES, VALID_CATEGORIES, VALID_SOURCES


def normalize_merchant_name(merchant: Optional[str]) -> Tuple[Optional[str], str]:
    """
    Normalizes merchant strings by stripping whitespace, collapsing multiple spaces,
    and generating a canonical lowercased comparison key for deduplication.

    Returns:
        (clean_display_name, canonical_search_key)
    """
    if not merchant or not merchant.strip():
        return (None, "")

    # Collapse multiple whitespace characters into single space
    cleaned = re.sub(r"\s+", " ", merchant.strip())
    # Canonical key for deduplication comparison (lowercase, trimmed)
    canonical = cleaned.lower()
    return (cleaned, canonical)


def normalize_transaction_input(
    amount: Decimal,
    transaction_type: str,
    category: str,
    merchant_name: Optional[str] = None,
    description: Optional[str] = None,
    transaction_date: Optional[Any] = None,
    source: str = "bank",
    reference_id: Optional[str] = None,
) -> Dict[str, Any]:
    """
    Validates and normalizes transaction inputs.

    Money Sign Convention:
    - Input amount MUST be positive (> 0).
    - If transaction_type is 'expense': database amount is converted to -abs(amount).
    - If transaction_type is 'income': database amount is converted to +abs(amount).

    Returns:
        Dict of validated, normalized attributes ready for database insertion.

    Raises:
        ValueError: If amount <= 0, transaction_type is invalid, category is invalid, or source is invalid.
    """
    # 1. Decimal validation
    if not isinstance(amount, Decimal):
        amount = Decimal(str(amount))

    if amount <= Decimal("0.00"):
        raise ValueError(f"Input transaction amount must be positive, got {amount}.")

    # 2. Transaction type validation & sign convention
    clean_type = transaction_type.strip().lower() if transaction_type else ""
    if clean_type not in VALID_TRANSACTION_TYPES:
        raise ValueError(f"Invalid transaction_type '{transaction_type}'. Must be one of: {sorted(VALID_TRANSACTION_TYPES)}")

    signed_amount = -abs(amount) if clean_type == "expense" else abs(amount)

    # 3. Category validation
    clean_category = category.strip() if category else "Other"
    # Case-insensitive match against VALID_CATEGORIES
    matched_cat = next((c for c in VALID_CATEGORIES if c.lower() == clean_category.lower()), None)
    if not matched_cat:
        raise ValueError(f"Invalid category '{category}'. Must be one of: {sorted(VALID_CATEGORIES)}")

    # 4. Source validation
    clean_source = source.strip().lower() if source else "bank"
    if clean_source not in VALID_SOURCES:
        raise ValueError(f"Invalid source '{source}'. Must be one of: {sorted(VALID_SOURCES)}")

    # 5. Merchant normalization
    clean_merchant, canonical_merchant = normalize_merchant_name(merchant_name)

    # 6. Date normalization
    if transaction_date is None:
        normalized_date = datetime.now()
    elif isinstance(transaction_date, datetime):
        normalized_date = transaction_date
    elif isinstance(transaction_date, date):
        normalized_date = datetime.combine(transaction_date, datetime.min.time())
    elif isinstance(transaction_date, str):
        try:
            normalized_date = datetime.fromisoformat(transaction_date)
        except ValueError:
            # Try date-only format
            try:
                d = date.fromisoformat(transaction_date)
                normalized_date = datetime.combine(d, datetime.min.time())
            except ValueError:
                raise ValueError(f"Invalid ISO date string format: '{transaction_date}'.")
    else:
        raise ValueError(f"Unsupported transaction_date type: {type(transaction_date)}")

    clean_ref = reference_id.strip() if reference_id and reference_id.strip() else None
    clean_desc = description.strip() if description and description.strip() else None

    return {
        "amount": signed_amount,
        "input_amount": amount,
        "transaction_type": clean_type,
        "category": matched_cat,
        "merchant_name": clean_merchant,
        "canonical_merchant": canonical_merchant,
        "description": clean_desc,
        "source": clean_source,
        "reference_id": clean_ref,
        "transaction_date": normalized_date,
    }
