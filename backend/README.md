# Rolio API

FastAPI backend for Rolio. It exposes all application endpoints under `/api/*` and is deployed as a Vercel Python function from the recognized `api/index.py` entrypoint.

## Local development

```bash
cd backend
pip install -r requirements.txt
alembic upgrade head
uvicorn main:app --reload --port 8001
```

The backend intentionally does **not** create tables, seed data, or run Alembic migrations in production. Run `alembic upgrade head` as a deliberate release step against the target PostgreSQL database before deploying code that needs a new schema.

See the root [README](../README.md) and [deployment guide](../DEPLOYMENT.md) for environment variables, Vercel routing, and verification steps.
