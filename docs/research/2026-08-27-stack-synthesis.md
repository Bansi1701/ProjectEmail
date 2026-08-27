# Stack Research — Full Synthesis (2026-08-27)

> **Archived research output. Read [`../VALIDATION.md`](../VALIDATION.md) first** — it summarises what
> matters and puts these findings in context.
>
> ⚠️ **Two caveats before you use this document.**
>
> 1. **It recommends the Cloudflare Workers stack.** We chose Python/FastAPI instead — see
>    [ADR 0001](../adr/0001-python-fastapi-over-cloudflare-workers.md). The deciding factor was team
>    fit, which this analysis could not weigh. Sections 2.x below describe a stack we are **not**
>    building; read them for the reasoning, not the recommendations.
> 2. **The policy quotations and prices are unverified research**, produced by AI agents searching the
>    web. Check anything against primary sources before it drives a spending decision.
>
> What transfers directly regardless of stack: the revenue analysis (§3), the ad-policy blockers, the
> pSEO spam-policy risk, the security findings, and the week-0 approvals checklist.

---

# NextGen TempMail — Definitive Tech Stack Recommendation

**Lead architect decision record. Supersedes section 7 of the business plan. Every conflict between the seven layer designs is resolved here with one default.**

---

## 1. Verdict on the doc's own stack (section 7)

The proposed architecture is **substantially correct and unusually well-chosen for the budget**. Cloudflare Email Routing → Email Worker → edge storage → Cloudflare-hosted frontend is the right spine, and no reviewed alternative beats it on cost, latency, or operational load for a 1–3 dev team. Keep it.

| Section 7 item | Verdict |
|---|---|
| Cloudflare Email Routing catch-all → Email Worker | **KEEP.** Inbound is free at any volume; Cloudflare performs SPF/DKIM/DMARC/RBL rejection at SMTP before you are billed. Verified: no ToS clause prohibits disposable email. |
| Workers (TypeScript) as edge compute | **KEEP**, but Workers **Paid ($5/mo) is mandatory** — Email Workers on Free hit `EXCEEDED_CPU` at 10ms and silently lose messages. |
| "Upstash Redis **OR** Cloudflare D1, 10–60 min TTL, zero cron jobs" | **REPLACE.** D1 has no TTL and is a sequential single-writer (~1,000 qps/db); KV is eventually consistent up to 60s, which is fatal for "OTP appears now". Use **one SQLite-backed Durable Object per inbox + DO `alarm()`**. |
| "SSE **or** WebSockets" | **RESOLVE — this is a company-killer as written.** See BLOCKER 1. |
| Next.js on Cloudflare Pages | **CHANGE** to **Astro 7 on Cloudflare Workers Static Assets.** Cloudflare's own docs say "Start new projects with Workers"; Next.js 16 emits ERR at 200k static pages and 1.84 GiB at 100k vs Astro's 46.8 MiB. |
| Sandboxed iframe for email HTML | **KEEP the control, FIX the config.** The doc's implied `allow-same-origin` is a total sandbox escape. See BLOCKER 3. |
| Strictly inbound-only relay | **KEEP.** Best single decision in the plan. Enforce structurally (no `send_email` binding, zero verified destination addresses). |
| Prebid.js + GAM/AdX, 35s viewability-gated refresh | **CHANGE.** See BLOCKERS 4 and 5. |
| 2,000 pSEO pages × 25 languages | **CHANGE.** See BLOCKER 6. |

### Blockers the founder must read before writing a line of code

**BLOCKER 1 — SSE held on a Durable Object is a ~$10,000/mo line item and a $5,760/hour attack primitive.**
Cloudflare bills DO duration at $12.50/M GB-s against a flat 128 MB whenever the object holds an in-flight request. An SSE `ReadableStream` returned from a DO *is* an in-flight request, so the object can never hibernate. 21M sessions × 300s × 0.128 GB = **806M GB-s = $10,075/mo**. The same design lets an attacker hold 1M idle connections for one hour for $5,760 of *your* money — Cloudflare budget alerts are documented as informational only and do not cap spend. The fix is one API call: `state.acceptWebSocket(ws)` (Hibernation API), which drops the same workload to ~$65/mo. **This is invisible at MVP scale (~$176/mo at Month 6), so it will pass every early review and detonate in Year 2.**

**BLOCKER 2 — The public API as specified reads any inbox by address alone, cancelling the entire access-control model.**
`GET /v1/inboxes/{address}/messages` on a keyless tier is a mass-OTP-disclosure endpoint, because handing the address to a third party *is the product* — the signup site, its ESP, every middlebox and every data broker downstream has it. `wait?match=otp` is worse: a purpose-built OTP-harvesting primitive. Reads must be keyed on an opaque `inbox_id` + a 128-bit `read_token`, never on the address.

**BLOCKER 3 — The iframe contract is specified four incompatible ways and two do not work.**
`allow-same-origin` + `allow-scripts` lets the frame delete its own `sandbox` attribute (two lines of JS). `sandbox=""` with zero tokens silently breaks the verification-link click, which is the core product function. One config only (§3.3).

**BLOCKER 4 — The inbox screen is a written AdSense placement violation.**
Verbatim: *"Publishers may not place Google ads alongside email messages when they are the primary focus of the page"* and *"may not place Google ads on screens where private communication between people is the primary focus."* The sandboxed iframe addresses a *different* policy (ad adjacency to UGC) and confers zero protection here. Enforcement is demonstrably lax (guerrillamail.com runs AdSense today), but 100% of revenue rides on an enforcement lottery with no subscription floor.

**BLOCKER 5 — The 35s timer refresh is prohibited under AdSense, and AdX is unobtainable at launch.**
Verbatim: *"Publishers are not permitted to refresh a page or an element of a page without the user requesting a refresh."* The 30s declared-refresh regime exists only in Google Ad Manager, and direct AdX access is not granted to new publishers — it requires a Google Certified Publishing Partner or an MCM "Manage Inventory" parent. During Phases 1–3 the 3.8 impressions/session assumption is unreachable.

**BLOCKER 6 — 2,000 × 25 locales matches two named Google spam policies simultaneously.**
Scaled content abuse *and* doorway abuse, plus the separate clause naming *"text translated by an automated tool without human review"* as spam. Google Publisher Policies apply the same low-value test to ad eligibility, so one determination removes ~50% of traffic and the primary demand source together.

**Consolidated revenue reality:** $2.80–3.50 blended eCPM is a tier-1, cookied, contextual-content number. This inventory is India-dominant, unaddressable, 40–55% adblocked, zero-context. Realistic Year-3 gross is **$15k–40k/mo, centred ~$22k**, against the plan's $279k/mo — 5–14% of plan, before an 15–20% MCM revenue share. **The 96.8% margin claim fails on the numerator, not the denominator.** Infrastructure is ~$1,150/mo either way.

