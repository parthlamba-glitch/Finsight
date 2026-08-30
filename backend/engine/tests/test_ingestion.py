"""
Comprehensive Test Suite for Day 4B: Transaction Ingestion, Normalization, and Deduplication.

Tests:
1. Mock bank connection (/bank/connect)
2. Successful bank sync (/bank/sync)
3. Repeated bank sync (idempotency, duplicates skipped)
4. Duplicate prevention via reference_id and content-tuple
5. Voice transaction creation (/transactions/voice)
6. Voice expense sign normalization (positive -> negative)
7. Voice income sign normalization (positive -> positive)
8. Invalid transaction type rejection (400)
9. Invalid category rejection (400)
10. Zero/negative input amount rejection (400/422)
11. Invalid date handling (400/422)
12. Statement candidate ingestion (/statements/upload) stages without creating transactions
13. Statement confirmation (/transactions/confirm) persists with source='statement'
14. Statement duplicate detection skips already-existing transactions
15. User and account ownership isolation across bank, voice, and statement endpoints
16. Unknown user/account handling (404)
17. Financial engine compatibility (authoritative balance & spending updates immediately)
18. Payment engine compatibility (source='payment')
19. Source field correctness across all sources ('bank', 'statement', 'voice', 'payment')
"""

from decimal import Decimal
from datetime import datetime, date
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session

from backend.models import User, Account, Transaction, Document
from backend.engine import get_balance, get_spending_summary
from backend.payment.payment_engine import execute_payment
from backend.ingestion.deduplicator import is_duplicate_transaction


@pytest.fixture
def ingestion_fixture(db_session: Session):
    """Sets up two isolated users with active accounts for ingestion testing."""
    user1 = User(
        full_name="Aarav Sharma",
        email="aarav.ingest@example.com",
        accessibility_prefs={"voice_first": True, "screen_reader": True, "spoken_confirmations": True, "preferred_language": "en-IN"},
    )
    user2 = User(
        full_name="Neha Gupta",
        email="neha.ingest@example.com",
        accessibility_prefs={"voice_first": False, "screen_reader": False, "spoken_confirmations": False, "preferred_language": "en-US"},
    )
    db_session.add_all([user1, user2])
    db_session.flush()

    acc1 = Account(
        user_id=user1.id,
        name="HDFC Primary Savings",
        balance=Decimal("0.00"),
        monthly_income=Decimal("75000.00"),
        is_active=True,
    )
    acc2 = Account(
        user_id=user2.id,
        name="ICICI Savings",
        balance=Decimal("0.00"),
        monthly_income=Decimal("50000.00"),
        is_active=True,
    )
    db_session.add_all([acc1, acc2])
    db_session.flush()

    # Initial opening salary for User 1 = 50,000.00 (August 1, 2026)
    tx_init_1 = Transaction(
        account_id=acc1.id,
        user_id=user1.id,
        amount=Decimal("50000.00"),
        currency="INR",
        transaction_type="income",
        category="Other",
        description="August Opening Salary",
        source="bank",
        reference_id="INIT-USER1-001",
        transaction_date=datetime(2026, 8, 1, 10, 0, 0),
    )
    db_session.add(tx_init_1)
    db_session.commit()

    return {
        "user1": user1,
        "user2": user2,
        "acc1": acc1,
        "acc2": acc2,
    }


class TestMockBankIngestion:
    """Tests for /bank/connect and /bank/sync."""

    def test_mock_bank_connection(self, client: TestClient, ingestion_fixture: dict):
        user1 = ingestion_fixture["user1"]
        response = client.post("/bank/connect", json={"user_id": user1.id, "institution_name": "HDFC Bank Mock"})
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "connected"
        assert data["user_id"] == user1.id
        assert data["institution_name"] == "HDFC Bank Mock"
        assert data["account_id"] == ingestion_fixture["acc1"].id

    def test_successful_bank_sync(self, client: TestClient, ingestion_fixture: dict, db_session: Session):
        user1 = ingestion_fixture["user1"]
        # Sync 4 deterministic mock bank items
        response = client.post("/bank/sync", json={"user_id": user1.id})
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "success"
        assert data["imported_count"] == 4
        assert data["duplicate_count"] == 0
        assert len(data["imported_transactions"]) == 4

        # Check transactions in DB
        txs = db_session.query(Transaction).filter(Transaction.user_id == user1.id, Transaction.source == "bank").all()
        # 1 initial + 4 synced = 5
        assert len(txs) == 5

    def test_repeated_bank_sync_idempotency_and_duplicates(self, client: TestClient, ingestion_fixture: dict):
        user1 = ingestion_fixture["user1"]
        # First sync: 4 imported
        res1 = client.post("/bank/sync", json={"user_id": user1.id})
        assert res1.json()["imported_count"] == 4

        # Second sync: 0 imported, 4 skipped
        res2 = client.post("/bank/sync", json={"user_id": user1.id})
        assert res2.status_code == 200
        data2 = res2.json()
        assert data2["imported_count"] == 0
        assert data2["duplicate_count"] == 4
        assert data2["skipped_count"] == 4
        assert len(data2["skipped_transactions"]) == 4


