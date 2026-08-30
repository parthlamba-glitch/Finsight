"""
Comprehensive Test Suite for FinSight Authentication, JWT, Passkeys, and User Isolation.

Tests:
1. Signup (creation, password hashing, no fake data, validation, duplicate email rejection).
2. Login (password verification, JWT issuance, wrong password/unknown email/inactive handling).
3. Authenticated Profile (/auth/me, token validation, tamper resistance).
4. User Isolation & Anti-Spoofing (/ask, /overview, /transactions, /goals, /payments).
5. WebAuthn Passkeys (registration options, verification, login options, assertion verify, credentials CRUD).
6. Payment Security (authenticated preview, single-use execution, cross-user rejection, expiry).
7. Production Strict Mode Enforcement (missing Bearer token rejected with 401).
"""

import os
import json
from unittest.mock import patch, MagicMock
from decimal import Decimal
from datetime import datetime, timedelta
import pytest
from fastapi.testclient import TestClient
from sqlalchemy.orm import Session
from webauthn.helpers import bytes_to_base64url

from backend.models import User, Account, Transaction, Goal, Bill, PendingPayment, PasskeyCredential
from backend.auth.security import hash_password, verify_password, create_access_token
from backend.auth.webauthn_service import create_and_save_challenge


# =============================================================================
# 1. Signup Tests
# =============================================================================

class TestUserSignup:
    def test_signup_success(self, client: TestClient, db_session: Session):
        """Valid registration creates user, hashes password, and creates default account."""
        payload = {
            "name": "Rohan Gupta",
            "email": "rohan.gupta@example.com",
            "password": "SecurePassword123!",
            "accessibility_prefs": {"voice_first": True, "preferred_language": "en-IN"},
        }
        res = client.post("/auth/signup", json=payload)
        assert res.status_code == 201
        data = res.json()

        assert data["id"] is not None
        assert data["full_name"] == "Rohan Gupta"
        assert data["email"] == "rohan.gupta@example.com"
        assert data["accessibility_prefs"]["voice_first"] is True
        assert "password" not in data
        assert "hashed_password" not in data

        # Verify database record
        user_in_db = db_session.query(User).filter(User.email == "rohan.gupta@example.com").first()
        assert user_in_db is not None
        assert user_in_db.hashed_password != "SecurePassword123!"
        assert verify_password("SecurePassword123!", user_in_db.hashed_password) is True

        # Verify initial account created with zero balance (no fake transactions)
        accounts = db_session.query(Account).filter(Account.user_id == user_in_db.id).all()
        assert len(accounts) == 1
        assert accounts[0].balance == Decimal("0.00")
        assert accounts[0].monthly_income == Decimal("0.00")

        # Verify zero transactions exist for newly signed up user
        tx_count = db_session.query(Transaction).filter(Transaction.user_id == user_in_db.id).count()
        assert tx_count == 0

    def test_signup_duplicate_email_rejected(self, client: TestClient, auth_user_alpha: dict):
        """Duplicate email registration must be rejected with 400."""
        payload = {
            "name": "Another Alpha",
            "email": auth_user_alpha["user"].email,
            "password": "Password123!",
        }
        res = client.post("/auth/signup", json=payload)
        assert res.status_code == 400
        assert "already exists" in res.json()["detail"].lower()

    def test_signup_short_password_rejected(self, client: TestClient):
        """Password under 8 characters must be rejected by schema validation."""
        payload = {
            "name": "Short Pass User",
            "email": "short@example.com",
            "password": "short",
        }
        res = client.post("/auth/signup", json=payload)
        assert res.status_code == 422


# =============================================================================
# 2. Login Tests
# =============================================================================

