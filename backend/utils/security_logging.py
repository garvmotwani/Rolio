"""
Structured security logging for audit trail and incident investigation.

Logs security-relevant events without exposing sensitive data.
"""
import logging
import json
from datetime import datetime

# Dedicated security logger
security_logger = logging.getLogger("rolio.security")
security_logger.setLevel(logging.INFO)

# Audit logger for compliance
audit_logger = logging.getLogger("rolio.audit")
audit_logger.setLevel(logging.INFO)


def log_auth_event(
    event_type: str,
    user_id: int = None,
    email: str = None,
    ip_address: str = None,
    success: bool = True,
    detail: str = "",
):
    """Log authentication events (login, logout, register, password change)."""
    entry = {
        "event": event_type,
        "timestamp": datetime.utcnow().isoformat(),
        "user_id": user_id,
        "email": _mask_email(email) if email else None,
        "ip": ip_address,
        "success": success,
        "detail": detail,
    }
    if success:
        security_logger.info(json.dumps(entry))
    else:
        security_logger.warning(json.dumps(entry))


def log_rate_limit_violation(
    endpoint: str,
    ip_address: str,
    limit: int,
    window: int,
):
    """Log rate limit violations."""
    entry = {
        "event": "rate_limit_exceeded",
        "timestamp": datetime.utcnow().isoformat(),
        "endpoint": endpoint,
        "ip": ip_address,
        "limit": limit,
        "window_seconds": window,
    }
    security_logger.warning(json.dumps(entry))


def log_unauthorized_access(
    endpoint: str,
    ip_address: str,
    detail: str = "",
):
    """Log unauthorized access attempts."""
    entry = {
        "event": "unauthorized_access",
        "timestamp": datetime.utcnow().isoformat(),
        "endpoint": endpoint,
        "ip": ip_address,
        "detail": detail,
    }
    security_logger.warning(json.dumps(entry))


def log_data_access(
    action: str,
    resource_type: str,
    resource_id: int,
    user_id: int,
    success: bool = True,
):
    """Log data access for audit trail."""
    entry = {
        "event": "data_access",
        "timestamp": datetime.utcnow().isoformat(),
        "action": action,
        "resource_type": resource_type,
        "resource_id": resource_id,
        "user_id": user_id,
        "success": success,
    }
    audit_logger.info(json.dumps(entry))


def log_upload_event(
    user_id: int,
    filename: str,
    file_size: int,
    success: bool = True,
    detail: str = "",
):
    """Log file upload events."""
    entry = {
        "event": "file_upload",
        "timestamp": datetime.utcnow().isoformat(),
        "user_id": user_id,
        "filename": filename,
        "file_size": file_size,
        "success": success,
        "detail": detail,
    }
    audit_logger.info(json.dumps(entry))


def log_api_error(
    endpoint: str,
    status_code: int,
    detail: str = "",
):
    """Log API errors (without sensitive data)."""
    entry = {
        "event": "api_error",
        "timestamp": datetime.utcnow().isoformat(),
        "endpoint": endpoint,
        "status_code": status_code,
        "detail": detail[:200],  # Truncate long messages
    }
    security_logger.info(json.dumps(entry))


def _mask_email(email: str) -> str:
    """Mask email for logging — show first char and domain."""
    if not email or "@" not in email:
        return "***"
    local, domain = email.split("@", 1)
    if len(local) <= 1:
        return f"*@{domain}"
    return f"{local[0]}***@{domain}"
