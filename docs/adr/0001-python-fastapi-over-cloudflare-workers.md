# ADR 0001 — Python/FastAPI over Cloudflare Workers

**Status:** Accepted · **Date:** 2026-08-27

## Context

The source business plan (§7) specifies an all-Cloudflare serverless edge stack: Workers for compute,
Email Routing for ingest, D1/KV for storage, Pages for the frontend. It is a coherent design with a
genuine advantage — near-zero fixed opex and automatic scaling.

We had to choose between adopting it as written and running conventional servers.

## Decision

Build the backend in **Python 3.12 / FastAPI on conventional servers**. Keep Cloudflare for CDN, WAF,
DNS and Turnstile.

## Rationale

1. **Team fit.** The team is Python. A stack the developers are fluent in ships faster and breaks
   less than a theoretically superior one they are learning. This outweighed the other two.
2. **Mail ingest economics.** At ~25M inbound messages/month, hosted inbound-mail pricing is a real
   line item (SES inbound at $0.10/1,000 ≈ $2,500/mo). Self-hosted Postfix is ~$0 marginal — savings
   that exceed the entire server bill.
3. **Platform risk.** Whether a provider's AUP tolerates a public disposable-email service at scale
   is a live question, and a bad answer means account termination rather than migration. Running our
   own SMTP removes the dependency.
4. **MIME parsing.** Python's stdlib `email` module is more mature than anything in the Node
   ecosystem, and it is covered by Python's security release process.

## Consequences

**Accepted costs**
- Real infrastructure: ~$350/mo at Year 1, ~$2,000–2,500/mo at Year 3.
- Capacity planning is now our job. The "scales automatically to 100M requests" property is gone.
- The financial model's near-zero-opex line must be corrected.

**Gained**
- Portability. No single vendor can end the business by enforcing a policy.
- Marginal ingest cost approaching zero at scale.
- A language the team is fast in.

**Load-bearing constraint:** FastAPI must be async throughout. A blocking call in a request path
stalls every SSE connection on that worker.

## Alternatives considered

| Option | Why not |
|---|---|
| Cloudflare Workers as specified | Above |
| Hybrid — CF Email Routing → FastAPI webhook | Keeps the AUP dependency for the least portable component |
| Node/TypeScript on servers | Loses the stdlib MIME advantage and the team's fluency |
| AWS Lambda + SES | Long-lived SSE connections fit per-request billing poorly |
