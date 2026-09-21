"""
URL scheme validation — defense against stored XSS via hyperlink fields.

Fields that end up rendered as `href` in the frontend (job apply links,
application external URLs, profile links) must only ever contain safe
remote schemes. A stored value like `javascript:alert(document.domain)`
or `data:text/html,...` becomes an executable link the moment any user
views the record.

Validation lives SERVER-SIDE at input time: the backend rejects unsafe
schemes so no unsafe value is ever persisted. (Frontend escaping alone
can't help — an href renders its value verbatim.)
"""
from urllib.parse import urlparse

# Only schemes a job/application/profile link legitimately needs.
ALLOWED_URL_SCHEMES = {"http", "https"}

# Maximum length for any stored URL (applied alongside schema limits).
MAX_URL_LENGTH = 2000


def is_safe_url(url: str | None) -> bool:
    """True if `url` is a well-formed http(s) URL with no hostile components.

    Rejects:
      - javascript:, data:, vbscript:, file:, and every other scheme
      - scheme-relative URLs (//evil.com) — scheme cannot be verified
      - embedded credentials (user:pass@host) — phishing/SSRF-adjacent
      - whitespace/control characters anywhere (browser parsers differ;
        `java\\nscript:` evades naive checks but not this one)
    Empty/None is considered safe (field is optional).
    """
    if not url:
        return True
    if len(url) > MAX_URL_LENGTH:
        return False
    # Control characters (incl. newlines/tabs) can split schemes in some parsers
    if any(ord(c) < 0x20 or c == "\x7f" for c in url):
        return False
    try:
        parsed = urlparse(url.strip())
    except ValueError:
        return False
    # urlparse on "javascript:alert(1)" → scheme='javascript'
    if parsed.scheme.lower() not in ALLOWED_URL_SCHEMES:
        return False
    if not parsed.netloc:  # rejects scheme-less junk and "https:" with no host
        return False
    # userinfo (user:pass@) in URLs is a phishing indicator — reject
    if "@" in parsed.netloc:
        return False
    return True


def sanitize_url_or_none(url: str | None) -> str | None:
    """Return the URL if safe, else None. Convenience for endpoint layer."""
    return url if is_safe_url(url) else None
