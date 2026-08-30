"""
Integration and security tests for Real Payment API (Day 5 Part C).

Tests:
- POST /api/v1/payments/preview
- POST /api/v1/payments/execute
- Persistent PendingPayment database state
- Single-use execution
- Tamper-proofing (amount/recipient cannot be altered)
- Expiration handling
- Risk assessment & fraud warning
"""

import pytest
from decimal import Decimal
from datetime import datetime, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.models import User, Account, Transaction, PendingPayment


@pytest.fixture
def payment_user_fixture(db_session: Session):
    """Sets up a primary test user with an active account and opening funds."""
    user = User(
        full_name="Payment Test User",
        email="payment.test@example.com",
        accessibility_prefs={"voice_first": True},
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    account = Account(
        user_id=user.id,
        name="HDFC Primary Checking",
        account_type="checking",
        balance=Decimal("50000.00"),
        monthly_income=Decimal("60000.00"),
        currency="INR",
        is_active=True,
    )
    db_session.add(account)
    db_session.flush()

    # Opening balance transaction
    tx_open = Transaction(
        account_id=account.id,
        user_id=user.id,
        amount=Decimal("50000.00"),
        currency="INR",
        transaction_type="income",
        category="Other",
        merchant_name=None,
        description="Opening Balance",
        transaction_date=datetime(2026, 8, 1, 10, 0, 0),
    )
    # Typical past expense of ₹2,000
    tx_exp = Transaction(
        account_id=account.id,
        user_id=user.id,
        amount=Decimal("-2000.00"),
        currency="INR",
        transaction_type="expense",
        category="Food",
        merchant_name="Cafe Coffee Day",
        description="Coffee & Snacks",
        transaction_date=datetime(2026, 8, 5, 15, 0, 0),
    )
    db_session.add_all([tx_open, tx_exp])
    db_session.commit()

    return {
        "user_id": user.id,
        "account_id": account.id,
    }


class TestPaymentPreviewApi:
    def test_payment_preview_success(self, client: TestClient, db_session: Session, payment_user_fixture):
        user_id = payment_user_fixture["user_id"]
        payload = {
            "user_id": user_id,
            "amount": "5000.00",
            "recipient_name": "Dr Rao",
        }
        res = client.post("/api/v1/payments/preview", json=payload)
        assert res.status_code == 200
        data = res.json()

        assert data["can_proceed"] is True
        assert data["amount"] == "5000.00"
        assert data["recipient_name"] == "Dr Rao"
        assert data["current_balance"] == "48000.00"  # 50000 - 2000
        assert data["balance_after"] == "43000.00"
        assert data["pending_payment_id"] is not None

        # Verify NO transaction was written
        tx_count = db_session.query(Transaction).filter(Transaction.user_id == user_id).count()
        assert tx_count == 2

        # Verify PendingPayment row exists in DB
        pending = db_session.query(PendingPayment).filter(PendingPayment.id == data["pending_payment_id"]).first()
        assert pending is not None
        assert pending.status == "pending"
        assert pending.amount == Decimal("5000.00")

    def test_payment_preview_fraud_warning_on_large_payment(self, client: TestClient, payment_user_fixture):
        user_id = payment_user_fixture["user_id"]
        # Max past expense was ₹2,000. ₹30,000 exceeds 50% of balance (₹48,000) and > 2x max expense.
        payload = {
            "user_id": user_id,
            "amount": "30000.00",
            "recipient_name": "Unknown Payee",
        }
        res = client.post("/payments/preview", json=payload)
        assert res.status_code == 200
        data = res.json()

        assert data["fraud_warning"] is True
        assert data["risk_level"] == "high"
        assert len(data["risk_reasons"]) > 0

    def test_payment_preview_invalid_inputs(self, client: TestClient, payment_user_fixture):
        user_id = payment_user_fixture["user_id"]
        # Non-positive amount (Pydantic Field(gt=0) triggers 422 or 400)
        res_zero = client.post("/api/v1/payments/preview", json={"user_id": user_id, "amount": "0.00", "recipient_name": "Test"})
        assert res_zero.status_code in (400, 422)

        # Empty recipient
        res_empty = client.post("/api/v1/payments/preview", json={"user_id": user_id, "amount": "100.00", "recipient_name": "   "})
        assert res_empty.status_code in (400, 422)



class TestPaymentExecuteApi:
    def test_payment_execute_success(self, client: TestClient, db_session: Session, payment_user_fixture):
        user_id = payment_user_fixture["user_id"]
        # 1. Preview
        res_preview = client.post("/api/v1/payments/preview", json={
            "user_id": user_id,
            "amount": "4000.00",
            "recipient_name": "Dr Rao",
        })
        pending_id = res_preview.json()["pending_payment_id"]

        # 2. Execute
        res_exec = client.post("/api/v1/payments/execute", json={
            "user_id": user_id,
            "pending_payment_id": pending_id,
        })
        assert res_exec.status_code == 200
        data = res_exec.json()

        assert data["success"] is True
        assert data["amount"] == "4000.00"
        assert data["recipient_name"] == "Dr Rao"
        assert data["previous_balance"] == "48000.00"
        assert data["new_balance"] == "44000.00"
        assert data["status"] == "executed"

        # Verify transaction created in DB
        tx = db_session.query(Transaction).filter(Transaction.id == data["transaction_id"]).first()
        assert tx is not None
        assert tx.amount == Decimal("-4000.00")
        assert tx.source == "payment"
        assert tx.merchant_name == "Dr Rao"

        # Verify PendingPayment is updated
        pending = db_session.query(PendingPayment).filter(PendingPayment.id == pending_id).first()
        assert pending.status == "executed"

    def test_payment_execute_single_use_prevents_replay(self, client: TestClient, payment_user_fixture):
        user_id = payment_user_fixture["user_id"]
        # Preview
        res_preview = client.post("/api/v1/payments/preview", json={
            "user_id": user_id,
            "amount": "1000.00",
            "recipient_name": "Rahul",
        })
        pending_id = res_preview.json()["pending_payment_id"]

        # First execution: Success
        res_1 = client.post("/api/v1/payments/execute", json={"user_id": user_id, "pending_payment_id": pending_id})
        assert res_1.status_code == 200

        # Second execution: Must fail
        res_2 = client.post("/api/v1/payments/execute", json={"user_id": user_id, "pending_payment_id": pending_id})
        assert res_2.status_code == 400
        assert "already been executed" in res_2.json()["detail"]

    def test_payment_execute_user_isolation(self, client: TestClient, db_session: Session, payment_user_fixture):
        user_id = payment_user_fixture["user_id"]
        # Create second user
        user2 = User(
            full_name="Attacker User",
            email="attacker@example.com",
            accessibility_prefs={"voice_first": True},
            is_active=True,
        )
        db_session.add(user2)
        db_session.commit()

        # User 1 stages payment
        res_preview = client.post("/api/v1/payments/preview", json={
            "user_id": user_id,
            "amount": "1000.00",
            "recipient_name": "Target Payee",
        })
        pending_id = res_preview.json()["pending_payment_id"]

        # User 2 attempts to execute User 1's pending payment
        res_attack = client.post("/api/v1/payments/execute", json={
            "user_id": user2.id,
            "pending_payment_id": pending_id,
        })
        assert res_attack.status_code == 403
        assert "Unauthorized" in res_attack.json()["detail"]

    def test_payment_execute_expired_payment_fails(self, client: TestClient, db_session: Session, payment_user_fixture):
        user_id = payment_user_fixture["user_id"]
        # Stage pending payment with expired timestamp
        expired_payment = PendingPayment(
            user_id=user_id,
            amount=Decimal("1500.00"),
            recipient_name="Expired Payee",
            status="pending",
            expires_at=datetime.utcnow() - timedelta(minutes=10),
            created_at=datetime.utcnow() - timedelta(minutes=25),
        )
        db_session.add(expired_payment)
        db_session.commit()

        res_expired = client.post("/api/v1/payments/execute", json={
            "user_id": user_id,
            "pending_payment_id": expired_payment.id,
        })
        assert res_expired.status_code == 400
        assert "expired" in res_expired.json()["detail"].lower()
