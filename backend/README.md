# Rolio API (FastAPI)

Backend for the Rolio career platform. Deployed on **Vercel** as a Python
serverless function (`api/index.py` boots the whole FastAPI app; `vercel.json`
routes `/api/*` to it) with PostgreSQL on Neon.

The frontend (also Vercel) proxies all `/api/*` requests here server-side, so
the backend URL never needs to be public-facing and auth cookies stay
first-party.

- Health: `/api/health`
- Migrations run automatically on cold start; schema is managed by Alembic.
- Configuration: environment variables — see `DEPLOYMENT.md` in the repo root
  for the full checklist.