---

## 2. The stack

### 2.1 Domains, DNS, registrars

| Concern | Recommendation | Why | Fallback |
|---|---|---|---|
| Brand domain | One `.com`, registered at **Cloudflare Registrar** (at-cost, API beta), separate account from the pool | seo layer: the pool is *designed* to be blacklisted; the ranking asset must never inherit it. Never link brand → pool, not even as an anchor | Porkbun |
| Mail pool (20–50) | **Porkbun API v3** primary, **NameSilo** secondary. `.xyz .online .email .site`; avoid `.top` where possible | Only registrar in this segment with a real API + `pk1_sb_` sandbox + per-account spend cap. Splitting registrars prevents one compliance suspension killing the whole pool | Dynadot |
| Render + link-interstitial origin | **Two separate registrable domains** (distinct eTLD+1, two registrars, two TLDs), client-side failover, **kept off the mail rotation** | A subdomain of the brand shares the cookie jar with the ad-bearing app and inherits Safe Browsing listings. This is a quarantine zone | — |
| DNS + Email Routing provisioning | Terraform `cloudflare/cloudflare` v5.24.0, `for_each` over a domain list in one JSON file | `cloudflare_email_routing_settings` / `_dns` / `_catch_all` all exist in v5. Domain #37 is a one-line PR | Cloudflare API script |
| Pool DNS posture | MX `route1/2/3.mx.cloudflare.net`; **SPF `v=spf1 -all`**; **DMARC `p=reject`**; TTL 300s | You never send. `-all` (not `~all`, which the wizard proposes) tells every MTA the domain never originates mail, slowing reputation decay and answering registrar abuse desks | — |
| Publishing the pool | **Publish burned/retired domains only.** `GET /v1/domains` returns 3–5 rotated actives | Resolves the infra/seo/api-ext vs data conflict. amieiro's feed regenerates every 15 min and groundcat validates by MX scan — publishing actives converts domain life from months to days | — |

### 2.2 Inbound mail, MIME, sanitization, OTP

| Concern | Recommendation | Why | Fallback |
|---|---|---|---|
| Ingest | Cloudflare Email Routing catch-all → Email Worker, **Workers Paid** | $0/message vs $6,829/mo (SES) and $41–45k/mo (Postmark/Mailgun) at Year-3 volume. Free SPF/DKIM/DMARC/RBL rejection at SMTP | SES inbound + Lambda — keep written and tested |
| MIME parser | **`postal-mime` 2.7.6, pinned exactly.** Always pass `maxNestingDepth` + `maxHeadersSize` | AIKIDO-2026-10419 affects 1.0.1–2.7.3. 3.0.0 (2026-08-11) changes duplicated single-value headers last-wins → first-wins — a security-relevant change on a hostile-input path. Upgrade in Phase 4 behind a regression corpus | `mail-parser` (Rust) WASM, Phase 4 |
| Sanitizer | **`sanitize-html` 2.17.7, pinned.** Week-1 go/no-go spike: bundle, `wrangler deploy --dry-run --outdir dist`, measure CPU on a 500 KB HTML email | Pure JS, no DOM shim. DOMPurify cannot run in Workers (`window is not defined`); `isomorphic-dompurify` drags jsdom | **If the spike fails: render `text/plain` only with linkification.** Do *not* hand-roll an HTMLRewriter allowlist — a streaming rewriter never builds a tree and is structurally blind to the mXSS/raw-text re-parse class that produced CVE-2026-44990 |
| Strip list | `script style iframe object embed applet form input button link meta base svg math template noscript` **+ `xmp plaintext listing noembed noframes title frameset frame portal`** | The four proposed lists all omit the raw-text elements where the 2026 sanitize-html CVEs live | — |
| Remote images | **Blocked by default.** Rewrite `src`/`srcset`/`background` → `data-blocked-src`; CSP `img-src 'self' data:`; strip `url()` `@import` `expression()` `image-set()` from `<style>` *and* inline `style` | Privacy is the product; tracking pixels confirm the address is live, which accelerates pool burn; and `font-src https:` / CSS `url()` are read-receipt channels no `src` rewriter touches | — |
| Image proxy | **Defer to Phase 3.** When built: scheme+port allowlist, DoH resolve with RFC1918/loopback/CGNAT/link-local/own-IP rejection, `redirect:'manual'` 1 hop, 20 images/msg, 2 MB cap, magic-byte sniff, forced `Content-Type`, `nosniff` | As specified in the layer designs it is an unbounded SSRF and traffic reflector. OTP mail is essentially never image-only | Ship without it |
| Link handling | Rewrite every `href` through an interstitial on the **quarantine domain** (not `link.brand.com`), HMAC bound to message id and expiring with the inbox, destination reputation check, per-destination-domain rate limit, `rel="noopener noreferrer nofollow ugc"`, **never prefetch** | Otherwise you sign attacker-chosen destinations with your own key on the domain carrying your SEO and ad account. Prefetching burns single-use verification links — the most common bug in this category | — |
| OTP extraction | **Scored regex + structural heuristics in the Worker (<1ms).** NFKC normalise, fold Arabic-Indic/Devanagari digits, operate on decoded text only, cap input at **256 KB** | An LLM on 100% of mail is $22,359/mo (Haiku) or $2,748/mo (Workers AI) at Year-3 volume, and adds 300–1500ms. Corpus is narrow: >80% of volume from <500 sender domains | Workers AI `llama-3.1-8b-fp8`, gated to <5% of misses, hard Neuron cap |
| Extraction training data | **First-party fixture corpus** — sign up to the top ~200 target services with your own inboxes, capture raw MIME into a private repo (3–5 days). Production misses persist a *structural fingerprint only* (sender domain, DKIM `d=`, redacted token-shape mask, block position) | Tuning the extractor on user mail contradicts the zero-retention posture. This is the only legally clean source. Offline Claude Haiku 4.5 Batch mines new regex templates from the corpus | — |
| Attachments | **Drop bytes. Persist metadata only** (filename, MIME, size, SHA-256) through Phase 3 | Cloudflare provides no malware scanning and explicitly disclaims it; ClamAV cannot run in a Worker; serving unscanned binaries next to AdSense is an account-termination and 24h-abuse-response problem | R2 + 1 MB cap + hard MIME allowlist, Phase 4 only |
| Header hygiene | Strip `Authentication-Results`, `Received-SPF`, `DKIM-Signature`, `ARC-*` from anything shown or returned. Strip bidi controls (U+202A–202E, U+2066–2069) and zero-width chars from filenames/subjects/display names; NFKC normalise; always render the envelope address, never the display name alone | Cloudflare exposes **no** auth result to the Worker; parsing `Authentication-Results` yields a forgeable "verified sender" badge. `invoice‮fdp.exe` renders as `invoiceexe.pdf` | — |

