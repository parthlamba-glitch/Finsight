"""
Goal model for FinSight.
All monetary amounts use Decimal-safe Numeric(12, 2).
"""

from datetime import datetime, date
from decimal import Decimal
from typing import Set
from sqlalchemy import Column, Integer, String, DateTime, Date, Numeric, ForeignKey
from sqlalchemy.orm import relationship, validates
from backend.db import Base

VALID_GOAL_STATUSES: Set[str] = {"active", "completed", "paused"}


class Goal(Base):
    __tablename__ = "goals"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    name = Column(String(255), nullable=False)
    target_amount = Column(Numeric(12, 2), nullable=False)
    current_amount = Column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    monthly_contribution = Column(Numeric(12, 2), default=Decimal("0.00"), nullable=False)
    currency = Column(String(3), default="INR", nullable=False)
    target_date = Column(Date, nullable=True)
    status = Column(String(50), default="active", nullable=False)  # active, completed, paused
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", back_populates="goals")

    @validates("status")
    def validate_status(self, key: str, value: str) -> str:
        if value not in VALID_GOAL_STATUSES:
            raise ValueError(f"Invalid goal status '{value}'. Must be one of: {VALID_GOAL_STATUSES}")
        return value

    def __repr__(self) -> str:
        return (
            f"<Goal(id={self.id}, user_id={self.user_id}, name='{self.name}', "
            f"target={self.target_amount}, current={self.current_amount}, status='{self.status}')>"
        )
