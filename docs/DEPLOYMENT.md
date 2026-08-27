# Deployment

> **Living document — v0.1.**

## The shape

```
  Browser
     │
     ├─── static HTML/CSS/JS ──────►  GitHub Pages
     │                                bansi1701.github.io/ProjectEmail/
     │                                free · no server · no database
     │
     └─── fetch / EventSource ─────►  FastAPI  (Render)
                                          │
                                          ├──────────►  Neon      (Postgres)
                                          └──────────►  Redis     (messages, TTL)
```

**GitHub Pages cannot connect to a database.** It is a static file host — there is no server
process to hold a connection. Credentials reach the database only from the API host.

> ⚠️ **Never put a connection string in a `NEXT_PUBLIC_` variable.** Those are baked into the
> JavaScript bundle every visitor downloads, and this repo is public. The only thing the frontend
> may know is the API's **URL**.

---

## Why Render (for now)

| | Free tier in 2026 | Cold start | Verdict |
|---|---|---|---|
| **Render** | ✅ Real. 512MB / 0.1 CPU, 750 hrs/mo, no card | 30–60s after 15 min idle | **Start here** |
| Fly.io | ❌ Trial only (2 VM hrs / 7 days), then pay-as-you-go | None | Best paid option |
| Railway | ❌ None. Plan fee + per-second metering | None | Easiest DX, costs from day one |
| Hetzner VPS | ❌ ~€4/mo | None | Cheapest at scale, most ops work |

**Render's cold start is a real problem for this product.** Users open an inbox and wait seconds
for an OTP; making the first visitor after idle wait a minute defeats the entire value proposition.

It is fine *now*, while proving the system works. **Move off the free plan before real users** —
either Render's paid tier or Fly.io, which has no cold start and suits the long-lived SSE
connections better.

Neon pairs well here specifically because Render's own free Postgres **expires after 30 days**.
Yours will not.

---

## Deploying the API

### 1. Create the service

Render dashboard → **New** → **Blueprint** → point at this repo. It reads
[`render.yaml`](../render.yaml) and creates `projectemail-api` from `backend/Dockerfile`.

### 2. Set the secrets

Everything marked `sync: false` in the blueprint must be set in the dashboard. **Never in the repo.**

| Variable | Value |
|---|---|
| `DATABASE_URL` | Neon **pooled** URI, exactly as the Console gives it |
| `MIGRATION_DATABASE_URL` | Neon **direct** (unpooled) URI |
| `REDIS_URL` | Upstash or Render Redis |
| `SANDBOX_ORIGIN` | The separate origin serving email HTML ([SECURITY.md §1](SECURITY.md#1-untrusted-email-html)) |
| `SECRET_KEY` | Generated automatically |
| `APP_ORIGIN` | Pre-set to the Pages origin. Comma-separated for more |

### 3. Migrate

```bash
# Render Shell, or locally with MIGRATION_DATABASE_URL pointed at Neon
alembic upgrade head
```

### 4. Point the frontend at it

Repo → **Settings → Secrets and variables → Actions → Variables**:

| Variable | Value |
|---|---|
| `API_URL` | `https://projectemail-api.onrender.com` |
| `SANDBOX_ORIGIN` | Your sandbox origin |

Then re-run **Deploy Pages**. Until `API_URL` is set the build falls back to `https://api.invalid`,
so a misconfiguration fails loudly instead of silently pointing at nothing.

### 5. Check CORS

`APP_ORIGIN` on the API must contain the Pages origin exactly — scheme, host, no trailing slash:

```
APP_ORIGIN=https://bansi1701.github.io
```

Wrong value = every browser request blocked, visible only in the browser console. The server logs
look clean, which makes this a slow one to diagnose.

---

## Port binding

The container binds `$PORT` when the platform sets one, falling back to 8000. Render, Railway and
Fly all assign it themselves, and a hardcoded bind fails their health checks.

`WEB_CONCURRENCY` controls gunicorn workers — **2 on Render free**, since four will OOM a 512MB
instance.

---

## What is not deployed yet

- **Redis** — needed before the inbox works. Upstash has a real free tier.
- **The SMTP listener.** Render's web services do not accept inbound SMTP on port 25, so mail
  ingestion cannot run there. It needs a VPS with a real IP, or an inbound-mail provider that
  forwards to a webhook. **This is the piece that decides where the product actually lives.**
- **The sandbox origin** for rendering email HTML.

Until those exist, the deployed API serves health checks and whatever endpoints do not need mail.

---

## Health endpoints

| Path | Purpose |
|---|---|
| `/health` | Liveness. Deliberately does **not** touch the database, so a Neon cold start cannot get the container killed |
| `/health/ready` | Readiness. Reports dependency state without failing the request |

Render's health check uses `/health`.
