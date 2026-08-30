"""
Comprehensive Unit Tests for Deterministic Simulated Payment Engine.

Verifies:
1. Preview affordable payment
2. Preview unaffordable payment (due to upcoming bills)
3. Preview amount larger than current balance
4. Zero amount rejected
5. Negative amount rejected
6. Unknown user rejected
7. Empty recipient rejected
8. Successful payment creates exactly one transaction
9. Payment transaction amount is negative
10. Payment reduces authoritative balance correctly
11. Account.balance is not used for payment calculation
12. User isolation: one user cannot create a payment from another user's account
13. Failed payment creates NO transaction
14. Decimal precision is preserved
15. Integration against live seeded demo dataset
"""

from decimal import Decimal
from datetime import datetime, date
import pytest
from sqlalchemy.orm import Session

from backend.models import User, Account, Transaction, Bill
from backend.engine import get_balance
from backend.payment.payment_engine import preview_payment, execute_payment


@pytest.fixture
def payment_user_fixture(db_session: Session):
    """Sets up a primary paying user and a second isolated user with accounts, bills, and initial balance."""
    # User 1 (Paying user)
    user1 = User(
        full_name="Aarav Sharma",
        email="aarav.pay@example.com",
        accessibility_prefs={"voice_first": True, "screen_reader": True, "spoken_confirmations": True, "preferred_language": "en-IN"},
    )
    # User 2 (Isolated user)
    user2 = User(
        full_name="Priya Patel",
        email="priya.pay@example.com",
        accessibility_prefs={"voice_first": False, "screen_reader": False, "spoken_confirmations": False, "preferred_language": "en-IN"},
    )
    db_session.add_all([user1, user2])
    db_session.flush()

    # User 1 Account (Cached balance deliberately set to 0.00 to verify authoritative derivation)
    acc1 = Account(
        user_id=user1.id,
        name="HDFC Primary Savings",
        balance=Decimal("0.00"),
        monthly_income=Decimal("75000.00"),
        is_active=True,
    )
    # User 2 Account
    acc2 = Account(
        user_id=user2.id,
        name="ICICI Savings",
        balance=Decimal("50000.00"),
        monthly_income=Decimal("50000.00"),
        is_active=True,
    )
    db_session.add_all([acc1, acc2])
    db_session.flush()

    # Initial balance for User 1 = 100,000.00 via transaction
    tx_init_1 = Transaction(
        account_id=acc1.id,
        user_id=user1.id,
        amount=Decimal("100000.00"),
        currency="INR",
        transaction_type="income",
        category="Other",
        description="Initial Deposit",
        transaction_date=datetime(2026, 8, 1, 10, 0, 0),
    )
    # Initial balance for User 2 = 50,000.00
    tx_init_2 = Transaction(
        account_id=acc2.id,
        user_id=user2.id,
        amount=Decimal("50000.00"),
        currency="INR",
        transaction_type="income",
        category="Other",
        description="Initial Deposit",
        transaction_date=datetime(2026, 8, 1, 10, 0, 0),
    )
    db_session.add_all([tx_init_1, tx_init_2])

    # Upcoming unpaid bill for User 1: 15,000.00 due in 10 days
    bill1 = Bill(
        user_id=user1.id,
        name="Quarterly Maintenance",
        amount=Decimal("15000.00"),
        category="Bills",
        due_date=date(2026, 8, 11),
        status="unpaid",
    )
    db_session.add(bill1)
    db_session.commit()

    return {
        "user1": user1,
        "user2": user2,
        "acc1": acc1,
        "acc2": acc2,
    }


