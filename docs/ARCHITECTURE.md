# Architecture

How a message travels from a stranger's SMTP server to a pixel on the user's screen.

> **Living document — v0.1.** Describes the intended design, not a shipped system. Expect this to
> change as real traffic teaches us things. Keep it in sync with the code; when they disagree, the
> code is the truth and this file is the bug.

---

## The critical path

```
                 ┌──────────────────────────────────────────────────┐
  Internet       │  Sender's mail server                            │
    SMTP :25     └────────────────────────┬─────────────────────────┘
                                          │
                  MX records for every domain in the rotating pool
                                          │
                                          ▼
                 ┌──────────────────────────────────────────────────┐
                 │  Cloudflare Email Routing + Email Worker         │
                 │  · catch-all MX and edge abuse controls          │
                 │  · normalize and authenticate webhook request    │
                 └────────────────────────┬─────────────────────────┘
                                          │  HTTPS webhook
                                          ▼
                 ┌──────────────────────────────────────────────────┐
                 │  Python mail consumer   (app/mail/)              │
                 │  1. parse MIME      stdlib email.BytesParser     │
                 │  2. resolve inbox   does this address exist?     │
                 │  3. sanitize HTML   nh3, strict allowlist        │
                 │  4. extract OTP     regex ladder                 │
                 │  5. store           Postgres with expires_at     │
                 │  6. publish         in-process inbox:{id}        │
                 └────────────────────────┬─────────────────────────┘
                                          │
                    ┌─────────────────────┴─────────────────────┐
                    ▼                                           ▼
        ┌────────────────────────┐                 ┌────────────────────────┐
        │  Event broker          │                 │  PostgreSQL            │
        │  · one-process fanout  │                 │  · domain pool         │
        │  · bounded queues      │                 │  · inboxes + messages  │
        │  · no durable content  │                 │  · API keys            │
        └───────────┬────────────┘                 └────────────────────────┘
                    │  SUBSCRIBE
                    ▼
        ┌────────────────────────────────────────────────────────┐
        │  FastAPI  ·  GET /api/v1/inbox/{id}/stream             │
        │  sse-starlette — one open SSE connection per viewer    │
        └───────────────────────────┬────────────────────────────┘
                                    │  text/event-stream
                                    ▼
        ┌────────────────────────────────────────────────────────┐
        │  Next.js client  ·  native EventSource                 │
        │  message list  →  OTP surfaced with one-click copy     │
        └────────────────────────────────────────────────────────┘
                                    │
                                    │  user opens a message
                                    ▼
        ┌────────────────────────────────────────────────────────┐
        │  <iframe sandbox> → content-sandbox.example.com        │
        │  SEPARATE ORIGIN. No ad script can reach it,           │
        │  and it can reach nothing of ours.                     │
        └────────────────────────────────────────────────────────┘
```

**The metric that matters:** time from the edge accepting mail to the message appearing in the
user's open tab. Target **p95 < 2 seconds**. The MVP keeps messages in Postgres and publishes live
notifications through one process; ADR 0003 defines the triggers for adding Redis.

---

## Why these shapes

### Postgres for the MVP lifecycle

Inbox and message rows have `expires_at`. Every read rejects expired data, so a delayed cleanup
pass cannot expose old mail; a supervised sweeper physically deletes expired inboxes and their
cascading messages. This avoids an extra service before traffic earns it. See
[ADR 0003](adr/0003-no-redis-for-mvp.md).

### Pub/sub, not polling

At target scale roughly 8 new sessions per second arrive, each holding a connection for ~5 minutes:

```
21M sessions/mo ÷ 2.59M sec/mo  ≈  8 sessions/sec
× ~300 sec average hold          ≈  2,400 concurrent SSE connections
× ~3 peak factor                 ≈  7,000 concurrent at peak
```

7,000 idle connections is comfortable for async Python across a small number of Uvicorn workers.
Polling those same sessions at a 3-second interval would instead mean ~800 req/s of almost entirely
empty responses. Pub/sub means a worker does nothing at all until a message actually arrives.

The MVP broker is in-process, so **`WEB_CONCURRENCY` must remain 1**. Multiple workers or instances
require shared pub/sub before they are enabled; otherwise a webhook can land in a different process
from the user's stream and the notification disappears.

