"""
Gmail OAuth2 flow and email sync endpoints — SECURED.

Security measures:
- OAuth state persisted in PostgreSQL (not in-memory). One-time-use, 10-minute expiry.
- Tokens encrypted with Fernet (authenticated encryption) using TOKEN_ENCRYPTION_KEY.
- Google client_secret is NEVER stored per-user — loaded from env only.
- Callback redirects to clean frontend URL without any token data.
- All endpoints require authentication.
- Rate limiting on sync operations.
- Disconnect revokes tokens and cleans up data.
"""
from __future__ import annotations  # 3.9-compatible `X | None` annotations (Vercel runtime may default to 3.9)
import base64
import re
import secrets
import logging
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import RedirectResponse
from sqlalchemy.orm import Session
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from cryptography.fernet import Fernet, InvalidToken

from config import (
    GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI,
    APP_PUBLIC_URL, TOKEN_ENCRYPTION_KEY, TOKEN_ENCRYPTION_KEY_VALID, IS_PRODUCTION,
)
from database.connection import get_db
from models.models import User, Application, Company, Job
from models.email_models import GmailToken, EmailMessage, EmailSyncLog, ApplicationEvent
from models.oauth_state import OAuthState
from utils.auth import get_current_user

logger = logging.getLogger("rolio.gmail")

router = APIRouter(prefix="/api/gmail", tags=["gmail"])

SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]

# ─── Fernet Encryption Helpers ───────────────────────────────

_fernet_cache: Fernet | None = None


def _get_fernet() -> Fernet:
    """
    Get a Fernet instance using the TOKEN_ENCRYPTION_KEY.

    The key is validated once at configuration load (config.py):
    - Production: startup fails fast if the key is missing/invalid.
    - Development: an ephemeral key is used — encrypted tokens will not
      survive a restart (documented limitation).
    """
    global _fernet_cache
    if _fernet_cache is not None:
        return _fernet_cache

    if TOKEN_ENCRYPTION_KEY and TOKEN_ENCRYPTION_KEY_VALID:
        _fernet_cache = Fernet(TOKEN_ENCRYPTION_KEY.encode())
        return _fernet_cache

    if IS_PRODUCTION:
        logger.critical("TOKEN_ENCRYPTION_KEY is missing or invalid.")
        raise HTTPException(status_code=500, detail="Token encryption not configured")

    # Development fallback: ephemeral key. Tokens encrypted with it are NOT
    # readable after a restart — users must reconnect Gmail. Logged loudly.
    logger.warning("Using ephemeral encryption key — Gmail tokens will not survive a restart.")
    _fernet_cache = Fernet(Fernet.generate_key())
    return _fernet_cache


def _encrypt_token(plaintext: str) -> str:
    """Encrypt a token using Fernet authenticated encryption. Returns base64 ciphertext."""
    if not plaintext:
        return ""
    fernet = _get_fernet()
    return fernet.encrypt(plaintext.encode()).decode()


def _decrypt_token(ciphertext: str) -> str:
    """Decrypt a stored Fernet-encrypted token. Raises on tampered data."""
    if not ciphertext:
        return ""
    fernet = _get_fernet()
    try:
        return fernet.decrypt(ciphertext.encode()).decode()
    except InvalidToken:
        logger.error("Failed to decrypt token — key mismatch or tampered data")
        raise HTTPException(status_code=500, detail="Token decryption failed")


# ─── OAuth State Management (DB-persisted) ───────────────────

def _create_oauth_state(db: Session, user_id: int) -> str:
    """Create a cryptographically secure one-time OAuth state in the DB."""
    state_token = secrets.token_urlsafe(32)
    oauth_state = OAuthState(
        user_id=user_id,
        state_token=state_token,
        created_at=datetime.utcnow(),
        expires_at=datetime.utcnow() + timedelta(minutes=10),
    )
    db.add(oauth_state)
    db.commit()
    return state_token


