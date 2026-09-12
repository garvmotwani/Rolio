---
title: Rolio API
emoji: 🚀
colorFrom: gray
colorTo: gray
sdk: docker
app_port: 8001
pinned: false
---

# Rolio API (FastAPI)

Backend for the Rolio career platform. Deployed as a Hugging Face **Docker
Space** — the frontend (Vercel) proxies all `/api/*` requests here
server-side, so the Space URL never needs to be public-facing.

- App URL: `https://garvmotwani-rolio-api.hf.space`
- Health: `/api/health`
- Migrations run automatically on startup (`alembic upgrade head`)

Configuration is via Space **secrets** (Settings → Variables and secrets):
see `DEPLOYMENT.md` in the main repository for the full checklist.
