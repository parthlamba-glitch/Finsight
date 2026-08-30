"""
Phase 1 Integration Verification Suite
======================================
Tests all 10 non-negotiable scenarios specified for Phase 1 AI <-> Backend integration.
"""

from datetime import datetime, date
from decimal import Decimal
import uuid
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.main import app
from backend.db import get_db, SessionLocal
from backend.models import User, Account, Transaction, Goal, Bill, PendingPayment
from ai.conversation import conversation_manager


@pytest.fixture
def db_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


@pytest.fixture
def client(db_session: Session):
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as c:
        yield c
    app.dependency_overrides.clear()


@pytest.fixture
def seed_user(db_session: Session):
    unique_email = f"phase1.{uuid.uuid4().hex[:8]}@example.com"
    user = User(
        email=unique_email,
        hashed_password="dummy_hash_for_testing",
        full_name="Phase1 Tester",
        is_active=True,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)

    account = Account(
        user_id=user.id,
        name="Primary Checking",
        account_type="checking",
        balance=Decimal("150000.00"),
        monthly_income=Decimal("150000.00"),
    )
    db_session.add(account)
    db_session.commit()
    db_session.refresh(account)

    # Inflow transaction
    t_income = Transaction(
        user_id=user.id,
        account_id=account.id,
        amount=Decimal("150000.00"),
        transaction_type="income",
        category="Other",
        description="Salary",
        source="bank",
        transaction_date=datetime(2026, 8, 1, 10, 0, 0),
    )
    # Food expense transaction
    t_food = Transaction(
        user_id=user.id,
        account_id=account.id,
        amount=Decimal("-8000.00"),
        transaction_type="expense",
        category="Food",
        description="Grocery Store",
        source="voice",
        transaction_date=datetime(2026, 8, 15, 12, 0, 0),
    )
    db_session.add_all([t_income, t_food])

    # Goal
    goal = Goal(
        user_id=user.id,
        name="Emergency Fund",
        target_amount=Decimal("100000.00"),
        current_amount=Decimal("40000.00"),
        monthly_contribution=Decimal("10000.00"),
        status="active",
    )
    db_session.add(goal)

    # Upcoming bill
    bill = Bill(
        user_id=user.id,
        name="Electricity",
        amount=Decimal("4000.00"),
        due_date=date(2026, 8, 28),
        category="Bills",
        status="unpaid",
    )
    db_session.add(bill)
    db_session.commit()

    return user.id


