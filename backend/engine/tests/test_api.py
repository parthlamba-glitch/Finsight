"""
Comprehensive API Endpoint Tests for FinSight.

Tests:
- Dashboard Overview (/overview, /api/v1/overview): balance, spending, surplus, upcoming bills, goals, 404 handling
- Transactions (/transactions, /api/v1/transactions): this_month, last_month, sign conventions, category totals, 400/404 handling
- Goals (/goals, /api/v1/goals): List, Create, Patch contribution with projection, 400/404/403 handling
- User Isolation: Verifies that User A cannot view or mutate User B's transactions, accounts, goals, or bills
- Live integration tests against the seeded demo dataset
"""

from decimal import Decimal
from datetime import datetime, date
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.models import User, Account, Transaction, Goal, Bill


@pytest.fixture
def setup_two_users(db_session: Session):
    """Creates two isolated users with accounts, transactions, bills, and goals."""
    # User 1
    user1 = User(
        full_name="User Alpha",
        email="alpha@example.com",
        accessibility_prefs={"voice_first": True, "screen_reader": True, "spoken_confirmations": True, "preferred_language": "en-IN"},
    )
    # User 2
    user2 = User(
        full_name="User Beta",
        email="beta@example.com",
        accessibility_prefs={"voice_first": False, "screen_reader": False, "spoken_confirmations": False, "preferred_language": "en-US"},
    )
    db_session.add_all([user1, user2])
    db_session.flush()

    # Accounts
    acc1 = Account(user_id=user1.id, name="Alpha Savings", monthly_income=Decimal("75000.00"), is_active=True)
    acc2 = Account(user_id=user2.id, name="Beta Checking", monthly_income=Decimal("50000.00"), is_active=True)
    db_session.add_all([acc1, acc2])
    db_session.flush()

    # Transactions for User 1 (August 2026 as_of: Aug 25)
    t1_1 = Transaction(
        account_id=acc1.id,
        user_id=user1.id,
        amount=Decimal("75000.00"),
        transaction_type="income",
        category="Other",
        description="Salary",
        transaction_date=datetime(2026, 8, 1, 9, 0),
    )
    t1_2 = Transaction(
        account_id=acc1.id,
        user_id=user1.id,
        amount=Decimal("-25000.00"),
        transaction_type="expense",
        category="Bills",
        merchant_name="Landlord",
        description="Rent",
        transaction_date=datetime(2026, 8, 2, 10, 0),
    )
    t1_3 = Transaction(
        account_id=acc1.id,
        user_id=user1.id,
        amount=Decimal("-8000.00"),
        transaction_type="expense",
        category="Food",
        merchant_name="BigBasket",
        description="Groceries",
        transaction_date=datetime(2026, 8, 20, 18, 0),
    )

    # July 2026 transaction for User 1 (last_month)
    t1_prev = Transaction(
        account_id=acc1.id,
        user_id=user1.id,
        amount=Decimal("-6000.00"),
        transaction_type="expense",
        category="Food",
        merchant_name="BigBasket",
        description="July Groceries",
        transaction_date=datetime(2026, 7, 15, 12, 0),
    )

    # Transactions for User 2
    t2_1 = Transaction(
        account_id=acc2.id,
        user_id=user2.id,
        amount=Decimal("50000.00"),
        transaction_type="income",
        category="Other",
        description="Beta Salary",
        transaction_date=datetime(2026, 8, 1, 9, 0),
    )
    t2_2 = Transaction(
        account_id=acc2.id,
        user_id=user2.id,
        amount=Decimal("-12000.00"),
        transaction_type="expense",
        category="Shopping",
        merchant_name="Apple Store",
        description="AirPods",
        transaction_date=datetime(2026, 8, 10, 14, 0),
    )

    db_session.add_all([t1_1, t1_2, t1_3, t1_prev, t2_1, t2_2])

    # Unpaid Bill for User 1
    bill1 = Bill(
        user_id=user1.id,
        name="BESCOM Electricity",
        amount=Decimal("1850.00"),
        category="Bills",
        due_date=date(2026, 9, 5),
        status="unpaid",
    )
    # Unpaid Bill for User 2
    bill2 = Bill(
        user_id=user2.id,
        name="Internet Bill",
        amount=Decimal("999.00"),
        category="Bills",
        due_date=date(2026, 9, 10),
        status="unpaid",
    )
    db_session.add_all([bill1, bill2])

    # Goals
    goal1 = Goal(
        user_id=user1.id,
        name="Emergency Fund Alpha",
        target_amount=Decimal("100000.00"),
        current_amount=Decimal("40000.00"),
        monthly_contribution=Decimal("10000.00"),
        status="active",
    )
    goal2 = Goal(
        user_id=user2.id,
        name="New Laptop Beta",
        target_amount=Decimal("80000.00"),
        current_amount=Decimal("20000.00"),
        monthly_contribution=Decimal("5000.00"),
        status="active",
    )
    db_session.add_all([goal1, goal2])
    db_session.commit()

    return {
        "user1": user1,
        "user2": user2,
        "goal1": goal1,
        "goal2": goal2,
    }


