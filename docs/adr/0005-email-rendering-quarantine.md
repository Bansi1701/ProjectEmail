# ADR 0005 — Email rendering quarantine

**Status:** Accepted · **Date:** 2026-08-27

## Context

Email HTML is attacker-controlled. Sanitization reduces risk, but HTML parsers and sanitizer
allowlists can fail in surprising ways. Rendering that content in the application origin would put
the user's inbox token, application state, analytics, and future monetization code in the same
security boundary as hostile markup.

## Decision

Rendered email HTML uses a **quarantine origin on a separate registrable domain**, not a subdomain
of the permanent ProjectEmail site and not a rotating mail domain. The viewer embeds it with exactly:

```html
<iframe
  sandbox="allow-popups allow-popups-to-escape-sandbox"
  referrerpolicy="no-referrer"
  src="https://<quarantine-domain>/msg/<opaque-id>">
</iframe>
```

It never receives `allow-scripts`, `allow-same-origin`, `allow-forms`, `allow-modals`, or top-level
navigation. Sanitized HTML is never injected into the trusted parent with `srcdoc` or
`dangerouslySetInnerHTML`.

Every message response on the quarantine origin must send:

```
Content-Security-Policy: default-src 'none'; script-src 'none'; style-src 'unsafe-inline'; img-src 'self' data:; font-src 'none'; form-action 'none'; base-uri 'none'; frame-ancestors <app-origin>; sandbox
Referrer-Policy: no-referrer
X-Content-Type-Options: nosniff
Cross-Origin-Resource-Policy: same-origin
X-Robots-Tag: noindex, nofollow, noarchive
```

Remote images are blocked by default. A future “show images” action may use a hardened proxy only
after SSRF controls, response-size/type limits, redirect limits, and spend limits exist.

Links are rewritten to a warning interstitial on the quarantine registrable domain. They open only
after explicit user action and carry `rel="noopener noreferrer nofollow ugc"`. The interstitial
never auto-redirects or prefetches a destination.

The frame uses a fixed/reserved viewing area with internal scrolling. It does not trust
`postMessage` origin checks: a sandboxed frame without `allow-same-origin` has an opaque origin that
serializes as `null`.

## Consequences

- Sanitization and origin isolation remain independent layers; either can fail without granting
  hostile email access to the application origin.
- A separate quarantine domain and deployment are required before HTML viewing can ship.
- Remote content and verification links require deliberate proxy/interstitial work instead of
  being enabled accidentally.
- A reputation incident on hostile message content is isolated from the permanent site and its
  search reputation.

## Verification gates

- CI rejects `allow-same-origin` in an email iframe.
- Browser tests prove scripts, forms, top navigation, parent DOM access, remote images, and indexing
  are blocked.
- Response-header tests assert the complete CSP and security-header set.
- A sanitizer regression corpus includes raw-text and malformed-markup cases.

## Alternatives considered

| Option | Why rejected |
|---|---|
| Sanitize and render in the app DOM | Treats the sanitizer as the only security boundary |
| `srcdoc` in a sandboxed app-origin iframe | Easy to weaken accidentally and does not provide independent origin/reputation isolation |
| `allow-scripts allow-same-origin` | Removes the effective sandbox boundary |
| Quarantine subdomain under the permanent site | Couples hostile-content reputation to the SEO and application asset |