class TestPaymentPreview:
    """Tests for preview_payment()."""

    def test_preview_affordable_payment(self, db_session: Session, payment_user_fixture: dict):
        user1 = payment_user_fixture["user1"]
        # Balance = 100,000; Bills = 15,000; Amount = 20,000.
        # Balance After = 80,000; Available after commitments = 65,000 >= 0.
        preview = preview_payment(
            user_id=user1.id,
            amount=Decimal("20000.00"),
            recipient_name="Deepak Electric Store",
            db=db_session,
        )

        assert preview["can_proceed"] is True
        assert preview["amount"] == Decimal("20000.00")
        assert preview["recipient_name"] == "Deepak Electric Store"
        assert preview["current_balance"] == Decimal("100000.00")
        assert preview["balance_after"] == Decimal("80000.00")
        assert preview["upcoming_bills"] == Decimal("15000.00")
        assert preview["available_after_commitments"] == Decimal("65000.00")
        assert preview["risk_level"] == "low"

        # Check reasoning facts
        facts = {f["fact"]: f.get("value") for f in preview["reasoning_facts"]}
        assert facts["current_balance"] == "100000.00"
        assert facts["purchase_amount"] == "20000.00"
        assert facts["upcoming_bills"] == "15000.00"
        assert facts["can_proceed"] == "True"

    def test_preview_unaffordable_due_to_upcoming_bills(self, db_session: Session, payment_user_fixture: dict):
        user1 = payment_user_fixture["user1"]
        # Balance = 100,000; Bills = 15,000; Amount = 90,000.
        # Balance After = 10,000 > 0; Available after commitments = 100k - 15k - 90k = -5,000 < 0.
        preview = preview_payment(
            user_id=user1.id,
            amount=Decimal("90000.00"),
            recipient_name="Luxury Watchmaker",
            db=db_session,
        )

        assert preview["can_proceed"] is False
        assert preview["balance_after"] == Decimal("10000.00")
        assert preview["available_after_commitments"] == Decimal("-5000.00")
        assert preview["risk_level"] == "high"

    def test_preview_amount_larger_than_balance(self, db_session: Session, payment_user_fixture: dict):
        user1 = payment_user_fixture["user1"]
        preview = preview_payment(
            user_id=user1.id,
            amount=Decimal("150000.00"),
            recipient_name="Auto Dealership",
            db=db_session,
        )

        assert preview["can_proceed"] is False
        assert preview["balance_after"] == Decimal("-50000.00")
        assert preview["available_after_commitments"] == Decimal("-65000.00")
        assert preview["risk_level"] == "high"

    def test_preview_zero_amount_rejected(self, db_session: Session, payment_user_fixture: dict):
        user1 = payment_user_fixture["user1"]
        with pytest.raises(ValueError, match="greater than zero"):
            preview_payment(user_id=user1.id, amount=Decimal("0.00"), recipient_name="Payee", db=db_session)

    def test_preview_negative_amount_rejected(self, db_session: Session, payment_user_fixture: dict):
        user1 = payment_user_fixture["user1"]
        with pytest.raises(ValueError, match="greater than zero"):
            preview_payment(user_id=user1.id, amount=Decimal("-500.00"), recipient_name="Payee", db=db_session)

    def test_preview_unknown_user_rejected(self, db_session: Session):
        with pytest.raises(ValueError, match="does not exist"):
            preview_payment(user_id=999999, amount=Decimal("500.00"), recipient_name="Payee", db=db_session)

    def test_preview_empty_recipient_rejected(self, db_session: Session, payment_user_fixture: dict):
        user1 = payment_user_fixture["user1"]
        with pytest.raises(ValueError, match="non-empty string"):
            preview_payment(user_id=user1.id, amount=Decimal("500.00"), recipient_name="   ", db=db_session)


