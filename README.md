# Rolio — AI-Powered Career Platform

Rolio is a full-stack portfolio project that turns a candidate profile or resume into explainable job matches, then helps them track applications in one place.

> **Demo note:** add a real dashboard screenshot or short walkthrough GIF here before publishing. Do not use production credentials or sensitive resumes in the public demo.

## What it demonstrates

- **Explainable matching** — weighted scores show how skills, experience, role, location, work type, and salary preferences affect a match.
- **Career workflow** — job search, saved jobs, a Kanban application pipeline, analytics, CSV export, resume parsing, and profile building.
- **Secure authentication** — HttpOnly cookie sessions, CSRF protection, rotating refresh tokens, server-side OAuth state, and rate limits.
- **Optional integrations** — Google sign-in, Gmail application-email sync, JSearch listings, and OpenAI-compatible AI assistance.

## Architecture

```text
Browser
  │ same-origin /api/* requests with first-party cookies
  ▼
Next.js 15 frontend (Vercel) ── rewrite ──► FastAPI backend (Vercel)
                                                 │
                                   PostgreSQL (production) / SQLite (local)
                                                 │
                                      Redis (optional rate-limit/cache store)
```

The browser talks to the frontend origin. Next.js proxies `/api/*` to the backend, keeping authentication cookies first-party on split-domain deployments.

## Tech stack

| Layer | Technology |
|---|---|
| Frontend | Next.js 15, React 19, TypeScript, Tailwind CSS, Framer Motion, Three.js, Zustand |
| Backend | Python 3.11+, FastAPI, SQLAlchemy, Alembic, Pydantic |
| Data | SQLite locally; PostgreSQL in production; optional Redis |
| Auth | HttpOnly cookies, JWT access/refresh rotation, CSRF double-submit, OAuth |
| AI / jobs | NVIDIA Nemotron-compatible API and JSearch (both optional) |

## Local setup

Prerequisites: Python 3.11+, Node.js 20+, and npm. API keys are optional for local development.

### Backend

macOS/Linux:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
alembic upgrade head
python seed.py
uvicorn main:app --reload --port 8001
```

Windows PowerShell:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
alembic upgrade head
python seed.py
uvicorn main:app --reload --port 8001
```

### Frontend

macOS/Linux:

```bash
cd frontend
npm install
cp .env.example .env.local
npm run dev
```

Windows PowerShell:

```powershell
cd frontend
npm install
Copy-Item .env.example .env.local
npm run dev
```

Open `http://localhost:3000`, register an account, and complete onboarding. API documentation is available locally at `http://localhost:8001/docs`.

## Environment variables

The app starts locally without third-party API keys. Set the following for production:

| Variable | Purpose |
|---|---|
| `DATABASE_URL` | PostgreSQL connection string |
| `ROLIO_ENV=production` | Enables production-only security behavior |
| `ROLIO_SECRET_KEY` / `CSRF_SECRET` | Required strong secrets for session and CSRF protection |
| `TOKEN_ENCRYPTION_KEY` | Fernet key required for encrypted Gmail tokens |
| `FRONTEND_ORIGINS`, `APP_PUBLIC_URL`, `BACKEND_PUBLIC_ORIGIN` | Public deployment origins |
| `BACKEND_ORIGIN` | Frontend-only server-side rewrite target |
| `REDIS_URL` | Recommended for shared rate limiting and cache storage |

See [DEPLOYMENT.md](DEPLOYMENT.md) for the verified deployment process and integration-specific variables.

## Verification

```bash
# Backend test suite
cd backend && python -m pytest tests/ -q

# Fresh migration sanity check
cd backend && DATABASE_URL="sqlite:///./verify.db" alembic upgrade head

# Frontend checks
cd frontend && npm run lint
cd frontend && npx tsc --noEmit
cd frontend && npm run build
```

The CI workflow runs backend tests with coverage, frontend linting/type-checking/build, and Docker image builds on `main`.

## Security notes

- Tokens are not returned in JSON, URLs, or localStorage; sessions use HttpOnly cookies.
- State-changing requests require CSRF validation.
- Refresh sessions rotate and reuse invalidates active sessions.
- OAuth states are one-time, time-limited, and stored server-side.
- Gmail tokens are Fernet-encrypted at rest.
- Uploads are type- and size-validated and rate limits protect sensitive endpoints.

## Known limitations

- This is a portfolio demo, not a production recruitment service.
- Use PostgreSQL and Redis for a multi-instance deployment; SQLite and in-memory limiting are local-development fallbacks.
- Vercel function filesystems are ephemeral. Resume uploads need object storage or another persistent volume for a real production deployment.
- AI, live job search, Gmail, and Google sign-in need their respective credentials and setup.

## Resume summary

> Built Rolio, an AI-powered career platform using Next.js, TypeScript, FastAPI, SQLAlchemy, and PostgreSQL. Implemented explainable job matching, application tracking, resume parsing, and secure cookie-based authentication with CSRF protection, rotating refresh sessions, and OAuth integrations.

## License

[MIT](LICENSE)
