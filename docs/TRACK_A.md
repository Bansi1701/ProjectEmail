# Track A — Platform and Trust

Track A owns mail ingestion, the FastAPI service, Neon/Postgres data lifecycle, domain operations,
security boundaries, reliability, observability, and infrastructure cost controls. Track B may
consume its HTTP/SSE contracts but does not bypass them.

## Foundation audit — 2026-08-27

| Area | Current state | Next gate |
|---|---|---|
| Repository | `main`, CI for backend/frontend/images, Render and Pages definitions | Require green CI before every deployment |
| Database | Neon-compatible async SQLAlchemy and Alembic; messages have explicit expiry | Exercise migrations against a Neon branch before production changes |
| Inbound mail | Cloudflare Email Worker normalized webhook with constant-time shared-secret check | Add size limits, signed freshness, idempotency, metrics, rotation test |
| Inbox access | Random address plus possession token; expired reads fail closed | Add shared/edge rate limiting and enumeration alerts |
| Erasure | Immediate authenticated delete plus automatic physical expiry sweep | Add integration tests against Postgres and deletion-lag alert |
| Live delivery | In-process SSE broker | Keep exactly one worker until shared pub/sub is introduced |
| HTML safety | Ingest sanitizer and separate-origin iframe contract | Build quarantine service and browser security tests before enabling HTML viewing |
| Operations | Liveness/readiness endpoints and startup migrations on one Render instance | Add structured metrics, SLOs, alerts, backups/restore drill, incident runbooks |
| Documentation | Several original Redis/Postfix descriptions predate the working MVP | Normalize documents to ADR 0003/0004 as implementation changes land |

## Active foundation sprint

- [x] Pull and audit repository, deployment, migrations, tests, secrets, and documentation drift.
- [x] Record the inbound gateway contract in ADR 0004.
- [x] Record the rendering quarantine in ADR 0005.
- [x] Add authenticated immediate inbox deletion.
- [x] Run a supervised expiry sweeper with a configurable interval.
- [x] Make one worker the safe container default while SSE fanout is in-process.
- [ ] Add a Postgres-backed API integration-test fixture.
- [ ] Add webhook size, signature freshness, replay/idempotency, and rotation tests.
- [ ] Add real per-IP/per-token rate limiting; configuration alone is not enforcement.
- [ ] Build and deploy the quarantine-origin renderer.
- [ ] Define SLOs and alerts for delivery latency, error rate, deletion lag, and Neon usage.

## Delivery order

1. **Security and lifecycle:** deletion, expiry, authenticated/idempotent ingress, rate limits.
2. **End-to-end mail path:** gateway Worker, test domain/MX, MIME corpus, live SSE delivery.
3. **Rendering quarantine:** isolated deployment, CSP, interstitial, browser attack tests.
4. **Reliability:** metrics, alerting, backups, restore and secret-rotation drills.
5. **Domain operations:** seed/admin path, health telemetry, drain/retire automation.
6. **Scale only after evidence:** shared pub/sub and additional workers when traffic requires them.

## Model routing for this track

- Architecture, threat boundaries, production UI/security contracts: flagship tier.
- Routine FastAPI implementation, refactoring, tests, migrations, integrations: balanced tier.
- Mechanical documentation and formatting: lightweight tier.

This routing controls effort, not ownership. One change still passes the same review and quality
gates regardless of which tier performs it.
