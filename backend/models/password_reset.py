"""
Password reset token model.

Security design:
- Stores a SHA-256 hash of the reset token (never plaintext) — same pattern
  as refresh sessions.
- Tokens are single-use (used_at) and expire after 30 minutes.
- Requesting a new reset invalidates all previously issued tokens for the
  user (only the newest link works).
- Completing a reset revokes every active login session.
"""
import hashlib
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship

from database.connection import Base


def hash_reset_token(token: str) -> str:
    """SHA-256 hash of a password reset token. Never store plaintext."""
    return hashlib.sha256(token.encode()).hexdigest()


class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    # SHA-256 hash of the reset token — never store plaintext
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    # Set when the token is consumed — tokens are single-use
    used_at = Column(DateTime, nullable=True)
    # Best-effort audit info
    request_ip = Column(String(45), default="")

    user = relationship("User", backref="password_reset_tokens")

    __table_args__ = (
        Index("idx_pwdreset_user_active", "user_id", "used_at"),
    )

    @property
    def is_expired(self) -> bool:
        return self.expires_at <= datetime.utcnow()

    @property
    def is_used(self) -> bool:
        return self.used_at is not None
