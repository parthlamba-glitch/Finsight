"""
Pytest configuration and test fixtures for FinSight foundation and engine tests.
Uses SQLite in-memory database with per-test schema recreation for complete isolation.
"""

import os
import pytest
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import StaticPool
from fastapi.testclient import TestClient

# Explicitly enable isolated demo/legacy unauthenticated compatibility mode for existing foundation tests
os.environ["FINSIGHT_ALLOW_DEMO_UNAUTHENTICATED"] = "true"

from backend.db import Base, get_db
from backend.main import app



# Shared in-memory SQLite engine with StaticPool
TEST_DATABASE_URL = "sqlite:///:memory:"

test_engine = create_engine(
    TEST_DATABASE_URL,
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
)

TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=test_engine)


@pytest.fixture(scope="function")
def db_session() -> Generator[Session, None, None]:
    """
    Provides an isolated transactional database session for an individual test.
    Creates clean tables before each test and drops all tables afterwards.
    """
    import backend.models  # noqa: F401
    Base.metadata.create_all(bind=test_engine)
    session = TestingSessionLocal()

    yield session

    session.close()
    Base.metadata.drop_all(bind=test_engine)


@pytest.fixture(scope="function")
def client(db_session: Session) -> Generator[TestClient, None, None]:
    """
    Provides a FastAPI TestClient with the database dependency overridden.
    """
    def override_get_db():
        try:
            yield db_session
        finally:
            pass

    app.dependency_overrides[get_db] = override_get_db
    with TestClient(app) as test_client:
        yield test_client
    app.dependency_overrides.clear()
