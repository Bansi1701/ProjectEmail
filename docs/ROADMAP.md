# Roadmap

24 weeks to a monetized platform, following the four phases in the business plan, with the budget
and staffing reality made explicit.

**Team assumption:** 1–3 developers. **Dev budget:** $12,000–$18,000.

---

## Before Phase 1 — validate three assumptions

The business model rests on three claims that no amount of good engineering can rescue if they are
false. Each is cheap to test and expensive to discover late.

| Assumption | How to test | Cost | If it fails |
|---|---|---|---|
| An ad network will approve and keep a temp-mail site monetized | Apply to an MCM partner / Google Certified Publishing Partner with the MVP on one domain | ~1 week, $0 | Revenue model needs restructuring — affiliate-first, not display-first |
| Blended eCPM reaches ~$3 on this traffic | Run real ads on real traffic in Phase 3 and measure | Included in Phase 3 | Every number in the financial model moves |
| 50k templated pages survive Google's scaled-content policies | Publish 50 pages, watch indexation for 4 weeks | ~1 week, $0 | pSEO plan restructures around fewer, genuinely useful pages |

Do this concurrently with Phase 1. Do not wait for the answers to start building — but do not commit
the full $18k before the first one comes back.

---

## Phase 1 — Build & Deploy · Weeks 1–4

**Goal:** working MVP on 3 test domains.

- [ ] Repo, Docker Compose (Postgres, Redis, MailHog), CI
- [ ] Postfix catch-all → LMTP → Python consumer (`aiosmtpd` locally)
- [ ] MIME parsing — stdlib `email`, multipart and encodings
- [ ] HTML sanitizing — `nh3`, strict allowlist
- [ ] OTP + verification-link extraction, bounded regex ladder
- [ ] Redis storage with TTL; Postgres schema + Alembic
- [ ] SSE endpoint — `sse-starlette` + Redis pub/sub
- [ ] Next.js inbox UI, mobile-first, one-click OTP copy
- [ ] Sandboxed iframe on a separate origin ([`SECURITY.md`](SECURITY.md#1-untrusted-email-html))
- [ ] Inbox address entropy + possession tokens ([`SECURITY.md`](SECURITY.md#2-inbox-enumeration--the-categorys-classic-breach))
- [ ] 3 domains live with MX; Sentry; spend caps on every metered service

**Exit:** mail arrives in the open tab in **p95 < 2s**. Security rules 1 and 2 verified by test.

> **Budget note.** Weeks 1–4 is realistic for the mail pipeline *or* a polished UI, not comfortably
> both. If it slips, ship a plain inbox UI and keep the pipeline solid — the pipeline is the hard part
> and the UI is cheap to improve later.

---

## Phase 2 — SEO & Traffic Engine · Weeks 5–8

**Goal:** organic traffic engine live.

- [ ] Keyword database + page template system
- [ ] Translation pipeline, 25 languages (LLM translation + native review on the top 5)
- [ ] Static generation — **measure build time early**, fall back to ISR for the long tail if needed
- [ ] hreflang, x-default, canonicals, sharded sitemaps (50k URL / 50MB limits)
- [ ] Search Console + Bing/IndexNow submission
- [ ] Public developer API — rate-limited, OpenAPI, docs site
- [ ] Browser extensions (Chrome, Firefox, Edge) via **WXT**
- [ ] Community seeding: Product Hunt, Hacker News, r/privacy, r/webdev

**Exit:** indexed on Google/Bing/Yandex; 50,000 organic visits/mo.

> **Two warnings.** (1) Start with **50 pages, not 2,000** — confirm they index and rank before
> scaling. Scaled thin content is the failure mode Google's recent policy updates target. (2) The
> plan proposes serving ads inside an extension iframe; verify that against Chrome Web Store and
> Google publisher policy before building it. The compliant pattern is the extension opening a real
> tab on the main domain.

---

## Phase 3 — Ad Ops & Monetization · Weeks 9–14

**Goal:** revenue on.

- [ ] Consent management platform (Google-certified, TCF v2.2) — **before any ad script**
- [ ] Google Ad Manager account (direct or via MCM partner)
- [ ] Prebid.js header bidding, staged SSP onboarding
- [ ] Ad slots with **reserved dimensions** — CLS is revenue ([CLAUDE.md Rule 5](../CLAUDE.md#rule-5-protect-core-web-vitals))
- [ ] Viewability-gated refresh — IntersectionObserver + Page Visibility API, verified against current GAM policy
- [ ] Sticky anchor units (320×50 mobile, 728×90 desktop)
- [ ] Affiliate fallback cards for adblocked sessions (native, not circumvention)
- [ ] Reporting + A/B harness for ad layouts

**Exit:** blended eCPM > $3.00, viewability > 75%, CWV green.

> **This phase is the one most likely to be under-budgeted.** Ad ops is a specialist trade —
> Prebid configuration, SSP onboarding, floor tuning and yield analysis are not general web
> development. Budget for a contractor or expect this phase to run long. It is also where policy
> mistakes are most expensive: a violation can demonetize the whole site.

---

## Phase 4 — Scale & Yield · Weeks 15–24

**Goal:** 500k+ MAU, $15k+/mo net.

- [ ] Domain pool to 20+, automated rotation and blacklist monitoring
- [ ] A/B test ad layouts, refresh timers, sizes
- [ ] Direct affiliate sponsors (VPN, password managers) at $50+ CPA
- [ ] pSEO to 5,000+ terms — **only if Phase 2 pages actually ranked**
- [ ] Horizontal scaling, load testing, cost review
- [ ] Support surface, status page, ops runbook

**Exit:** 500,000+ MAU, $15,000+/mo net cash flow.

---

## Where the budget is short

| Phase | Plan | Realistic | Note |
|---|---|---|---|
| 1 — Build | 4 weeks | 4–6 weeks | Mail pipeline plus polished UI is tight |
| 2 — SEO | 4 weeks | 4 weeks | Achievable if page count starts small |
| 3 — Ad ops | 6 weeks | 6–10 weeks | **Specialist skill set; most likely to slip** |
| 4 — Scale | 10 weeks | 10 weeks | Elastic by nature |

**Cheapest viable proof** — if you want to test the model before committing the full spend:
Phase 1 only, one domain, a single AdSense unit instead of the full Prebid stack, 50 SEO pages in
English. Roughly 4 weeks and a few hundred dollars. It answers the eCPM and ad-approval questions
before you spend $18k finding out.