class TestDashboardAPI:
    """Tests for GET /overview and /api/v1/overview."""

    def test_get_overview_success(self, client: TestClient, setup_two_users: dict):
        user1 = setup_two_users["user1"]
        response = client.get(f"/overview?user_id={user1.id}")
        assert response.status_code == 200
        data = response.json()

        # Balance = 75,000 - 25,000 - 8,000 - 6,000 = 36,000.00
        assert data["balance"] == "36000.00"
        assert data["monthly_income"] == "75000.00"
        # Monthly spending (August) = 25,000 (Rent) + 8,000 (Food) = 33,000.00
        assert data["monthly_spending"] == "33000.00"
        # Savings / Surplus = 75,000 - 33,000 = 42,000.00
        assert data["savings"] == "42000.00"
        assert data["monthly_surplus"] == "42000.00"
        assert data["upcoming_bills"] == "1850.00"
        assert len(data["goals"]) == 1
        assert data["goals"][0]["name"] == "Emergency Fund Alpha"

    def test_get_overview_versioned_endpoint(self, client: TestClient, setup_two_users: dict):
        user1 = setup_two_users["user1"]
        response = client.get(f"/api/v1/overview?user_id={user1.id}")
        assert response.status_code == 200
        assert response.json()["balance"] == "36000.00"

    def test_get_overview_nonexistent_user(self, client: TestClient):
        response = client.get("/overview?user_id=999999")
        assert response.status_code == 404
        assert "not found" in response.json()["detail"].lower()


class TestTransactionsAPI:
    """Tests for GET /transactions and /api/v1/transactions."""

    def test_get_transactions_this_month(self, client: TestClient, setup_two_users: dict):
        user1 = setup_two_users["user1"]
        response = client.get(f"/transactions?user_id={user1.id}&period=this_month")
        assert response.status_code == 200
        data = response.json()

        txs = data["transactions"]
        # 3 August transactions for user1
        assert len(txs) == 3
        # Check amounts preserve sign
        amounts = [t["amount"] for t in txs]
        assert "75000.00" in amounts
        assert "-25000.00" in amounts
        assert "-8000.00" in amounts

        # Category spending
        assert data["by_category"]["Food"] == "8000.00"
        assert data["by_category"]["Bills"] == "25000.00"

    def test_get_transactions_last_month(self, client: TestClient, setup_two_users: dict):
        user1 = setup_two_users["user1"]
        response = client.get(f"/transactions?user_id={user1.id}&period=last_month")
        assert response.status_code == 200
        data = response.json()

        txs = data["transactions"]
        # 1 July transaction for user1
        assert len(txs) == 1
        assert txs[0]["description"] == "July Groceries"
        assert txs[0]["amount"] == "-6000.00"
        assert data["by_category"]["Food"] == "6000.00"

    def test_get_transactions_unsupported_period(self, client: TestClient, setup_two_users: dict):
        user1 = setup_two_users["user1"]
        response = client.get(f"/transactions?user_id={user1.id}&period=next_month")
        assert response.status_code == 400
        assert "Unsupported period" in response.json()["detail"]

    def test_get_transactions_nonexistent_user(self, client: TestClient):
        response = client.get("/transactions?user_id=888888")
        assert response.status_code == 404

    def test_transactions_user_isolation(self, client: TestClient, setup_two_users: dict):
        user1 = setup_two_users["user1"]
        user2 = setup_two_users["user2"]

        res1 = client.get(f"/transactions?user_id={user1.id}&period=this_month")
        res2 = client.get(f"/transactions?user_id={user2.id}&period=this_month")

        txs1 = res1.json()["transactions"]
        txs2 = res2.json()["transactions"]

        # Ensure User 1 sees zero transactions from User 2
        user1_ids = {t["id"] for t in txs1}
        user2_ids = {t["id"] for t in txs2}
        assert user1_ids.isdisjoint(user2_ids)

        # User 1 has no Shopping; User 2 has 12,000 Shopping
        assert res1.json()["by_category"]["Shopping"] == "0.00"
        assert res2.json()["by_category"]["Shopping"] == "12000.00"


