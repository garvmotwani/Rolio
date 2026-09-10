"""
OAuth state model — server-side persistent state for OAuth flows.

Security design:
- State is cryptographically random, stored in DB, tied to a user (for
  connect flows) or to a session identifier (for sign-in flows, where the
  user doesn't exist yet).
- One-time-use: consumed atomically on callback.
- Expires after 10 minutes.
- Resistant to replay — consumed states are deleted.
"""
from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Boolean, Index
from database.connection import Base


class OAuthState(Base):
    __tablename__ = "oauth_states"

    id = Column(Integer, primary_key=True, index=True)
    # Nullable: NULL for sign-in flows (no Rolio user yet), set for connect flows.
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    state_token = Column(String(64), nullable=False, unique=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    expires_at = Column(DateTime, nullable=False)
    is_consumed = Column(Boolean, default=False)
    # For sign-in states, a random session id ties the browser that started the
    # flow to the callback (prevents state fixation across browsers).
    session_id = Column(String(64), nullable=True, index=True)
    # "gmail" (connect flow) or "google_signin" (authentication flow)
    flow_type = Column(String(32), default="gmail")
    # PKCE code_verifier for the sign-in flow (RFC 7636). Server-side only —
    # never sent to the browser; only the S256 challenge goes to Google.
    code_verifier = Column(String(128), nullable=True)

    __table_args__ = (
        Index("idx_oauth_state_lookup", "state_token", "is_consumed"),
    )