### SSE, not WebSockets

The data flow is entirely server → client. SSE gives us that over plain HTTP, with automatic browser
reconnection and no protocol upgrade to shepherd through proxies and CDNs. `EventSource` is native —
no client library. WebSockets would add a bidirectional channel we have no use for.

### An edge gateway in front of Python

Cloudflare Email Routing accepts public SMTP and an Email Worker forwards a small normalized HTTPS
request. FastAPI remains provider-neutral and owns MIME parsing. The boundary, authentication,
response semantics and public-beta hardening gates are in
[ADR 0004](adr/0004-inbound-mail-gateway-contract.md).

---

## Components

### `backend/app/mail/` — the consumer

The only component that touches untrusted input. Order matters:

1. **Parse** — `email.BytesParser(policy=policy.default)`. Handles multipart, transfer encodings and
   charsets correctly.
2. **Resolve** — does this address correspond to a live inbox? If not, drop immediately. Never store
   mail for an address nobody is watching; that is how a temp-mail service becomes a spam archive.
3. **Sanitize** — `nh3` with a strict allowlist. Strip `<script>`, `<style>`, event handlers, `<form>`,
   `<iframe>`, `<object>`. Rewrite links to pass through an interstitial. Remote images are proxied or
   blocked — see [`SECURITY.md`](SECURITY.md).
4. **Extract OTP** — an ordered regex ladder, most-specific first. Codes near words like *code*,
   *verification*, *OTP*, *PIN* beat bare digit runs. Every pattern is bounded to prevent ReDoS.
5. **Store** — a Postgres message row sharing the inbox's `expires_at`.
6. **Publish** — publish to the in-process `inbox:{inbox_id}` channel with a lightweight envelope,
   not the full body. Clients
   fetch the body over REST when they open the message.

### `backend/app/api/v1/` — the API

Thin routers. Validate, delegate to `app/services/`, return a Pydantic schema. No business logic and
no ORM objects returned directly.

### `backend/app/services/` — business logic

`inbox` (creation, address generation, possession tokens), `domains` (pool health, rotation),
`sanitize`, `otp`. This is where the testable logic lives.

### `backend/app/workers/` — supervised jobs

The MVP runs a supervised expiry sweep in the API lifespan. Shared/background workers arrive with
Redis when domain checks, pool rotation and aggregate rollups need retries and horizontal scale.

### `frontend/src/`

- `app/` — routes. The inbox is a client component; the ~50k pSEO pages are statically generated.
- `components/inbox/` — message list, viewer, OTP copy control.
- `components/ads/` — ad slots. **Every slot reserves its dimensions before the ad loads** ([CLAUDE.md Rule 5](../CLAUDE.md#rule-5-protect-core-web-vitals)).
- `components/seo/` — templates for the programmatic landing pages.

---

## The domain pool

Third-party sites actively blacklist known temp-mail domains, so domains are consumable inventory
rather than fixed identity.

**Two categories, and conflating them would be a serious mistake:**

| | Brand domain | Mail domains |
|---|---|---|
| Count | 1, permanent | 20–50, rotating |
| Carries | The site, all SEO pages, all accumulated domain authority | MX records only |
| When blacklisted | Never happens — it receives no mail | Retire and replace |

All SEO equity accrues to the brand domain. Mail domains are disposable and can be burned and
replaced without touching search rankings. A rotation that took the site's pages down with it would
destroy years of SEO work.

Health monitoring watches blacklist APIs and per-domain delivery success. When a domain degrades past
threshold it stops being handed to new inboxes, drains its existing ones, then retires.

---

## Local development

`infra/docker/compose.yml` brings up four services — Postgres, Mailpit, the API and the
web app — with source bind-mounted so both apps hot-reload on edit.

```bash
docker compose -f infra/docker/compose.yml up
```

**Mailpit** receives on `:1025` and gives a web UI on `:8025` for inspecting local fixtures. The
public ingestion path is exercised through the webhook with test RFC 5322 payloads. No real domains
or external mail are required locally.

Every published port is overridable via `infra/docker/.env` — developer machines run other stacks,
and 5432 and 8000 in particular are commonly taken.

Both Dockerfiles are multi-stage: the `dev` stage mounts source and hot-reloads, the `runner` stage
runs non-root with a healthcheck and is what deploys.
