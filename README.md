# Rolio — AI-Powered Career Platform

A full-stack AI career platform: discover relevant jobs, understand why they match, manage applications, and improve your chances of getting hired.

> Add a dashboard or landing-page screenshot before publishing the repository;
> the project intentionally ships without a broken placeholder image.

## Features

- **Google sign-in** — one-click registration/login; profile details can be filled in later
- **AI job matching** — match scores with per-factor breakdown (skills, experience, role, location, work type, salary) for every job
- **Real-time job search** — live listings from Google for Jobs via the JSearch API, merged with a local job database
- **Application tracking** — kanban board across pipeline stages, with status history and application events
- **AI career assistant** — streaming chat with per-user quotas
- **Cover letter generator** — AI-written, streaming token-by-token
- **Interview prep** — AI-generated flashcards per job (behavioral, technical, system design)
- **Resume parsing** — upload PDF/DOCX, extract skills/experience, build the matching profile
- **Resume builder** — AI-assisted resume generation
- **Gmail integration** — OAuth sync of job-related emails, auto-matched to applications with status updates
- **Application analytics** — status distribution, weekly application trends, match-score buckets
- **Search history & saved searches** — re-run past searches with one click
- **CSV export** — applications and saved jobs

## Architecture

```
┌─────────────────────┐         ┌──────────────────────────┐
│  Next.js 14 (SPA)   │  HTTP   │  FastAPI backend         │
│  - App Router       │──────►  │  - REST API (/api/*)     │
│  - Zustand store    │ cookies │  - Cookie sessions       │
│  - Framer Motion    │  + CSRF │  - Rate limiting         │
│  - 3D (Three.js)    │         │  - Alembic migrations    │
└─────────────────────┘         └────────┬─────────┬───────┘
                                         │         │
                              ┌──────────▼──┐  ┌───▼──────────────┐
                              │ SQLite dev  │  │ External APIs     │
                              │ Postgres/   │  │ - JSearch (paid)  │
                              │ Supabase    │  │ - NVIDIA Nemotron │
                              └─────────────┘  │ - Gmail OAuth     │
                                               └──────────────────┘
```

**Monorepo layout**

```
backend/          FastAPI application
  alembic/        Database migrations
  models/         SQLAlchemy models
  routes/         API endpoints (auth, jobs, ai, gmail, ...)
  services/       Business logic (matching, JSearch, AI provider)
  tests/          Pytest suite (76 tests)
frontend/         Next.js 14 application
  src/app/        Pages (App Router)
  src/components/ UI components
  src/lib/        API client, auth store
```

## Tech Stack

| Layer | Technologies |
|---|---|
| Frontend | Next.js 15, React 19, TypeScript, Tailwind CSS, Framer Motion, Three.js (react-three-fiber v9), Zustand |
| Backend | Python 3.11+, FastAPI, SQLAlchemy 2, Alembic, Pydantic v2 |
| Auth | HttpOnly cookie sessions, JWT access + rotating refresh tokens, CSRF double-submit |
| Database | SQLite (local dev) / PostgreSQL (Supabase ready) |
| AI | NVIDIA Nemotron (OpenAI-compatible API) |
| Job data | JSearch via RapidAPI + seeded local database |

## How It Works

**Authentication** — access + refresh JWTs are issued as HttpOnly cookies; JavaScript never sees a token. Refresh tokens rotate on every use, are persisted as hashes, and reuse of a revoked token kills all sessions. State-changing requests require a CSRF header (double-submit cookie, constant-time compare).

**Resume parsing** — upload a PDF/DOCX (validated by magic bytes, size-capped, stored outside static paths); text is extracted, skills/experience parsed into your profile, which drives matching.

**Job matching** — every job is scored 0–100 from weighted factors (skills 30%, experience 20%, role 20%, location 10%, work type 10%, salary 10%). The dashboard explains each factor so you can see *why* a job matches.

**AI integration** — the backend proxies an OpenAI-compatible endpoint (Nemotron). Prompts are size-capped and rate-limited per user; responses stream as NDJSON; structured outputs are validated before use. Without an API key, features return graceful fallbacks.

**Gmail integration** — standard server-side OAuth: a cryptographically random one-time `state` is persisted in the DB (10-minute expiry), the callback validates and consumes it, tokens are stored Fernet-encrypted, and the browser is redirected to a clean URL with no token data. Synced emails are classified (interview / offer / rejection) and matched to applications.

