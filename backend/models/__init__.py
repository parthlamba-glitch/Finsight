"""
FinSight Models Package.
Exports all SQLAlchemy ORM models and constants.
"""

from backend.db import Base
from backend.models.user import User, DEFAULT_ACCESSIBILITY_PREFS
from backend.models.account import Account
from backend.models.transaction import (
    Transaction,
    VALID_TRANSACTION_TYPES,
    VALID_CATEGORIES,
)
from backend.models.goal import Goal, VALID_GOAL_STATUSES
from backend.models.bill import Bill, VALID_BILL_STATUSES
from backend.models.document import Document
from backend.models.pending_payment import PendingPayment, VALID_PENDING_PAYMENT_STATUSES
from backend.models.passkey import PasskeyCredential, AuthChallenge

__all__ = [
    "Base",
    "User",
    "Account",
    "Transaction",
    "Goal",
    "Bill",
    "Document",
    "PendingPayment",
    "PasskeyCredential",
    "AuthChallenge",
    "DEFAULT_ACCESSIBILITY_PREFS",
    "VALID_TRANSACTION_TYPES",
    "VALID_CATEGORIES",
    "VALID_GOAL_STATUSES",
    "VALID_BILL_STATUSES",
    "VALID_PENDING_PAYMENT_STATUSES",
]