### 2.3 Compute, storage, TTL, real-time

| Concern | Recommendation | Why | Fallback |
|---|---|---|---|
| Real-time transport | **WebSocket accepted via `state.acceptWebSocket()` (Hibernation API)** on a per-inbox DO. `setWebSocketAutoResponse()` for keepalive (explicitly not billed for wall-clock). Answer heartbeats in the Worker so they never hit the 20:1 inbound-message meter | See BLOCKER 1. Outgoing messages and protocol pings are free; hibernated objects accrue no duration | SSE held on a **plain Worker** (billed on CPU, not wall-clock) that holds a hibernatable WS to the DO — ship as automatic fallback for the ~1–3% behind WS-hostile proxies. Interval polling never |
| Ephemeral store | **One SQLite-backed DO per inbox**, addressed `idFromName(hex(HMAC-SHA256(SERVER_SECRET, lower(address))))` | Store + CAS point for address claiming + fanout hub in one primitive, auto-sharded. KV disqualified on 60s eventual consistency incl. cached negative lookups | Upstash Redis only if DOs prove a team comprehension barrier |
| Schema discipline | **One row per message.** Never per-header KV puts, no secondary indexes | Rows-written is the one meter that scales linearly: 2-rows/email = ~$60/mo at Year 3; 5-rows/email = ~$347/mo. Each `setAlarm()` bills as one row write | — |
| TTL | **Two-phase DO alarm.** Phase 1 at `expires_at` (60 min): delete all message rows, bodies, R2 objects, close sockets. Phase 2 at `expires_at + 7d`: `deleteAll()` | Resolves the blocker where `deleteAll()` erases the tombstone that prevents a delayed ESP retry delivering a stranger's OTP into a new owner's inbox. Between phases the object holds only `tombstone_until`, `burned_at`, `read_token_hash` | — |
| Privacy claim wording | *"Message content is deleted at expiry; a non-reversible record that the address was used is retained 7 days to prevent mail reaching the wrong person."* | Accurate and a stronger story than an overclaim you cannot honour | — |
| Legal hold | **None. Retrospective-impossible posture**, stated in the LE policy | infra specified both a freeze path and "design the system so you cannot comply". Abuse reports arrive after the DO no longer exists. Any freeze can only be prospective and needs counsel | — |
| Control plane | **D1 database `control`**, read replication `mode: auto` | ~50 MB. Domain pool, blocklist health, hashed API keys, pSEO corpus, `metric_daily` rollups. 30-day Time Travel free | — |
| Hot config | **KV single key `pool:active`**, read with `{cacheTtl: 300}` | KV's eventual consistency is fatal for messages and harmless for "which domain to mint on" | — |
| Domain pool state | **D1 table + optimistic locking + KV projection.** No `DomainPool` Durable Object | data's own alternatives note: "genuinely fine at this scale and one fewer concept for the team." Three storage systems for ~50 strings is not proportionate | — |
| Attachment blobs | R2, explicit delete by alarm, 1-day lifecycle backstop. **Not used in Phases 1–3** | Free egress; lifecycle granularity is days, so explicit deletes are mandatory anyway | — |
| Secret rotation | Document the `SERVER_SECRET` rotation procedure **now**: rotate at the daily trough, accept one 60-min TTL window of orphaned inboxes, rely on the weekly orphan sweep | Rotating changes every derived DO id. Discovering this during an incident is how a team decides not to rotate a compromised secret | — |

### 2.4 Frontend, real-time client, pSEO/i18n

| Concern | Recommendation | Why | Fallback |
|---|---|---|---|
| Framework | **One Astro 7.2.x project** (`output: 'static'`, per-route `prerender = false`), inbox as **one** React 19.2 island, `@astrojs/cloudflare` 14.2.5 | pSEO ships 0 KB JS; inbox shell is static HTML so LCP paints and CLS locks before React runs. 100k-page build: Astro 22.6s/46.8 MiB vs Next.js 264.5s/1.84 GiB, ERR at 200k | Next.js 16.3.3 + `@opennextjs/cloudflare` 1.20.4 **only if Astro experience cannot be verified in the hiring loop** — hiring risk beats framework elegance at this budget |
| Hosting | **Cloudflare Workers Static Assets.** Not Pages | Cloudflare: "Start new projects with Workers." Static asset requests free and unlimited; zero egress. **Hard cap: 100,000 files/version (Paid)** — 5,000 terms × 25 locales = 125,000 breaks the deploy | — |
| Address in URL | **Fragment only**: `https://brand.com/i#<inbox_id>:<read_token>` | Fragments are never sent to the server, never in `Referer`, and are not read by GPT's page-URL collection. A path-based address is broadcast to a dozen SSPs in every bid request | — |
| Render iframe | `<iframe sandbox="allow-popups allow-popups-to-escape-sandbox" src="https://<quarantine-etld+1>/m/<opaque-id>" referrerpolicy="no-referrer" loading="lazy">` | `allow-popups` is required for the link click; no `allow-scripts`, no `allow-same-origin`, no `allow-forms`, no `allow-modals`, no `allow-top-navigation`. Safe only because links go through the interstitial | — |
| Render CSP (response header) | `default-src 'none'; script-src 'none'; style-src 'unsafe-inline'; img-src 'self' data:; font-src 'none'; form-action 'none'; base-uri 'none'; frame-ancestors https://<app-origin>; sandbox` + `nosniff`, `CORP: same-origin`, `COOP: same-origin`, `X-Robots-Tag: noindex`, `robots.txt: Disallow: /` | The CSP `sandbox` directive applies independently of the iframe attribute, so a mis-set attribute cannot un-sandbox the document. `font-src 'none'` closes the `@font-face` read-receipt channel | — |
| iframe → parent messaging | **Transfer a dedicated `MessagePort`** at load, or validate `event.source === iframeEl.contentWindow` (object identity) plus a nonce | A sandboxed opaque-origin frame reports `event.origin === "null"` — origin validation is unwritable. Best: fixed frame height with internal scroll, no channel at all | — |
| Client state | Zustand 5.0.15, `localStorage` (guarded in try/catch — private windows throw on *access*), `BroadcastChannel` leader election for one socket per browser | Halves peak concurrency (~7,300 → ~4,000 at Year 3). Losing the address on reload is the most rage-inducing failure this product has | — |
| Reconnect | Jittered exponential backoff + `GET /messages?since=<cursor>` re-sync on every reconnect | **Every deploy terminates every open WebSocket.** Without this, each deploy silently drops every user mid-OTP and will be misdiagnosed as a burned domain | — |
| Styling | Tailwind 4.3.3 + shadcn/ui (island only). **System font stack, no webfont** | Removes a render-blocking request and FOUT-driven CLS on pages whose CLS budget is spoken for by ads | — |
| pSEO corpus | **~290 telemetry-gated service pages × 8 human-reviewed locales ≈ 2,300 URLs.** SQL `indexable` view (`observations >= 50` in trailing 30d AND `locale.reviewed = 1`) drives both the `noindex` meta tag and the sitemap. simhash CI gate fails the build above 70% inter-page similarity | Resolves BLOCKER 6. Pages are built from live inbound telemetry — acceptance status per domain, p50/p90 delivery, DKIM signer, code format — which no competitor and no LLM can reproduce. Also: URL Inspection API is 2,000/day/site, so 2,300 URLs sweep in 2 days; 50,000 takes 25 | — |
| i18n | Astro built-in i18n routing + Paraglide JS 2.24.1. **Subdirectories on one apex** (`/hi/…`), hreflang in the **sitemap** via `<xhtml:link>`, never in `<head>` | Every incumbent uses subdirectories (temp-mail.org ~37, temp-mail.io ~28). Reciprocity is mandatory and fails silently — CI assertion required. **Never install `astro-i18next`** (abandoned 2023-03-09) | i18next 26.4.0 |
| Translation | Claude Haiku 4.5 Message Batches (~$12 for 7 locales) **+ mandatory human light post-editing at $0.03/word ≈ $1,932 per 7-locale tranche** | Unreviewed MT is a *written* Google spam policy violation. This line item does not exist in the plan. **Ship 8 reviewed locales, not 25 unreviewed ones.** Launch set: en, hi, id, pt-BR, ru, es, tr, fr | — |
| Docs | **Astro Starlight at `brand.com/docs`**, same project, same build | Resolves the Docusaurus/Starlight/Pages conflict. Subdirectory consolidates link equity; one build pipeline for 1–3 devs | — |
| Indexation hygiene | `X-Robots-Tag: noindex` + `robots.txt Disallow` on every inbox route and the render origin, from day one | Incumbents do exactly this (`Disallow: /view/`). Inbox contents in Google is a privacy incident *and* a policy violation |— |