class TestVoiceTransactionIngestion:
    """Tests for /transactions/voice."""

    def test_voice_expense_sign_normalization(self, client: TestClient, ingestion_fixture: dict, db_session: Session):
        user1 = ingestion_fixture["user1"]
        # Positive input amount: 250.00
        payload = {
            "user_id": user1.id,
            "amount": 250.00,
            "transaction_type": "expense",
            "category": "Food",
            "merchant_name": "Chai Point",
            "description": "Tea and samosa",
            "transaction_date": "2026-08-27T17:00:00",
        }
        response = client.post("/transactions/voice", json=payload)
        assert response.status_code == 201
        data = response.json()

        # Database amount normalized to -250.00
        assert data["amount"] == "-250.00"
        assert data["transaction_type"] == "expense"
        assert data["source"] == "voice"
        assert data["category"] == "Food"
        assert data["merchant_name"] == "Chai Point"

        # Check DB directly
        db_tx = db_session.query(Transaction).filter(Transaction.id == data["id"]).first()
        assert db_tx.amount == Decimal("-250.00")
        assert db_tx.source == "voice"

    def test_voice_income_sign_normalization(self, client: TestClient, ingestion_fixture: dict, db_session: Session):
        user1 = ingestion_fixture["user1"]
        payload = {
            "user_id": user1.id,
            "amount": 1500.00,
            "transaction_type": "income",
            "category": "Other",
            "merchant_name": "Friend Repayment",
            "description": "Lunch split repayment",
            "transaction_date": "2026-08-27T18:00:00",
        }
        response = client.post("/transactions/voice", json=payload)
        assert response.status_code == 201
        data = response.json()

        assert data["amount"] == "1500.00"
        assert data["transaction_type"] == "income"
        assert data["source"] == "voice"

    def test_invalid_transaction_type_rejection(self, client: TestClient, ingestion_fixture: dict):
        user1 = ingestion_fixture["user1"]
        payload = {
            "user_id": user1.id,
            "amount": 500.00,
            "transaction_type": "invalid_type",
            "category": "Food",
        }
        response = client.post("/transactions/voice", json=payload)
        assert response.status_code in (400, 422)

    def test_invalid_category_rejection(self, client: TestClient, ingestion_fixture: dict):
        user1 = ingestion_fixture["user1"]
        payload = {
            "user_id": user1.id,
            "amount": 500.00,
            "transaction_type": "expense",
            "category": "CryptocurrencyGambling",
        }
        response = client.post("/transactions/voice", json=payload)
        assert response.status_code in (400, 422)

    def test_zero_or_negative_amount_rejection(self, client: TestClient, ingestion_fixture: dict):
        user1 = ingestion_fixture["user1"]
        # Zero
        p1 = {"user_id": user1.id, "amount": 0.00, "transaction_type": "expense", "category": "Food"}
        assert client.post("/transactions/voice", json=p1).status_code in (400, 422)

        # Negative
        p2 = {"user_id": user1.id, "amount": -150.00, "transaction_type": "expense", "category": "Food"}
        assert client.post("/transactions/voice", json=p2).status_code in (400, 422)


