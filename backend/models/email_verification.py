"""
Email verification token model.

Security design:
- Stores a SHA-256 hash of the verification token (never plaintext) — same
  pattern as refresh sessions and password reset tokens.
- Tokens are single-use (used_at) and expire after 24 hours (a friendly
  window for verification emails, unlike the 30-minute reset window).
- Requesting a new verification email invalidates all previously issued
  tokens for the user (only the newest link works).
- Google sign-in users never get tokens — their email is verified by Google.
"""
import hashlib
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Index
from sqlalchemy.orm import relationship

from database.connection import Base


def hash_verification_token(token: str) -> str:
    """SHA-256 hash of an email verification token. Never store plaintext."""
    return hashlib.sha256(token.encode()).hexdigest()


class EmailVerificationToken(Base):
    __tablename__ = "email_verification_tokens"

    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    # SHA-256 hash of the verification token — never store plaintext
    token_hash = Column(String(64), nullable=False, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    # Set when the token is consumed — tokens are single-use
    used_at = Column(DateTime, nullable=True)

    user = relationship("User", backref="email_verification_tokens")

    __table_args__ = (
        Index("idx_emailverify_user_active", "user_id", "used_at"),
    )

    @property
    def is_expired(self) -> bool:
        return self.expires_at <= datetime.utcnow()

    @property
    def is_used(self) -> bool:
        return self.used_at is not None