class TestPaymentExecution:
    """Tests for execute_payment()."""

    def test_successful_payment_execution(self, db_session: Session, payment_user_fixture: dict):
        user1 = payment_user_fixture["user1"]
        acc1 = payment_user_fixture["acc1"]

        initial_tx_count = db_session.query(Transaction).filter(Transaction.user_id == user1.id).count()

        # Execute payment of ₹12,500.50
        result = execute_payment(
            user_id=user1.id,
            amount=Decimal("12500.50"),
            recipient_name="Sharma Medical Store",
            db=db_session,
        )

        assert result["success"] is True
        assert result["recipient_name"] == "Sharma Medical Store"
        assert result["amount"] == Decimal("12500.50")
        assert result["previous_balance"] == Decimal("100000.00")
        # 100,000.00 - 12,500.50 = 87,499.50
        assert result["new_balance"] == Decimal("87499.50")
        assert result["transaction_type"] == "expense"

        # 8. Exactly one transaction created
        current_tx_count = db_session.query(Transaction).filter(Transaction.user_id == user1.id).count()
        assert current_tx_count == initial_tx_count + 1

        # 9. Payment transaction amount is negative
        created_tx = db_session.query(Transaction).filter(Transaction.id == result["transaction_id"]).first()
        assert created_tx is not None
        assert created_tx.amount == Decimal("-12500.50")
        assert created_tx.account_id == acc1.id
        assert created_tx.user_id == user1.id
        assert created_tx.merchant_name == "Sharma Medical Store"
        assert created_tx.transaction_type == "expense"
        assert created_tx.category == "Other"

        # 10. Authoritative balance matches
        auth_bal = get_balance(user1.id, db_session)["balance"]
        assert auth_bal == Decimal("87499.50")

    def test_failed_payment_creates_no_transaction(self, db_session: Session, payment_user_fixture: dict):
        user1 = payment_user_fixture["user1"]
        initial_tx_count = db_session.query(Transaction).filter(Transaction.user_id == user1.id).count()

        # Attempt to pay ₹95,000 when available after bills is only 85,000
        with pytest.raises(ValueError, match="insufficient funds or commitments"):
            execute_payment(
                user_id=user1.id,
                amount=Decimal("95000.00"),
                recipient_name="Luxury Store",
                db=db_session,
            )

        # 13. Verify NO transaction was added to the database
        post_tx_count = db_session.query(Transaction).filter(Transaction.user_id == user1.id).count()
        assert post_tx_count == initial_tx_count

        # Balance remains unaffected
        auth_bal = get_balance(user1.id, db_session)["balance"]
        assert auth_bal == Decimal("100000.00")

    def test_user_isolation_cannot_pay_from_another_users_account(self, db_session: Session, payment_user_fixture: dict):
        user1 = payment_user_fixture["user1"]
        user2 = payment_user_fixture["user2"]

        # User 2 executes payment of 10,000
        res2 = execute_payment(
            user_id=user2.id,
            amount=Decimal("10000.00"),
            recipient_name="Coffee Roasters",
            db=db_session,
        )
        assert res2["success"] is True

        # Ensure transaction was created under User 2 and User 2's account
        tx2 = db_session.query(Transaction).filter(Transaction.id == res2["transaction_id"]).first()
        assert tx2.user_id == user2.id
        assert tx2.account_id == payment_user_fixture["acc2"].id

        # Ensure User 1's balance was completely untouched (still 100,000.00)
        auth_bal1 = get_balance(user1.id, db_session)["balance"]
        assert auth_bal1 == Decimal("100000.00")

    def test_decimal_precision_is_preserved(self, db_session: Session, payment_user_fixture: dict):
        user1 = payment_user_fixture["user1"]
        # Payment with odd decimal: 33.33
        result = execute_payment(
            user_id=user1.id,
            amount=Decimal("33.33"),
            recipient_name="Chai Point",
            db=db_session,
        )
        assert result["new_balance"] == Decimal("99966.67")
        assert isinstance(result["new_balance"], Decimal)


class TestLiveSeededPaymentIntegration:
    """Verifies simulated preview and payment execution against the live demo user in finsight.db."""

    def test_preview_on_live_demo_user(self):
        from backend.db import SessionLocal
        db = SessionLocal()
        try:
            demo_user = db.query(User).filter_by(email="aarav.sharma@example.com").first()
            assert demo_user is not None

            preview = preview_payment(
                user_id=demo_user.id,
                amount=Decimal("5000.00"),
                recipient_name="Dr. Rao Clinic",
                db=db,
            )

            assert preview["can_proceed"] is True
            assert preview["current_balance"] == Decimal("138372.00")
            assert preview["balance_after"] == Decimal("133372.00")
            assert preview["upcoming_bills"] == Decimal("6529.00")
            assert preview["available_after_commitments"] == Decimal("126843.00")
        finally:
            db.close()