class TestUserLogin:
    def test_login_success(self, client: TestClient, auth_user_alpha: dict):
        """Correct credentials return a signed JWT token and user profile."""
        payload = {
            "email": "alpha.tester@example.com",
            "password": "Password123!",
        }
        res = client.post("/auth/login", json=payload)
        assert res.status_code == 200
        data = res.json()

        assert "access_token" in data
        assert data["token_type"] == "bearer"
        assert data["expires_in"] > 0
        assert data["user"]["email"] == "alpha.tester@example.com"
        assert data["user"]["full_name"] == "Alpha Tester"
        assert "password" not in data["user"]

    def test_login_wrong_password_rejected(self, client: TestClient, auth_user_alpha: dict):
        """Incorrect password returns 401 Unauthorized."""
        payload = {
            "email": "alpha.tester@example.com",
            "password": "WrongPassword!",
        }
        res = client.post("/auth/login", json=payload)
        assert res.status_code == 401
        assert "invalid email or password" in res.json()["detail"].lower()

    def test_login_unknown_email_rejected(self, client: TestClient):
        """Unregistered email returns 401 Unauthorized."""
        payload = {
            "email": "nonexistent@example.com",
            "password": "AnyPassword123!",
        }
        res = client.post("/auth/login", json=payload)
        assert res.status_code == 401

    def test_login_inactive_user_rejected(self, client: TestClient, db_session: Session):
        """Inactive user account returns 403 Forbidden."""
        inactive_user = User(
            full_name="Inactive User",
            email="inactive@example.com",
            hashed_password=hash_password("Password123!"),
            is_active=False,
        )
        db_session.add(inactive_user)
        db_session.commit()

        res = client.post("/auth/login", json={"email": "inactive@example.com", "password": "Password123!"})
        assert res.status_code == 403


# =============================================================================
# 3. Authenticated Profile & Token Verification (/auth/me)
# =============================================================================

class TestAuthProfile:
    def test_get_me_success(self, client: TestClient, auth_user_alpha: dict):
        """Valid Bearer token returns current user profile."""
        res = client.get("/auth/me", headers=auth_user_alpha["headers"])
        assert res.status_code == 200
        data = res.json()
        assert data["id"] == auth_user_alpha["user"].id
        assert data["email"] == "alpha.tester@example.com"

    def test_get_me_invalid_token_rejected(self, client: TestClient):
        """Tampered or invalid token returns 401."""
        res = client.get("/auth/me", headers={"Authorization": "Bearer invalid.token.string"})
        assert res.status_code == 401

    def test_get_me_missing_token_rejected_in_strict_mode(self, client: TestClient):
        """Missing Authorization header strictly returns 401 in production mode."""
        with patch.dict(os.environ, {"FINSIGHT_ALLOW_DEMO_UNAUTHENTICATED": "false"}):
            res = client.get("/auth/me")
            assert res.status_code == 401


# =============================================================================
# 4. User Isolation & Anti-Spoofing Tests
# =============================================================================

class TestUserIsolationAndAntiSpoofing:
    def test_user_a_cannot_access_user_b_overview(
        self, client: TestClient, auth_user_alpha: dict, auth_user_beta: dict
    ):
        """User A sending user_id=User B still retrieves User A's data."""
        user_a = auth_user_alpha["user"]
        user_b = auth_user_beta["user"]

        # User A makes request with User B's ID in query
        res = client.get(f"/overview?user_id={user_b.id}", headers=auth_user_alpha["headers"])
        assert res.status_code == 200
        data = res.json()

        # Balance must match User A's balance (50,000), NOT User B's (20,000)
        assert data["balance"] == "50000.00"

    def test_user_a_cannot_access_user_b_transactions(
        self, client: TestClient, auth_user_alpha: dict, auth_user_beta: dict
    ):
        """User A sending user_id=User B still receives User A's transactions."""
        user_b = auth_user_beta["user"]
        res = client.get(f"/transactions?user_id={user_b.id}&period=this_month", headers=auth_user_alpha["headers"])
        assert res.status_code == 200
        data = res.json()

        for tx in data["transactions"]:
            assert tx["user_id"] == auth_user_alpha["user"].id

    def test_user_a_cannot_modify_user_b_goal(
        self, client: TestClient, auth_user_alpha: dict, auth_user_beta: dict
    ):
        """User A attempts to modify User B's goal -> 403 Forbidden."""
        goal_b = auth_user_beta["goal"]
        patch_payload = {"monthly_contribution": 15000.0}

        res = client.patch(f"/goals/{goal_b.id}", json=patch_payload, headers=auth_user_alpha["headers"])
        assert res.status_code == 403

    def test_authenticated_ask_uses_current_user_id(
        self, client: TestClient, auth_user_alpha: dict, auth_user_beta: dict
    ):
        """
        CRITICAL TEST:
        User A calls /ask claiming user_id = User B.
        Backend MUST ignore body user_id and strictly use User A's identity (50,000 balance).
        """
        user_b = auth_user_beta["user"]

        ask_payload = {
            "query": "What is my balance?",
            "user_id": user_b.id,  # Malicious / spoofed attempt
            "voice": True,
        }
        res = client.post("/ask", json=ask_payload, headers=auth_user_alpha["headers"])
        assert res.status_code == 200
        data = res.json()

        assert data["intent"] == "get_balance"
        assert str(data["structured_facts"]["balance"]) == "50000.00"
        assert "50,000" in data["answer_text"] or "50000" in data["answer_text"]

    def test_ask_strict_production_unauthenticated_rejected(self, client: TestClient, auth_user_alpha: dict):
        """In production mode, /ask without Bearer token returns 401."""
        with patch.dict(os.environ, {"FINSIGHT_ALLOW_DEMO_UNAUTHENTICATED": "false"}):
            res = client.post("/ask", json={"query": "What is my balance?"})
            assert res.status_code == 401