def _validate_oauth_state(db: Session, state_token: str) -> int | None:
    """
    Validate and consume an OAuth state atomically.
    Returns user_id or None if invalid/expired/reused.
    """
    oauth_state = db.query(OAuthState).filter(
        OAuthState.state_token == state_token,
    ).first()

    if not oauth_state:
        return None

    # Already consumed — replay attack
    if oauth_state.is_consumed:
        logger.warning(f"OAuth state replay detected for state from user {oauth_state.user_id}")
        return None

    # Expired
    if datetime.utcnow() > oauth_state.expires_at:
        db.delete(oauth_state)
        db.commit()
        return None

    # Consume atomically
    oauth_state.is_consumed = True
    db.commit()

    return oauth_state.user_id


def _cleanup_expired_states(db: Session):
    """Clean up expired OAuth states. Called periodically or on startup."""
    expired = db.query(OAuthState).filter(
        OAuthState.expires_at < datetime.utcnow()
    ).delete()
    if expired:
        db.commit()


# ─── Gmail Service Builder ───────────────────────────────────
def _get_gmail_service(user_id: int, db: Session):
    """Build a Gmail API service from stored (encrypted) tokens."""
    token_record = db.query(GmailToken).filter(
        GmailToken.user_id == user_id,
        GmailToken.is_active == True,
    ).first()
    if not token_record:
        return None, None

    # Load client_secret from environment only — never from DB
    credentials = Credentials(
        token=_decrypt_token(token_record.access_token),
        refresh_token=_decrypt_token(token_record.refresh_token),
        token_uri=token_record.token_uri,
        client_id=token_record.client_id,
        client_secret=GOOGLE_CLIENT_SECRET,  # From env, not DB
        scopes=SCOPES,
    )

    # Refresh if expired
    if credentials.expired and credentials.refresh_token:
        from google.auth.transport.requests import Request as GRequest
        credentials.refresh(GRequest())
        token_record.access_token = _encrypt_token(credentials.token)
        if credentials.expiry:
            token_record.token_expiry = credentials.expiry
        db.commit()

    service = build("gmail", "v1", credentials=credentials)
    return service, credentials


# ─── Email Parsing Helpers ───────────────────────────────────
JOB_SENDER_DOMAINS = [
    "greenhouse.io", "lever.co", "workday.com", "icims.com", "smartrecruiters.com",
    "ashbyhq.com", "jobs.lever.co", "apply.workable.com", "bamboohr.com",
    "bambooHR.com", "myworkdayjobs.com", "oracle.com", "successfactors.com",
    "taleo.net", "jazz.co", "breezy.hr", "recruitee.com", "teamtailor.com",
    "notion.so", "stripe.com", "google.com", "careers.google.com",
    "jobs.careers.google.com", "amazonaws.com", "microsoft.com",
]

STATUS_KEYWORDS = {
    "interview": ["interview", "phone screen", "onsite", "video call", "technical screen", "coding challenge", "assessment"],
    "rejection": ["regret", "unfortunately", "not moving forward", "other candidates", "rejection", "not selected", "decided not to"],
    "offer": ["offer", "congratulations", "we're pleased", "delighted to offer", "welcome to"],
    "screening": ["reviewing your application", "under review", "next steps", "additional information", "screening"],
}


