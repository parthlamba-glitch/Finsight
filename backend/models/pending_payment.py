"""
PendingPayment Model for FinSight.

Persists payment confirmation state in the database to survive browser
reloads and prevent re-execution or token tampering.
"""

from datetime import datetime, timedelta
from decimal import Decimal
from sqlalchemy import Column, Integer, String, Numeric, DateTime, ForeignKey
from sqlalchemy.orm import relationship

from backend.db import Base

VALID_PENDING_PAYMENT_STATUSES = {"pending", "executed", "expired", "cancelled"}


class PendingPayment(Base):
    """
    SQLAlchemy model for persistent pending payments awaiting explicit user confirmation.
    """
    __tablename__ = "pending_payments"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    amount = Column(Numeric(12, 2), nullable=False)
    recipient_name = Column(String(255), nullable=False)
    status = Column(String(50), default="pending", nullable=False, index=True)
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    # Relationships
    user = relationship("User", backref="pending_payments", passive_deletes=True)


    def is_expired(self, current_time: datetime = None) -> bool:
        """Returns True if the pending payment has passed its expiration time."""
        now = current_time or datetime.utcnow()
        return now > self.expires_at

    def __repr__(self) -> str:
        return (
            f"<PendingPayment(id={self.id}, user_id={self.user_id}, "
            f"amount={self.amount}, recipient='{self.recipient_name}', status='{self.status}')>"
        )
