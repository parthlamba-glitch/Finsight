"""
FinSight Authentication Package.

Provides password hashing, JWT token issuing/verification,
WebAuthn passkey management, and FastAPI current_user dependencies.
"""

from backend.auth.security import (
    hash_password,
    verify_password,
    create_access_token,
    decode_access_token,
)
from backend.auth.dependencies import get_current_user
from backend.auth.webauthn_service import (
    get_registration_options,
    verify_registration,
    get_authentication_options,
    verify_authentication,
    create_and_save_challenge,
    verify_and_consume_challenge,
)

__all__ = [
    "hash_password",
    "verify_password",
    "create_access_token",
    "decode_access_token",
    "get_current_user",
    "get_registration_options",
    "verify_registration",
    "get_authentication_options",
    "verify_authentication",
    "create_and_save_challenge",
    "verify_and_consume_challenge",
]
