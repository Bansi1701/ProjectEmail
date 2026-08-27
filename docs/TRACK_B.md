# Track B — Product and Growth

Track B owns the public website, browser product experience, design system, accessibility,
SEO/GEO foundations, content operations, consent surfaces, and policy-safe monetization UI. It
consumes Track A's API and security contracts without weakening or reinterpreting them.

## Live baseline audit — 2026-08-27

The deployed GitHub Pages site was a centered placeholder with one heading and no links, generator,
canonical, crawl directive, trust evidence, product states, or substantive publisher content. The
FastAPI liveness and Neon readiness endpoints were healthy during the audit.

The live create-inbox endpoint returned `503 no domain available` during the post-build smoke test.
Track B handles that state without inventing an address, but inbox creation will remain unavailable
until Track A activates and verifies a receiving domain in the production database.

| Area | Baseline | First implementation |
|---|---|---|
| Product action | No action available | One-click create flow connected to the live API |
| Private state | No browser session | Possession token held in `sessionStorage`, never page metadata or analytics |
| Inbox | No route | Noindex client route with address copy, expiry, SSE state, messages, OTP copy and delete |
| Design | Placeholder gray shell | Versioned navy/slate/teal tokens from the approved roadmap |
| Accessibility | Minimal semantic HTML | Skip link, visible focus, live regions, 44px actions, reduced-motion support |
| SEO | Title and description only | Canonical, Open Graph, robots, sitemap, visible answer-first copy and JSON-LD |
| GEO | No crawlable answers | Direct product/security answers, explicit limits, stable entity and GitHub links |
| Monetization | None | Correctly remains absent from home/inbox while approval and route policy are unresolved |

## Active foundation sprint

- [x] Audit the live site, metadata, route structure and current frontend.
- [x] Implement ProjectEmail design tokens and responsive page primitives.
- [x] Replace the placeholder with the homepage generator and trust/content sections.
- [x] Connect inbox creation to the deployed API without logging or persisting sensitive fields.
- [x] Add private inbox states: restoring, live-empty, reconnecting, message, OTP and expired.
- [x] Add user-confirmed immediate deletion and browser-state cleanup.
- [x] Add canonical metadata, SoftwareApplication JSON-LD, robots and sitemap.
- [x] Add session-state unit tests and run them in CI.
- [ ] Generate TypeScript contracts directly from the checked-in FastAPI OpenAPI document.
- [ ] Build the sandbox-origin message viewer and warning interstitial after Track A's CSP endpoint.
- [ ] Add privacy, security, abuse, status, terms and cookies pages after ownership/legal inputs exist.
- [ ] Add browser E2E at 390/768/1440 plus Lighthouse budgets.
- [ ] Conduct 10 observed tester sessions before changing copy based on opinion alone.

## Route policy

| Route | Indexing | Ads | Sensitive data rule |
|---|---|---|---|
| `/` | Index | None during private alpha | Generator events must never include address or token |
| `/inbox/` | Noindex, nofollow, noarchive | Never Google ads | Token exists only in browser session memory/storage and API requests |
| Future guides/docs | Index after substantive review | Eligible only after approval/consent | No inbox or message fields |
| Future sandbox/message origin | Noindex plus robots disallow | Never | Isolated origin, no app cookies or analytics |

## Next Track B slice

1. Export and check in the FastAPI OpenAPI schema; generate frontend types and add a CI drift gate.
2. Add browser tests for create/copy/reconnect/expiry/delete and mobile keyboard navigation.
3. Build complete security/privacy/abuse/status pages from verified operating facts.
4. Add the first four original cornerstone guides only after the custom-domain decision.
5. Configure Search Console, Bing Webmaster Tools and IndexNow after canonical-host migration.