class TestGoalsAPI:
    """Tests for GET /goals, POST /goals, and PATCH /goals/{id}."""

    def test_list_goals_success(self, client: TestClient, setup_two_users: dict):
        user1 = setup_two_users["user1"]
        response = client.get(f"/goals?user_id={user1.id}")
        assert response.status_code == 200
        goals = response.json()
        assert len(goals) == 1
        assert goals[0]["name"] == "Emergency Fund Alpha"
        assert goals[0]["target_amount"] == "100000.00"

    def test_list_goals_user_isolation(self, client: TestClient, setup_two_users: dict):
        user1 = setup_two_users["user1"]
        user2 = setup_two_users["user2"]

        res1 = client.get(f"/goals?user_id={user1.id}")
        res2 = client.get(f"/goals?user_id={user2.id}")

        assert len(res1.json()) == 1
        assert res1.json()[0]["name"] == "Emergency Fund Alpha"
        assert len(res2.json()) == 1
        assert res2.json()[0]["name"] == "New Laptop Beta"

    def test_create_goal_success(self, client: TestClient, setup_two_users: dict):
        user1 = setup_two_users["user1"]
        payload = {
            "user_id": user1.id,
            "name": "Trip to Japan",
            "target_amount": 250000.0,
            "monthly_contribution": 20000.0,
            "target_date": "2027-12-31",
        }
        response = client.post("/goals", json=payload)
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Trip to Japan"
        assert data["target_amount"] == "250000.00"
        assert data["current_amount"] == "0.00"
        assert data["monthly_contribution"] == "20000.00"
        assert data["status"] == "active"
        assert data["target_date"] == "2027-12-31"

    def test_create_goal_nonexistent_user(self, client: TestClient):
        payload = {
            "user_id": 999999,
            "name": "Ghost Goal",
            "target_amount": 50000.0,
            "monthly_contribution": 5000.0,
        }
        response = client.post("/goals", json=payload)
        assert response.status_code == 404

    def test_create_goal_invalid_amount_or_contribution(self, client: TestClient, setup_two_users: dict):
        user1 = setup_two_users["user1"]
        # Zero target amount
        payload1 = {"user_id": user1.id, "name": "Bad Goal 1", "target_amount": 0, "monthly_contribution": 5000}
        assert client.post("/goals", json=payload1).status_code in (400, 422)

        # Negative contribution
        payload2 = {"user_id": user1.id, "name": "Bad Goal 2", "target_amount": 50000, "monthly_contribution": -100}
        assert client.post("/goals", json=payload2).status_code in (400, 422)

    def test_patch_goal_contribution_and_projection(self, client: TestClient, setup_two_users: dict):
        goal1 = setup_two_users["goal1"]
        # Remaining = 100,000 - 40,000 = 60,000.
        # Updated monthly_contribution = 15,000 -> ceil(60,000 / 15,000) = 4 months.
        patch_payload = {
            "monthly_contribution": 15000.0,
            "user_id": goal1.user_id,
        }
        response = client.patch(f"/goals/{goal1.id}", json=patch_payload)
        assert response.status_code == 200
        data = response.json()

        assert data["goal"]["monthly_contribution"] == "15000.00"
        assert data["projection"]["current_months_remaining"] == "4"

    def test_patch_goal_user_isolation_forbidden(self, client: TestClient, setup_two_users: dict):
        goal1 = setup_two_users["goal1"]  # belongs to user 1
        user2 = setup_two_users["user2"]  # user 2 tries to update user 1's goal

        patch_payload = {
            "monthly_contribution": 25000.0,
            "user_id": user2.id,  # Spoofed user_id
        }
        response = client.patch(f"/goals/{goal1.id}", json=patch_payload)
        assert response.status_code == 403

    def test_patch_nonexistent_goal(self, client: TestClient):
        response = client.patch("/goals/999999", json={"monthly_contribution": 10000.0})
        assert response.status_code == 404


class TestLiveSeededDatasetEndpoints:
    """Integration verification tests executing against the live seeded database (finsight.db)."""

    def test_seeded_user_overview(self):
        from backend.main import app
        with TestClient(app) as live_client:
            # Query demo user (user_id=1)
            response = live_client.get("/overview?user_id=1")
            assert response.status_code == 200
            data = response.json()

            # Exact values from Day 2 dataset audit
            assert data["balance"] == "138372.00"
            assert data["monthly_income"] == "75000.00"
            assert data["monthly_spending"] == "50297.00"
            assert data["savings"] == "24703.00"
            assert data["monthly_surplus"] == "24703.00"
            assert data["upcoming_bills"] == "6529.00"
            assert len(data["goals"]) == 1
            assert data["goals"][0]["name"] == "Emergency Fund"

    def test_seeded_user_transactions(self):
        from backend.main import app
        with TestClient(app) as live_client:
            response = live_client.get("/transactions?user_id=1&period=this_month")
            assert response.status_code == 200
            data = response.json()

            assert len(data["transactions"]) == 21  # August transactions
            assert data["by_category"]["Food"] == "14450.00"
            assert data["by_category"]["Bills"] == "27969.00"

    def test_seeded_user_goals_and_patch(self):
        from backend.main import app
        with TestClient(app) as live_client:
            response = live_client.get("/goals?user_id=1")
            assert response.status_code == 200
            goals = response.json()
            assert len(goals) >= 1
            emergency_goal = next(g for g in goals if g["name"] == "Emergency Fund")

            # Test PATCH contribution
            patch_res = live_client.patch(
                f"/goals/{emergency_goal['id']}",
                json={"monthly_contribution": 15000.0, "user_id": 1},
            )
            assert patch_res.status_code == 200
            data = patch_res.json()
            assert data["goal"]["monthly_contribution"] == "15000.00"
            # (150,000 - 45,000) / 15,000 = 7 months
            assert data["projection"]["current_months_remaining"] == "7"

            # Reset back to 10000 for idempotency
            live_client.patch(
                f"/goals/{emergency_goal['id']}",
                json={"monthly_contribution": 10000.0, "user_id": 1},
            )
