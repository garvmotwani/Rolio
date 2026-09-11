# Deploying Rolio

Rolio is a two-service app: a **Next.js frontend** and a **FastAPI backend**,
plus managed **PostgreSQL** and **Redis**. This guide uses free tiers end to end.

## Architecture

```
Browser ──> Frontend (Vercel)  ──/api/* proxy──>  Backend (Render)  ──>  Postgres (Neon/Supabase)
                                                                   ──>  Redis (Upstash)
```

The frontend **proxies all `/api/*` requests to the backend** (Next.js rewrites).
The browser only ever talks to the frontend origin, so auth cookies are
first-party — this sidesteps third-party cookie blocking entirely. Do not point
the frontend directly at the backend origin.

## Recommended free-tier stack

| Component | Service | Free tier |
|---|---|---|
| Frontend | [Vercel](https://vercel.com) | Hobby plan |
| Backend | [Render](https://render.com) or [Railway](https://railway.app) | Free web service |
| PostgreSQL | [Neon](https://neon.tech) or Supabase | Free Postgres |
| Redis | [Upstash](https://upstash.com) | Free tier |

## Step 1 — Database (Neon/Supabase)

1. Create a project, copy the connection string.
2. Convert to the SQLAlchemy driver form:
   `postgresql+psycopg2://user:pass@host/db` (or `postgresql://` — both work).
3. Note it as `DATABASE_URL`.

## Step 2 — Backend (Render)

1. **New Web Service** → connect your GitHub repo.
2. Settings:
   - **Root directory:** `backend`
   - **Runtime:** Docker (uses `backend/Dockerfile`) — or Python with
     start command `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Health check path:** `/api/health`
3. Environment variables (see checklist below).
4. After first deploy, run the migration once (Render Shell or a one-off job):
   `alembic upgrade head`
   - For a demo, `seed_database()` runs automatically in development mode.
     In production mode, seed manually if you want the demo account:
     `python -c "from seed import seed_database; seed_database()"`

## Step 3 — Frontend (Vercel)

1. **Add New Project** → import the repo.
2. Settings:
   - **Root directory:** `frontend`
   - Framework preset: Next.js (zero config otherwise)
3. Environment variables:
   - `NEXT_PUBLIC_API_URL` — **leave unset.** The default (empty) makes the
     browser call `/api/...` same-origin, which the rewrite proxies to the
     backend. This is what makes cookies work.
   - `BACKEND_ORIGIN` = your Render backend URL, e.g. `https://rolio-api.onrender.com`
     (used server-side by the rewrite; never exposed to the browser).
4. Deploy.

## Step 4 — Google OAuth redirect URIs

In Google Cloud Console → Credentials → your OAuth client → **Authorized
redirect URIs**, add (replace with your real domains):

```
https://<frontend-domain>/api/auth/google/callback
https://<frontend-domain>/api/gmail/callback
```

Because the frontend proxies `/api/*`, Google callbacks land on the frontend
origin and are proxied to the backend — keeping every cookie first-party.

Then set on the backend:

- `GOOGLE_SIGNIN_REDIRECT_URI=https://<frontend-domain>/api/auth/google/callback`
- `GOOGLE_REDIRECT_URI=https://<frontend-domain>/api/gmail/callback`

## Environment variable checklist

### Backend (Render)

| Variable | Required | Notes |
|---|---|---|
| `ROLIO_ENV` | ✅ | `production` — enables fail-fast secret validation, disables `/docs`, skips auto-seed |
| `DATABASE_URL` | ✅ | Postgres connection string |
| `REDIS_URL` | recommended | e.g. `rediss://default:...@upstash.io:6379` (note `rediss://` for TLS) |
| `ROLIO_SECRET_KEY` | ✅ | `openssl rand -base64 48` — **new value, never reuse dev** |
| `CSRF_SECRET` | ✅ | `openssl rand -base64 32` |
| `TOKEN_ENCRYPTION_KEY` | ✅ (for Gmail) | Fernet key: `python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"` |
| `APP_PUBLIC_URL` | ✅ | `https://<frontend-domain>` — used in password-reset / verification links and OAuth redirects |
| `BACKEND_PUBLIC_ORIGIN` | ✅ | `https://<backend-domain>` |
| `FRONTEND_ORIGINS` | ✅ | `https://<frontend-domain>` (comma-separated) |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | optional | Google sign-in + Gmail sync |
| `GOOGLE_SIGNIN_REDIRECT_URI` | with Google | `https://<frontend-domain>/api/auth/google/callback` |
| `GOOGLE_REDIRECT_URI` | with Google | `https://<frontend-domain>/api/gmail/callback` |
| `NEMOTRON_API_KEY` | optional | AI features degrade gracefully without it |
| `JSEARCH_API_KEY` | optional | External job search; local seeded jobs always work |
| `RESEND_API_KEY` / `EMAIL_FROM` | optional | Password-reset/verification emails |
| `FORCE_HTTPS` | auto | Defaults on in production |
| `TRUSTED_PROXIES` | ✅ | `*` on Render/Railway (app is only reachable via their proxy) |
| `MAX_UPLOAD_SIZE_MB` | optional | Default 10 |

### Frontend (Vercel)

| Variable | Required | Notes |
|---|---|---|
| `BACKEND_ORIGIN` | ✅ | Backend URL, used by the server-side `/api/*` rewrite |
| `NEXT_PUBLIC_API_URL` | leave unset | Empty = same-origin proxy (recommended) |

## Post-deploy verification

1. `curl https://<backend-domain>/api/health` → `{"status":"ok",...}`
2. Open the app, register an account — cookies should be set on the frontend
   domain (DevTools → Application → Cookies).
3. Log out / log back in; refresh the page while signed in (session survives).
4. Google sign-in and Gmail connect (if configured) complete without
   `?...=error` redirects.
5. Password-reset email links open the correct frontend domain.

## Updating

Push to `main` — Vercel and Render auto-deploy. Backend schema changes need
`alembic upgrade head` (Render: run in shell or add a release-job command).