### 2.5 Ad ops, consent, analytics

| Concern | Recommendation | Why | Fallback |
|---|---|---|---|
| Route split | **Google demand (AdSense → MCM/AdX) on pSEO/content/utility routes ONLY. Inbox route runs non-Google Prebid demand** (Magnite, PubMatic, Index Exchange, Media.net, Amazon TAM, Sovrn, OneTag) | Resolves the frontend/adops conflict on the evidence side. BLOCKER 4 is a written policy; the incumbent ads.txt evidence (temp-mail.org runs BuySellAds with 16+ Google pub IDs via resellers; 10minutemail.com 30+) shows Google demand reaches this vertical through aggregators, not direct placement approval | — |
| Ad server | GAM standard (free tier) + GPT, `disableInitialLoad()` + IntersectionObserver-gated refresh | Do not model the free cap as unconditional — Google does not publish the threshold, and header-bidding trafficking is a **GAM 360-only** feature. Confirm with the MCM partner | AdSense auto-ads at launch |
| Demand access | **AdSense at launch → MCM "Manage Inventory" partner at Phase 3.** Shortlist: PubGalaxy (already live on emailondeck.com), Snigel (100k pv/mo, ~$50/day), Adnimation, Setupad | Direct AdX is not obtainable by a new publisher. Model the 15–20% share as a **revenue haircut, and as the substitute for the ad-ops hire the budget cannot fund** | Media.net |
| Wrapper | **Prebid.js 11.31.0**, self-hosted custom build, 5–7 adapters, 1200ms timeout | 10.x is now `legacy-10.x`; most writeups are stale. A stock all-adapter bundle is ~1.5 MB of parse cost. 5th SSP ≈ +6.8% revenue, 15th ≈ +0.4% | — |
| Refresh | **User-action triggered** (generate, copy, open message, delete, manual refresh) — no minimum interval under either policy. Add declared 30s+ time-based refresh **only after AdX exists**. Always gate on `document.visibilityState === 'visible'` | Resolves BLOCKER 5. This product has more legitimate refresh triggers than almost any content site. Undeclared/misdeclared refresh is a separate "Dishonest declarations" violation | Event-driven on new-mail arrival, declared at 30s |
| Identity | ID5 (free) + `sharedId`. **Nothing else** | Privacy Sandbox is retired (Topics/PAAPI removal targeted Chrome 150, Jul 2026) — write zero code against it. Third-party cookies stay in Chrome | — |
| **Hard exclusion** | **Never hash generated addresses into UID2/EUID/LiveRamp.** Write it into the spec | Anonymous cookied match rates are <20% so it wouldn't work; it would breach UID2 consent requirements and destroy the product's premise. This *will* be re-proposed as a Phase-4 growth idea | — |
| CMP | Google Funding Choices (free, Google-certified), **TCF v2.3** | v2.2 was superseded 2026-02-28; Google no longer supports newly created v2.2 strings and publishers still emitting them report 60–80% CPM collapse. Note: GAM web interstitials require Purpose 1 consent, so EU interstitial revenue is thin | Usercentrics ~€49/mo |
| Adblock | Google's own free Ad Blocking Recovery messaging + native affiliate fallback cards. **No third-party circumvention** | ePrivacy Art 5(3) detection consent is contested; German BGH revived *Axel Springer v. eyeo* 2025-07-31 with OLG Hamburg reconsidering in 2026 | Blockthrough (already deployed on mail.tm) |
| Attribution join | **One first-party session id minted at first paint**, stamped into every Analytics Engine data point, passed to GPT as a key-value, appended as the affiliate subid. Bucket A/B on the server-issued id, not a cookie | Nobody owned this. Without it, neither the SEO restructure nor the $0.50 → $0.84 tier-1-targeting thesis is measurable. One dev-day | — |
| Analytics | Workers Analytics Engine, 3 datasets, nightly cron rollup → D1 `metric_daily`. **Never put message content, sender addresses or OTP codes in a blob** | Currently unbilled; list price $0.25/M points. 3-month retention is why the D1 rollup exists. AE blobs are queryable storage and would silently convert a zero-retention product into a 90-day one | ClickHouse Cloud (~$66/mo min) at Year 3+ |

### 2.6 Public API, extensions

