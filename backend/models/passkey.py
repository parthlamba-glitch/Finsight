"""
Passkey (WebAuthn) Credential and Challenge models for FinSight.

FIDO2 / WebAuthn standard compliant.
CRITICAL SECURITY GUARANTEE:
FinSight NEVER stores raw biometrics, fingerprint scans, or facial templates.
Only cryptographic public keys and credential IDs are stored.
Biometric verification is performed locally by the user's platform authenticator.
"""

from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, LargeBinary, ForeignKey, JSON
from sqlalchemy.orm import relationship

from backend.db import Base


class PasskeyCredential(Base):
    """
    Persisted WebAuthn public key credential registered to a user.
    """
    __tablename__ = "passkey_credentials"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    credential_id = Column(LargeBinary, unique=True, index=True, nullable=False)
    public_key = Column(LargeBinary, nullable=False)
    sign_count = Column(Integer, default=0, nullable=False)
    transports = Column(JSON, nullable=True)
    nickname = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    last_used_at = Column(DateTime, nullable=True)

    # Relationships
    user = relationship("User", back_populates="passkey_credentials")

    def __repr__(self) -> str:
        return f"<PasskeyCredential(id={self.id}, user_id={self.user_id}, nickname='{self.nickname}')>"


class AuthChallenge(Base):
    """
    Time-bound ephemeral challenge for WebAuthn registration or authentication flow.
    """
    __tablename__ = "auth_challenges"

    id = Column(Integer, primary_key=True, index=True, autoincrement=True)
    challenge = Column(String(255), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=True, index=True)
    flow_type = Column(String(50), nullable=False)  # "registration" or "authentication"
    expires_at = Column(DateTime, nullable=False)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)

    def is_expired(self, current_time: datetime = None) -> bool:
        now = current_time or datetime.utcnow()
        return now > self.expires_at

    def __repr__(self) -> str:
        return f"<AuthChallenge(id={self.id}, flow='{self.flow_type}', expired={self.is_expired()})>"