class TestPhase1TenScenarios:
    """Explicit verification of the 10 required Phase 1 integration scenarios."""

    def test_scenario_1_balance(self, client: TestClient, seed_user):
        """1. Balance: 'What is my current balance?' -> get_balance"""
        res = client.post("/ask", json={"user_id": seed_user, "query": "What is my current balance?"})
        assert res.status_code == 200
        data = res.json()
        assert data["intent"] == "get_balance"
        assert "142,000.00" in data["answer_text"] or "142000" in data["answer_text"]
        assert data["structured_facts"]["balance"] == "142000.00"

    def test_scenario_2_spending(self, client: TestClient, seed_user):
        """2. Spending: 'How much did I spend on food this month?' -> get_spending_summary"""
        res = client.post("/ask", json={"user_id": seed_user, "query": "How much did I spend on food this month?"})
        assert res.status_code == 200
        data = res.json()
        assert data["intent"] == "get_spending_summary"
        assert "8,000.00" in data["answer_text"] or "8000" in data["answer_text"]
        assert "Food" in data["structured_facts"]["by_category"]

    def test_scenario_3_affordability(self, client: TestClient, seed_user):
        """3. Affordability: 'Can I afford headphones for ₹8,000?' -> check_affordability"""
        res = client.post("/ask", json={"user_id": seed_user, "query": "Can I afford headphones for ₹8,000?"})
        assert res.status_code == 200
        data = res.json()
        assert data["intent"] == "check_affordability"
        assert data["structured_facts"]["can_afford"] is True
        assert "Yes, you can afford" in data["answer_text"]

    def test_scenario_4_clarification_flow(self, client: TestClient, seed_user):
        """4. Clarification: 'Can I afford it?' -> clarification_needed; then '8k' -> check_affordability amount 8000"""
        conv_id = f"phase1-clarify-conv-{uuid.uuid4().hex[:6]}"
        conversation_manager.clear(conv_id)

        # Turn 1
        res1 = client.post("/ask", json={"user_id": seed_user, "query": "Can I afford it?", "conversation_id": conv_id})
        assert res1.status_code == 200
        data1 = res1.json()
        assert data1["conversation_status"] == "clarification_needed"
        assert "How much does the item cost?" in data1["answer_text"]

        # Turn 2
        res2 = client.post("/ask", json={"user_id": seed_user, "query": "8k", "conversation_id": conv_id})
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2["intent"] == "check_affordability"
        assert data2["structured_facts"]["can_afford"] is True
        assert data2["conversation_status"] == "completed"

    def test_scenario_5_goal(self, client: TestClient, seed_user):
        """5. Goal: 'When will I finish my Emergency Fund?' -> project_goal_completion"""
        res = client.post("/ask", json={"user_id": seed_user, "query": "When will I finish my Emergency Fund?"})
        assert res.status_code == 200
        data = res.json()
        assert data["intent"] == "project_goal_completion"
        assert "Emergency Fund" in data["answer_text"]
        assert int(data["structured_facts"]["current_months_remaining"]) == 6

    def test_scenario_6_payment_preview(self, client: TestClient, seed_user, db_session: Session):
        """6. Payment preview: 'Send ₹5,000 to Dr Rao' -> payment_preview staged, 0 transactions created"""
        initial_tx_count = db_session.query(Transaction).filter(Transaction.user_id == seed_user).count()

        res = client.post("/ask", json={"user_id": seed_user, "query": "Send ₹5,000 to Dr Rao"})
        assert res.status_code == 200
        data = res.json()
        assert data["intent"] == "payment_preview"
        assert data["requires_confirmation"] is True
        assert data["pending_payment_id"] is not None
        assert data["conversation_status"] == "awaiting_confirmation"

        # Assert no new transactions were created
        current_tx_count = db_session.query(Transaction).filter(Transaction.user_id == seed_user).count()
        assert current_tx_count == initial_tx_count

    def test_scenario_7_payment_confirmation(self, client: TestClient, seed_user, db_session: Session):
        """7. Payment confirmation: 'Confirm payment' -> payment_execute -> PendingPayment executed"""
        # Stage preview
        res_prev = client.post("/ask", json={"user_id": seed_user, "query": "Send ₹5,000 to Dr Rao"})
        pending_id = res_prev.json()["pending_payment_id"]

        # Confirm
        res_exec = client.post("/ask", json={
            "user_id": seed_user,
            "query": "Confirm payment",
            "confirmation_token": str(pending_id),
        })
        assert res_exec.status_code == 200
        data = res_exec.json()
        assert data["intent"] == "payment_execute"
        assert "successfully completed" in data["answer_text"]
        assert data["structured_facts"]["status"] == "executed"
        assert data["structured_facts"]["new_balance"] == "137000.00"

    def test_scenario_8_payment_replay_rejected(self, client: TestClient, seed_user):
        """8. Payment replay: repeat confirmation -> rejected with 400 Bad Request"""
        res_prev = client.post("/ask", json={"user_id": seed_user, "query": "Send ₹2,000 to Rahul"})
        pending_id = res_prev.json()["pending_payment_id"]

        # 1st execute -> 200
        r1 = client.post("/ask", json={"user_id": seed_user, "query": "Confirm payment", "confirmation_token": str(pending_id)})
        assert r1.status_code == 200

        # 2nd execute -> 400
        r2 = client.post("/ask", json={"user_id": seed_user, "query": "Confirm payment", "confirmation_token": str(pending_id)})
        assert r2.status_code == 400
        assert "already executed" in r2.json()["detail"]

    def test_scenario_9_cross_user_payment_access(self, client: TestClient, seed_user, db_session: Session):
        """9. Cross-user payment access -> rejected with 400 Unauthorized"""
        other_user = User(email=f"other.{uuid.uuid4().hex[:8]}@example.com", hashed_password="pw", full_name="Other", is_active=True)
        db_session.add(other_user)
        db_session.commit()

        # User 1 stages payment
        res_prev = client.post("/ask", json={"user_id": seed_user, "query": "Send ₹3,000 to Merchant"})
        pending_id = res_prev.json()["pending_payment_id"]

        # User 2 attempts to confirm
        tamper_res = client.post("/ask", json={
            "user_id": other_user.id,
            "query": "Confirm payment",
            "confirmation_token": str(pending_id),
        })
        assert tamper_res.status_code == 400
        assert "Unauthorized" in tamper_res.json()["detail"]

    def test_scenario_10_high_risk_payment(self, client: TestClient, seed_user):
        """10. High-risk payment: 'Send ₹90,000 to Unknown Vendor' -> fraud_warning=True, risk_level='high'"""
        res = client.post("/ask", json={"user_id": seed_user, "query": "Send ₹90,000 to Unknown Vendor"})
        assert res.status_code == 200
        data = res.json()
        assert data["intent"] == "payment_preview"
        assert data["aria_priority"] == "assertive"
        assert data["structured_facts"]["risk_level"] == "high"
        assert data["structured_facts"]["fraud_warning"] is True
