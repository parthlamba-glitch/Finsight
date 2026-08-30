"""
Transaction model for FinSight.

NON-NEGOTIABLE MONEY SIGN CONVENTION:
-------------------------------------
- Positive amount (+): Money entering the account (e.g., Salary = +75000.00, Opening Balance = +25000.00, Refund = +450.00).
- Negative amount (-): Money leaving the account (e.g., Rent = -18000.00, Food = -620.00, Bills = -1500.00).

Authoritative Balance:
----------------------
SUM(transaction.amount) for all transactions belonging to the user's accounts
constitutes the true, authoritative balance.

Transaction Types (MVP):
- 'income'
- 'expense'

Transaction Categories:
- 'Food', 'Transport', 'Shopping', 'Bills', 'Entertainment', 'Healthcare', 'Education', 'Other'
"""

from datetime import datetime
from decimal import Decimal
from typing import Set
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Numeric, ForeignKey
from sqlalchemy.orm import relationship, validates
from backend.db import Base

VALID_TRANSACTION_TYPES: Set[str] = {"income", "expense"}

VALID_CATEGORIES: Set[str] = {
    "Food",
    "Transport",
    "Shopping",
    "Bills",
    "Entertainment",
    "Healthcare",
    "Education",
    "Other",
}

VALID_SOURCES: Set[str] = {
    "bank",
    "statement",
    "voice",
    "payment",
    "manual",
}


class Transaction(Base):
    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    account_id = Column(Integer, ForeignKey("accounts.id", ondelete="CASCADE"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    amount = Column(Numeric(12, 2), nullable=False)  # Signed: Positive = Inflow, Negative = Outflow
    currency = Column(String(3), default="INR", nullable=False)
    transaction_type = Column(String(20), nullable=False)  # 'income' or 'expense'
    category = Column(String(50), nullable=False)  # Food, Transport, Shopping, Bills, etc.
    merchant_name = Column(String(255), nullable=True)
    description = Column(String(500), nullable=True)
    source = Column(String(50), nullable=False, default="bank")  # 'bank', 'statement', 'voice', 'payment', 'manual'
    reference_id = Column(String(255), nullable=True, index=True)  # External/statement/bank transaction ID
    transaction_date = Column(DateTime, index=True, nullable=False, default=datetime.utcnow)
    is_suspicious = Column(Boolean, default=False, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    account = relationship("Account", back_populates="transactions")
    user = relationship("User", back_populates="transactions")

    @validates("transaction_type")
    def validate_transaction_type(self, key: str, value: str) -> str:
        if value not in VALID_TRANSACTION_TYPES:
            raise ValueError(f"Invalid transaction_type '{value}'. Must be one of: {VALID_TRANSACTION_TYPES}")
        return value

    @validates("category")
    def validate_category(self, key: str, value: str) -> str:
        if value not in VALID_CATEGORIES:
            raise ValueError(f"Invalid category '{value}'. Must be one of: {VALID_CATEGORIES}")
        return value

    @validates("source")
    def validate_source(self, key: str, value: str) -> str:
        if value not in VALID_SOURCES:
            raise ValueError(f"Invalid source '{value}'. Must be one of: {VALID_SOURCES}")
        return value

    def __repr__(self) -> str:
        return (
            f"<Transaction(id={self.id}, user_id={self.user_id}, account_id={self.account_id}, "
            f"amount={self.amount}, category='{self.category}', source='{self.source}', date='{self.transaction_date}')>"
        )
