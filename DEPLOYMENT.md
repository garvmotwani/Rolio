# Deploying Rolio

Rolio is deployed as two Vercel projects plus a managed PostgreSQL database. Redis is optional but recommended for shared rate limiting and external-job caching.

```text
Browser → Vercel frontend → same-origin /api/* rewrite → Vercel FastAPI function
                                                        → PostgreSQL
                                                        → Redis (optional)
```

## 1. Provision PostgreSQL

Create a Neon, Supabase, or other managed PostgreSQL database and keep its connection string as `DATABASE_URL`. Use a pooled connection URL if your provider recommends one.

Before the first production deployment, run migrations from a trusted machine or release environment:

```bash
cd backend
DATABASE_URL='postgresql+psycopg2://USER:PASSWORD@HOST/DATABASE' alembic upgrade head
```

PowerShell:

```powershell
cd backend
$env:DATABASE_URL = 'postgresql+psycopg2://USER:PASSWORD@HOST/DATABASE'
alembic upgrade head
```

Run this deliberately for every schema release. The production application deliberately skips `create_all`, seeding, and automatic migrations; serverless cold starts are not a safe migration runner.

## 2. Deploy the backend

Create a Vercel project with `backend` as its Root Directory. Vercel automatically detects the FastAPI application exported from `api/index.py`; no legacy `vercel.json` rewrite or build configuration is required. FastAPI receives the original `/api/*` paths and routes them normally.

Set these production variables:

| Variable | Required | Notes |
|---|---:|---|
| `ROLIO_ENV` | yes | `production` |
| `DATABASE_URL` | yes | Managed PostgreSQL URL |
| `ROLIO_SECRET_KEY` | yes | New strong random value |
| `CSRF_SECRET` | yes | New strong random value |
| `TOKEN_ENCRYPTION_KEY` | yes | Valid Fernet key for encrypted Gmail tokens |
| `APP_PUBLIC_URL` | yes | Frontend HTTPS origin |
| `BACKEND_PUBLIC_ORIGIN` | yes | Backend HTTPS origin |
| `FRONTEND_ORIGINS` | yes | Frontend HTTPS origin, comma-separated if needed |
| `TRUSTED_PROXIES` | yes | `*` when traffic is only behind Vercel |
| `REDIS_URL` | recommended | Upstash `rediss://` URL |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | optional | Google sign-in / Gmail integration |
| `NEMOTRON_API_KEY`, `JSEARCH_API_KEY` | optional | AI and live job listings |
| `RESEND_API_KEY`, `EMAIL_FROM` | optional | Email verification and reset messages |

The function returns generic production errors and logs detailed failures only in Vercel logs. Do not configure secrets in frontend environment variables.

## 3. Deploy the frontend

Create another Vercel project with `frontend` as its Root Directory. Set one server-side environment variable:

| Variable | Value |
|---|---|
| `BACKEND_ORIGIN` | Backend Vercel URL, including `https://`, without a trailing slash |

Leave `NEXT_PUBLIC_API_URL` unset in production. The configured rewrite keeps browser requests and authentication cookies on the frontend domain.

After setting or changing `BACKEND_ORIGIN`, redeploy the frontend so Next.js rebuilds its rewrite configuration.

## 4. Configure OAuth only when needed

In Google Cloud, add these authorized redirect URIs using the **frontend** domain:

```text
https://YOUR-FRONTEND/api/auth/google/callback
https://YOUR-FRONTEND/api/gmail/callback
```

Set the equivalent backend variables:

```text
GOOGLE_SIGNIN_REDIRECT_URI=https://YOUR-FRONTEND/api/auth/google/callback
GOOGLE_REDIRECT_URI=https://YOUR-FRONTEND/api/gmail/callback
```

## 5. Verify after deployment

1. Visit `https://YOUR-BACKEND/api/health` and confirm the database is healthy.
2. Visit `https://YOUR-FRONTEND/api/health` and confirm the frontend rewrite reaches the backend.
3. Register a test account, refresh while signed in, then log out and back in.
4. Confirm browser cookies are set on the frontend domain and are `Secure` in production.
5. If enabled, test Google sign-in, Gmail connection, password reset, and email verification using the frontend callback URLs.

## Operational notes

- Vercel’s filesystem is ephemeral. Store production resume uploads in object storage rather than local disk.
- Configure Redis for multi-instance rate limiting and caching.
- Keep regular PostgreSQL backups and monitor `/api/health`.
- Never commit `.env` files, database files, uploaded resumes, API keys, OAuth secrets, or production dumps.
