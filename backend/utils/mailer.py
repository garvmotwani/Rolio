"""
Email sending — transactional mail for password resets.

Design:
- Uses the Resend HTTP API (free tier) when RESEND_API_KEY is configured.
- Without a key (local development / CI), the email is NOT sent: the reset
  link is logged server-side instead, so the flow remains fully testable.
- Never logs or returns anything sensitive beyond the reset URL itself in
  server-side logs (the URL contains a single-use token that expires in
  30 minutes; log access is required to read it).
"""
import logging

import httpx

from config import RESEND_API_KEY, EMAIL_FROM, APP_PUBLIC_URL

logger = logging.getLogger("rolio.mailer")

RESEND_API_URL = "https://api.resend.com/emails"
SEND_TIMEOUT_SECONDS = 10


def is_email_configured() -> bool:
    """True when real email delivery is available."""
    return bool(RESEND_API_KEY)


def _reset_email_html(name: str, reset_url: str) -> str:
    display_name = name or "there"
    return f"""
<html>
  <body style="margin:0;background:#0a0a0a;padding:40px 20px;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
    <div style="max-width:480px;margin:0 auto;background:#111;border:1px solid #222;border-radius:16px;padding:40px;">
      <p style="margin:0 0 24px;font-size:20px;font-weight:700;color:#fff;letter-spacing:-0.02em;">RO<span style="color:#555;">LIO</span></p>
      <h1 style="margin:0 0 12px;font-size:22px;color:#fff;letter-spacing:-0.02em;">Reset your password</h1>
      <p style="margin:0 0 28px;font-size:14px;line-height:1.6;color:#999;">Hi {display_name}, we received a request to reset your Rolio password. This link is valid for <strong style="color:#ccc;">30 minutes</strong> and can be used only once.</p>
      <a href="{reset_url}" style="display:inline-block;background:#fff;color:#000;text-decoration:none;font-size:14px;font-weight:600;padding:14px 32px;border-radius:999px;">Reset password</a>
      <p style="margin:28px 0 0;font-size:12px;line-height:1.6;color:#666;">If you didn't request this, you can safely ignore this email — your password won't change.</p>
    </div>
  </body>
</html>
"""


def send_password_reset_email(to_email: str, name: str, reset_url: str) -> bool:
    """
    Send the password reset email. Returns True when the email was actually
    delivered (Resend configured), False when falling back to dev logging.

    Never raises — delivery failures are logged and reported as False so the
    auth flow can respond generically without leaking provider errors.
    """
    if not RESEND_API_KEY:
        logger.info(
            "RESEND_API_KEY not configured — password reset link for %s: %s "
            "(dev fallback: the email was not sent)",
            to_email,
            f"{APP_PUBLIC_URL}/reset-password?token=..." if not reset_url else reset_url,
        )
        return False

    try:
        resp = httpx.post(
            RESEND_API_URL,
            headers={
                "Authorization": f"Bearer {RESEND_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "from": EMAIL_FROM,
                "to": [to_email],
                "subject": "Reset your Rolio password",
                "html": _reset_email_html(name, reset_url),
            },
            timeout=SEND_TIMEOUT_SECONDS,
        )
        if resp.status_code in (200, 201):
            return True
        # Log status only — never the API key or provider response body
        logger.warning("Resend send failed with status %s", resp.status_code)
        return False
    except Exception:
        logger.exception("Resend send raised an exception")
        return False
