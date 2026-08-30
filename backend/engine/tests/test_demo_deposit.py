"""
Unit and Integration Tests for Development Demo Deposit Endpoint.

Tests:
1. Authenticated user can add demo deposit when FINSIGHT_DEMO_MODE=true.
2. Cross-user isolation: User A cannot deposit into User B's account.
3. Client-supplied user_id is strictly ignored/rejected in favor of JWT identity.
4. Authoritative balance is dynamically and accurately calculated by the deterministic financial engine.
5. Endpoint is strictly unavailable (403 Forbidden) when FINSIGHT_DEMO_MODE is disabled or false.
6. Input validation (positive amounts, valid categories).
7. Direct route /demo/deposit accessibility.
"""

from decimal import Decimal
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.models import User, Account, Transaction
from backend.auth.security import hash_password, create_access_token
from backend.engine import get_balance


@pytest.fixture
def test_user(db_session: Session) -> User:
    """Creates a clean test user with a zero-balance primary checking account."""
    user = User(
        full_name="Demo Test User",
        email="demotester@example.com",
        hashed_password=hash_password("SecurePassword123!"),
        accessibility_prefs={"voice_first": True},
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    acc = Account(
        user_id=user.id,
        name="Primary Account",
        account_type="checking",
        balance=Decimal("0.00"),
        monthly_income=Decimal("0.00"),
        currency="INR",
        is_active=True,
    )
    db_session.add(acc)
    db_session.commit()
    db_session.refresh(user)
    return user


@pytest.fixture
def user_auth_headers(test_user: User) -> dict:
    """Generates valid JWT Bearer authentication headers for test_user."""
    token = create_access_token(data={"sub": str(test_user.id), "email": test_user.email})
    return {"Authorization": f"Bearer {token}"}


class TestDemoDepositEndpoint:
    """Test suite verifying development demo deposit endpoint behavior and security."""

    def test_demo_deposit_success_when_enabled(
        self,
        client: TestClient,
        db_session: Session,
        test_user: User,
        user_auth_headers: dict,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Authenticated user successfully creates a demo deposit when demo mode is active."""
        monkeypatch.setenv("FINSIGHT_DEMO_MODE", "true")

        # Initial balance must be ₹0.00
        initial_balance = get_balance(test_user.id, db_session)["balance"]
        assert initial_balance == Decimal("0.00")

        # 1. Create first synthetic deposit
        payload = {
            "amount": 50000.00,
            "merchant_name": "Demo Salary Deposit",
            "description": "Initial synthetic testing funds",
            "category": "Other",
        }
        res = client.post("/transactions/demo-deposit", headers=user_auth_headers, json=payload)
        assert res.status_code == 201
        data = res.json()

        assert data["status"] == "success"
        assert Decimal(str(data["transaction"]["amount"])) == Decimal("50000.00")
        assert data["transaction"]["transaction_type"] == "income"
        assert data["transaction"]["source"] == "demo"
        assert data["transaction"]["user_id"] == test_user.id
        assert Decimal(str(data["authoritative_balance"])) == Decimal("50000.00")

        # Verify underlying database record
        tx = db_session.query(Transaction).filter(Transaction.id == data["transaction"]["id"]).first()
        assert tx is not None
        assert tx.user_id == test_user.id
        assert tx.amount == Decimal("50000.00")
        assert tx.source == "demo"

        # 2. Create second deposit to verify dynamic balance recalculation
        res2 = client.post(
            "/transactions/demo-deposit",
            headers=user_auth_headers,
            json={"amount": 15000.00, "category": "Other"},
        )
        assert res2.status_code == 201
        data2 = res2.json()
        assert Decimal(str(data2["authoritative_balance"])) == Decimal("65000.00")

        # Verify deterministic engine reflects updated balance
        current_engine_balance = get_balance(test_user.id, db_session)["balance"]
        assert current_engine_balance == Decimal("65000.00")

    def test_demo_deposit_direct_route_alias(
        self,
        client: TestClient,
        test_user: User,
        user_auth_headers: dict,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Verifies the direct route /demo/deposit works identically."""
        monkeypatch.setenv("FINSIGHT_DEMO_MODE", "true")

        res = client.post(
            "/demo/deposit",
            headers=user_auth_headers,
            json={"amount": 10000.00, "merchant_name": "Direct Route Deposit"},
        )
        assert res.status_code == 201
        data = res.json()
        assert data["status"] == "success"
        assert Decimal(str(data["transaction"]["amount"])) == Decimal("10000.00")

    def test_demo_deposit_disabled_when_env_var_missing_or_false(
        self,
        client: TestClient,
        user_auth_headers: dict,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Endpoint strictly returns 403 Forbidden when FINSIGHT_DEMO_MODE is not enabled."""
        # Case A: Variable is unset / empty
        monkeypatch.delenv("FINSIGHT_DEMO_MODE", raising=False)
        res1 = client.post("/transactions/demo-deposit", headers=user_auth_headers, json={"amount": 1000.00})
        assert res1.status_code == 403
        assert "disabled" in res1.json()["detail"].lower()

        # Case B: Variable is explicitly 'false'
        monkeypatch.setenv("FINSIGHT_DEMO_MODE", "false")
        res2 = client.post("/transactions/demo-deposit", headers=user_auth_headers, json={"amount": 1000.00})
        assert res2.status_code == 403
        assert "disabled" in res2.json()["detail"].lower()

    def test_cross_user_isolation_cannot_fund_another_user_account(
        self,
        client: TestClient,
        db_session: Session,
        test_user: User,
        user_auth_headers: dict,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """User A cannot deposit into User B's account ID."""
        monkeypatch.setenv("FINSIGHT_DEMO_MODE", "true")

        # Create User B with an account
        user_b = User(
            full_name="User Beta",
            email="userbeta@example.com",
            hashed_password=hash_password("Pass123456!"),
            is_active=True,
        )
        db_session.add(user_b)
        db_session.flush()

        acc_b = Account(
            user_id=user_b.id,
            name="Beta Account",
            balance=Decimal("0.00"),
            is_active=True,
        )
        db_session.add(acc_b)
        db_session.commit()

        # User A tries to deposit targeting account_id of User B
        res = client.post(
            "/transactions/demo-deposit",
            headers=user_auth_headers,
            json={"amount": 5000.00, "account_id": acc_b.id},
        )
        assert res.status_code == 404
        assert "not found" in res.json()["detail"].lower()

        # Verify User B's balance remains 0
        balance_b = get_balance(user_b.id, db_session)["balance"]
        assert balance_b == Decimal("0.00")

    def test_client_supplied_user_id_in_body_is_ignored(
        self,
        client: TestClient,
        db_session: Session,
        test_user: User,
        user_auth_headers: dict,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Any client-supplied user_id in body is ignored; identity derives from JWT."""
        monkeypatch.setenv("FINSIGHT_DEMO_MODE", "true")

        # Send arbitrary dummy user_id in payload
        payload = {
            "amount": 20000.00,
            "merchant_name": "Test Payer",
            "user_id": 99999,  # Spoofed user_id
        }
        res = client.post("/transactions/demo-deposit", headers=user_auth_headers, json=payload)
        assert res.status_code == 201
        data = res.json()

        # Must belong strictly to test_user (from JWT), NOT 99999
        assert data["transaction"]["user_id"] == test_user.id
        assert data["transaction"]["user_id"] != 99999

    def test_demo_deposit_validation_errors(
        self,
        client: TestClient,
        user_auth_headers: dict,
        monkeypatch: pytest.MonkeyPatch,
    ):
        """Rejects non-positive amounts and invalid categories."""
        monkeypatch.setenv("FINSIGHT_DEMO_MODE", "true")

        # Zero or negative amount
        res_zero = client.post("/transactions/demo-deposit", headers=user_auth_headers, json={"amount": 0.00})
        assert res_zero.status_code == 422

        res_neg = client.post("/transactions/demo-deposit", headers=user_auth_headers, json={"amount": -500.00})
        assert res_neg.status_code == 422

        # Invalid category
        res_cat = client.post(
            "/transactions/demo-deposit",
            headers=user_auth_headers,
            json={"amount": 1000.00, "category": "InvalidCategory123"},
        )
        assert res_cat.status_code == 400
        assert "invalid category" in res_cat.json()["detail"].lower()