# =============================================================================
# 5. Passkey (WebAuthn) Flow Tests
# =============================================================================

class TestPasskeyEndpoints:
    def test_passkey_register_options_generated(self, client: TestClient, auth_user_alpha: dict):
        """Authenticated user receives WebAuthn registration options."""
        res = client.post("/auth/passkey/register/options", headers=auth_user_alpha["headers"])
        assert res.status_code == 200
        data = res.json()

        assert "challenge" in data
        assert "rp" in data
        assert "user" in data
        assert data["user"]["name"] == auth_user_alpha["user"].email

    def test_passkey_register_and_login_flow(self, client: TestClient, db_session: Session, auth_user_alpha: dict):
        """Full passkey registration and login verification with mocked WebAuthn cryptographic response."""
        user = auth_user_alpha["user"]

        # 1. Request registration options
        opt_res = client.post("/auth/passkey/register/options", headers=auth_user_alpha["headers"])
        assert opt_res.status_code == 200
        challenge_str = opt_res.json()["challenge"]

        # Mock WebAuthn registration verification
        mock_cred_id = b"mock-credential-id-12345"
        mock_pub_key = b"mock-public-key-bytes-67890"

        mock_reg_verification = MagicMock()
        mock_reg_verification.credential_id = mock_cred_id
        mock_reg_verification.credential_public_key = mock_pub_key
        mock_reg_verification.sign_count = 0

        # 2. Register credential
        reg_payload = {
            "credential": {
                "id": bytes_to_base64url(mock_cred_id),
                "rawId": bytes_to_base64url(mock_cred_id),
                "response": {"clientDataJSON": "{}", "attestationObject": "{}"},
                "type": "public-key",
            },
            "challenge": challenge_str,
            "nickname": "MacBook Touch ID",
        }

        with patch("backend.routers.auth.verify_registration", return_value=mock_reg_verification):
            verify_res = client.post(
                "/auth/passkey/register/verify",
                json=reg_payload,
                headers=auth_user_alpha["headers"],
            )
            assert verify_res.status_code == 200
            assert verify_res.json()["status"] == "success"

        # Verify credential persisted in DB
        cred_in_db = db_session.query(PasskeyCredential).filter(PasskeyCredential.user_id == user.id).first()
        assert cred_in_db is not None
        assert cred_in_db.nickname == "MacBook Touch ID"
        assert cred_in_db.credential_id == mock_cred_id

        # 3. Request Passkey Login Options
        login_opt_res = client.post("/auth/passkey/login/options", json={"email": user.email})
        assert login_opt_res.status_code == 200
        login_challenge_str = login_opt_res.json()["challenge"]

        # Mock WebAuthn authentication assertion verification
        mock_auth_verification = MagicMock()
        mock_auth_verification.new_sign_count = 1

        # 4. Verify Passkey Login Assertion
        login_verify_payload = {
            "credential": {
                "id": bytes_to_base64url(mock_cred_id),
                "rawId": bytes_to_base64url(mock_cred_id),
                "response": {"clientDataJSON": "{}", "authenticatorData": "{}", "signature": "{}"},
                "type": "public-key",
            },
            "challenge": login_challenge_str,
        }

        with patch("backend.routers.auth.verify_authentication", return_value=mock_auth_verification):
            login_res = client.post("/auth/passkey/login/verify", json=login_verify_payload)
            assert login_res.status_code == 200
            auth_data = login_res.json()
            assert "access_token" in auth_data
            assert auth_data["user"]["email"] == user.email
            assert auth_data["user"]["has_passkey"] is True

        # Verify sign_count updated
        db_session.refresh(cred_in_db)
        assert cred_in_db.sign_count == 1

        # 5. List registered passkeys
        list_res = client.get("/auth/passkey/credentials", headers=auth_user_alpha["headers"])
        assert list_res.status_code == 200
        assert len(list_res.json()) == 1
        assert list_res.json()[0]["nickname"] == "MacBook Touch ID"

        # 6. Delete registered passkey
        del_res = client.delete(f"/auth/passkey/credentials/{cred_in_db.id}", headers=auth_user_alpha["headers"])
        assert del_res.status_code == 200
        assert db_session.query(PasskeyCredential).count() == 0

    def test_passkey_login_unknown_credential_rejected(self, client: TestClient, db_session: Session):
        """Unrecognized passkey credential rejected with 404."""
        challenge_str = create_and_save_challenge(db=db_session, flow_type="authentication")

        payload = {
            "credential": {
                "id": bytes_to_base64url(b"unknown-credential-id"),
                "response": {},
            },
            "challenge": challenge_str,
        }
        res = client.post("/auth/passkey/login/verify", json=payload)
        assert res.status_code == 404


