"""
Vercel serverless entrypoint.

Vercel's Python runtime detects the FastAPI ASGI app in `app` and serves it
per-request (no uvicorn needed). Routing note: incoming paths keep their
ORIGINAL path in the ASGI scope, so /api/health still hits /api/health even
though vercel.json rewrites everything into this function.

The backend package root (the parent of api/) must be importable, hence the
sys.path insert — main.py, routes/, services/ etc. live there.

Boot failures must never be silent: a bare crash surfaces to the user only as
FUNCTION_INVOCATION_FAILED. Wrapping the import lets the function log the full
traceback (visible in Vercel's Runtime Logs) and return a diagnostic body so
the root cause is immediately obvious instead of an opaque 500.
"""
import os
import sys
import traceback

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Serverless functions may land on a read-only FS; keep resume uploads in /tmp.
os.environ.setdefault("UPLOAD_DIR", "/tmp/rolio-uploads")

try:
    from main import app  # noqa: E402
except Exception:
    # Log the real traceback (shows up in Vercel → Logs) and return a short
    # diagnostic so an owner hitting the URL sees WHY boot failed. Never
    # include env values here — only the exception type and message.
    traceback.print_exc()
    _err = traceback.format_exc(limit=-3).strip()

    from fastapi import FastAPI  # noqa: E402

    _boot = FastAPI()

    @_boot.api_route("/{path:path}", methods=["GET", "POST", "PUT", "DELETE", "PATCH"])
    async def _boot_failure(path: str):
        return {
            "error": "Backend failed to start — check Vercel Runtime Logs for the full traceback.",
            "exception": _err.splitlines()[-1] if _err else "unknown",
        }

    app = _boot

handler = app  # Vercel ASGI adapter picks this up
