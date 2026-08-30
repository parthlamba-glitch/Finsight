"""
Authentication Router for FinSight.

Provides:
- User registration (signup) with bcrypt password hashing
- Password authentication (login) with JWT session tokens
- FIDO2 / WebAuthn standard passkey registration and login
- Authenticated user profile retrieval (/auth/me)
- Passkey credential management

CRITICAL SECURITY & PRIVACY GUARANTEES:
1. Zero raw biometrics (fingerprints, face data) are stored, processed, or transmitted.
2. Cryptographic public keys and credential IDs are stored strictly for WebAuthn verification.
3. Passwords are never returned in responses, logged, or fed to AI systems.
"""

from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from decimal import Decimal
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from webauthn.helpers import base64url_to_bytes, bytes_to_base64url

from backend.db import get_db
from backend.models.user import User, DEFAULT_ACCESSIBILITY_PREFS
from backend.models.account import Account
from backend.models.passkey import PasskeyCredential
from backend.auth.security import (
    hash_password,
    verify_password,
    create_access_token,
    ACCESS_TOKEN_EXPIRE_MINUTES,
)
from backend.auth.dependencies import get_current_user
from backend.auth.webauthn_service import (
    get_registration_options,
    verify_registration,
    get_authentication_options,
    verify_authentication,
    verify_and_consume_challenge,
)
from backend.schemas import (
    UserSignupRequest,
    UserLoginRequest,
    UserResponse,
    TokenResponse,
    PasskeyRegisterVerifyRequest,
    PasskeyLoginOptionsRequest,
    PasskeyLoginVerifyRequest,
    PasskeyCredentialResponse,
)

router = APIRouter(prefix="/auth", tags=["Authentication"])


# =============================================================================
# 1. User Registration (Signup)
# =============================================================================

@router.post(
    "/signup",
    response_model=UserResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Register New User Account",
)
def signup(
    payload: UserSignupRequest,
    db: Session = Depends(get_db),
) -> UserResponse:
    """
    Registers a new user account with secure password hashing and default profile/account structure.
    Does NOT generate fake financial transactions.
    """
    # 1. Validate email uniqueness
    existing_user = db.query(User).filter(User.email == payload.email.strip().lower()).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="A user with this email address already exists.",
        )

    # 2. Hash password securely
    hashed_pw = hash_password(payload.password)

    # 3. Accessibility preferences initialization
    prefs = dict(DEFAULT_ACCESSIBILITY_PREFS)
    if payload.accessibility_prefs:
        prefs.update(payload.accessibility_prefs)

    # 4. Create User entity
    user = User(
        full_name=payload.name.strip(),
        email=payload.email.strip().lower(),
        hashed_password=hashed_pw,
        accessibility_prefs=prefs,
        is_active=True,
    )
    db.add(user)
    db.flush()

    # 5. Create default initial account (zero-balance, no fake transactions)
    account = Account(
        user_id=user.id,
        name="Primary Account",
        account_type="checking",
        balance=Decimal("0.00"),
        monthly_income=Decimal("0.00"),
        currency="INR",
        is_active=True,
    )
    db.add(account)
    db.commit()
    db.refresh(user)

    return UserResponse(
        id=user.id,
        full_name=user.full_name,
        email=user.email,
        accessibility_prefs=user.accessibility_prefs,
        is_active=user.is_active,
        has_passkey=False,
        created_at=user.created_at,
    )


# =============================================================================
# 2. Password Login
# =============================================================================

@router.post(
    "/login",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="User Password Login",
)
def login(
    payload: UserLoginRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """
    Authenticates a user via email and password, issuing a signed JWT access token.
    """
    user = db.query(User).filter(User.email == payload.email.strip().lower()).first()
    if not user or not verify_password(payload.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password.",
            headers={"WWW-Authenticate": "Bearer"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive. Please contact support.",
        )

    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email}
    )

    has_passkey = bool(
        db.query(PasskeyCredential).filter(PasskeyCredential.user_id == user.id).first()
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse(
            id=user.id,
            full_name=user.full_name,
            email=user.email,
            accessibility_prefs=user.accessibility_prefs,
            is_active=user.is_active,
            has_passkey=has_passkey,
            created_at=user.created_at,
        ),
    )


