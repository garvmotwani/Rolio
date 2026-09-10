"""
Shared client-IP extraction for rate limiting and security logging.

Security design (audit fix L1):
- X-Forwarded-For is honoured ONLY when the direct peer is a trusted proxy
  (TRUSTED_PROXIES from config). When no proxies are configured, the header
  is ignored entirely — a direct client cannot spoof a fresh rate-limit
  bucket by sending a fake X-Forwarded-For.
- Falls back to the socket peer address, which is always unspoofable.
"""
from fastapi import Request

from config import TRUSTED_PROXIES


def _ip_in_trusted(peer: str) -> bool:
    """True when the direct connection peer is a configured trusted proxy.

    Supports exact IPs and simple wildcard suffixes (e.g. "172.18.*." style
    entries are NOT supported — keep the config to exact IPs or "*").
    """
    if not TRUSTED_PROXIES:
        return False
    if "*" in TRUSTED_PROXIES:
        return True
    return peer in TRUSTED_PROXIES


def get_client_ip(request: Request) -> str:
    """
    Best-effort client IP for rate limiting.

    - Direct peer when not behind a trusted proxy (unspoofable).
    - First X-Forwarded-For hop when the peer IS a trusted proxy (the
      proxy appends the real client address; anything before it in the
      chain is untrusted, so we take only the last appended value).
    """
    peer = request.client.host if request.client else "unknown"

    if not _ip_in_trusted(peer):
        return peer

    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        # Right-most value is the one our trusted proxy appended.
        chain = [hop.strip() for hop in forwarded.split(",") if hop.strip()]
        if chain:
            return chain[-1][:45]
    return peer
