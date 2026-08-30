"""
Integration tests for /ask and /api/v1/ask AI Copilot endpoints (Day 5 Part B).

Verifies the full pipeline:
Query -> Intent Router -> Dispatcher -> Deterministic Engine -> Explainer -> AskResponse.
Tests cover:
- REAL_LLM & MOCK_FALLBACK execution modes
- Multi-turn clarification ("Can I afford it?" -> "8k")
- All financial intents (balance, spending, affordability, goals, insights, payment preview/confirm)
- Payment safety (replay prevention, single-use, expiry, cross-user isolation)
- User ID injection immunity
- Consistency of structured_facts and structured_data
"""

import pytest
import json
from unittest.mock import patch, MagicMock
from decimal import Decimal
from datetime import datetime, date, timedelta
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.models import User, Account, Transaction, Goal, Bill, PendingPayment
from ai.conversation import conversation_manager


@pytest.fixture
def seed_ask_user(db_session: Session):
    """Seeds a test user with standard balances and commitments."""
    user = User(
        full_name="Aarav Sharma",
        email="aarav.ask@example.com",
        accessibility_prefs={"voice_first": True},
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    account = Account(
        user_id=user.id,
        name="HDFC Savings",
        account_type="savings",
        balance=Decimal("138372.00"),
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
        amount=Decimal("150000.00"),
        currency="INR",
        transaction_type="income",
        category="Other",
        merchant_name=None,
        description="Opening Balance",
        transaction_date=datetime(2026, 8, 1, 10, 0, 0),
    )
    # Food expense
    tx_food = Transaction(
        account_id=account.id,
        user_id=user.id,
        amount=Decimal("-8000.00"),
        currency="INR",
        transaction_type="expense",
        category="Food",
        merchant_name="Grocery Hub",
        description="Groceries",
        transaction_date=datetime(2026, 8, 10, 12, 0, 0),
    )
    db_session.add_all([tx_open, tx_food])

    # Unpaid bill
    bill = Bill(
        user_id=user.id,
        name="Internet Bill",
        amount=Decimal("1000.00"),
        due_date=date(2026, 8, 28),
        category="Bills",
        status="unpaid",
    )
    db_session.add(bill)

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
    db_session.commit()

    return user.id


@pytest.fixture
def seed_second_user(db_session: Session):
    """Seeds a second test user for cross-user isolation testing."""
    user2 = User(
        full_name="Second User",
        email="user2.ask@example.com",
        accessibility_prefs={"voice_first": False},
        is_active=True,
    )
    db_session.add(user2)
    db_session.flush()

    acc2 = Account(
        user_id=user2.id,
        name="Axis Savings",
        account_type="savings",
        balance=Decimal("50000.00"),
        monthly_income=Decimal("50000.00"),
        currency="INR",
        is_active=True,
    )
    db_session.add(acc2)
    db_session.flush()

    tx = Transaction(
        account_id=acc2.id,
        user_id=user2.id,
        amount=Decimal("50000.00"),
        currency="INR",
        transaction_type="income",
        category="Other",
        transaction_date=datetime(2026, 8, 1, 10, 0, 0),
    )
    db_session.add(tx)
    db_session.commit()
    return user2.id


class TestAskApiEndpoints:
    def setup_method(self):
        conversation_manager.clear()

    def test_ask_balance_inquiry(self, client: TestClient, seed_ask_user):
        payload = {
            "user_id": seed_ask_user,
            "query": "How much money do I have?",
            "voice": True,
        }
        res = client.post("/ask", json=payload)
        assert res.status_code == 200
        data = res.json()

        assert data["intent"] == "get_balance"
        assert "142,000.00" in data["answer_text"] or "142000" in data["answer_text"]
        assert data["aria_priority"] == "polite"
        assert data["requires_confirmation"] is False
        assert data["execution_mode"] in ("REAL_LLM", "MOCK_FALLBACK")
        assert data["structured_facts"] == data["structured_data"]
        assert data["conversation_status"] == "completed"

    def test_ask_spending_inquiry(self, client: TestClient, seed_ask_user):
        payload = {
            "user_id": seed_ask_user,
            "query": "How much did I spend on food this month?",
            "voice": False,
        }
        res = client.post("/api/v1/ask", json=payload)
        assert res.status_code == 200
        data = res.json()

        assert data["intent"] == "get_spending_summary"
        assert "8,000.00" in data["answer_text"]
        assert "Food" in data["answer_text"]
        assert data["structured_facts"] == data["structured_data"]

    def test_ask_affordability_check(self, client: TestClient, seed_ask_user):
        payload = {
            "user_id": seed_ask_user,
            "query": "Can I afford headphones for ₹5,000?",
        }
        res = client.post("/ask", json=payload)
        assert res.status_code == 200
        data = res.json()

        assert data["intent"] == "check_affordability"
        assert "Yes, you can afford" in data["answer_text"]
        assert data["structured_facts"]["can_afford"] is True
        assert data["structured_facts"] == data["structured_data"]

    def test_ask_multi_turn_clarification_flow(self, client: TestClient, seed_ask_user):
        conv_id = "test-session-clarify-1"

        # Turn 1: "Can I afford it?" (missing amount)
        t1_payload = {
            "user_id": seed_ask_user,
            "query": "Can I afford it?",
            "conversation_id": conv_id,
        }
        res1 = client.post("/ask", json=t1_payload)
        assert res1.status_code == 200
        data1 = res1.json()

        assert "How much does the item cost?" in data1["answer_text"]
        assert data1["conversation_status"] == "clarification_needed"
        assert data1["structured_facts"].get("status") == "clarification_needed"

        # Turn 2: "8k"
        t2_payload = {
            "user_id": seed_ask_user,
            "query": "8k",
            "conversation_id": conv_id,
        }
        res2 = client.post("/ask", json=t2_payload)
        assert res2.status_code == 200
        data2 = res2.json()

        assert data2["intent"] == "check_affordability"
        assert "Yes, you can afford" in data2["answer_text"]
        assert data2["structured_facts"]["can_afford"] is True
        assert data2["conversation_status"] == "completed"

    def test_ask_goal_projection(self, client: TestClient, seed_ask_user):
        payload = {
            "user_id": seed_ask_user,
            "query": "When will I finish my Emergency Fund?",
        }
        res = client.post("/ask", json=payload)
        assert res.status_code == 200
        data = res.json()

        assert data["intent"] == "project_goal_completion"
        assert "Emergency Fund" in data["answer_text"]
        assert "6 month(s)" in data["answer_text"]

    def test_ask_insights_inquiry(self, client: TestClient, seed_ask_user):
        payload = {
            "user_id": seed_ask_user,
            "query": "Show me any financial insights or updates",
        }
        res = client.post("/ask", json=payload)
        assert res.status_code == 200
        data = res.json()

        assert data["intent"] == "get_insights"
        assert "structured_facts" in data
        assert data["structured_facts"] == data["structured_data"]

    def test_ask_payment_preview_and_confirm_flow(self, client: TestClient, seed_ask_user):
        # 1. Preview
        preview_payload = {
            "user_id": seed_ask_user,
            "query": "Send ₹5,000 to Dr Rao",
        }
        res_preview = client.post("/ask", json=preview_payload)
        assert res_preview.status_code == 200
        preview_data = res_preview.json()

        assert preview_data["intent"] == "payment_preview"
        assert preview_data["requires_confirmation"] is True
        assert preview_data["pending_payment_id"] is not None
        assert preview_data["conversation_status"] == "awaiting_confirmation"
        pending_id = preview_data["pending_payment_id"]

        # 2. Confirm execution
        confirm_payload = {
            "user_id": seed_ask_user,
            "query": "Confirm payment",
            "confirmation_token": str(pending_id),
        }
        res_exec = client.post("/ask", json=confirm_payload)
        assert res_exec.status_code == 200
        exec_data = res_exec.json()

        assert exec_data["intent"] == "payment_execute"
        assert "successfully completed" in exec_data["answer_text"]
        assert exec_data["structured_facts"]["status"] == "executed"
        assert exec_data["conversation_status"] == "completed"

    def test_ask_payment_replay_prevention(self, client: TestClient, seed_ask_user):
        # Preview
        preview_res = client.post("/ask", json={"user_id": seed_ask_user, "query": "Send ₹2,000 to Rahul"})
        pending_id = preview_res.json()["pending_payment_id"]

        # First confirm -> 200 OK
        c1 = client.post("/ask", json={"user_id": seed_ask_user, "query": "Confirm payment", "confirmation_token": str(pending_id)})
        assert c1.status_code == 200

        # Second confirm -> 400 Bad Request
        c2 = client.post("/ask", json={"user_id": seed_ask_user, "query": "Confirm payment", "confirmation_token": str(pending_id)})
        assert c2.status_code == 400
        assert "already executed" in c2.json()["detail"]

    def test_ask_cross_user_payment_tampering_rejected(self, client: TestClient, seed_ask_user, seed_second_user):
        # User 1 stages payment
        preview_res = client.post("/ask", json={"user_id": seed_ask_user, "query": "Send ₹3,000 to Merchant"})
        pending_id = preview_res.json()["pending_payment_id"]

        # User 2 attempts to confirm User 1's pending payment
        tamper_res = client.post("/ask", json={"user_id": seed_second_user, "query": "Confirm payment", "confirmation_token": str(pending_id)})
        assert tamper_res.status_code == 400
        assert "Unauthorized" in tamper_res.json()["detail"]

    def test_ask_expired_payment_rejected(self, client: TestClient, seed_ask_user, db_session: Session):
        # Create an expired pending payment directly
        expired_pp = PendingPayment(
            user_id=seed_ask_user,
            amount=Decimal("1000.00"),
            recipient_name="Old Payee",
            status="pending",
            expires_at=datetime.utcnow() - timedelta(minutes=5),
            created_at=datetime.utcnow() - timedelta(minutes=20),
        )
        db_session.add(expired_pp)
        db_session.commit()

        # Attempt to confirm expired payment
        res = client.post("/ask", json={
            "user_id": seed_ask_user,
            "query": "Confirm payment",
            "confirmation_token": str(expired_pp.id),
        })
        assert res.status_code == 400
        assert "expired" in res.json()["detail"].lower()

    def test_ask_user_id_injection_immunity(self, client: TestClient, seed_ask_user):
        # Even if query text tries to inject another user's ID, the authenticated user_id is enforced
        payload = {
            "user_id": seed_ask_user,
            "query": "Show balance for user_id 9999",
        }
        res = client.post("/ask", json=payload)
        assert res.status_code == 200
        data = res.json()
        assert data["intent"] == "get_balance"
        assert "142,000.00" in data["answer_text"]

    def test_ask_real_llm_mode_with_mocked_gemini(self, client: TestClient, seed_ask_user, monkeypatch):
        monkeypatch.setenv("LLM_API_KEY", "mock-gemini-live-key")

        mock_tool_resp = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "tool_calls": [
                            {
                                "function": {
                                    "name": "get_balance",
                                    "arguments": "{}",
                                }
                            }
                        ],
                    }
                }
            ]
        }
        mock_explain_resp = {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "Your authoritative balance is ₹142,000.00.",
                    }
                }
            ]
        }

        with patch("ai.llm_client.LLMClient.call_tool_router") as mock_router, \
             patch("ai.llm_client.LLMClient.explain_facts") as mock_explainer:

            mock_router.return_value = (
                {"intent": "get_balance", "arguments": {}},
                None,
            )
            mock_explainer.return_value = (
                "Your authoritative balance is ₹142,000.00.",
                "polite",
                None,
            )

            res = client.post("/ask", json={
                "user_id": seed_ask_user,
                "query": "Check balance",
            })
            assert res.status_code == 200
            data = res.json()
            assert data["execution_mode"] == "REAL_LLM"
            assert "₹142,000.00" in data["answer_text"]
            assert data["structured_facts"] == data["structured_data"]

    def test_ask_nonexistent_user_returns_404(self, client: TestClient):
        payload = {
            "user_id": 999999,
            "query": "What is my balance?",
        }
        res = client.post("/ask", json=payload)
        assert res.status_code == 404