**Google sign-in** — same server-side OAuth infrastructure: the ID token is verified against Google's public keys (signature, audience, issuer, expiry), the state is session-bound to the initiating browser, and accounts are linked by verified email. New users get a password-less account and land on onboarding; existing users sign in with one click. Sessions are identical to password login (HttpOnly cookies + rotating refresh).

**External job search** — JSearch requests are cached (in-memory; 24h in Redis when available), input-bounded, and rate-limited per-user (authenticated) or per-IP (anonymous, tight quota). Without an API key the app clearly reports external search as unavailable and falls back to local seeded jobs.

## Local Setup

### Prerequisites

- Python 3.11+
- Node.js 18+
- No API keys required to boot — the app runs fully without them.

### 1. Backend

```bash
cd backend
python -m venv .venv && source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt

cp .env.example .env        # defaults work for local dev

# Create the schema
alembic upgrade head

# (Optional) seed demo jobs so search has data without a JSearch key
python seed.py              # see seed script section below

uvicorn main:app --reload --port 8001
```

API docs: http://localhost:8001/docs

### 2. Frontend

```bash
cd frontend
npm install

cp .env.example .env.local   # NEXT_PUBLIC_API_URL=http://localhost:8001

npm run dev
```

Open http://localhost:3000, click **Sign Up**, register, and complete onboarding.

### Demo credentials

No pre-seeded user is required — registration is open in development. Create your own account at `/signup`; any password of 8+ characters works.

## Environment Variables

### Backend (`backend/.env`)

| Variable | Required | Notes |
|---|---|---|
| `ROLIO_ENV` | — | `development` (default) / `production` |
| `ROLIO_SECRET_KEY` | prod | JWT signing. Generate: `openssl rand -base64 48` |
| `CSRF_SECRET` | prod | Generate: `openssl rand -base64 32` |
| `TOKEN_ENCRYPTION_KEY` | prod / Gmail | Fernet key. Generate: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `DATABASE_URL` | — | `sqlite:///./rolio.db` (default) or a PostgreSQL URL |
| `FRONTEND_ORIGINS` | — | Comma-separated CORS origins |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | Gmail / Google sign-in only | Google Cloud OAuth client — add **both** redirect URIs: `/api/gmail/callback` and `/api/auth/google/callback` |
| `REDIS_URL` | — | Optional. Without it, rate limiting and search caching use an in-memory per-process fallback |
| `NEMOTRON_API_KEY` | AI features only | NVIDIA build.nvidia.com key |
| `JSEARCH_API_KEY` | Live job search only | RapidAPI key |

In production mode the backend **refuses to start** if required secrets are missing or invalid.

### Frontend (`frontend/.env.local`)

| Variable | Required | Notes |
|---|---|---|
| `NEXT_PUBLIC_API_URL` | — | Backend URL. Default: `http://localhost:8001` |

## Optional Integrations

The app boots and works with **zero** API keys:

| Integration | Without a key |
|---|---|
| `JSEARCH_API_KEY` | Local seeded jobs still searchable; live search reports "unavailable" |
| `NEMOTRON_API_KEY` | AI features return graceful fallback messages |
| `GMAIL_*` + `TOKEN_ENCRYPTION_KEY` | Gmail sync section shows "not configured"; everything else works |
| Google sign-in | "Continue with Google" buttons fall back to email/password registration only |

## Tests & Checks

```bash
# Backend (76 tests — auth, CSRF, sessions, uploads, JSearch protection,
# OAuth state, token encryption, cross-user isolation)
cd backend && python -m pytest tests/ -q

# Frontend
cd frontend && npx tsc --noEmit     # typecheck
cd frontend && npm run build        # production build

# Migration sanity on a throwaway DB
cd backend && DATABASE_URL="sqlite:///./verify.db" alembic upgrade head
```

## Database Migrations

```bash
cd backend
alembic upgrade head          # apply all migrations
alembic history               # view the migration chain
alembic downgrade -1          # roll back the last migration
```

The chain: `d555c3fbfe92` (initial schema) → `873760469030` (constraints/indexes) → `b05a93c793ce` (refresh sessions) → `0219e6bcb03a` (oauth states) → `7c2e9f1a4b5d` (search history).

## Security Notes

