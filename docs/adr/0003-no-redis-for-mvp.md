# ADR 0003 — No Redis for the MVP

**Status:** Accepted · **Date:** 2026-08-27 · **Supersedes part of [ADR 0001](0001-python-fastapi-over-cloudflare-workers.md)**

## Context

The original design put messages in Redis for three reasons: native TTL expiry, pub/sub
fanout to SSE connections, and rate-limit counters. All three are real needs at scale.

None of them are load-bearing at MVP volume, and Redis is a service to provision, secure and
pay for. The team is pre-revenue with a working local stack and no deployment yet.

## Decision

**Ship the MVP without Redis.** Messages live in Postgres (Neon); fanout is in-process.

## Rationale

| Job | Redis | MVP replacement |
|---|---|---|
| TTL expiry | `SETEX` | `expires_at` column. Reads filter on it, so correctness never depends on a sweeper; a periodic delete keeps the table from growing |
| Pub/sub fanout | Native | `app/services/events.py` — an in-process asyncio broker |
| Rate limiting | Atomic counters | In-process at this volume |

One less service to run, secure and pay for, on a stack that has not proven its business
model yet.

## Consequences

**The constraint this creates:** in-process fanout works only within a single process. With
two workers, a webhook landing on worker A while the user's SSE stream is held by worker B
means that user never sees their mail — and it is invisible in local testing with one worker.

**`WEB_CONCURRENCY` must therefore be 1.** This is enforced in `render.yaml` and documented
at the top of `events.py`. On Render's free 0.1 CPU a single async worker is the right shape
regardless; async Python holds thousands of idle SSE connections in one process comfortably.

**What this costs:** Postgres write churn that Redis would absorb better, and Neon bills by
compute time. Irrelevant at thousands of messages/month, material at millions.

**Deliberately kept cheap to reverse.** `EventBroker` has a two-method interface —
`subscribe` and `publish`. Swapping in Redis pub/sub is one module, not a refactor.

## When to revisit

Any one of these:
- More than one worker or server is needed
- Write volume makes Neon's compute billing noticeable
- Rate limiting has to be shared across processes

## Alternatives considered

| Option | Why not now |
|---|---|
| Redis (Upstash free tier) | Another service and signup for no MVP gain. Also unverified whether their free tier supports blocking `SUBSCRIBE` from asyncio — several serverless Redis products are HTTP-only, which would break the design outright |
| Postgres `LISTEN`/`NOTIFY` | Works, and survives multiple workers. But Neon's pooled endpoint runs PgBouncer in transaction mode, which does not support it — it would need the direct endpoint plus a dedicated held connection, which fights Neon's scale-to-zero |
| Keep Redis anyway | Provisioning a service the MVP does not need, before the model is proven |