# =============================================================================
# 3. Authenticated User Profile (/auth/me)
# =============================================================================

@router.get(
    "/me",
    response_model=UserResponse,
    status_code=status.HTTP_200_OK,
    summary="Get Authenticated User Profile",
)
def get_me(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> UserResponse:
    """
    Returns the currently authenticated user's profile information.
    """
    has_passkey = bool(
        db.query(PasskeyCredential).filter(PasskeyCredential.user_id == current_user.id).first()
    )
    return UserResponse(
        id=current_user.id,
        full_name=current_user.full_name,
        email=current_user.email,
        accessibility_prefs=current_user.accessibility_prefs,
        is_active=current_user.is_active,
        has_passkey=has_passkey,
        created_at=current_user.created_at,
    )


# =============================================================================
# 4. Passkey (WebAuthn) Registration Flow
# =============================================================================

@router.post(
    "/passkey/register/options",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Generate Passkey Registration Options",
)
def passkey_register_options(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Generates WebAuthn registration options with challenge bound to current user.
    """
    existing_creds = (
        db.query(PasskeyCredential)
        .filter(PasskeyCredential.user_id == current_user.id)
        .all()
    )
    options = get_registration_options(
        user=current_user,
        existing_credentials=existing_creds,
        db=db,
    )
    return options


@router.post(
    "/passkey/register/verify",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Verify and Register Passkey Credential",
)
def passkey_register_verify(
    payload: PasskeyRegisterVerifyRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Verifies browser WebAuthn registration response and registers credential for authenticated user.
    """
    # 1. Validate and consume challenge
    is_valid_challenge = verify_and_consume_challenge(
        db=db,
        challenge_str=payload.challenge,
        flow_type="registration",
        user_id=current_user.id,
    )
    if not is_valid_challenge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Registration challenge is invalid, expired, or already used.",
        )

    # 2. Verify cryptographic registration response
    try:
        verification = verify_registration(
            credential_data=payload.credential,
            expected_challenge_str=payload.challenge,
            user=current_user,
            db=db,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Passkey registration verification failed: {str(e)}",
        )

    # 3. Store WebAuthn credential (public key only; zero biometrics stored)
    cred_id_bytes = verification.credential_id
    pub_key_bytes = verification.credential_public_key

    # Check for duplicate registration
    existing = db.query(PasskeyCredential).filter(PasskeyCredential.credential_id == cred_id_bytes).first()
    if existing:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This passkey credential is already registered.",
        )

    new_cred = PasskeyCredential(
        user_id=current_user.id,
        credential_id=cred_id_bytes,
        public_key=pub_key_bytes,
        sign_count=verification.sign_count,
        nickname=payload.nickname or "My Device Passkey",
        created_at=datetime.utcnow(),
    )
    db.add(new_cred)
    db.commit()
    db.refresh(new_cred)

    return {
        "status": "success",
        "message": "Device passkey registered successfully.",
        "credential_id": bytes_to_base64url(cred_id_bytes),
        "nickname": new_cred.nickname,
    }


# =============================================================================
# 5. Passkey (WebAuthn) Login Flow
# =============================================================================