# =============================================================================
# 6. Payment Security with Authentication
# =============================================================================

class TestPaymentSecurityWithAuth:
    def test_payment_preview_and_execute_flow(
        self, client: TestClient, db_session: Session, auth_user_alpha: dict
    ):
        """Authenticated user previews and confirms payment."""
        user = auth_user_alpha["user"]

        # Preview payment
        preview_payload = {
            "amount": 2500.00,
            "recipient_name": "Grocery Store",
            "user_id": 999999,  # Malicious body user_id ignored
        }
        preview_res = client.post("/payments/preview", json=preview_payload, headers=auth_user_alpha["headers"])
        assert preview_res.status_code == 200
        preview_data = preview_res.json()

        assert preview_data["can_proceed"] is True
        assert Decimal(str(preview_data["amount"])) == Decimal("2500.00")
        pending_id = preview_data["pending_payment_id"]


        # Verify PendingPayment is bound strictly to User Alpha
        pending_in_db = db_session.query(PendingPayment).filter(PendingPayment.id == pending_id).first()
        assert pending_in_db.user_id == user.id
        assert pending_in_db.amount == Decimal("2500.00")

        # Execute payment
        exec_payload = {"pending_payment_id": pending_id}
        exec_res = client.post("/payments/execute", json=exec_payload, headers=auth_user_alpha["headers"])
        assert exec_res.status_code == 200
        exec_data = exec_res.json()

        assert exec_data["success"] is True
        assert exec_data["status"] == "executed"
        assert exec_data["new_balance"] == "47500.00"

        # Replay execution must be rejected (single-use)
        replay_res = client.post("/payments/execute", json=exec_payload, headers=auth_user_alpha["headers"])
        assert replay_res.status_code == 400
        assert "already been executed" in replay_res.json()["detail"].lower()

    def test_payment_execute_cross_user_forbidden(
        self, client: TestClient, db_session: Session, auth_user_alpha: dict, auth_user_beta: dict
    ):
        """User B cannot execute User A's staged pending payment."""
        user_a = auth_user_alpha["user"]

        # Stage payment for User A
        pending_a = PendingPayment(
            user_id=user_a.id,
            amount=Decimal("1000.00"),
            recipient_name="User A Payee",
            status="pending",
            expires_at=datetime.utcnow() + timedelta(minutes=15),
            created_at=datetime.utcnow(),
        )
        db_session.add(pending_a)
        db_session.commit()
        db_session.refresh(pending_a)

        # User B attempts to execute User A's payment
        exec_payload = {"pending_payment_id": pending_a.id}
        res = client.post("/payments/execute", json=exec_payload, headers=auth_user_beta["headers"])
        assert res.status_code == 403
        assert "unauthorized" in res.json()["detail"].lower()
