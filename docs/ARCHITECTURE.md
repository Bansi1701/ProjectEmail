# Architecture

How a message travels from a stranger's SMTP server to a pixel on the user's screen.

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
                 │  Postfix  (catch-all virtual transport)          │
                 │  · SPF / DKIM / DMARC verification               │
                 │  · size limits, connection + rate caps           │
                 └────────────────────────┬─────────────────────────┘
                                          │  LMTP
                                          ▼
                 ┌──────────────────────────────────────────────────┐
                 │  Python mail consumer   (app/mail/)              │
                 │  1. parse MIME      stdlib email.BytesParser     │
                 │  2. resolve inbox   does this address exist?     │
                 │  3. sanitize HTML   nh3, strict allowlist        │
                 │  4. extract OTP     regex ladder                 │
                 │  5. store           Redis SETEX  (TTL 10–60m)    │
                 │  6. publish         Redis PUBLISH inbox:{id}     │
                 └────────────────────────┬─────────────────────────┘
                                          │
                    ┌─────────────────────┴─────────────────────┐
                    ▼                                           ▼
        ┌────────────────────────┐                 ┌────────────────────────┐
        │  Redis                 │                 │  PostgreSQL            │
        │  · messages (TTL)      │                 │  · domain pool         │
        │  · pub/sub fanout      │                 │  · API keys            │
        │  · rate-limit counters │                 │  · aggregate counters  │
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

**The metric that matters:** time from SMTP `DATA` accepted to the message appearing in the user's
open tab. Target **p95 < 2 seconds**. Everything above is shaped by that number — it is why the
consumer publishes to pub/sub rather than the client polling, and why messages live in Redis rather
than Postgres.

---

## Why these shapes

### Redis for messages, Postgres for everything else

Messages are born to die. Redis `SETEX` gives us TTL expiry as a native primitive — no cron job, no
vacuum, no deletion pass, no risk of a bug leaving user mail on disk for a month. Postgres holds only
what must outlive a session: the domain pool, API keys, and aggregate counters that contain no
message content.

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

Because any app server may hold the connection while any other consumes the mail, the fanout **must**
go through Redis pub/sub rather than in-process state. This is the constraint that stops us from
scaling horizontally by accident and then wondering why some users never see their mail.

### SSE, not WebSockets

The data flow is entirely server → client. SSE gives us that over plain HTTP, with automatic browser
reconnection and no protocol upgrade to shepherd through proxies and CDNs. `EventSource` is native —
no client library. WebSockets would add a bidirectional channel we have no use for.

### Postfix in front of Python

Postfix has spent decades absorbing the SMTP protocol's edge cases and abuse patterns. It handles
protocol negotiation, connection limits, size caps and flood control, then hands our consumer clean
messages over LMTP. Writing that in Python would be re-implementing a solved problem badly, on the
one surface most exposed to hostile input.

In development, `aiosmtpd` on `:1025` stands in — no Postfix needed to run locally.

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
5. **Store** — `SETEX message:{inbox_id}:{msg_id}` with the inbox's TTL.
6. **Publish** — `PUBLISH inbox:{inbox_id}` with a lightweight envelope, not the full body. Clients
   fetch the body over REST when they open the message.

### `backend/app/api/v1/` — the API

Thin routers. Validate, delegate to `app/services/`, return a Pydantic schema. No business logic and
no ORM objects returned directly.

### `backend/app/services/` — business logic

`inbox` (creation, address generation, possession tokens), `domains` (pool health, rotation),
`sanitize`, `otp`. This is where the testable logic lives.

### `backend/app/workers/` — ARQ jobs

Domain blacklist checks, pool rotation, aggregate rollups. Nothing here is on the critical path.

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

`infra/docker/compose.yml` brings up Postgres, Redis, MailHog, the API and the web app. MailHog
receives on `:1025` and gives a web UI on `:8025` — send a message there and watch it appear in the
inbox. No real domains, no real mail, no risk.