| Concern | Recommendation | Why | Fallback |
|---|---|---|---|
| Framework | **Hono 4.13.5** + `@hono/zod-openapi` 1.6.1 + Zod 4.4.3 on `api.<brand>` | Cloudflare ships a first-party template. Zod schemas are the single source of truth for validation *and* the OpenAPI 3.1 doc, so drift is structurally impossible. Elysia's Workers adapter is self-described as experimental | chanfana 3.4.0 |
| Auth model | **Capability-keyed.** `POST /v1/inboxes` → `{inbox_id, address, read_token}`. Every read: `Authorization: Bearer <read_token>`, constant-time compare, identical 404 for "no such inbox" and "wrong token". Keyless tier may create but never read what it did not create. Public namespace on a separate path `/v1/public-inboxes/{localpart}` | Resolves BLOCKER 2 without killing the no-signup funnel. **No cookie auth anywhere** — CI assertion that no route emits `Set-Cookie` | — |
| OTP endpoints | `wait`, `match=otp` and the parsed `otp_code` field require an **identified API key** (email + Turnstile) | These are the highest-fraud-utility primitives in the product. Abuse needs an owner and a revocation handle | — |
| Never build | Public per-domain blacklist/health endpoint; "check any inbox" box; "recent inboxes" feed | Fraud enablement / standing data leak | — |
| Rate limiting | **One shared package**: WAF rule on brand zones only; Workers Rate Limiting binding for burst; **one DO per identity for accurate daily quota** | The RL binding is per-Cloudflare-location, `period` ∈ {10, 60}s, and Cloudflare states it is "intentionally designed to not be used as an accurate accounting system." WAF across 20–50 pool zones is $400–1,000/mo for 2 IP-only rules each | — |
| Docs/reference | `@scalar/hono-api-reference` 0.11.16 at `/v1/docs` (try-it console), guides in Starlight | — | Redoc |
| SDK scope, Year 1 | **TS client (~300 LOC, types via `openapi-typescript` 7.13.0) + Playwright fixture. That is all.** | Defer Python SDK, MCP server, Postman collection, CLI, GitHub Action until the API has measured users. Recovers ~1.5 dev-weeks. **Note the cannibalisation:** every agent that fetches an OTP over the API replaces a human holding a tab open for 3–8 minutes producing 3–6 impressions. api-ext rejected Zapier for exactly this reason and then ranked MCP #2 | — |
| Extension build | **WXT 0.21.4**, MV3 only, Chrome first, Firefox deferred | Plasmo has had no core npm release since 2025-05-17. MV2 is fully removed from CWS as of 2026-08-31. Firefox needs `browser_specific_settings.gecko.data_collection_permissions` (mandatory) and a buildable source-zip submission | Vite + `@crxjs/vite-plugin` |
| Extension monetization | **Zero ads in the extension.** Every action opens a real tab via `chrome.tabs.create()` | Prohibited three ways: AdSense placement policy ("toolbars, browser extensions"), CWS Ads policy ("AdSense may not be used to serve ads in Products"), GAM Partner Guidelines. Wrapping in Prebid does not launder it — the auction still resolves to a GAM call. **And it is the better revenue design:** a popup closes on blur and cannot produce a viewable 3–8 min session, dragging blended viewability below the 75% gate |
| Extension permissions | `activeTab` only. `host_permissions` limited to `https://api.<brand>/*` | Adding autofill-any-field needs `<all_urls>` + content scripts, which jumps to the strictest review and data-scrutiny tier under the CWS data policy enforced from 2026-08-01 | — |

### 2.7 Security, abuse, privacy, ops

| Concern | Recommendation | Why |
|---|---|---|
| Address entropy | 15 chars Crockford base32 = **75 bits**, server-generated, copy/QR only. Plus separate 128-bit read token | At ~150k concurrent inboxes, 50 bits yields 4.2 successful guesses/year at 1,000 guesses/sec; 44-bit word schemes are worse *and* fingerprintable by fraud vendors |
| Outbound | **Structurally impossible**: no `send_email` binding, zero verified destination addresses, no sending domain. CI lint fails the build on `send_email`, `message.forward(`, `message.reply(` | Platform-enforced, survives a compromised deploy. Carve out the domain-health probe mailboxes explicitly in writing or someone will "fix" the invariant by deleting them |
| Recipient denylist | Hard-reject at `setReject()` before any storage: `admin administrator webmaster hostmaster postmaster ssladmin abuse security noc dmarc support billing noreply` | Where your own abuse reports, registrar notices and delisting mail arrive. Residual CA/B Forum email-DCV exposure runs to 2028 |
| Unknown mailbox | `setReject('550 5.1.1 No such mailbox')` after a **KV existence check** — before DO wake or MIME parse | Largest single cost and abuse reduction available: drops a modelled 50M-message mailbomb from $138 to <$20. Rate-limit rejects per connecting IP with `450 4.7.1` to bound the live-address oracle |
| Connection auth | Validate `inbox_id` + `read_token` in a **plain Worker before the DO is addressed**; cap 2 concurrent connections/inbox, 10/IP; create the inbox DO lazily on first inbound message or first authenticated read | Otherwise an unauthenticated flood wakes a DO for any address — the actual wallet-DoS hole |
| Kill switch | **`HALT=1` secret checked at the top of every handler, Phase 1.** Billing alert on DO GB-s from week one. Full three-state circuit breaker deferred to Phase 4 | Cloudflare has no hard spend cap; budget alerts are informational only |
| Silent-ingest detection | **End-to-end mail canary every 5 min** from a `scheduled()` handler: provision inbox → send real mail from an external provider → open WS → record latency. Plus hourly per-pool-domain deliverability probe from Gmail + Outlook business mailboxes at a third provider | The worst failure mode is ingest dying with no exception and no 5xx. HTTP checks stay green throughout |
| SLO | `otp_delivery_latency_ms` = L1 (`email()` entry → `ws.send()`) + L2 (½ WS RTT) + L3 (`onmessage` → rAF commit), each on one clock. **p50 ≤ 2.0s, p95 ≤ 5.0s, 99.0% under 5.0s / 28d** | **Restate Phase 1's "sub-100ms" exit criterion as "p95 API < 100ms; p95 SMTP-accept-to-rendered < 500ms."** Receipt-to-pixel sub-100ms is unachievable and will be scored as a miss |
| Auth-rejection UX | Surface *"a message from X was rejected because it failed sender authentication"* instead of an empty inbox | Cloudflare's SPF-or-DKIM + DMARC enforcement cannot be disabled and silently drops some legitimate OTP mail. An empty inbox is the worst failure this product has and will be misdiagnosed as a burned domain |
| "Didn't get your code" control | **Phase 1.** Writes `domain_rejected` with domain id, offers one-click re-mint on another domain, shows any recorded SMTP rejection reason | One control serving as abuse intake, earliest domain-burn signal, SEO telemetry source and retention save. Four layers consume it; none scheduled it |
| Secondary MX | **A disjoint subset of pool domains whose only MX is your own** (Haraka 3.3.3, 2× Hetzner CX, per-domain MX hostnames). **Not a priority-20 backup MX** | A backup MX behind Cloudflare doesn't change the `*.mx.cloudflare.net` fingerprint at all, and senders deliberately target the lowest-priority MX to bypass the primary's filtering — i.e. bypass the free SPF/DKIM/DMARC/RBL rejection. Trigger: build in Phase 2 if measured Cloudflare auth-rejection rate exceeds ~2%, else Phase 4 |
| GDPR | Art. 6(1)(b) for the core inbox; Art. 6(1)(f) for security logging **and for sender/third-party data inside messages** (LIA leaning on the 60-min TTL, no profiling, no backups), Art. 14(5)(b) for the notification duty, **Art. 11 for DSARs** (no account + 60-min TTL = you genuinely cannot identify a data subject). Truncated `HMAC(daily_salt, ip)` is pseudonymisation, **not** anonymisation — do not claim otherwise | Only the user was covered in every layer analysis. Budget **$2,000–5,000 counsel** (not in the ask) for entity/jurisdiction, the LIA, DPA chain, Art. 27 EU rep and UK rep, CCPA/CPRA at 6M MAU |
| PII rule at schema level | No `user` table; no column anywhere holds a raw IP, raw email or message body. `CF-Connecting-IP` never reaches D1 or AE | Enforce in code review |
| Log leakage | Aggressive Sentry `beforeSend`: drop exception `message` and all `extra`/breadcrumbs for the ingest Worker; report only error class + message id + size. Never pass the message object into an exception constructor. Head-sample Workers Logs 2–10%. **End-to-end data-flow audit before launch** | The leak is never a deliberate log line — it's a parse-failure exception payload carrying raw MIME. Sentry EU residency is enterprise-only |
| Public posture | RFC 9116 `security.txt`, monitored `abuse@` on a **non-pool** domain, "report this message" UI control, published Acceptable Use page, `domains.txt` of burned domains, honoured blocklist requests, annual transparency report, DMCA agent ($6) | These are the documents the ad network, registrar compliance team and Cloudflare abuse desk actually read |