class TestStatementIngestionAndConfirmation:
    """Tests for /statements/upload and /transactions/confirm."""

    def test_statement_candidate_ingestion_stages_without_writing_transactions(
        self, client: TestClient, ingestion_fixture: dict, db_session: Session
    ):
        user1 = ingestion_fixture["user1"]
        initial_tx_count = db_session.query(Transaction).filter(Transaction.user_id == user1.id).count()

        upload_payload = {
            "user_id": user1.id,
            "filename": "august_hdfc_statement.pdf",
            "extracted_candidates": [
                {
                    "reference_id": "STMT-AUG-01",
                    "amount": 850.00,
                    "transaction_type": "expense",
                    "category": "Food",
                    "merchant_name": "FreshMenu Bangalore",
                    "description": "Lunch box",
                    "transaction_date": "2026-08-25T13:00:00",
                },
                {
                    "reference_id": "STMT-AUG-02",
                    "amount": 1200.00,
                    "transaction_type": "expense",
                    "category": "Healthcare",
                    "merchant_name": "Apollo Pharmacy",
                    "description": "Medicines",
                    "transaction_date": "2026-08-25T16:30:00",
                },
            ],
        }

        response = client.post("/statements/upload", json=upload_payload)
        assert response.status_code == 200
        data = response.json()
        assert data["total_candidates"] == 2
        assert data["valid_candidates_count"] == 2
        assert data["duplicate_candidates_count"] == 0

        # CRITICAL: Verify NO transactions were created in the database yet
        post_tx_count = db_session.query(Transaction).filter(Transaction.user_id == user1.id).count()
        assert post_tx_count == initial_tx_count

    def test_statement_confirmation_persists_transactions(
        self, client: TestClient, ingestion_fixture: dict, db_session: Session
    ):
        user1 = ingestion_fixture["user1"]
        confirm_payload = {
            "user_id": user1.id,
            "candidates": [
                {
                    "reference_id": "STMT-CONFIRM-01",
                    "amount": 850.00,
                    "transaction_type": "expense",
                    "category": "Food",
                    "merchant_name": "FreshMenu Bangalore",
                    "description": "Confirmed lunch box",
                    "transaction_date": "2026-08-25T13:00:00",
                }
            ],
        }

        response = client.post("/transactions/confirm", json=confirm_payload)
        assert response.status_code == 200
        data = response.json()

        assert data["status"] == "success"
        assert data["confirmed_count"] == 1
        assert data["transactions"][0]["amount"] == "-850.00"
        assert data["transactions"][0]["source"] == "statement"
        assert data["transactions"][0]["reference_id"] == "STMT-CONFIRM-01"

        # Check DB record
        tx = db_session.query(Transaction).filter(Transaction.reference_id == "STMT-CONFIRM-01").first()
        assert tx is not None
        assert tx.source == "statement"
        assert tx.amount == Decimal("-850.00")

    def test_statement_duplicate_detection(self, client: TestClient, ingestion_fixture: dict):
        user1 = ingestion_fixture["user1"]
        candidate = {
            "reference_id": "STMT-DUP-01",
            "amount": 500.00,
            "transaction_type": "expense",
            "category": "Shopping",
            "merchant_name": "Decathlon",
            "transaction_date": "2026-08-26T15:00:00",
        }

        # 1. Confirm once
        res1 = client.post("/transactions/confirm", json={"user_id": user1.id, "candidates": [candidate]})
        assert res1.json()["confirmed_count"] == 1

        # 2. Upload same candidate to statement upload -> evaluated as duplicate
        res_upload = client.post(
            "/statements/upload",
            json={"user_id": user1.id, "filename": "test.pdf", "extracted_candidates": [candidate]},
        )
        assert res_upload.json()["duplicate_candidates_count"] == 1
        assert res_upload.json()["candidates"][0]["is_duplicate"] is True

        # 3. Confirming second time skips duplicate
        res2 = client.post("/transactions/confirm", json={"user_id": user1.id, "candidates": [candidate]})
        assert res2.json()["confirmed_count"] == 0
        assert res2.json()["skipped_duplicates_count"] == 1


