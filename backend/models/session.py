"""
Refresh session model — tracks active and revoked refresh tokens.

Security design:
- Stores a SHA-256 hash of the refresh token (never plaintext).
- Tracks creation, expiry, revocation, and rotation chain.
- Enables reuse detection: if a revoked token is reused, all sessions for
  that user are revoked (potential token theft).
"""
import hashlib
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Text, Index
from sqlalchemy.orm import relationship

from database.connection import Base


def hash_token(token: str) -> str:
    """SHA-256 hash of a refresh token. Never store plaintext tokens."""
    return hashlib.sha256(token.encode()).hexdigest()


class RefreshSession(Base):
    __tablename__ = "refresh_sessions"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    # SHA-256 hash of the refresh token — never store plaintext
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    # JTI from the JWT for correlation
    jti = Column(String(64), nullable=False, index=True)
    # Lifecycle
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    revoked_at = Column(DateTime, nullable=True)
    replaced_by_id = Column(Integer, ForeignKey("refresh_sessions.id"), nullable=True)
    # Metadata
    user_agent = Column(Text, default="")
    ip_address = Column(String(45), default="")
    is_reused = Column(Boolean, default=False)  # Set True if reuse detected (security event)

    user = relationship("User", backref="refresh_sessions")
    replaced_by = relationship("RefreshSession", remote_side=[id], backref="replaced_session")

    __table_args__ = (
        Index("idx_refresh_user_active", "user_id", "revoked_at"),
    )

    @property
    def is_active(self) -> bool:
        return self.revoked_at is None and self.expires_at > datetime.utcnow()

    @property
    def is_expired(self) -> bool:
        return self.expires_at <= datetime.utcnow()
