# Tech Stack — Decisions & Rationale

Every choice, why we made it, what we rejected. If you want the short version, see
[`CLAUDE.md` §3](../CLAUDE.md#3-the-stack--current-defaults).

**How to change something here:** write an ADR in [`adr/`](adr/) and raise it. Do not silently
substitute an alternative mid-task.

> **Living document — v0.1.** These are current defaults chosen on today's information, not
> permanent commitments. Several rest on assumptions we have not yet tested against real traffic
> (see [Cost model](#cost-model)). Revisiting a choice with evidence is the process working, not a
> deviation from it.

---

## The decision that shaped everything else

The [source business plan](.) proposed an all-Cloudflare serverless edge stack: Workers, Email
Routing, D1/KV, Pages. **We chose Python on conventional servers instead.**

| | Cloudflare Workers (proposed) | Python / FastAPI (chosen) |
|---|---|---|
| Opex | Near zero | A few hundred $/mo at scale |
| Scaling | Automatic | We do capacity planning |
| Language | TypeScript only | Python + TS frontend |
| MIME parsing | `postal-mime` (fine) | stdlib `email` (better) |
| Mail ingest at scale | Provider-dependent | Self-hosted Postfix, ~$0 marginal |
| Platform risk | Concentrated on one vendor's AUP | Portable |

**Why we switched.** Three reasons, in order of weight:

1. **Team fit.** The team is Python. That beats every architectural argument on this page — a stack
   your developers are fluent in ships faster and breaks less.
2. **Mail ingest economics.** At ~25M inbound messages/month, hosted inbound-mail pricing is a real
   line item (SES inbound at $0.10/1,000 ≈ $2,500/mo). Postfix on a server we already run is ~$0
   marginal. The savings alone exceed the server bill.
3. **Platform risk.** Whether a given provider's acceptable-use policy tolerates a public
   disposable-email service at scale is a live question — and one that, if answered badly, is an
   account termination rather than a migration. Running our own SMTP removes that dependency
   entirely.

**What we give up.** The "scales from 100 to 100,000,000 requests automatically" property in the
business plan's §7, and the near-zero-opex line in the financial model. Both are worth stating plainly
rather than quietly dropping. The concurrency math ([`ARCHITECTURE.md`](ARCHITECTURE.md#pubsub-not-polling))
shows the actual load is modest — roughly 7,000 concurrent connections at peak target scale — so the
tradeoff costs us hundreds of dollars a month, not thousands.

---

## Backend

### FastAPI + Uvicorn

We hold thousands of long-lived SSE connections. That makes async non-negotiable, which rules out
Flask and traditional Django. FastAPI gives us async throughout, Pydantic v2 validation, and OpenAPI
generation for free — and the OpenAPI schema is the contract for both the frontend and the public
developer API in Phase 2.

**Rejected:** Flask/Django (sync-first, wrong concurrency model), Litestar (credible, smaller
ecosystem), Starlette alone (we'd rebuild FastAPI's validation).

**Consequence:** a blocking call anywhere in a request path stalls every connection on that worker.
No `requests`, no sync DB drivers, no unwrapped CPU-heavy work. Use `httpx` and async SQLAlchemy.

### uv

Astral's package manager. Order-of-magnitude faster than pip/poetry, handles venv + lockfile +
Python version in one tool.

**Rejected:** poetry (slow), pip + requirements.txt (no real lockfile), pipenv (effectively dead).

### stdlib `email` for MIME parsing

**This is where Python genuinely beats the Node ecosystem.** `BytesParser` with `policy.default`
handles multipart nesting, transfer encodings and charset edge cases correctly, and it is maintained
as part of Python's security release process. Adding a third-party parser here would add CVE surface
on our most-exposed input path in exchange for nothing.

**Rejected:** `mail-parser` (thin wrapper over the same stdlib), `flanker` (unmaintained).

### nh3 for sanitizing

Python bindings to Rust's `ammonia`. Fast, memory-safe, actively maintained.

**`bleach` is archived and deprecated — never add it.** It is still the top search result and the
most common wrong answer here.

Sanitizing is only half the defence; see [`SECURITY.md`](SECURITY.md#1-untrusted-email-html).

### Redis for ephemeral messages

Messages are born to die. `SETEX` gives TTL expiry as a native primitive — no cron, no vacuum, no
deletion pass we could get wrong and leave a month of user mail on disk. Redis also gives us the
pub/sub fanout and rate-limit counters, so it earns its place three times over.

**Rejected:** Postgres for messages (we'd write the expiry job Redis gives us free), in-memory state
(breaks the moment we run more than one app server), Memcached (no pub/sub, no persistence option).

### PostgreSQL + SQLAlchemy 2.0 + Alembic

For the small durable surface: domain pool, API keys, aggregate counters. SQLAlchemy 2.0's async
support is mature and its typing is genuinely good now.

**No message content ever lands in Postgres.**

### sse-starlette + Redis pub/sub

The data flow is one-way, server → client. SSE gives us that over plain HTTP with automatic browser
reconnection and no protocol upgrade to shepherd through proxies. `EventSource` is native — no client
library, no bundle cost.

Because any app server may hold the connection while any other consumes the mail, fanout **must** go
through Redis pub/sub rather than in-process state.

**Rejected:** WebSockets (bidirectional channel we have no use for; more proxy friction), long-polling
(same connection cost, worse latency, more complexity), interval polling (~800 req/s of empty
responses at target scale).

### ARQ for background jobs

Async-native and Redis-backed, so it shares infrastructure we already run. Domain blacklist checks,
pool rotation, aggregate rollups — nothing on the critical path.

**Rejected:** Celery (heavier than this workload justifies, sync-first), cron (no retries, no visibility).

### Ruff + mypy + pytest

Ruff replaces black, isort and flake8 in one fast tool. mypy strict on `app/`. pytest with
`pytest-asyncio` and `httpx.AsyncClient`.

---

## Frontend

### Next.js 15, App Router

The frontend has two very different jobs: ~50,000 static SEO pages (2,000 keywords × 25 languages)
and one highly interactive real-time inbox. Next.js does both — SSG for the pages, client components
for the inbox — without running two frameworks.

**Rejected:** Astro (excellent for the static half, awkward for the interactive half), SvelteKit
(smaller ecosystem, and ad-tech integrations assume React), plain SPA (fatal for SEO, and SEO is the
entire traffic strategy).

**Watch this:** building 50,000 pages at once is a real build-time cost. If full SSG becomes
intractable, fall back to ISR for the long tail while keeping the top keywords statically generated.
This is the most likely place the frontend plan needs to bend.

### Tailwind v4 + shadcn/ui

Tailwind ships zero runtime — relevant because [CWV are revenue mechanics](../CLAUDE.md#rule-5-protect-core-web-vitals),
not polish. shadcn/ui gives accessible Radix primitives as code we own rather than a dependency we fight.

**Rejected:** CSS-in-JS with a runtime (styled-components, Emotion) — costs us LCP. MUI/Chakra —
heavy bundles, hard to slim down.

### Hosting

Cloudflare in front for CDN, WAF and Turnstile. Origin on Hetzner or Fly.io.

**Note on Vercel:** its bandwidth pricing at 21M sessions/month would materially damage the margin
model. Not a fit for an ad-supported product at this volume.

---

## Cost model

Rough monthly figures. The business plan's projections are optimistic in ways worth naming.

| | Year 1 (~1.8M sessions/mo) | Year 3 (~21M sessions/mo) |
|---|---|---|
| App servers | ~$40 (1× CPX31) | ~$150 (3× CPX41) |
| Postgres | ~$20 | ~$60 (managed) |
| Redis | ~$15 | ~$50 |
| Mail server (Postfix) | ~$10 | ~$40 |
| Object storage | ~$5 | ~$25 |
| Cloudflare | $0–20 | ~$200 (Pro/Business) |
| Domain pool (25–50) | ~$150 | ~$1,100 |
| Sentry, monitoring, SEO tools | ~$100 | ~$400 |
| **Total infra** | **~$350–400** | **~$2,000–2,500** |

Against the plan's projected $279k/mo gross revenue at Year 3, infrastructure is not the risk. The
risks are on the revenue side:

- **eCPM assumptions.** $2.80–$3.50 blended on anonymous, global, adblock-heavy, largely cookieless
  privacy-tool traffic is optimistic. Temp-mail users are among the least addressable audiences on
  the internet — that is precisely why they are here.
- **Ad network approval.** The plan assumes direct Google AdX access. In practice a new site in this
  category will likely need a Google Certified Publishing Partner / MCM intermediary, which takes a
  revenue share.
- **Programmatic SEO exposure.** 50,000 templated permutation pages is the exact pattern Google's
  scaled-content-abuse and doorway-page policies target. Each page needs genuine standalone utility,
  not just a swapped keyword.

None of these change the *stack*. All three should be validated before the full $18k build spend —
see [`ROADMAP.md`](ROADMAP.md).

---

## Rejected wholesale

| | Why not |
|---|---|
| Cloudflare Workers backend | Covered above — team fit, ingest economics, platform risk |
| Serverless (Lambda/Cloud Run) | Long-lived SSE connections are a poor fit for per-request billing |
| Kubernetes | Wildly disproportionate for a 1–3 person team |
| GraphQL | A handful of endpoints. REST + OpenAPI is less machinery |
| MongoDB | No document-shaped problem here. Redis + Postgres cover both access patterns |
| Microservices | One backend, one frontend. Split when there is a reason, not before |
| Django | Sync-first ORM and request model fight the concurrency requirement |