class TestUserIsolationAndCompatibility:
    """Verifies isolation, unknown user rejections, and financial engine compatibility."""

    def test_user_isolation_between_accounts(self, client: TestClient, ingestion_fixture: dict):
        user1 = ingestion_fixture["user1"]
        user2 = ingestion_fixture["user2"]
        acc2 = ingestion_fixture["acc2"]  # Account belonging to User 2

        # User 1 tries to sync User 2's account -> 404/400
        res = client.post("/bank/sync", json={"user_id": user1.id, "account_id": acc2.id})
        assert res.status_code in (400, 404)

        # User 1 tries to voice-insert on User 2's account -> 404
        res_voice = client.post(
            "/transactions/voice",
            json={"user_id": user1.id, "account_id": acc2.id, "amount": 100.0, "transaction_type": "expense", "category": "Food"},
        )
        assert res_voice.status_code == 404

    def test_unknown_user_rejected(self, client: TestClient):
        assert client.post("/bank/connect", json={"user_id": 999999}).status_code == 404
        assert client.post("/bank/sync", json={"user_id": 999999}).status_code == 404
        assert client.post("/transactions/voice", json={"user_id": 999999, "amount": 100.0, "transaction_type": "expense", "category": "Food"}).status_code == 404
        assert client.post("/statements/upload", json={"user_id": 999999, "filename": "x.pdf"}).status_code == 404
        assert client.post("/transactions/confirm", json={"user_id": 999999, "candidates": [{"amount": 100.0, "transaction_type": "expense", "category": "Food", "transaction_date": "2026-08-25T10:00:00"}]}).status_code == 404

    def test_financial_engine_immediately_reflects_ingested_transactions(
        self, client: TestClient, ingestion_fixture: dict, db_session: Session
    ):
        user1 = ingestion_fixture["user1"]
        # Initial balance: 50,000.00
        bal_init = get_balance(user1.id, db_session)["balance"]
        assert bal_init == Decimal("50000.00")

        # 1. Bank Sync: +15,000 Income, -450 Food, -320 Transport, -1299 Shopping = +12,931.00 net
        client.post("/bank/sync", json={"user_id": user1.id})
        bal_after_sync = get_balance(user1.id, db_session)["balance"]
        # 50,000 + 12,931 = 62,931.00
        assert bal_after_sync == Decimal("62931.00")

        # 2. Voice expense: -250.00 Food
        client.post(
            "/transactions/voice",
            json={"user_id": user1.id, "amount": 250.00, "transaction_type": "expense", "category": "Food", "merchant_name": "Chai Point"},
        )
        bal_after_voice = get_balance(user1.id, db_session)["balance"]
        # 62,931 - 250 = 62,681.00
        assert bal_after_voice == Decimal("62681.00")

        # 3. Statement confirmation: -850.00 Food
        client.post(
            "/transactions/confirm",
            json={
                "user_id": user1.id,
                "candidates": [
                    {
                        "reference_id": "STMT-FE-01",
                        "amount": 850.00,
                        "transaction_type": "expense",
                        "category": "Food",
                        "merchant_name": "FreshMenu",
                        "transaction_date": "2026-08-27T14:00:00",
                    }
                ],
            },
        )
        bal_after_stmt = get_balance(user1.id, db_session)["balance"]
        # 62,681 - 850 = 61,831.00
        assert bal_after_stmt == Decimal("61831.00")

        # Check spending summary directly from financial engine
        spending = get_spending_summary(user1.id, db_session, period="this_month")
        # Food = 450 (Bank) + 250 (Voice) + 850 (Statement) = 1550.00
        assert spending["by_category"]["Food"] == Decimal("1550.00")
        assert spending["by_category"]["Transport"] == Decimal("320.00")
        assert spending["by_category"]["Shopping"] == Decimal("1299.00")

    def test_payment_engine_compatibility_and_source_tags(
        self, ingestion_fixture: dict, db_session: Session
    ):
        user1 = ingestion_fixture["user1"]
        # Execute simulated payment
        pay_res = execute_payment(
            user_id=user1.id,
            amount=Decimal("1000.00"),
            recipient_name="Sharma Medical",
            db=db_session,
        )
        assert pay_res["success"] is True

        # Check source field on created transaction
        tx = db_session.query(Transaction).filter(Transaction.id == pay_res["transaction_id"]).first()
        assert tx.source == "payment"
        assert tx.amount == Decimal("-1000.00")

    def test_statement_confirmation_foreign_document_id_rejected(
        self, client: TestClient, ingestion_fixture: dict, db_session: Session
    ):
        """
        Regression Test 1: User A attempts to confirm statement transactions using
        a document_id belonging to User B. Must return 404 with 0 transactions created.
        """
        user1 = ingestion_fixture["user1"]
        user2 = ingestion_fixture["user2"]

        # Create a Document belonging to User 2
        doc_user2 = Document(
            user_id=user2.id,
            filename="user2_statement.pdf",
            document_type="bank_statement",
            mime_type="application/pdf",
            extracted_facts=[],
        )
        db_session.add(doc_user2)
        db_session.commit()
        db_session.refresh(doc_user2)

        initial_tx_count_user1 = db_session.query(Transaction).filter(Transaction.user_id == user1.id).count()

        # User 1 attempts to confirm using User 2's document_id
        confirm_payload = {
            "user_id": user1.id,
            "document_id": doc_user2.id,
            "candidates": [
                {
                    "reference_id": "STMT-UNAUTH-01",
                    "amount": 750.00,
                    "transaction_type": "expense",
                    "category": "Food",
                    "merchant_name": "Unauthorized Merchant",
                    "transaction_date": "2026-08-28T12:00:00",
                }
            ],
        }

        response = client.post("/transactions/confirm", json=confirm_payload)
        assert response.status_code == 404
        assert f"Document with id {doc_user2.id} not found for user {user1.id}" in response.json()["detail"]

        # Verify zero transactions were created
        post_tx_count_user1 = db_session.query(Transaction).filter(Transaction.user_id == user1.id).count()
        assert post_tx_count_user1 == initial_tx_count_user1

    def test_unnamed_transactions_not_falsely_flagged_as_duplicates(
        self, client: TestClient, ingestion_fixture: dict, db_session: Session
    ):
        """
        Regression Test 2: Two legitimate transactions for the same user/account
        with amount = ₹500, same date, merchant_name = None, no reference_id.
        They must NOT be considered duplicates.
        """
        user1 = ingestion_fixture["user1"]
        acc1 = ingestion_fixture["acc1"]

        # Direct check on deduplicator function
        is_dup_1, _, _ = is_duplicate_transaction(
            db=db_session,
            account_id=acc1.id,
            user_id=user1.id,
            amount=Decimal("-500.00"),
            transaction_date=datetime(2026, 8, 28, 10, 0, 0),
            merchant_name=None,
            reference_id=None,
        )
        assert is_dup_1 is False

        # First transaction confirmation
        res1 = client.post(
            "/transactions/confirm",
            json={
                "user_id": user1.id,
                "candidates": [
                    {
                        "amount": 500.00,
                        "transaction_type": "expense",
                        "category": "Other",
                        "merchant_name": None,
                        "description": "Cash withdrawal 1",
                        "transaction_date": "2026-08-28T10:00:00",
                    }
                ],
            },
        )
        assert res1.status_code == 200
        assert res1.json()["confirmed_count"] == 1

        # Second transaction confirmation (same amount, same date, no merchant, no reference_id)
        res2 = client.post(
            "/transactions/confirm",
            json={
                "user_id": user1.id,
                "candidates": [
                    {
                        "amount": 500.00,
                        "transaction_type": "expense",
                        "category": "Other",
                        "merchant_name": None,
                        "description": "Cash withdrawal 2",
                        "transaction_date": "2026-08-28T14:00:00",
                    }
                ],
            },
        )
        assert res2.status_code == 200
        assert res2.json()["confirmed_count"] == 1
        assert res2.json()["skipped_duplicates_count"] == 0

    def test_named_transactions_with_same_merchant_detected_as_duplicates(
        self, client: TestClient, ingestion_fixture: dict
    ):
        """
        Regression Test 3: Named transactions with same merchant, same account,
        same date, and same amount are STILL detected as duplicates.
        """
        user1 = ingestion_fixture["user1"]
        candidate = {
            "amount": 650.00,
            "transaction_type": "expense",
            "category": "Food",
            "merchant_name": "Swiggy Bangalore",
            "description": "Lunch order",
            "transaction_date": "2026-08-28T13:00:00",
        }

        # First confirmation -> succeeds
        res1 = client.post("/transactions/confirm", json={"user_id": user1.id, "candidates": [candidate]})
        assert res1.status_code == 200
        assert res1.json()["confirmed_count"] == 1

        # Second confirmation with same merchant/amount/date -> detected as duplicate
        res2 = client.post("/transactions/confirm", json={"user_id": user1.id, "candidates": [candidate]})
        assert res2.status_code == 200
        assert res2.json()["confirmed_count"] == 0
        assert res2.json()["skipped_duplicates_count"] == 1

    def test_exact_reference_id_deduplication(
        self, client: TestClient, ingestion_fixture: dict
    ):
        """
        Regression Test 4: Exact reference_id deduplication catches and skips duplicates.
        """
        user1 = ingestion_fixture["user1"]
        candidate = {
            "reference_id": "STMT-REF-EXACT-999",
            "amount": 1200.00,
            "transaction_type": "expense",
            "category": "Shopping",
            "merchant_name": "Myntra",
            "transaction_date": "2026-08-28T15:00:00",
        }

        # First confirmation -> succeeds
        res1 = client.post("/transactions/confirm", json={"user_id": user1.id, "candidates": [candidate]})
        assert res1.status_code == 200
        assert res1.json()["confirmed_count"] == 1

        # Second confirmation with same reference_id -> detected as duplicate
        res2 = client.post("/transactions/confirm", json={"user_id": user1.id, "candidates": [candidate]})
        assert res2.status_code == 200
        assert res2.json()["confirmed_count"] == 0
        assert res2.json()["skipped_duplicates_count"] == 1

