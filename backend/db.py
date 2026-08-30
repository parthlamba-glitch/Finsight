"""
Database configuration and session management for FinSight.
Uses SQLite with SQLAlchemy ORM.
"""

import os
from typing import Generator
from sqlalchemy import create_engine
from sqlalchemy.orm import declarative_base, sessionmaker, Session

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./finsight.db")

# SQLite-specific connect args (check_same_thread=False for FastAPI multi-threaded requests)
connect_args = {"check_same_thread": False} if DATABASE_URL.startswith("sqlite") else {}

engine = create_engine(
    DATABASE_URL,
    connect_args=connect_args,
    echo=os.getenv("SQL_ECHO", "false").lower() == "true",
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()


def get_db() -> Generator[Session, None, None]:
    """
    FastAPI dependency that provides a database session per request.
    Creates a session, yields it, and ensures it is closed after request completion.
    Does not auto-commit.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def init_db() -> None:
    """
    Initializes the database by creating all tables defined in models,
    and safely ensuring schema migrations (like source/reference_id) exist.
    """
    # Import all models to register them on Base.metadata
    from backend import models  # noqa: F401
    from sqlalchemy import text
    Base.metadata.create_all(bind=engine)

    # Safe idempotent SQLite schema migration
    if DATABASE_URL.startswith("sqlite"):
        with engine.connect() as conn:
            # Transactions columns check
            cursor = conn.execute(text("PRAGMA table_info(transactions)"))
            tx_cols = [row[1] for row in cursor.fetchall()]
            if tx_cols:
                if "source" not in tx_cols:
                    conn.execute(text("ALTER TABLE transactions ADD COLUMN source VARCHAR(50) DEFAULT 'bank' NOT NULL"))
                    conn.commit()
                if "reference_id" not in tx_cols:
                    conn.execute(text("ALTER TABLE transactions ADD COLUMN reference_id VARCHAR(255)"))
                    conn.commit()

            # Users table columns check
            cursor = conn.execute(text("PRAGMA table_info(users)"))
            user_cols = [row[1] for row in cursor.fetchall()]
            if user_cols and "hashed_password" not in user_cols:
                conn.execute(text("ALTER TABLE users ADD COLUMN hashed_password VARCHAR(255)"))
                conn.commit()