### 2.8 CI/CD, IaC, observability, support

| Concern | Recommendation |
|---|---|
| Monorepo | pnpm 11.24.0 workspaces + Turborepo 2.10.12. `apps/web` (Astro), `workers/ingest`, `workers/api`, `workers/render`, `workers/admin`, `packages/shared`, `packages/sanitizer`, `packages/ratelimit`, `infra/terraform`, `ops/canary` |
| Language | TypeScript 7.0.2 (Go-native), `strict`, **`noUncheckedIndexedAccess`**, `exactOptionalPropertyTypes`. Week-1 go/no-go: `tsc --noEmit` across the full dependency tree |
| Lint/format | **Biome 2.5.10** — one binary, one config. Plus custom rules failing the build on `send_email`/`forward(`/`reply(`, on `ws.accept()` in DO code, on `allow-scripts`/`allow-same-origin` in render code, and on address-shaped path segments under `/api` |
| Tests | Vitest 4.1.11 + `@cloudflare/vitest-pool-workers` 0.22.0 (real workerd, real DOs, real `email()` handler). Playwright 1.62.1. **100% branch coverage on the sanitizer and extractor only.** Regression corpus: mXSS namespace confusion, `xmp` payload, charset confusion, malformed MIME fuzz |
| Key E2E test | Provision inbox → send real mail through the standby SMTP path → assert OTP in DOM within SLO. Plus a reconnect test (the one failure guaranteed on every deploy) |
| CI/CD | GitHub Actions: `biome ci` → `tsc --noEmit` → `vitest` → `terraform plan` → staging deploy → Playwright → gated prod deploy → smoke canary. `wrangler versions upload` + `versions deploy` for gradual ingest rollout. Deploy ingest and API independently; schedule ingest deploys off-peak |
| IaC split | **Terraform** (`cloudflare/cloudflare` v5.24.0): zones, DNS, Email Routing, Turnstile, WAF, Access, R2, D1. **Wrangler 4.127.0**: Workers, DO namespaces/migrations, bindings, secrets. State in R2 |
| Environments | **One long-lived staging** on a separate Cloudflare account with its own 2 test domains at a different registrar. **Per-PR Preview URLs do not exist here** — verified: "Preview URLs are not generated for Workers that implement a Durable Object", and they have no Workers Logs, `wrangler tail` or Logpush |
| Errors | Sentry `@sentry/cloudflare` 10.71.0, `withSentry()` (covers the `email` handler), `instrumentDurableObjectWithSentry()`. Team $26/mo from Phase 3 |
| Logs | Workers Logs, `head_sampling_rate` 2–10%, 7-day retention. **No third-party log vendor before Phase 3.** Baselime is discontinued (acquired by Cloudflare, team folded into Workers Observability) |
| Uptime + status | Checkly Hobby (free) for HTTP; mail canary as the primary monitor; **status page on Instatus (~$30/mo), hosted off Cloudflare, `status.<brand>` pointed by a registrar-level record** so it resolves during a Cloudflare incident |
| Admin console | **One Cloudflare-Access-protected Worker, ~1.5 dev-weeks, Phase 2.** Domain state machine + burn control, global kill switch, D1 flags table read through a 60s-cached KV key, abuse-report queue, API key revocation. Four layers assume this exists; none scoped it |
| Support | Shared mailbox on a non-pool domain + one helpdesk seat (~$50–100/mo) from Phase 1, with a **named human owner** for abuse, DSAR and law enforcement. Cloudflare requires a 24h abuse-report response |
| Accessibility | Half a dev-week, Phase 1: `aria-live="polite"` on the message list and OTP chip, real `<button>` for copy with inline text swap, visible focus rings, no keyboard trap in the GPT interstitial, `prefers-reduced-motion` |

---

## 3. Monthly cost — arithmetic shown

**Volume model** (instrument in Phase 1 — every figure scales linearly off it): inbound = sessions × 1.3 wanted messages × 1.4 junk multiplier; Cloudflare rejects ~10% at SMTP before billing. Y1: 1.8M sessions → **2.9M billable ingests**. Y3: 21M sessions → **34.4M billable ingests**.

### Cloudflare core

