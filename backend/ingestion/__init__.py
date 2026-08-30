"""
Unified Transaction Ingestion Package for FinSight.

Provides normalization, deduplication, mock bank synchronization, and statement ingestion boundaries.
"""

from backend.ingestion.normalizer import (
    normalize_transaction_input,
    normalize_merchant_name,
)
from backend.ingestion.deduplicator import is_duplicate_transaction
from backend.ingestion.bank_sync import sync_mock_bank_transactions

__all__ = [
    "normalize_transaction_input",
    "normalize_merchant_name",
    "is_duplicate_transaction",
    "sync_mock_bank_transactions",
]
