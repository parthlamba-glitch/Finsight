"""
Unit tests for Backend Dispatcher (Day 5 Part A).

Validates intent parsing, user_id injection, monetary precision, goal resolution,
clarification triggers, and authoritative fact returns.
"""

import pytest
from decimal import Decimal
from datetime import datetime, date, timedelta
from sqlalchemy.orm import Session

from backend.models import User, Account, Transaction, Goal, Bill, PendingPayment
from backend.engine.dispatcher import dispatch_intent


@pytest.fixture
def setup_user_data(db_session: Session):
    """Sets up a test user with accounts, transactions, bills, and goals."""
    user = User(
        full_name="Dispatcher Test User",
        email="dispatcher.test@example.com",
        accessibility_prefs={"voice_first": True},
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    account = Account(
        user_id=user.id,
        name="Test Savings",
        account_type="savings",
        balance=Decimal("100000.00"),
        monthly_income=Decimal("75000.00"),
        currency="INR",
        is_active=True,
    )
    db_session.add(account)
    db_session.flush()

    # Opening balance
    tx_open = Transaction(
        account_id=account.id,
        user_id=user.id,
        amount=Decimal("100000.00"),
        currency="INR",
        transaction_type="income",
        category="Other",
        merchant_name=None,
        description="Opening Balance",
        transaction_date=datetime(2026, 8, 1, 10, 0, 0),
    )
    # Expenses
    tx_food = Transaction(
        account_id=account.id,
        user_id=user.id,
        amount=Decimal("-5000.00"),
        currency="INR",
        transaction_type="expense",
        category="Food",
        merchant_name="Supermarket",
        description="Groceries",
        transaction_date=datetime(2026, 8, 10, 12, 0, 0),
    )
    tx_shopping = Transaction(
        account_id=account.id,
        user_id=user.id,
        amount=Decimal("-3000.00"),
        currency="INR",
        transaction_type="expense",
        category="Shopping",
        merchant_name="Clothing Store",
        description="Clothes",
        transaction_date=datetime(2026, 8, 15, 14, 0, 0),
    )
    db_session.add_all([tx_open, tx_food, tx_shopping])

    # Unpaid bill
    bill = Bill(
        user_id=user.id,
        name="Electricity Bill",
        amount=Decimal("2000.00"),
        due_date=date(2026, 8, 25),
        category="Bills",
        status="unpaid",
    )
    db_session.add(bill)

    # Goal
    goal = Goal(
        user_id=user.id,
        name="Emergency Fund",
        target_amount=Decimal("50000.00"),
        current_amount=Decimal("20000.00"),
        monthly_contribution=Decimal("5000.00"),
        status="active",
    )
    db_session.add(goal)
    db_session.commit()

    return {
        "user_id": user.id,
        "account_id": account.id,
        "goal_id": goal.id,
    }


class TestDispatcherGetBalance:
    def test_get_balance_intent(self, db_session: Session, setup_user_data):
        user_id = setup_user_data["user_id"]
        intent_data = {"intent": "get_balance", "arguments": {}}
        facts = dispatch_intent(user_id=user_id, intent_data=intent_data, db=db_session)

        assert facts["intent"] == "get_balance"
        assert facts["balance"] == Decimal("92000.00")  # 100000 - 5000 - 3000
        assert facts["as_of"] == datetime(2026, 8, 15, 14, 0, 0)

    def test_get_balance_ignores_ai_user_id(self, db_session: Session, setup_user_data):
        user_id = setup_user_data["user_id"]
        intent_data = {"intent": "get_balance", "arguments": {"user_id": 9999}}
        facts = dispatch_intent(user_id=user_id, intent_data=intent_data, db=db_session)

        # Must execute for authenticated user_id, not 9999
        assert facts["balance"] == Decimal("92000.00")


class TestDispatcherSpendingSummary:
    def test_spending_summary_intent(self, db_session: Session, setup_user_data):
        user_id = setup_user_data["user_id"]
        intent_data = {"intent": "get_spending_summary", "arguments": {"period": "this_month"}}
        facts = dispatch_intent(user_id=user_id, intent_data=intent_data, db=db_session)

        assert facts["intent"] == "get_spending_summary"
        assert facts["total"] == Decimal("8000.00")
        assert facts["by_category"]["Food"] == Decimal("5000.00")
        assert facts["by_category"]["Shopping"] == Decimal("3000.00")


class TestDispatcherAffordability:
    def test_affordability_affordable(self, db_session: Session, setup_user_data):
        user_id = setup_user_data["user_id"]
        intent_data = {"intent": "check_affordability", "arguments": {"amount": "5000"}}
        facts = dispatch_intent(user_id=user_id, intent_data=intent_data, db=db_session)

        assert facts["intent"] == "check_affordability"
        assert facts["can_afford"] is True
        assert facts["balance_after"] == Decimal("87000.00")
        assert facts["upcoming_bills"] == Decimal("2000.00")

    def test_affordability_missing_amount_requests_clarification(self, db_session: Session, setup_user_data):
        user_id = setup_user_data["user_id"]
        intent_data = {"intent": "check_affordability", "arguments": {}}
        facts = dispatch_intent(user_id=user_id, intent_data=intent_data, db=db_session)

        assert facts["status"] == "clarification_needed"
        assert "How much" in facts["question"]

    def test_affordability_negative_amount_raises_error(self, db_session: Session, setup_user_data):
        user_id = setup_user_data["user_id"]
        intent_data = {"intent": "check_affordability", "arguments": {"amount": "-500"}}
        with pytest.raises(ValueError, match="positive"):
            dispatch_intent(user_id=user_id, intent_data=intent_data, db=db_session)


class TestDispatcherGoalCompletion:
    def test_goal_resolution_by_name(self, db_session: Session, setup_user_data):
        user_id = setup_user_data["user_id"]
        intent_data = {
            "intent": "project_goal_completion",
            "arguments": {"goal_name": "Emergency Fund"},
        }
        facts = dispatch_intent(user_id=user_id, intent_data=intent_data, db=db_session)

        assert facts["intent"] == "project_goal_completion"
        assert facts["goal_name"] == "Emergency Fund"
        assert facts["current_months_remaining"] == Decimal("6")  # (50000 - 20000) / 5000 = 6

    def test_single_active_goal_fallback_when_name_omitted(self, db_session: Session, setup_user_data):
        user_id = setup_user_data["user_id"]
        intent_data = {"intent": "project_goal_completion", "arguments": {}}
        facts = dispatch_intent(user_id=user_id, intent_data=intent_data, db=db_session)

        assert facts["intent"] == "project_goal_completion"
        assert facts["goal_name"] == "Emergency Fund"

    def test_unresolvable_goal_triggers_clarification(self, db_session: Session, setup_user_data):
        user_id = setup_user_data["user_id"]
        intent_data = {
            "intent": "project_goal_completion",
            "arguments": {"goal_name": "Nonexistent Vacation Goal"},
        }
        facts = dispatch_intent(user_id=user_id, intent_data=intent_data, db=db_session)

        assert facts["status"] == "clarification_needed"
        assert "Which savings goal" in facts["question"]


class TestDispatcherPaymentPreviewAndExecution:
    def test_payment_preview_creates_pending_payment(self, db_session: Session, setup_user_data):
        user_id = setup_user_data["user_id"]
        intent_data = {
            "intent": "payment_preview",
            "arguments": {"amount": "4000.00", "recipient_name": "Dr Rao"},
        }
        facts = dispatch_intent(user_id=user_id, intent_data=intent_data, db=db_session)

        assert facts["intent"] == "payment_preview"
        assert facts["requires_confirmation"] is True
        assert facts["can_proceed"] is True
        assert facts["pending_payment_id"] is not None

        # Verify record exists in PendingPayment table
        pending = db_session.query(PendingPayment).filter(PendingPayment.id == facts["pending_payment_id"]).first()
        assert pending is not None
        assert pending.amount == Decimal("4000.00")
        assert pending.recipient_name == "Dr Rao"
        assert pending.status == "pending"

    def test_payment_execute_via_dispatcher(self, db_session: Session, setup_user_data):
        user_id = setup_user_data["user_id"]
        # Preview first
        preview_data = {
            "intent": "payment_preview",
            "arguments": {"amount": "2000.00", "recipient_name": "Rahul"},
        }
        preview_facts = dispatch_intent(user_id=user_id, intent_data=preview_data, db=db_session)
        pending_id = preview_facts["pending_payment_id"]

        # Execute
        exec_data = {
            "intent": "payment_execute",
            "arguments": {"pending_payment_id": pending_id},
        }
        exec_facts = dispatch_intent(user_id=user_id, intent_data=exec_data, db=db_session)

        assert exec_facts["intent"] == "payment_execute"
        assert exec_facts["success"] is True
        assert exec_facts["status"] == "executed"
        assert exec_facts["new_balance"] == Decimal("90000.00")  # 92000 - 2000

        # Verify second execution fails
        with pytest.raises(ValueError, match="already executed"):
            dispatch_intent(user_id=user_id, intent_data=exec_data, db=db_session)


class TestDispatcherEdgeCases:
    def test_unsupported_intent_handling(self, db_session: Session, setup_user_data):
        user_id = setup_user_data["user_id"]
        intent_data = {"intent": "unsupported_crypto_trade", "arguments": {}}
        facts = dispatch_intent(user_id=user_id, intent_data=intent_data, db=db_session)

        assert facts["status"] == "unsupported_intent"

    def test_nonexistent_user_raises_error(self, db_session: Session):
        intent_data = {"intent": "get_balance", "arguments": {}}
        with pytest.raises(ValueError, match="does not exist"):
            dispatch_intent(user_id=99999, intent_data=intent_data, db=db_session)