| Line | Year 1 | Year 3 |
|---|---|---|
| Workers Paid base | $5.00 | $5.00 |
| Worker requests | (7.2M API + 2.9M ingest) − 10M incl = 0.1M × $0.30/M = **$0.03** | (84M API + 34.4M ingest) − 10M = 108.4M × $0.30/M = **$32.52** |
| Worker CPU | (21.6M + 43.5M) − 30M = 35.1M ms × $0.02/M = **$0.70** | (252M + 516M) − 30M = 738M ms × $0.02/M = **$14.76** |
| DO requests | 6.6M − 1M = 5.6M × $0.15/M = **$0.84** | (33.6M connects + 34.4M deliveries + 24M alarms + 2.1M client msgs @20:1) = 94M − 1M = 93M × $0.15/M = **$13.95** |
| DO duration (hibernating) | 0.3M GB-s < 400k incl = **$0** | 1.4M GB-s × 4 (imperfect hibernation budget) = 5.6M − 0.4M = 5.2M × $12.50/M = **$65.00** |
| *counterfactual: SSE-on-DO* | *$176* | ***$10,075*** |
| DO SQLite rows written | 9M < 50M incl = **$0** | (2/email × 34.4M) + 24M alarms + overhead ≈ 110M − 50M = 60M × $1.00/M = **$60.00** |
| KV reads | < 10M incl = **$0** | 24M − 10M = 14M × $0.50/M = **$7.00** |
| D1 control plane | inside included = **$0** | inside included = **$0** |
| R2 (metadata only) | **$0** | **$0** |
| Analytics Engine | 12M − 10M = 2M × $0.25/M = **$0.50** | 150M − 10M = 140M × $0.25/M = **$35.00** *(unbilled today)* |
| Workers Logs (sampled) | included | **$30.00** |
| Cloudflare Pro (brand zones) | $20.00 | $40.00 |
| **Cloudflare subtotal** | **$27** | **$303** |

### Everything else

| Line | Year 1 | Year 3 |
|---|---|---|
| Sentry | $26 | $100 (PAYG overage on ~155k events) |
| Domain pool (20 → 50, incl. burn/replace) | $15 | $120 |
| Quarantine/render domains (2) | $3 | $5 |
| Secondary MX (2× Hetzner CX) | $0 (Phase 4) | $10 |
| Probe mailboxes (business tier, 3rd provider) | $12 | $12 |
| Helpdesk seat + shared mailbox | $50 | $100 |
| Status page (Instatus, off-Cloudflare) | $30 | $30 |
| GitHub Team + Actions | $8 | $32 |
| Screaming Frog (€245/yr) | $22 | $22 |
| DataForSEO SERP API | $10 (weekly, 8 locales) | $216 (daily, 800 kw × 15 locales) |
| Ahrefs | $0 (deferred to Phase 3; AWT free) | $207 (Standard, annual) |
| Synthetics beyond free tier | $0 | $40 |
| CMP (Funding Choices) / Turnstile / Email Routing inbound | $0 | $0 |
| **TOTAL** | **≈ $203/mo** | **≈ $1,197/mo** |

**One-time:** human LPE for 7 locales $1,932 · counsel $2,000–5,000 · brand domain $15 · Chrome dev fee $5 · DMCA agent $6 · MT via Claude Batch ~$50.

### Against revenue

| | Plan | Realistic base | Realistic bull |
|---|---|---|---|
| Y3 impressions/session | 3.8 | 2.5 (user-action refresh) | 3.8 |
| Adblock delivery | 100% | 50% | 55% |
| Served impressions/mo | 79.8M | 26.3M | 43.9M |
| Blended eCPM | $3.50 | $0.55 | $0.84 |
| Gross ad revenue/mo | **$279,000** | **$14,440** | **$36,900** |
| Less 18% MCM share | — | $11,840 | $30,260 |
| Affiliate | — | $3,000 | $10,000 |
| **Net revenue** | $279,000 | **≈ $14,800** | **≈ $40,300** |
| Infra as % of gross | 3.2% (claimed) | **8.3%** | **3.2%** |

The plan over-budgets infrastructure ~7× and under-budgets labour, translation review, counsel, support and the MCM revenue share entirely. Once the revenue line is corrected, infrastructure stops being noise: **$1,200/mo against $14k/mo of revenue is a real cost centre, not a rounding error.**

---

## 4. 24-week build sequence

### Week 0 — non-engineering critical path (zero dev capacity, do it first)

Every external approval below has a 2–12 week cycle and every layer scheduled it in the phase that needs it. Register the brand `.com` (separate registrar from the pool). Verify GSC + Bing and **switch on GSC Bulk Data Export immediately — it is forward-only and does not backfill.** Open a Cloudflare support ticket describing the inbound-only, no-outbound use case at ~25–35M msgs/mo across 20–50 zones on one account, and ask for the per-account zone ceiling. Open the AdSense application. Start pre-application conversations with PubGalaxy and Snigel. Pay the $5 Chrome dev fee, create the AMO account. Register the DMCA agent. Engage counsel.

### Phase 1 (doc: wk 1–4) → **weeks 1–6.** Underfunded by ~50%.

Repo, CI, Terraform, 3 domains provisioned end-to-end. **Week 1 go/no-go spikes:** (a) `sanitize-html` bundles and is CPU-viable in a Worker; (b) `tsc --noEmit` clean across the full tree on TS 7. DO-per-inbox + hibernating WebSocket + reconnect/re-sync. postal-mime 2.7.6 + sanitizer + render Worker on the quarantine domain + link interstitial. Scored OTP extractor + first-party fixture corpus (200 services, 3–5 days). Astro shell + React island, mobile-first, a11y pass. Session-id attribution. "Didn't get your code" control. `HALT` switch + KV recipient-existence check. Mail canary + SLO instrumentation. Helpdesk + `abuse@` live.
**Exit:** MVP on 3 domains, p95 API <100ms, p95 SMTP-accept-to-rendered <500ms, measured junk multiplier, measured Cloudflare auth-rejection rate, measured WS-failure rate.

### Phase 2 (doc: wk 5–8) → **weeks 7–14.** Scope cut ~20×.

Abuse controls (Turnstile on generate only, shared rate-limit package, denylist). Admin console (1.5 dev-weeks). Legal artifacts, LE policy, AUP, `security.txt`, transparency page. Domain automation to 10–15 domains + health state machine. **pSEO: ~40 hand-written English evergreen pages only** — service pages cannot exist until the 50-observation threshold is met (realistically month 3–4). Sitemaps, hreflang CI assertions, IndexNow (**note: Google does not support IndexNow** — sitemaps and GSC only). Starlight docs. If measured auth-rejection >2%, build the Haraka path now.
**Deferred out of Phase 2:** public API, both SDKs, MCP server, Postman, CLI, GitHub Action, Firefox extension, 24 of 25 locales.
**Honest note:** the doc's 50k organic visits/mo by week 8 is unreachable through data-driven pages. Expect month 5–6.