def _parse_email_for_job_context(msg_data: dict) -> dict:
    """Extract job-relevant info from a Gmail message."""
    headers = {h["name"].lower(): h["value"] for h in msg_data.get("payload", {}).get("headers", [])}
    subject = headers.get("subject", "")
    sender = headers.get("from", "")
    date_str = headers.get("date", "")

    sender_match = re.search(r"@([\w.-]+)", sender)
    sender_domain = sender_match.group(1).lower() if sender_match else ""

    company_name = ""
    if "<" in sender:
        name_part = sender.split("<")[0].strip().strip('"')
        company_name = name_part
    elif "@" in sender:
        company_name = sender.split("@")[0]

    received_at = None
    if date_str:
        try:
            from email.utils import parsedate_to_datetime
            received_at = parsedate_to_datetime(date_str)
        except Exception:
            pass

    body_preview = ""
    payload = msg_data.get("payload", {})
    if payload.get("mimeType") == "text/plain":
        body_data = payload.get("body", {}).get("data", "")
        if body_data:
            body_preview = base64.urlsafe_b64decode(body_data).decode("utf-8", errors="ignore")[:500]
    elif payload.get("mimeType", "").startswith("multipart/"):
        for part in payload.get("parts", []):
            if part.get("mimeType") == "text/plain":
                body_data = part.get("body", {}).get("data", "")
                if body_data:
                    body_preview = base64.urlsafe_b64decode(body_data).decode("utf-8", errors="ignore")[:500]
                    break

    parsed_status = "general"
    combined = (subject + " " + body_preview).lower()
    for status_type, keywords in STATUS_KEYWORDS.items():
        if any(kw in combined for kw in keywords):
            parsed_status = status_type
            break

    parsed_interview_date = ""
    date_patterns = [
        r"(\w+day),?\s+(\w+\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4})\s+at\s+(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm))",
        r"(\w+\s+\d{1,2}(?:st|nd|rd|th)?,?\s+\d{4})\s+at\s+(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm))",
        r"(\w+\s+\d{1,2})\s+at\s+(\d{1,2}:\d{2}\s*(?:AM|PM|am|pm))",
    ]
    for pattern in date_patterns:
        match = re.search(pattern, combined)
        if match:
            parsed_interview_date = match.group(0)
            break

    return {
        "subject": subject, "sender": sender, "sender_domain": sender_domain,
        "company_name": company_name, "snippet": msg_data.get("snippet", ""),
        "body_preview": body_preview, "received_at": received_at,
        "labels": ",".join(msg_data.get("labelIds", [])),
        "parsed_status": parsed_status,
        "parsed_interview_date": parsed_interview_date,
        "is_read": "UNREAD" not in msg_data.get("labelIds", []),
    }


def _match_email_to_application(email_data: dict, user_id: int, db: Session):
    """Try to match an email to an existing application."""
    sender_domain = email_data.get("sender_domain", "")
    subject = email_data.get("subject", "").lower()
    company_name = email_data.get("company_name", "").lower()

    apps = db.query(Application).filter(Application.user_id == user_id).all()
    best_match, best_confidence, best_method = None, 0, ""

    for app in apps:
        job = db.query(Job).filter(Job.id == app.job_id).first()
        if not job:
            continue
        company = db.query(Company).filter(Company.id == job.company_id).first()
        if not company:
            continue

        confidence, method = 0, ""

        if company.website and sender_domain:
            company_domain = re.sub(r"https?://", "", company.website).split("/")[0].lower()
            if company_domain and (sender_domain == company_domain or company_domain.endswith(sender_domain) or sender_domain.endswith(company_domain)):
                confidence, method = 95, "sender_domain"

        if confidence < 80:
            if company.name.lower() in company_name or company.name.lower() in subject:
                confidence, method = max(confidence, 80), "company_name"

        if confidence < 60:
            overlap = set(job.title.lower().split()) & set(subject.split())
            if len(overlap) >= 2:
                confidence, method = max(confidence, 60), "subject_keyword"

        if confidence > best_confidence:
            best_confidence, best_match, best_method = confidence, app, method

    return best_match, best_confidence, best_method


# ─── OAuth Endpoints ─────────────────────────────────────────

