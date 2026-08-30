"""
Bill model for FinSight.

Status Semantics:
- 'unpaid': Bill has been generated/scheduled but not yet settled.
- 'paid': Bill has been settled.
- 'overdue': Due date has passed without settlement.

The deterministic affordability engine will consider unpaid upcoming bills.
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Set
from sqlalchemy import Column, Integer, String, Boolean, DateTime, Date, Numeric, ForeignKey
from sqlalchemy.orm import relationship, validates
from backend.db import Base

VALID_BILL_STATUSES: Set[str] = {"unpaid", "paid", "overdue"}


class Bill(Base):
    __tablename__ = "bills"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    amount = Column(Numeric(12, 2), nullable=False)
    currency = Column(String(3), default="INR", nullable=False)
    category = Column(String(50), nullable=False)
    due_date = Column(Date, index=True, nullable=False)
    frequency = Column(String(50), default="monthly", nullable=False)  # monthly, weekly, yearly, one_time
    status = Column(String(50), default="unpaid", nullable=False)  # unpaid, paid, overdue
    is_recurring = Column(Boolean, default=True, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="bills")

    @validates("status")
    def validate_status(self, key: str, value: str) -> str:
        if value not in VALID_BILL_STATUSES:
            raise ValueError(f"Invalid bill status '{value}'. Must be one of: {VALID_BILL_STATUSES}")
        return value

    def __repr__(self) -> str:
        return (
            f"<Bill(id={self.id}, user_id={self.user_id}, name='{self.name}', "
            f"amount={self.amount}, due_date='{self.due_date}', status='{self.status}')>"
        )
