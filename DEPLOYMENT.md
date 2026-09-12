# Deploying Rolio

Rolio is a two-service app: a **Next.js frontend** and a **FastAPI backend**,
plus managed **PostgreSQL** and **Redis**. This guide uses free tiers end to end.

## Architecture

```
Browser ──> Frontend (Vercel)  ──/api/* proxy──>  Backend (Vercel fn)  ──>  Postgres (Neon)
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
| Backend | [Vercel](https://vercel.com) | Hobby plan (Python serverless function) |
| PostgreSQL | [Neon](https://neon.tech) or Supabase | Free Postgres |
| Redis | [Upstash](https://upstash.com) | Free tier (optional) |

> **Why the backend is also on Vercel:** Render's free tier now requires a
> card in some regions and HF Spaces paywalled Docker containers (July 2026).
> The whole backend ships as one Python serverless function (`api/index.py`
> boots the FastAPI app; `vercel.json` routes `/api/*` to it) — no card, and
> cold starts double as migration runs. Vercel Hobby allows 100GB-hrs/month,
> plenty for a portfolio demo.

## Step 1 — Database (Neon/Supabase)

1. Create a project, copy the connection string.
2. Convert to the SQLAlchemy driver form:
   `postgresql+psycopg2://user:pass@host/db` (or `postgresql://` — both work).
3. Note it as `DATABASE_URL`.

> **Using Neon? Skip their CLI onboarding** (`neon login`, `neon skills`,
> `neon.ts`, `neon deploy`). Those steps configure Neon's platform extras —
> Neon Auth and storage buckets — which Rolio does not use: the app has its
> own cookie sessions and Google sign-in, and only needs plain Postgres.
> Just open Dashboard → **Connect** on the right branch and copy the
> **pooled** connection string (hostname contains `-pooler`) as `DATABASE_URL`.

## Step 2 — Backend (Vercel)

1. Vercel dashboard → **Add New… → Project** → import `garvmotwani/Rolio` again.
2. On the configure screen:
   - **Project name:** `rolio-api`
   - **Root Directory:** click `Edit` → select `backend`
   - Framework preset: **Other** — the `vercel.json` inside `backend/` handles the rest
3. Open **Environment Variables** and add the backend variables from the
   checklist below (`ROLIO_ENV`, `DATABASE_URL`, secrets, etc.).
4. Click **Deploy**. Migrations run automatically on the first request.
   - For demo data, seed once from your machine with `DATABASE_URL` pointed
     at the production database: `python -c "from seed import seed_database; seed_database()"`

## Step 3 — Frontend (Vercel)

1. Go to [vercel.com](https://vercel.com) → **Sign up with GitHub** (Hobby plan is free, no credit card).
2. Dashboard → **Add New… → Project** → find `garvmotwani/Rolio` → **Import**.
3. On the configure screen:
   - **Root Directory:** click `Edit` → select `frontend` (the repo root is the monorepo, Vercel must build only the frontend folder).
   - Framework preset auto-detects **Next.js** — leave everything else at defaults (build command `next build`, output auto).
4. Open **Environment Variables** and add exactly one:
   - Name: `BACKEND_ORIGIN`
   - Value: your backend URL **with** `https://`, **no** trailing slash — e.g. `https://rolio-api.vercel.app` or `https://rolio-api-<team>.vercel.app`
   - Environments: check Production, Preview, and Development.
   - Do **NOT** set `NEXT_PUBLIC_API_URL` — leaving it unset activates the same-origin proxy that makes auth cookies work.
5. Click **Deploy**. First build takes ~2–3 minutes; you'll get a `*.vercel.app` URL.
6. Every push to `main` auto-deploys; pull requests get preview URLs automatically.

> Deploying before the backend is live is fine — the build succeeds either way.
> The site will only fully work once `BACKEND_ORIGIN` points at a running
> backend. If you set it later, just trigger a redeploy (Deployments → ⋯ →
> Redeploy) so the rewrite picks it up.

## Step 4 — Google OAuth redirect URIs

In Google Cloud Console → Credentials → your OAuth client → **Authorized
redirect URIs**, add (replace with your real domains):

```
https://<frontend-domain>/api/auth/google/callback
https://<frontend-domain>/api/gmail/callback
```

Because the frontend proxies `/api/*`, Google callbacks land on the frontend
origin and are proxied to the backend — keeping every cookie first-party.
(In the all-Vercel setup, `BACKEND_ORIGIN` is the backend project's URL and
both projects proxy `/api/*` through it.)

Then set on the backend:

- `GOOGLE_SIGNIN_REDIRECT_URI=https://<frontend-domain>/api/auth/google/callback`
- `GOOGLE_REDIRECT_URI=https://<frontend-domain>/api/gmail/callback`

## Environment variable checklist

### Backend (Vercel → project `rolio-api`)

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
| `TRUSTED_PROXIES` | ✅ | `*` on Vercel (app is only reachable via their proxy) |
| `MAX_UPLOAD_SIZE_MB` | optional | Default 10 |

### Frontend (Vercel → project `rolio`)

| Variable | Required | Notes |
|---|---|---|
| `BACKEND_ORIGIN` | ✅ | Backend URL, used by the server-side `/api/*` rewrite |
| `NEXT_PUBLIC_API_URL` | leave unset | Empty = same-origin proxy (recommended) |

## Post-deploy verification

1. `curl https://<backend-domain>/api/health` → `{"status":"ok",...}` (first
   call may take ~10s — that's the cold start running migrations)
2. `curl https://<frontend-domain>/api/health` → same JSON. This proves the
   frontend → backend proxy rewrite works (the browser never needs the backend URL).
3. Open the app, register an account — cookies should be set on the frontend
   domain (DevTools → Application → Cookies).
4. Log out / log back in; refresh the page while signed in (session survives).
5. Google sign-in and Gmail connect (if configured) complete without
   `?...=error` redirects.
6. Password-reset email links open the correct frontend domain.

## Updating

Push to `main` — both Vercel projects auto-deploy (each only rebuilds when
its root directory changes). Backend schema changes apply via automatic
migrations on the next cold start.
