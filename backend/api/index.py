"""
Vercel serverless entrypoint.

Vercel's Python runtime detects the FastAPI ASGI app in `app` and serves it
per-request (no uvicorn needed). Routing note: incoming paths keep their
ORIGINAL path in the ASGI scope, so /api/health still hits /api/health even
though vercel.json rewrites everything into this function.

The backend package root (the parent of api/) must be importable, hence the
sys.path insert — main.py, routes/, services/ etc. live there.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Serverless functions may land on a read-only FS; keep resume uploads in /tmp.
os.environ.setdefault("UPLOAD_DIR", "/tmp/rolio-uploads")

from main import app  # noqa: E402

handler = app  # Vercel ASGI adapter picks this up
