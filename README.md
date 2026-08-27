# ProjectEmail — Disposable Email Platform

A temporary / disposable email service. Users generate a throwaway inbox, receive their
verification code, and move on. Ad-supported, privacy-preserving, built to run cheaply at scale.

> **New here? Read [`CLAUDE.md`](CLAUDE.md) first.** It is the single source of truth for what we
> use and how we work — for both humans and AI assistants.

> **Status: v0.1 — a living project.** Everything in this repo is a starting point, not a final
> design. Stack choices, architecture and the roadmap will all change as we build and learn.
> Improvements are expected and welcome — see [CONTRIBUTING.md](CONTRIBUTING.md).

---

## Stack at a glance

| | |
|---|---|
| **Backend** | Python 3.12 · FastAPI · Uvicorn · SQLAlchemy 2.0 · Pydantic v2 · uv |
| **Frontend** | TypeScript · Next.js 15 (App Router) · Tailwind v4 · shadcn/ui · pnpm |
| **Data** | PostgreSQL 16 / Neon · explicit message expiry and automatic cleanup |
| **Mail** | Cloudflare Email Routing Worker → authenticated webhook · stdlib `email` parser · `nh3` sanitizer |
| **Real-time** | Server-Sent Events via `sse-starlette`, one-process broker for the MVP |
| **Infra** | Docker (multi-stage) · Render · GitHub Pages · Cloudflare · Sentry |

Full rationale, alternatives considered and cost analysis: [`docs/TECH_STACK.md`](docs/TECH_STACK.md).

---

## Repo layout

```
backend/      FastAPI app, SMTP consumer, MIME parsing, OTP extraction
frontend/     Next.js inbox UI + programmatic-SEO pages
extension/    Browser extension (Chrome/Firefox/Edge, MV3) — Phase 2
infra/        Docker Compose stack, deployment and ops scripts
docs/         Architecture, tech stack, roadmap, security, ADRs
```

---

## Getting started

**Only Docker is required.**

```bash
git clone https://github.com/Bansi1701/ProjectEmail.git
cd ProjectEmail
docker compose -f infra/docker/compose.yml up
```

That's it. Four services come up and both apps hot-reload on edit:

| | URL | |
|---|---|---|
| **web** | http://localhost:3000 | Next.js app |
| **api** | http://localhost:8000 | FastAPI — interactive docs at `/docs` |
| **mailpit** | http://localhost:8025 | Send test mail to `:1025`, watch it arrive |
| postgres | `:5432` | |

**Port already taken?** Another project on your machine may hold 5432 or 8000. Copy
`infra/docker/.env.example` to `infra/docker/.env` and override only what clashes.

Local mail testing uses **Mailpit** — no real domains, no real mail, nothing leaves your machine.

### Neon database connection

The hosted PostgreSQL database is the Neon project **ProjectEmail**. For local backend work:

1. Copy `backend/.env.example` to `backend/.env`.
2. Set `DATABASE_URL` to the **pooled** Neon connection URI, pasted exactly as the Console gives it.
3. Never commit `backend/.env` — it is gitignored.

No hand-editing of the URI is needed. The `postgresql://` scheme is upgraded to
`postgresql+asyncpg://` and the `?sslmode=require&channel_binding=require` suffix is stripped and
translated automatically — asyncpg is not libpq and rejects those params outright. See
[`backend/app/core/db.py`](backend/app/core/db.py).

For migrations, set `MIGRATION_DATABASE_URL` to the **direct** (unpooled) endpoint; DDL through
PgBouncer is unreliable.

The local Docker stack continues to use its own PostgreSQL container by default. Hosted
environments should inject `DATABASE_URL` through their secret manager.

Full detail, including the three Neon behaviours that bite: [`docs/DATABASE.md`](docs/DATABASE.md).

<details>
<summary>Running without Docker</summary>

Needs [uv](https://docs.astral.sh/uv/), Node 20+ and pnpm, plus Postgres.

```bash
cd backend  && uv sync && uv run uvicorn app.main:app --reload   # → :8000
cd frontend && pnpm install && pnpm dev                          # → :3000
```
</details>

---

## Documentation

| Document | What it covers |
|---|---|
| [`CLAUDE.md`](CLAUDE.md) | **Start here.** Stack decisions, non-negotiable rules, conventions |
| [`docs/TECH_STACK.md`](docs/TECH_STACK.md) | Every technology choice with rationale and alternatives |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | How mail flows from SMTP to the user's screen |
| [`docs/SECURITY.md`](docs/SECURITY.md) | Threat model, abuse governance, compliance posture |
| [`docs/DATABASE.md`](docs/DATABASE.md) | Neon setup, schema and migrations |
| [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) | How Pages, the API host and Neon fit together |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | 24-week build sequence and exit criteria |
| [`docs/VALIDATION.md`](docs/VALIDATION.md) | Research findings on the revenue model and ad-policy risk |
| [`docs/TRACK_A.md`](docs/TRACK_A.md) | Platform, trust, security and operations execution track |
| [`docs/adr/`](docs/adr/) | Architecture Decision Records |

---

## Three things to know before you write code

1. **Email HTML is untrusted.** It is sanitized with `nh3` and rendered in a sandboxed iframe on a
   separate origin. Never `allow-scripts` together with `allow-same-origin`.
2. **We never send email.** Inbound only, permanently. It is what keeps us off blocklists.
3. **Inbox addresses must be unguessable** and reads require a possession token. Address enumeration
   is the classic breach in this product category.

The full set is in [`CLAUDE.md` §4](CLAUDE.md#4-non-negotiable-rules).

---

## Contributing

Conventional Commits (`feat:`, `fix:`, `docs:`…), branches named `feat/short-description`.
Run lint, types and tests for the side you touched before opening a PR. Architectural decisions get
an ADR in `docs/adr/`.