@router.post(
    "/passkey/login/options",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Generate Passkey Login Options",
)
def passkey_login_options(
    payload: Optional[PasskeyLoginOptionsRequest] = None,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Generates WebAuthn authentication options with challenge for passkey sign-in.
    """
    credentials = None
    target_user_id = None

    if payload and payload.email:
        user = db.query(User).filter(User.email == payload.email.strip().lower()).first()
        if user:
            target_user_id = user.id
            credentials = (
                db.query(PasskeyCredential)
                .filter(PasskeyCredential.user_id == user.id)
                .all()
            )

    options = get_authentication_options(
        credentials=credentials,
        db=db,
        user_id=target_user_id,
    )
    return options


@router.post(
    "/passkey/login/verify",
    response_model=TokenResponse,
    status_code=status.HTTP_200_OK,
    summary="Verify Passkey and Authenticate User",
)
def passkey_login_verify(
    payload: PasskeyLoginVerifyRequest,
    db: Session = Depends(get_db),
) -> TokenResponse:
    """
    Verifies browser WebAuthn assertion signature and logs in the user with a JWT.
    """
    # 1. Validate and consume challenge
    is_valid_challenge = verify_and_consume_challenge(
        db=db,
        challenge_str=payload.challenge,
        flow_type="authentication",
    )
    if not is_valid_challenge:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Authentication challenge is invalid, expired, or already used.",
        )

    # 2. Extract credential ID
    cred_dict = payload.credential
    raw_id = cred_dict.get("id") or cred_dict.get("rawId")
    if not raw_id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Credential payload missing identifier.",
        )

    try:
        cred_id_bytes = base64url_to_bytes(raw_id)
    except Exception:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Invalid credential ID encoding.",
        )

    # 3. Retrieve registered passkey credential from DB
    stored_cred = (
        db.query(PasskeyCredential)
        .filter(PasskeyCredential.credential_id == cred_id_bytes)
        .first()
    )
    if not stored_cred:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Passkey credential not recognized for any registered user.",
        )

    # 4. Verify cryptographic signature assertion
    try:
        verification = verify_authentication(
            credential_data=payload.credential,
            expected_challenge_str=payload.challenge,
            stored_credential=stored_cred,
            db=db,
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Passkey assertion verification failed: {str(e)}",
        )

    # 5. Update sign counter and last used timestamp
    stored_cred.sign_count = verification.new_sign_count
    stored_cred.last_used_at = datetime.utcnow()
    db.commit()

    # 6. Issue authenticated session token for the identified user
    user = stored_cred.user
    if not user or not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Account is inactive or does not exist.",
        )

    access_token = create_access_token(
        data={"sub": str(user.id), "email": user.email}
    )

    return TokenResponse(
        access_token=access_token,
        token_type="bearer",
        expires_in=ACCESS_TOKEN_EXPIRE_MINUTES * 60,
        user=UserResponse(
            id=user.id,
            full_name=user.full_name,
            email=user.email,
            accessibility_prefs=user.accessibility_prefs,
            is_active=user.is_active,
            has_passkey=True,
            created_at=user.created_at,
        ),
    )


# =============================================================================
# 6. Passkey Credential Management
# =============================================================================

@router.get(
    "/passkey/credentials",
    response_model=List[PasskeyCredentialResponse],
    status_code=status.HTTP_200_OK,
    summary="List Registered Passkeys",
)
def list_passkeys(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> List[PasskeyCredentialResponse]:
    """
    Lists all registered passkey credentials belonging to the authenticated user.
    """
    creds = (
        db.query(PasskeyCredential)
        .filter(PasskeyCredential.user_id == current_user.id)
        .order_by(PasskeyCredential.created_at.desc())
        .all()
    )
    return [PasskeyCredentialResponse.model_validate(c) for c in creds]


@router.delete(
    "/passkey/credentials/{id}",
    response_model=Dict[str, Any],
    status_code=status.HTTP_200_OK,
    summary="Delete Registered Passkey",
)
def delete_passkey(
    id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Deletes a registered passkey credential belonging to the authenticated user.
    """
    cred = (
        db.query(PasskeyCredential)
        .filter(PasskeyCredential.id == id, PasskeyCredential.user_id == current_user.id)
        .first()
    )
    if not cred:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"Passkey credential with id {id} not found.",
        )

    db.delete(cred)
    db.commit()

    return {
        "status": "success",
        "message": "Passkey deleted successfully.",
        "id": id,
    }
