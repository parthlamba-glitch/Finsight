"""
WebAuthn and Passkey Service for FinSight.

FIDO2 / WebAuthn Level 3 Standard Compliant.

SECURITY ARCHITECTURE:
- Zero raw biometrics (fingerprints, face data, templates) are ever handled or stored.
- Biometric verification happens entirely on the user's platform authenticator (Windows Hello, Touch ID, Face ID, Android Biometrics).
- The FinSight backend stores only public keys and credential IDs.
- Challenges are single-use and time-bound.
"""

import os
import json
from datetime import datetime, timedelta
from typing import Optional, List, Dict, Any, Union
from sqlalchemy.orm import Session

import webauthn
from webauthn.helpers.structs import (
    PublicKeyCredentialDescriptor,
    UserVerificationRequirement,
    AuthenticatorSelectionCriteria,
    AuthenticatorAttachment,
    ResidentKeyRequirement,
    AttestationConveyancePreference,
)
from webauthn.helpers import base64url_to_bytes, bytes_to_base64url

from backend.models.user import User
from backend.models.passkey import PasskeyCredential, AuthChallenge

# Configuration
RP_ID = os.getenv("WEBAUTHN_RP_ID", "localhost")
RP_NAME = os.getenv("WEBAUTHN_RP_NAME", "FinSight Financial Copilot")
ORIGINS_RAW = os.getenv("WEBAUTHN_ORIGINS", "http://localhost:8000,http://127.0.0.1:8000,http://localhost:3000,http://localhost:5173")
EXPECTED_ORIGINS = [orig.strip() for orig in ORIGINS_RAW.split(",") if orig.strip()]


def create_and_save_challenge(
    db: Session,
    flow_type: str,
    user_id: Optional[int] = None,
    ttl_seconds: int = 300,
) -> str:
    """
    Generates a cryptographically secure WebAuthn challenge, persists it in the database
    with a TTL, and cleans up expired challenges.
    """
    # Clean up expired challenges
    now = datetime.utcnow()
    db.query(AuthChallenge).filter(AuthChallenge.expires_at < now).delete(synchronize_session=False)

    # Generate random challenge string
    challenge_bytes = os.urandom(32)
    challenge_str = bytes_to_base64url(challenge_bytes)

    auth_challenge = AuthChallenge(
        challenge=challenge_str,
        user_id=user_id,
        flow_type=flow_type,
        expires_at=now + timedelta(seconds=ttl_seconds),
        created_at=now,
    )
    db.add(auth_challenge)
    db.commit()
    db.refresh(auth_challenge)

    return challenge_str


def verify_and_consume_challenge(
    db: Session,
    challenge_str: str,
    flow_type: str,
    user_id: Optional[int] = None,
) -> bool:
    """
    Verifies that a challenge exists, is unexpired, matches the flow type,
    and consumes (deletes) it to prevent replay attacks.
    """
    if not challenge_str:
        return False

    query = db.query(AuthChallenge).filter(
        AuthChallenge.challenge == challenge_str,
        AuthChallenge.flow_type == flow_type,
    )
    if user_id is not None:
        query = query.filter(AuthChallenge.user_id == user_id)

    record = query.first()
    if not record or record.is_expired():
        if record:
            db.delete(record)
            db.commit()
        return False

    # Single-use: delete challenge
    db.delete(record)
    db.commit()
    return True


def get_registration_options(
    user: User,
    existing_credentials: List[PasskeyCredential],
    db: Session,
) -> Dict[str, Any]:
    """
    Generates WebAuthn PublicKeyCredentialCreationOptions for registering a new passkey.
    """
    exclude_credentials = []
    for cred in existing_credentials:
        exclude_credentials.append(
            PublicKeyCredentialDescriptor(id=cred.credential_id)
        )

    # User ID as bytes (stable hash or string bytes)
    user_id_bytes = str(user.id).encode("utf-8")

    # Generate and record challenge
    challenge_str = create_and_save_challenge(db=db, flow_type="registration", user_id=user.id)
    challenge_bytes = base64url_to_bytes(challenge_str)

    options = webauthn.generate_registration_options(
        rp_id=RP_ID,
        rp_name=RP_NAME,
        user_id=user_id_bytes,
        user_name=user.email,
        user_display_name=user.full_name,
        challenge=challenge_bytes,
        attestation=AttestationConveyancePreference.NONE,
        authenticator_selection=AuthenticatorSelectionCriteria(
            authenticator_attachment=None,  # Supports platform (Touch ID/Face ID/Windows Hello) & cross-platform keys
            resident_key=ResidentKeyRequirement.PREFERRED,
            user_verification=UserVerificationRequirement.PREFERRED,
        ),
        exclude_credentials=exclude_credentials if exclude_credentials else None,
    )

    return json.loads(webauthn.options_to_json(options))


def verify_registration(
    credential_data: Union[Dict[str, Any], str],
    expected_challenge_str: str,
    user: User,
    db: Session,
) -> Any:
    """
    Verifies client WebAuthn registration assertion against the stored challenge.
    """
    expected_challenge_bytes = base64url_to_bytes(expected_challenge_str)

    if isinstance(credential_data, dict):
        cred_payload = json.dumps(credential_data)
    else:
        cred_payload = credential_data

    verification = webauthn.verify_registration_response(
        credential=cred_payload,
        expected_challenge=expected_challenge_bytes,
        expected_rp_id=RP_ID,
        expected_origin=EXPECTED_ORIGINS,
        require_user_verification=False,
    )

    return verification


def get_authentication_options(
    credentials: Optional[List[PasskeyCredential]],
    db: Session,
    user_id: Optional[int] = None,
) -> Dict[str, Any]:
    """
    Generates WebAuthn PublicKeyCredentialRequestOptions for signing in with a passkey.
    """
    allow_credentials = []
    if credentials:
        for cred in credentials:
            allow_credentials.append(
                PublicKeyCredentialDescriptor(id=cred.credential_id)
            )

    challenge_str = create_and_save_challenge(db=db, flow_type="authentication", user_id=user_id)
    challenge_bytes = base64url_to_bytes(challenge_str)

    options = webauthn.generate_authentication_options(
        rp_id=RP_ID,
        challenge=challenge_bytes,
        allow_credentials=allow_credentials if allow_credentials else None,
        user_verification=UserVerificationRequirement.PREFERRED,
    )

    return json.loads(webauthn.options_to_json(options))


def verify_authentication(
    credential_data: Union[Dict[str, Any], str],
    expected_challenge_str: str,
    stored_credential: PasskeyCredential,
    db: Session,
) -> Any:
    """
    Verifies client WebAuthn authentication assertion against stored public key and challenge.
    """
    expected_challenge_bytes = base64url_to_bytes(expected_challenge_str)

    if isinstance(credential_data, dict):
        cred_payload = json.dumps(credential_data)
    else:
        cred_payload = credential_data

    verification = webauthn.verify_authentication_response(
        credential=cred_payload,
        expected_challenge=expected_challenge_bytes,
        expected_rp_id=RP_ID,
        expected_origin=EXPECTED_ORIGINS,
        credential_public_key=stored_credential.public_key,
        credential_current_sign_count=stored_credential.sign_count,
        require_user_verification=False,
    )

    return verification