- Tokens are never in JSON responses, localStorage, or URLs — HttpOnly cookies only
- Refresh-token rotation with reuse detection; logout revokes server-side
- CSRF double-submit on every state-changing endpoint (including refresh)
- Fernet (authenticated) encryption for Gmail tokens at rest; client secret lives only in env config
- One-time, expiring OAuth states persisted server-side
- Upload validation by file signature (PDF/DOCX only), size-capped, stored outside static serving
- Per-user/IP rate limits on auth, AI, uploads, and paid external search
- Generic auth errors (no account enumeration); no stack traces in production responses

## Known Limitations

- **SQLite for local development** — fine for the demo; use PostgreSQL for anything real (Supabase works as-is via `DATABASE_URL`).
- **In-memory rate limiting & search cache** — Redis is used when available (`REDIS_URL`), but the fallback is per-process. For multi-worker production, run Redis.
- **External APIs need keys** — AI and live job search require your own NVIDIA/RapidAPI keys; free tiers are sufficient for a demo.
- **Gmail needs Google Cloud setup** — create an OAuth client and add `http://localhost:8001/api/gmail/callback` as a redirect URI; test users must be added while the app is unverified.
- **Dev-mode encryption key** — if `TOKEN_ENCRYPTION_KEY` is empty in development, an ephemeral key is used and Gmail tokens don't survive restarts (set a real key to avoid this).
- **AI fallback behavior** — without an AI key, generated content is template-based rather than AI-written.
- **External job listings** — JSearch returns whatever currency/location the source listing publishes; local seeded jobs and salary benchmarks are India/INR.
- **Single-region demo** — a real production deployment would add HTTPS termination, Redis, monitoring, and backups (see checklist below).

## Deployment Checklist

For deploying beyond a demo:

1. **Database** — provision PostgreSQL (Supabase works); set `DATABASE_URL`; run `alembic upgrade head` before first boot (the app does **not** auto-create schema in production).
2. **Secrets** — set `ROLIO_ENV=production`, `ROLIO_SECRET_KEY`, `CSRF_SECRET`, `TOKEN_ENCRYPTION_KEY` (all validated at startup; the app refuses to boot with missing/weak values). Never commit `.env`.
3. **CORS / origins** — set `FRONTEND_ORIGINS` to your frontend URL(s), `BACKEND_PUBLIC_ORIGIN` to the API URL, `APP_PUBLIC_URL` to the frontend URL (used for OAuth redirects).
4. **HTTPS** — terminate TLS at your proxy/host; production cookies get `Secure` automatically when `ROLIO_ENV=production`. Set `FORCE_HTTPS=true` (auto-on in production) to 308-redirect any plain-HTTP request, and `TRUSTED_PROXIES=<proxy IPs|*>` so only your proxy can set `X-Forwarded-*` (both frontend and backend enforce this; the frontend reads `FORCE_HTTPS` at runtime).
5. **Google OAuth** — add `https://<your-api-host>/api/gmail/callback` and `https://<your-api-host>/api/auth/google/callback` as authorized redirect URIs.
6. **Frontend** — set `NEXT_PUBLIC_API_URL` at build time (`npm run build`), deploy `.next/` (standalone output is configured).
7. **Redis** (optional but recommended) — set `REDIS_URL` for cross-process rate limiting and 24h search caching.
8. **Uploads** — set `UPLOAD_DIR` to a persistent volume if not containerized ephemeral storage.
9. **Monitoring** — `/api/health` reports DB + Redis status; wire it to your uptime checker.

## Docker (Optional)

`docker-compose.yml` is included as a **local** Postgres + Redis + backend + frontend stack. It intentionally runs in development mode over HTTP; use HTTPS and set `ROLIO_ENV=production` only in a real deployment:

```bash
cp .env.docker.example .env   # fill in secrets
docker-compose up -d
```

**Dependency security:** both stacks are audit-clean. Verify with:
```bash
pip-audit -r backend/requirements.txt --no-deps   # Python
cd frontend && npm audit --omit=dev               # npm
```

## Technical Highlights

Full-stack AI career platform (Next.js 14, TypeScript, FastAPI, SQLAlchemy) featuring cookie-based JWT auth with rotating refresh sessions and CSRF protection, resume parsing with weighted job-matching, streaming AI assistance, Gmail OAuth with Fernet-encrypted tokens and replay-resistant server-side state, rate-limited external job search integration, Alembic-managed schema, and a 76-test security-focused pytest suite.

> Résumé wording: *"Built a full-stack AI career platform using Next.js, TypeScript, FastAPI, SQLAlchemy, cookie-based authentication, resume parsing, job matching, application tracking, Gmail OAuth, AI career assistance, and real-time job search."*

## License

MIT
