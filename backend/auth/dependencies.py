"""
FastAPI Authentication Dependencies for FinSight.

Enforces strict user identity verification.
CRITICAL ARCHITECTURAL GUARANTEE:
- In production, all protected endpoints strictly require a valid JWT Bearer token.
- The authenticated current_user.id is authoritative.
- Client-supplied user_id parameters cannot override or spoof the authenticated identity.
"""

import os
from typing import Optional
from fastapi import Depends, HTTPException, status, Header, Query, Request
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from sqlalchemy.orm import Session

from backend.db import get_db
from backend.models.user import User
from backend.auth.security import decode_access_token

security_scheme = HTTPBearer(auto_error=False)

def is_demo_unauthenticated_allowed() -> bool:
    """
    Checks if unauthenticated demo/test mode is explicitly enabled via environment variable.
    Defaults to False in production.
    """
    return os.getenv("FINSIGHT_ALLOW_DEMO_UNAUTHENTICATED", "false").lower() in ("true", "1", "yes")


async def get_current_user(
    request: Request,
    credentials: Optional[HTTPAuthorizationCredentials] = Depends(security_scheme),
    db: Session = Depends(get_db),
) -> User:
    """
    Standard production authentication dependency.
    Resolves authenticated User from the Authorization Bearer JWT.

    Security Guarantees:
    - When a valid JWT Bearer token is present, current_user is authoritative.
    - Client-supplied user_id in the body or query CANNOT override or spoof identity.
    - In production (FINSIGHT_ALLOW_DEMO_UNAUTHENTICATED=false), missing tokens always raise 401.
    """
    # 1. Check for Bearer token in Authorization header
    if credentials and credentials.credentials:
        token = credentials.credentials
        payload = decode_access_token(token)
        if not payload:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired authentication token.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user_id_str = payload.get("sub")
        if not user_id_str:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token missing subject identifier.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        try:
            user_id = int(user_id_str)
        except (ValueError, TypeError):
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Malformed user identifier in token.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        user = db.query(User).filter(User.id == user_id, User.is_active == True).first()
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User associated with token does not exist or is inactive.",
                headers={"WWW-Authenticate": "Bearer"},
            )

        return user

    # 2. Explicit Isolated Legacy / Demo Compatibility Mode
    # ONLY active when FINSIGHT_ALLOW_DEMO_UNAUTHENTICATED is explicitly set to true.
    if is_demo_unauthenticated_allowed():
        demo_id = None

        # Check X-Demo-User-Id header
        demo_header = request.headers.get("X-Demo-User-Id")
        if demo_header:
            try:
                demo_id = int(demo_header)
            except ValueError:
                pass

        # Check query parameters
        if demo_id is None:
            demo_param = request.query_params.get("user_id")
            if demo_param:
                try:
                    demo_id = int(demo_param)
                except ValueError:
                    pass

        # Check JSON request body for legacy pre-auth test payloads
        if demo_id is None and request.method in ("POST", "PUT", "PATCH"):
            try:
                body_bytes = await request.body()
                if body_bytes:
                    import json
                    body_json = json.loads(body_bytes)
                    if isinstance(body_json, dict) and "user_id" in body_json and body_json["user_id"] is not None:
                        demo_id = int(body_json["user_id"])
            except Exception:
                pass

        if demo_id is not None:
            user = db.query(User).filter(User.id == demo_id).first()
            if not user:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"User with id {demo_id} not found.",
                )
            if not user.is_active:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="Account is inactive.",
                )
            return user

        # Single user fallback for demo/test sandbox
        all_users = db.query(User).all()
        if len(all_users) == 1:
            return all_users[0]
        elif len(all_users) == 0:
            # Ephemeral placeholder user for unauthenticated unit tests with empty test database
            return User(id=1, full_name="Test Demo User", email="test.demo@example.com", accessibility_prefs={})


    # 3. Production Default: Strict 401 Unauthorized
    raise HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Authentication required. Please provide a valid Bearer token in the Authorization header.",
        headers={"WWW-Authenticate": "Bearer"},
    )