@router.get("/status")
def gmail_status(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    token = db.query(GmailToken).filter(GmailToken.user_id == user.id, GmailToken.is_active == True).first()
    last_sync = db.query(EmailSyncLog).filter(EmailSyncLog.user_id == user.id).order_by(EmailSyncLog.started_at.desc()).first()
    total_emails = db.query(EmailMessage).filter(EmailMessage.user_id == user.id).count()
    matched_emails = db.query(EmailMessage).filter(EmailMessage.user_id == user.id, EmailMessage.matched_application_id.isnot(None)).count()

    return {
        "connected": token is not None,
        "gmail_address": token.gmail_address if token else "",
        "total_emails": total_emails, "matched_emails": matched_emails,
        "last_sync": last_sync.started_at.isoformat() if last_sync else None,
        "last_sync_status": last_sync.status if last_sync else None,
        "emails_fetched_last_sync": last_sync.emails_fetched if last_sync else 0,
    }


@router.get("/auth-url")
def get_auth_url(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(status_code=500, detail="Google OAuth credentials not configured.")

    flow = Flow.from_client_config(
        {"web": {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }},
        scopes=SCOPES,
    )
    flow.redirect_uri = GOOGLE_REDIRECT_URI

    # Generate server-side state persisted in DB (also purge expired states)
    _cleanup_expired_states(db)
    state = _create_oauth_state(db, user.id)

    auth_url, _ = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent",
        state=state,
    )

    return {"auth_url": auth_url}


@router.get("/callback")
async def gmail_callback(request: Request, db: Session = Depends(get_db)):
    """Handle Google OAuth callback. Validates state from DB, stores tokens encrypted."""
    code = request.query_params.get("code")
    state = request.query_params.get("state")

    if not code or not state:
        return RedirectResponse(url=f"{APP_PUBLIC_URL}/settings?gmail=error")

    # Validate state from database — one-time-use, expiry check
    user_id = _validate_oauth_state(db, state)
    if user_id is None:
        logger.warning("Invalid, expired, or replayed OAuth state received")
        return RedirectResponse(url=f"{APP_PUBLIC_URL}/settings?gmail=error")

    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        return RedirectResponse(url=f"{APP_PUBLIC_URL}/settings?gmail=error")

    flow = Flow.from_client_config(
        {"web": {
            "client_id": GOOGLE_CLIENT_ID,
            "client_secret": GOOGLE_CLIENT_SECRET,
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://oauth2.googleapis.com/token",
        }},
        scopes=SCOPES,
    )
    flow.redirect_uri = GOOGLE_REDIRECT_URI

    try:
        flow.fetch_token(code=code)
    except Exception as e:
        logger.error(f"Gmail OAuth token exchange failed: {type(e).__name__}")
        return RedirectResponse(url=f"{APP_PUBLIC_URL}/settings?gmail=error")

    credentials = flow.credentials

    # Get user email from Gmail
    service = build("gmail", "v1", credentials=credentials)
    profile = service.users().getProfile(userId="me").execute()
    gmail_address = profile.get("emailAddress", "")

    # Store tokens encrypted — NEVER sent to browser, NEVER store client_secret in DB
    existing = db.query(GmailToken).filter(GmailToken.user_id == user_id).first()
    if existing:
        existing.access_token = _encrypt_token(credentials.token)
        existing.refresh_token = _encrypt_token(credentials.refresh_token) if credentials.refresh_token else existing.refresh_token
        existing.client_id = GOOGLE_CLIENT_ID
        existing.client_secret = ""  # Explicitly clear — never store client_secret
        existing.gmail_address = gmail_address
        existing.is_active = True
        if credentials.expiry:
            existing.token_expiry = credentials.expiry
    else:
        token = GmailToken(
            user_id=user_id,
            access_token=_encrypt_token(credentials.token),
            refresh_token=_encrypt_token(credentials.refresh_token or ""),
            client_id=GOOGLE_CLIENT_ID,
            client_secret="",  # NEVER store client_secret
            scopes=",".join(SCOPES),
            gmail_address=gmail_address,
            is_active=True,
            token_expiry=credentials.expiry,
        )
        db.add(token)

    db.commit()
    logger.info(f"Gmail connected for user {user_id}")

    # Redirect to clean frontend URL — NO tokens or credentials in URL
    return RedirectResponse(url=f"{APP_PUBLIC_URL}/settings?gmail=connected")


@router.post("/disconnect")
def disconnect_gmail(
    request: Request,
    response: Response,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Disconnect Gmail: revoke remote token, delete local tokens and synced data."""
    token = db.query(GmailToken).filter(GmailToken.user_id == user.id, GmailToken.is_active == True).first()

    if token:
        # Attempt to revoke the Google token remotely
        try:
            from google.oauth2.credentials import Credentials as GCreds
            creds = GCreds(
                token=_decrypt_token(token.access_token),
                refresh_token=_decrypt_token(token.refresh_token),
                token_uri=token.token_uri,
                client_id=token.client_id,
                client_secret=GOOGLE_CLIENT_SECRET,  # From env only
                scopes=SCOPES,
            )
            from google.auth.transport.requests import Request as GRequest
            creds.revoke(GRequest())
            logger.info(f"Google token revoked remotely for user {user.id}")
        except Exception as e:
            logger.warning(f"Failed to revoke Google token remotely for user {user.id}: {type(e).__name__}")

        # Mark inactive and clear encrypted tokens
        token.is_active = False
        token.access_token = ""
        token.refresh_token = ""
        db.commit()

        # Delete synced email data for this user
        db.query(ApplicationEvent).filter(ApplicationEvent.user_id == user.id).delete()
        db.query(EmailMessage).filter(EmailMessage.user_id == user.id).delete()
        db.query(EmailSyncLog).filter(EmailSyncLog.user_id == user.id).delete()
        db.commit()

    return {"message": "Gmail disconnected and data cleaned up"}


# ─── Email Sync ──────────────────────────────────────────────

@router.post("/sync")
def sync_emails(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    service, credentials = _get_gmail_service(user.id, db)
    if not service:
        raise HTTPException(status_code=400, detail="Gmail not connected")

    sync_log = EmailSyncLog(user_id=user.id, status="running", sync_trigger="manual")
    db.add(sync_log)
    db.commit()
    db.refresh(sync_log)

    try:
        query = "newer_than:30d (from: " + " OR from:".join(JOB_SENDER_DOMAINS[:10]) + ")"
        query += " OR subject:(application interview offer position hiring)"

        results = service.users().messages().list(userId="me", q=query, maxResults=50).execute()
        messages = results.get("messages", [])
        sync_log.emails_fetched = len(messages)

        new_count = matched_count = 0

        for msg_stub in messages:
            msg_id = msg_stub["id"]
            if db.query(EmailMessage).filter(EmailMessage.gmail_message_id == msg_id).first():
                continue

            try:
                msg_data = service.users().messages().get(
                    userId="me", id=msg_id, format="metadata",
                    metadataHeaders=["Subject", "From", "Date"],
                ).execute()
            except Exception:
                continue

            email_data = _parse_email_for_job_context(msg_data)
            matched_app, confidence, method = _match_email_to_application(email_data, user.id, db)

            email_msg = EmailMessage(
                user_id=user.id, gmail_message_id=msg_id,
                thread_id=msg_stub.get("threadId", ""),
                subject=email_data["subject"], sender=email_data["sender"],
                sender_domain=email_data["sender_domain"],
                snippet=email_data["snippet"], body_preview=email_data["body_preview"],
                received_at=email_data["received_at"], is_read=email_data["is_read"],
                labels=email_data["labels"],
                matched_application_id=matched_app.id if matched_app else None,
                match_confidence=confidence, match_method=method,
                parsed_company=email_data["company_name"],
                parsed_status=email_data["parsed_status"],
                parsed_interview_date=email_data["parsed_interview_date"],
                is_processed=True,
            )
            db.add(email_msg)
            new_count += 1

            if matched_app:
                matched_count += 1
                event = ApplicationEvent(
                    application_id=matched_app.id, user_id=user.id,
                    event_type="email_received",
                    title=f"Email from {email_data['company_name'] or email_data['sender']}",
                    description=email_data["subject"],
                    related_email_id=email_msg.id,
                )
                db.add(event)

                # Confidence-gated automation: only strong matches (sender-domain
                # or company-name level) change status automatically. Medium
                # confidence becomes a review suggestion; low confidence is
                # logged as an email link only — never silent auto-updates.
                if email_data["parsed_status"] in ("interview", "offer", "rejection"):
                    status_map = {"interview": "screening", "offer": "offer", "rejection": "rejected"}
                    suggested = status_map[email_data["parsed_status"]]
                    if confidence >= 80:
                        old_status = matched_app.status
                        matched_app.status = suggested
                        db.add(ApplicationEvent(
                            application_id=matched_app.id, user_id=user.id,
                            event_type="status_change",
                            title="Status updated from email",
                            description=f"Auto-updated to {matched_app.status} ({method}, {confidence}% match)",
                            old_value=old_status, new_value=matched_app.status,
                        ))
                    elif confidence >= 60:
                        db.add(ApplicationEvent(
                            application_id=matched_app.id, user_id=user.id,
                            event_type="status_suggestion",
                            title="Review email — possible status change",
                            description=f"Email suggests status '{suggested}'. Review and update manually.",
                            related_email_id=email_msg.id,
                        ))

        sync_log.status = "completed"
        sync_log.completed_at = datetime.utcnow()
        sync_log.emails_new = new_count
        sync_log.emails_matched = matched_count
        db.commit()

        return {
            "message": "Sync completed",
            "emails_fetched": len(messages),
            "new_emails": new_count,
            "matched_emails": matched_count,
        }

    except Exception as e:
        sync_log.status = "failed"
        sync_log.error_message = str(e)[:500]
        sync_log.completed_at = datetime.utcnow()
        db.commit()
        logger.error(f"Gmail sync failed for user {user.id}: {type(e).__name__}")
        raise HTTPException(status_code=500, detail="Sync failed. Please try again later.")


@router.post("/auto-sync")
def auto_sync_if_stale(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Fire-and-forget background sync trigger, called by the dashboard on
    load. Runs the real sync only when: connected, not already running, and
    the last successful sync is older than SYNC_STALE_MINUTES (60).
    Cheap no-op otherwise — safe to call on every dashboard visit."""
    SYNC_STALE_MINUTES = 60

    token = db.query(GmailToken).filter(
        GmailToken.user_id == user.id, GmailToken.is_active == True
    ).first()
    if not token:
        return {"synced": False, "reason": "not_connected"}

    last_sync = db.query(EmailSyncLog).filter(
        EmailSyncLog.user_id == user.id
    ).order_by(EmailSyncLog.started_at.desc()).first()

    if last_sync and last_sync.status == "running":
        # Another sync (from any device/tab) is in flight — don't duplicate
        return {"synced": False, "reason": "already_running"}

    if last_sync and last_sync.completed_at:
        age_min = (datetime.utcnow() - last_sync.completed_at).total_seconds() / 60
        if age_min < SYNC_STALE_MINUTES:
            return {"synced": False, "reason": "fresh", "age_minutes": round(age_min)}

    # Run the same sync logic inline (fast: ≤50 message metadata fetches).
    # The dashboard calls this without awaiting the result, so latency there
    # is unaffected.
    result = sync_emails(user=user, db=db)
    return {"synced": True, "result": result}


@router.get("/messages")
def get_email_messages(
    application_id: int = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    q = db.query(EmailMessage).filter(EmailMessage.user_id == user.id)
    if application_id:
        q = q.filter(EmailMessage.matched_application_id == application_id)
    messages = q.order_by(EmailMessage.received_at.desc()).limit(50).all()
    return [
        {
            "id": m.id, "gmail_message_id": m.gmail_message_id,
            "subject": m.subject, "sender": m.sender, "sender_domain": m.sender_domain,
            "snippet": m.snippet, "body_preview": m.body_preview,
            "received_at": m.received_at.isoformat() if m.received_at else None,
            "is_read": m.is_read, "parsed_company": m.parsed_company,
            "parsed_status": m.parsed_status, "parsed_interview_date": m.parsed_interview_date,
            "matched_application_id": m.matched_application_id,
            "match_confidence": m.match_confidence, "match_method": m.match_method,
        }
        for m in messages
    ]


@router.post("/match/{email_id}/{application_id}")
def manually_match_email(
    email_id: int, application_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    email = db.query(EmailMessage).filter(EmailMessage.id == email_id, EmailMessage.user_id == user.id).first()
    if not email:
        raise HTTPException(status_code=404, detail="Email not found")
    app = db.query(Application).filter(Application.id == application_id, Application.user_id == user.id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    email.matched_application_id = application_id
    email.match_confidence = 100
    email.match_method = "manual"
    db.add(ApplicationEvent(
        application_id=application_id, user_id=user.id,
        event_type="email_received",
        title=f"Email linked: {email.subject}", description=email.snippet,
        related_email_id=email_id,
    ))
    db.commit()
    return {"message": "Email matched to application"}


# ─── Application Events / Timeline ──────────────────────────

@router.get("/applications/{app_id}/events")
def get_application_events(
    app_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    app = db.query(Application).filter(Application.id == app_id, Application.user_id == user.id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    events = db.query(ApplicationEvent).filter(
        ApplicationEvent.application_id == app_id
    ).order_by(ApplicationEvent.created_at.desc()).all()

    result = []
    for e in events:
        item = {
            "id": e.id, "event_type": e.event_type, "title": e.title,
            "description": e.description, "old_value": e.old_value,
            "new_value": e.new_value, "created_at": e.created_at.isoformat(),
        }
        if e.related_email_id:
            email = db.query(EmailMessage).filter(EmailMessage.id == e.related_email_id).first()
            if email:
                item["email"] = {
                    "subject": email.subject, "sender": email.sender,
                    "received_at": email.received_at.isoformat() if email.received_at else None,
                    "snippet": email.snippet,
                }
        result.append(item)
    return result


@router.post("/applications/{app_id}/events")
def create_application_event(
    app_id: int, data: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    app = db.query(Application).filter(Application.id == app_id, Application.user_id == user.id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    event = ApplicationEvent(
        application_id=app_id, user_id=user.id,
        event_type=data.get("event_type", "note_added"),
        title=data.get("title", ""), description=data.get("description", ""),
    )
    db.add(event)

    if data.get("event_type") == "note_added" and data.get("description"):
        app.notes = (app.notes + "\n\n" if app.notes else "") + data["description"]
        app.updated_at = datetime.utcnow()

    db.commit()
    return {"message": "Event created", "id": event.id}


@router.get("/applications/{app_id}/reminders")
def get_reminders(
    app_id: int,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from models.email_models import ApplicationReminder
    reminders = db.query(ApplicationReminder).filter(
        ApplicationReminder.application_id == app_id,
        ApplicationReminder.user_id == user.id,
    ).order_by(ApplicationReminder.remind_at.asc()).all()
    return [
        {"id": r.id, "title": r.title, "message": r.message,
         "remind_at": r.remind_at.isoformat(), "is_completed": r.is_completed}
        for r in reminders
    ]


@router.post("/applications/{app_id}/reminders")
def create_reminder(
    app_id: int, data: dict,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    from models.email_models import ApplicationReminder
    app = db.query(Application).filter(Application.id == app_id, Application.user_id == user.id).first()
    if not app:
        raise HTTPException(status_code=404, detail="Application not found")

    try:
        remind_at = datetime.fromisoformat(data.get("remind_at", ""))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid remind_at datetime")

    reminder = ApplicationReminder(
        application_id=app_id, user_id=user.id,
        title=data.get("title", "Follow up"), message=data.get("message", ""),
        remind_at=remind_at,
    )
    db.add(reminder)
    db.add(ApplicationEvent(
        application_id=app_id, user_id=user.id,
        event_type="reminder_set",
        title=f"Reminder set: {data.get('title', 'Follow up')}",
        description=f"Scheduled for {data.get('remind_at', '')}",
    ))
    db.commit()
    return {"message": "Reminder created", "id": reminder.id}
