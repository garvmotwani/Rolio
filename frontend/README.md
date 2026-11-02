# Rolio frontend

Next.js 15 / React 19 frontend for Rolio.

```bash
cd frontend
npm install
npm run dev
```

By default, browser requests use same-origin `/api/*` paths. In deployment, `BACKEND_ORIGIN` configures the server-side Next.js rewrite to the FastAPI backend; do not expose backend secrets through `NEXT_PUBLIC_*` variables.

Run `npm run lint`, `npx tsc --noEmit`, and `npm run build` before publishing. See the root [README](../README.md) for full setup and deployment instructions.
