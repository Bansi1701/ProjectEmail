# ADR 0004 — Inbound mail gateway contract

**Status:** Accepted for MVP · **Date:** 2026-08-27

## Context

The API is hosted as an HTTPS web service and cannot accept SMTP on port 25. ProjectEmail still
needs a narrow, replaceable boundary between internet mail delivery and the application. Choosing
a mail-routing vendor must not spread provider-specific payloads through the parser or data layer.

## Decision

For the MVP, **Cloudflare Email Routing plus an Email Worker is the inbound gateway**. The Worker
receives mail for a catch-all domain and posts one normalized request to:

```
POST /api/v1/webhook/inbound
X-Webhook-Secret: <secret>
Content-Type: application/json

{"to": "inbox@example.test", "sender": "sender@example.test", "raw": "<RFC 5322>"}
```

The FastAPI route accepts only the normalized contract. It does not know Cloudflare event types.
The raw RFC 5322 message is parsed once, inside `app/mail/`. The shared secret is stored only in
the Worker secret store and the API host secret store, compared in constant time, and never logged.
HTTPS is mandatory.

Response semantics deliberately reveal no inbox existence:

| Result | Response |
|---|---|
| Delivered to a live inbox | `202 {"status":"delivered"}` |
| Unknown, expired, or capped inbox | `202 {"status":"dropped"}` |
| Missing or wrong secret | `401` |
| API has no webhook secret configured | `503` |

## Security and reliability gates

Before public beta, the gateway must also have:

- a hard request-size limit at Cloudflare and the API proxy;
- a stable delivery/event identifier and one-inbox-TTL idempotency window so retries do not create
  duplicate messages;
- a timestamped signature or an equivalently strong provider-native signature when the provider
  offers one;
- metrics for accepted, dropped, rejected, duplicate, oversized, and parse-failed deliveries;
- a tested dual-secret rotation window and a written rollback procedure.

The current shared-secret control authenticates the gateway but does not by itself provide replay
protection. That limitation is accepted only for the private MVP and is tracked as a public-beta
exit gate, not silently treated as complete.

## Provider portability

A different inbound provider may replace Cloudflare if it is more reliable or contractually safer.
That change belongs in the edge adapter. The application contract, parser, inbox service, and
message model remain unchanged unless a new ADR says otherwise.

## Consequences

- Render remains suitable for the API despite not exposing SMTP.
- Provider-specific code stays outside the core application.
- The MVP has one clear ingestion path and one secret to rotate.
- Public launch is blocked until replay/idempotency and size limits are implemented and tested.

## Alternatives considered

| Option | Why not now |
|---|---|
| Self-hosted Postfix | More portable at scale, but requires a real mail host, port 25, IP reputation, and operations work before the MVP is validated |
| Provider-specific payload in FastAPI | Couples the application to one vendor and duplicates MIME parsing behavior |
| Unauthenticated webhook | Lets anyone inject arbitrary mail into a guessed or stolen inbox address |
