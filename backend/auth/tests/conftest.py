"""
Pytest fixtures for FinSight authentication and passkey tests.
Uses SQLite in-memory database with per-test schema recreation.
"""

import os
import pytest
from typing import Generator
from decimal import Decimal
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

from backend.db import Base, get_db
from backend.main import app
from backend.models import User, Account, Transaction, Goal, Bill, PendingPayment, PasskeyCredential
from backend.auth.security import hash_password, create_access_token

TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """Provides an isolated database session for each test."""
    import backend.models  # noqa: F401
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()

    yield session

    session.close()
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """Provides a FastAPI TestClient with overridden get_db dependency."""
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()


@pytest.fixture
def auth_user_alpha(db_session: Session) -> dict:
    """Creates authenticated User Alpha with accounts and financial data."""
    user = User(
        full_name="Alpha Tester",
        email="alpha.tester@example.com",
        hashed_password=hash_password("Password123!"),
        accessibility_prefs={"voice_first": True, "screen_reader": True},
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    acc = Account(
        user_id=user.id,
        name="Alpha Checking",
        account_type="checking",
        balance=Decimal("50000.00"),
        monthly_income=Decimal("60000.00"),
        currency="INR",
        is_active=True,
    )
    db_session.add(acc)
    db_session.flush()

    # Opening balance transaction
    tx_open = Transaction(
        account_id=acc.id,
        user_id=user.id,
        amount=Decimal("50000.00"),
        transaction_type="income",
        category="Other",
        description="Opening Balance",
        transaction_date=datetime(2026, 8, 1, 10, 0, 0),
    )
    db_session.add(tx_open)

    # Goal
    goal = Goal(
        user_id=user.id,
        name="Alpha Vacation",
        target_amount=Decimal("30000.00"),
        current_amount=Decimal("10000.00"),
        monthly_contribution=Decimal("5000.00"),
        status="active",
    )
    db_session.add(goal)
    db_session.commit()
    db_session.refresh(user)

    token = create_access_token(data={"sub": str(user.id), "email": user.email})

    return {
        "user": user,
        "token": token,
        "headers": {"Authorization": f"Bearer {token}"},
        "account": acc,
        "goal": goal,
    }


@pytest.fixture
def auth_user_beta(db_session: Session) -> dict:
    """Creates authenticated User Beta with separate financial records."""
    user = User(
        full_name="Beta Tester",
        email="beta.tester@example.com",
        hashed_password=hash_password("Password456!"),
        accessibility_prefs={"voice_first": False},
        is_active=True,
    )
    db_session.add(user)
    db_session.flush()

    acc = Account(
        user_id=user.id,
        name="Beta Savings",
        account_type="savings",
        balance=Decimal("20000.00"),
        monthly_income=Decimal("40000.00"),
        currency="INR",
        is_active=True,
    )
    db_session.add(acc)
    db_session.flush()

    tx_open = Transaction(
        account_id=acc.id,
        user_id=user.id,
        amount=Decimal("20000.00"),
        transaction_type="income",
        category="Other",
        description="Opening Balance",
        transaction_date=datetime(2026, 8, 1, 10, 0, 0),
    )
    db_session.add(tx_open)

    goal = Goal(
        user_id=user.id,
        name="Beta Laptop",
        target_amount=Decimal("80000.00"),
        current_amount=Decimal("20000.00"),
        monthly_contribution=Decimal("10000.00"),
        status="active",
    )
    db_session.add(goal)
    db_session.commit()
    db_session.refresh(user)

    token = create_access_token(data={"sub": str(user.id), "email": user.email})

    return {
        "user": user,
        "token": token,
        "headers": {"Authorization": f"Bearer {token}"},
        "account": acc,
        "goal": goal,
    }
