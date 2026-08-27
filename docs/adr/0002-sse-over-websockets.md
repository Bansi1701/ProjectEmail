# ADR 0002 — Server-Sent Events over WebSockets

**Status:** Accepted · **Date:** 2026-08-27

## Context

Users open an inbox and wait 3–8 minutes for a verification code with the tab active. Mail must
appear near-instantly. At target scale (~21M sessions/mo) roughly 7,000 connections are open
concurrently at peak.

Options: interval polling, long-polling, WebSockets, or SSE.

## Decision

**Server-Sent Events** via `sse-starlette`, with fanout over **Redis pub/sub**.

## Rationale

- **The data flow is one-way.** Server → client is the entire requirement. WebSockets would add a
  bidirectional channel we have no use for, plus proxy and CDN friction from the protocol upgrade.
- **`EventSource` is native.** No client library, no bundle cost, automatic reconnection with
  `Last-Event-ID` resumption built into the browser.
- **Polling is wasteful here.** At a 3-second interval, target scale means ~800 req/s of almost
  entirely empty responses. Pub/sub means a worker does nothing until mail actually arrives.
- **The load is modest.** ~7,000 idle async connections is comfortable across a few Uvicorn workers.

## Consequences

- **Fanout must go through Redis pub/sub, not in-process state.** Any app server may hold the
  connection while any other consumes the mail. In-process fanout works on one server and silently
  breaks the moment we scale horizontally — some users would simply never see their mail.
- SSE is HTTP, so buffering proxies can delay events. Disable response buffering on the SSE route.
- Browsers cap ~6 connections per origin under HTTP/1.1. HTTP/2 removes this — ensure it is enabled.
- Idle connections need timeouts; drop them when the inbox TTL expires.

## Alternatives considered

| Option | Why not |
|---|---|
| WebSockets | Bidirectional capability we don't need; more proxy friction |
| Long-polling | Same connection cost, worse latency, more complexity |
| Interval polling | ~800 req/s of empty responses; worse UX |
