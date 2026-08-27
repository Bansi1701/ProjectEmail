# CLAUDE.md

Guidance for Claude Code (and any human) working in this repository.
**Read this before writing code.** Deeper detail lives in [docs/](docs/) — see [Further reading](#further-reading).

---

## 1. What this project is

A **disposable / temporary email platform**. Users generate a throwaway inbox, receive mail
(overwhelmingly a one-time verification code), and leave. Sessions are 3–8 minutes with the browser
tab held **active** while waiting for an OTP.

**Revenue is 100% programmatic advertising.** There is no paid tier in the current model. This single
fact drives most architectural decisions in this repo: page-load speed, ad viewability, session
duration and SEO rank are not polish — they are the product's revenue mechanics.

**Inbound only.** The platform never sends email. See [Rule 3](#rule-3-inbound-only-never-send-mail).

Business context, financial model and roadmap: [`docs/`](docs/).

---

## 2. Repo layout

```
backend/      Python 3.12 · FastAPI · the API, SMTP consumer, MIME parsing, OTP extraction
frontend/     TypeScript · Next.js 15 · the inbox UI and the programmatic-SEO pages
extension/    Browser extension (Chrome/Firefox/Edge, MV3) — Phase 2
infra/        Docker, deployment and operational scripts
docs/         Architecture, tech-stack rationale, roadmap, security, ADRs
```

`backend/` and `frontend/` are **independent deployables** that share nothing but the HTTP contract.
Do not import across them. The contract is the OpenAPI schema FastAPI generates.

---

## 3. The stack — decided, not open for casual change

These are settled decisions. If you believe one is wrong, **write an ADR in `docs/adr/` and raise it**;
do not silently substitute an alternative mid-task.

### Backend

| Concern | Use | Do NOT use |
|---|---|---|
| Language | Python 3.12+ | |
| Framework | **FastAPI** (async throughout) | Flask, Django — we hold thousands of open SSE connections |
| Server | **Uvicorn** workers under Gunicorn | |
| Packaging | **uv** (`uv sync`, `uv add`) | pip, poetry, pipenv, raw venv |
| Inbound SMTP (prod) | **Postfix** catch-all → LMTP → Python consumer | |
| Inbound SMTP (dev) | **aiosmtpd** on `:1025` | |
| MIME parsing | **stdlib `email`** (`BytesParser` + `policy.default`) | `mail-parser`, `flanker` — the stdlib is better and has no CVE surface of its own |
| HTML sanitizing | **nh3** | **`bleach` is archived/deprecated — never add it** |
| Ephemeral messages | **Redis** with native `EXPIRE` (TTL 10–60 min) | Storing messages in Postgres |
| Live push | **sse-starlette** + Redis **pub/sub** | Long-polling; WebSockets (one-way is all we need) |
| Durable data | **PostgreSQL 16** + **SQLAlchemy 2.0** (async) + **Alembic** | |
| Attachments | **S3** or **Cloudflare R2** | The database |
| Validation | **Pydantic v2** | Hand-rolled dict validation |
| Background jobs | **ARQ** (async, Redis-backed) | Celery — too heavy for this |
| Rate limiting | Redis counters at the edge + **SlowAPI** | |
| Lint + format | **Ruff** | black, isort, flake8 (Ruff replaces all three) |
| Types | **mypy** (strict on `app/`) | |
| Tests | **pytest** + **pytest-asyncio** + **httpx** | `unittest` |

### Frontend

| Concern | Use | Do NOT use |
|---|---|---|
| Framework | **Next.js 15** (App Router) | Pages Router |
| Language | **TypeScript**, `strict: true` | Plain JS; `any` |
| Styling | **Tailwind CSS v4** | CSS-in-JS runtimes — they cost us LCP |
| Components | **shadcn/ui** (Radix primitives) | Heavy component kits (MUI, Chakra) |
| State | React state + native `EventSource`. Add **Zustand** only when genuinely shared | Redux |
| Data fetching | **TanStack Query** for REST; raw `EventSource` for the live stream | |
| i18n (25 languages) | **next-intl** | |
| Package manager | **pnpm** | npm, yarn |
| Lint + format | **Biome** | ESLint + Prettier |
| Tests | **Vitest** + **Playwright** (e2e) | Jest |

### Infrastructure

| Concern | Use |
|---|---|
| Containers | Docker + Docker Compose (local), same images in prod |
| Hosting | Hetzner or Fly.io — real servers, not serverless |
| CDN / WAF / DNS | Cloudflare |
| Bot mitigation | Cloudflare Turnstile + WAF rate limits |
| Errors | Sentry (both backend and frontend) |

---

## 4. Non-negotiable rules

These encode failure modes that have killed real services in this category. Violating one is a bug
even if tests pass.

### Rule 1: Email HTML and ad scripts must NEVER share an origin

Rendered email is **untrusted attacker-controlled HTML**. It is served from a **separate origin**
(e.g. `content-sandbox.example.com`) and embedded in a sandboxed iframe.

```html
<!-- CORRECT -->
<iframe sandbox="allow-popups allow-popups-to-escape-sandbox" src="https://content-sandbox.../msg/{id}">

<!-- CATASTROPHIC — never write this -->
<iframe sandbox="allow-scripts allow-same-origin" srcdoc="{{ email_html }}">
```

`allow-scripts` + `allow-same-origin` **together** let the framed document reach into the parent
page, read session state and tamper with ad scripts. It defeats the entire sandbox.
The original business plan proposes `allow-same-origin`; **that is an error and we do not follow it.**

Sanitize with `nh3` on the way in **and** sandbox on the way out. Both. Never one or the other.

### Rule 2: Inbox addresses must be unguessable

Public catch-all domains mean anyone can poll an address and read whatever arrives. Address
enumeration is the most common real-world breach in this product category — it leaks other people's
OTPs, which is an account-takeover vector.

- Address local-parts carry **≥ 64 bits of entropy** for randomly generated inboxes.
- Reading an inbox requires a **possession token** issued at creation, not just knowledge of the address.
- User-chosen addresses are **opt-in, clearly marked as public**, and never the default.
- Rate-limit inbox reads per IP and per token. Always.

### Rule 3: Inbound only — never send mail

No SMTP client, no sending library, no "reply" feature, no forwarding. Ever. This is what keeps our
IPs and hosting accounts off blocklists and keeps the platform from being a spam/phishing relay.
If a task seems to need outbound mail, stop and raise it.

### Rule 4: Store the minimum, expire it fast

Short TTL is a genuine privacy protection and our best answer to a legal request. Do not add
retention, do not archive messages "for analytics", do not log message bodies. Aggregate counters
only.

### Rule 5: Protect Core Web Vitals

Ad revenue and SEO rank both depend on them. Every frontend change should hold **CLS < 0.1** and
**INP < 200ms**.

- Ad slots get **reserved fixed dimensions** before the ad loads. Never let an ad reflow content.
- Third-party ad scripts load **async / after hydration**, never blocking.
- No layout shift when a new email arrives — the list grows downward into reserved space.

### Rule 6: Never commit secrets

`.env` is gitignored. Add new config to `.env.example` with a placeholder value and document it.
No API keys, SSP credentials, registrar tokens or database URLs in source. Ever.

---

## 5. Conventions

**Python**
- `async def` all the way down. A blocking call in a request path stalls every connection on that worker.
- Full type annotations. `mypy --strict` passes on `app/`.
- Pydantic models in `app/schemas/`, SQLAlchemy models in `app/models/`. Never return an ORM object from a route.
- Business logic in `app/services/`, not in routers. Routers do validation and delegation only.
- Custom exceptions in `app/core/exceptions.py`, mapped to HTTP responses by one handler.

**TypeScript**
- Server Components by default. Add `"use client"` only when you need state, effects or browser APIs.
- Co-locate components with their route unless genuinely shared, then `src/components/`.
- No `any`. Use `unknown` and narrow.
- All user-facing strings go through `next-intl`. Never hardcode English in a component.

**Both**
- Conventional Commits: `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`.
- Branch naming: `feat/short-description`, `fix/short-description`.
- Write the test with the code, not after.

---

## 6. Commands

```bash
# Backend
cd backend
uv sync                                  # install
uv run uvicorn app.main:app --reload     # dev server → :8000
uv run pytest                            # tests
uv run ruff check --fix . && uv run ruff format .
uv run mypy app/
uv run alembic upgrade head              # migrations
uv run alembic revision --autogenerate -m "..."

# Frontend
cd frontend
pnpm install
pnpm dev                                 # → :3000
pnpm build
pnpm test                                # Vitest
pnpm test:e2e                            # Playwright
pnpm check                               # Biome lint + format

# Full local stack (Postgres, Redis, MailHog, api, web)
docker compose -f infra/docker/compose.yml up
```

---

## 7. Working on this repo

**Before you start a task**
- Check whether it touches a [non-negotiable rule](#4-non-negotiable-rules). If it does, follow the rule, not the ticket.
- Ad-ops and mail-routing changes have revenue and deliverability consequences. Read [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) first.

**When you finish**
- Run lint, types and tests for the side you touched. Do not report done on unverified work.
- If you made an architectural decision, record it in `docs/adr/`.

**Ask a human rather than guessing about**
- Anything that would send email, extend data retention, or weaken the iframe sandbox.
- Ad network integration and SSP configuration — policy violations here can get the whole site demonetized.
- Adding a new inbound-mail provider or moving domains.

**Do not**
- Add a dependency that duplicates something already in the stack table above.
- Introduce a second state manager, HTTP client, ORM, or CSS approach.
- Disable a lint rule or type check to make something pass — fix the code.
- Weaken a security control to make a test pass.

---

## 8. Further reading

| Document | What it covers |
|---|---|
| [`docs/TECH_STACK.md`](docs/TECH_STACK.md) | Every choice above with full rationale, alternatives and costs |
| [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) | How mail flows from SMTP to the user's screen |
| [`docs/SECURITY.md`](docs/SECURITY.md) | Threat model, abuse governance, compliance |
| [`docs/ROADMAP.md`](docs/ROADMAP.md) | 24-week build sequence and phase exit criteria |
| [`docs/adr/`](docs/adr/) | Architecture Decision Records |