### Phase 3 (doc: wk 9–14) → **weeks 15–20.** Gated by the MCM reply, not by code.

CMP (Funding Choices, TCF v2.3) with consent-conditional ad init. Prebid 11.31.0 custom build. **Route-split ad stack: Google on content routes, non-Google on the inbox route.** User-action refresh with IntersectionObserver + visibility gating, declared in GAM. CLS discipline (pre-reserved min-heights on ad slots *and* the message container; transform-based row entry). Chrome extension (MV3, WXT, no ads). Web-vitals → Worker → AE. Adblock-rate and impressions-per-session measurement.
**Exit:** restate as *measured* blended eCPM and viewability, not a $3.00 target.

### Phase 4 (doc: wk 15–24) → **weeks 21–24 + post-revenue.**

Pool to 20–30 domains. Haraka secondary path on a disjoint domain subset. A/B harness. Affiliate cards. Full circuit breaker. Image proxy with SSRF controls. postal-mime 3.x migration behind the corpus. Telemetry-gated service pages as data crosses threshold. First 7-locale LPE tranche.
**Post-revenue only:** public API + SDK, Firefox extension, MCP, pSEO beyond ~300 pages.

### Where the budget is short

Realistic scope after these cuts is **~28–34 dev-weeks**. $12–18k buys **7.5 dev-weeks at $60/hr or 18 at $25/hr** — 22–64% funded. The `$5,000/mo maintenance/devops/SEO tools` line is ~93% labour; real tooling is ~$1,200/mo, and $5,000/mo does not buy the ~1.5 FTE this platform needs at Year-3 scale. **Present the raise as funding an MVP plus a monetization experiment, not a 24-week full-scope build.**

---

## 5. Decisions that need a human

1. **Does the investment case clear at ~$15–40k/mo Year-3 gross instead of $279k?** On a $22–33k raise, ~$8–25k/mo net profit is a genuinely attractive return — but it is a different proposition from the one presented. Re-run the model before anything else.
2. **Do you accept the AdSense placement risk on the inbox route, or route-split now?** Default here is route-split. Reversing it requires a written determination from a GAM/MCM rep — a two-week email exercise that de-risks ten weeks of build.
3. **Publish the domain pool?** Default: burned/retired only. Full publication buys seo's citations and the good-citizen posture but converts effective domain life from months to days and multiplies the churn-labour line.
4. **Does the Tier-2 public (user-chosen) namespace exist at all?** It is a real UX expectation and the thing the API wants, and it is structurally a public bulletin board that will generate the first abuse complaint.
5. **Astro or Next.js?** Decided by the hiring loop in week 0, not by the benchmark. If Astro experience cannot be verified, take Next.js 16 + `@opennextjs/cloudflare` and accept the pSEO JS weight and the build-time cap.
6. **Passive telemetry only, or active signup probes** against third-party services for the "does X accept our domains right now" data? Active probing has ToS implications and sits badly against the inbound-only posture.
7. **Reserve a paid tier?** Do not build billing now, but keep a `plan` column and the paid surface defined (custom domain, 24h TTL, ad-free, API quota). ~50% of the audience is unmonetizable by adblock; when you need it, take a merchant of record (Paddle, 5% + $0.50) rather than a PSP — VAT/GST registration across 25 countries is what a 3-person team cannot do.
8. **Who owns the Cloudflare and registrar accounts, and what is the recovery path if that person is unavailable?** For a team this size, single-person credential control is a more probable cause of total loss than any technical failure in this document.

---

## 6. Cheapest viable variant — 4-week MVP

Prove the two things that decide the business: **can you receive mail reliably, and what does the inventory actually earn.** Everything else is deferrable.

| | Included | Cut |
|---|---|---|
| Domains | 3 pool domains at Porkbun + 1 brand `.com` + 1 quarantine domain | 20–50 pool, rotation, health state machine |
| Ingest | Email Routing catch-all → Email Worker, postal-mime 2.7.6, KV recipient-existence check, `HALT` secret | Haraka secondary, circuit breaker, SES fallback |
| Sanitize | `sanitize-html` 2.17.7 — **or, if the week-1 spike fails, `text/plain` only with linkification** | Image proxy, attachment handling of any kind |
| Storage | SQLite DO per inbox, two-phase alarm (60 min / 7d tombstone) | D1 control plane, R2, KV config projection |
| Real-time | `state.acceptWebSocket()` + reconnect/re-sync. **Non-negotiable** — it is the cost and security control | SSE fallback path |
| Frontend | One Astro project, one React island, Tailwind, `#fragment` address+token, copy button, OTP chip, "didn't get your code" control, `aria-live` | i18n, pSEO, docs, PWA manifest, extension |
| Security | 75-bit address + 128-bit read token, HMAC DO name, constant-time 404, denylist, `sandbox="allow-popups allow-popups-to-escape-sandbox"` + strict CSP on the quarantine origin, `noindex` everywhere | Admin console, Turnstile (add if abused), WAF beyond one rule |
| Ads | **AdSense only, no refresh, on a `/temp-mail-guide` content route** — inbox route carries no Google code | Prebid, GAM, MCM, CMP (English-only, geo-block EU at the CDN for 4 weeks to defer the CMP entirely) |
| Ops | Mail canary every 5 min, Workers Logs, free Checkly, one shared mailbox | Sentry, status page, Ahrefs, DataForSEO, Screaming Frog |
| Data | Analytics Engine: sessions, msgs/session, OTP-extraction rate, adblock rate, impressions/session | Attribution join, D1 rollups |

**Effort:** ~5–6 dev-weeks at 1 dev, **~3.5 at 2 devs.** **Cost: ~$45/mo** ($5 Workers + $20 Pro + ~$3 domains + ~$12 probe mailbox + $5 Chrome fee once).

**What it proves in 4 weeks of live traffic:** the real inbound-junk multiplier, the Cloudflare auth-rejection rate (does the Haraka path move to Phase 2?), OTP-extraction coverage, the WS-failure rate, adblock rate by geo, actual impressions per session under user-action refresh, and whether AdSense approves the domain at all. Those seven numbers determine whether the $12–18k is worth spending — and every one of them is currently an assumption in the plan.

**Carry forward unchanged into the full build:** the hibernating-WebSocket transport, the capability-keyed access model, the two-phase alarm, the quarantine-origin render contract, and the fixture corpus. Nothing in the cheap variant is throwaway.