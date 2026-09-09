from sqlalchemy import Column, Integer, String, Float, Boolean, DateTime, ForeignKey, Text, Index
from sqlalchemy.orm import relationship
from datetime import datetime

from database.connection import Base


class GmailToken(Base):
    """Stores encrypted OAuth2 tokens for Gmail access per user.
    
    Tokens are encrypted at rest using TOKEN_ENCRYPTION_KEY.
    The Google client_secret is NOT stored per-user — it's in env config only.
    """
    __tablename__ = "gmail_tokens"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False, index=True)
    # Tokens stored encrypted — decrypted only when building Gmail API client
    access_token = Column(Text, nullable=False)
    refresh_token = Column(Text, nullable=False)
    token_uri = Column(String, default="https://oauth2.googleapis.com/token")
    client_id = Column(String, nullable=False)
    # DEPRECATED: client_secret is NEVER stored — loaded from GOOGLE_CLIENT_SECRET env var only.
    # This column exists only for backward compatibility. Always empty for new records.
    client_secret = Column(Text, default="", nullable=True)
    scopes = Column(Text, default="https://www.googleapis.com/auth/gmail.readonly")
    token_expiry = Column(DateTime, nullable=True)
    gmail_address = Column(String, default="")
    is_active = Column(Boolean, default=True, index=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    user = relationship("User", backref="gmail_token")


class EmailMessage(Base):
    """Stores synced Gmail messages relevant to job applications."""
    __tablename__ = "email_messages"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    gmail_message_id = Column(String, unique=True, nullable=False, index=True)
    thread_id = Column(String, default="")
    subject = Column(Text, default="")
    sender = Column(String, default="")
    sender_domain = Column(String, default="", index=True)
    snippet = Column(Text, default="")
    body_preview = Column(Text, default="")
    received_at = Column(DateTime, nullable=True, index=True)
    is_read = Column(Boolean, default=False)
    labels = Column(Text, default="")
    # Matching
    matched_application_id = Column(Integer, ForeignKey("applications.id"), nullable=True, index=True)
    match_confidence = Column(Float, default=0.0)
    match_method = Column(String, default="")
    # Parsed data
    parsed_company = Column(String, default="")
    parsed_status = Column(String, default="")
    parsed_interview_date = Column(String, default="")
    parsed_next_step = Column(String, default="")
    # Sync tracking
    synced_at = Column(DateTime, default=datetime.utcnow)
    is_processed = Column(Boolean, default=False)

    user = relationship("User", backref="email_messages")
    matched_application = relationship("Application", backref="matched_emails")

    __table_args__ = (
        Index("idx_email_user_received", "user_id", "received_at"),
    )


class EmailSyncLog(Base):
    """Tracks each sync run for debugging and status display."""
    __tablename__ = "email_sync_logs"
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    started_at = Column(DateTime, default=datetime.utcnow)
    completed_at = Column(DateTime, nullable=True)
    status = Column(String, default="running")
    emails_fetched = Column(Integer, default=0)
    emails_matched = Column(Integer, default=0)
    emails_new = Column(Integer, default=0)
    error_message = Column(Text, default="")
    sync_trigger = Column(String, default="manual")

    user = relationship("User", backref="sync_logs")


class ApplicationEvent(Base):
    """Timeline events for each application."""
    __tablename__ = "application_events"
    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    event_type = Column(String, nullable=False)
    title = Column(String, default="")
    description = Column(Text, default="")
    old_value = Column(String, default="")
    new_value = Column(String, default="")
    related_email_id = Column(Integer, ForeignKey("email_messages.id"), nullable=True)
    metadata_json = Column(Text, default="")
    created_at = Column(DateTime, default=datetime.utcnow)

    application = relationship("Application", backref="events")
    user = relationship("User")
    related_email = relationship("EmailMessage")

    __table_args__ = (
        Index("idx_event_app_created", "application_id", "created_at"),
    )


class ApplicationReminder(Base):
    """Follow-up reminders for applications."""
    __tablename__ = "application_reminders"
    id = Column(Integer, primary_key=True, index=True)
    application_id = Column(Integer, ForeignKey("applications.id"), nullable=False, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    title = Column(String, default="Follow up")
    message = Column(Text, default="")
    remind_at = Column(DateTime, nullable=False, index=True)
    is_completed = Column(Boolean, default=False)
    is_sent = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.utcnow)

    application = relationship("Application", backref="reminders")
    user = relationship("User")
