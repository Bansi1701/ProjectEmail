# Security, Abuse Governance & Compliance

The threat model for this product is unusual: **the primary untrusted input arrives by email from
anyone on the internet, unauthenticated, by design.** We cannot refuse mail — receiving it is the
product. Everything below follows from that.

> **Living document — v0.1.** The threat model grows as the product does. Add to it whenever you
> find a new attack surface.
>
> **One exception to "nothing is final":** the controls in §1 (origin isolation) and §2 (address
> entropy) are not up for casual revision. They are load-bearing, and both are enforced by tests.
> Changing either needs an ADR and a second reviewer.

---

## 1. Untrusted email HTML

**Threat.** An attacker sends HTML mail to a public inbox containing scripts, tracking pixels,
CSS exfiltration, phishing forms or clickjacking overlays. If it executes in our origin it can read
session state, tamper with ad scripts (revenue and Google policy consequences), or attack the user.

**Defence — both layers, always. Never one or the other.**

**Layer 1 — sanitize on ingest.** `nh3` with a strict allowlist. Remove `<script>`, `<style>`,
`<iframe>`, `<object>`, `<embed>`, `<form>`, every `on*` handler, and `javascript:` / `data:` URLs.

**Layer 2 — sandbox on render.** Rendered mail is served from a **separate origin**
(`content-sandbox.example.com`), never from the app origin.

```html
<!-- CORRECT -->
<iframe sandbox="allow-popups allow-popups-to-escape-sandbox"
        src="https://content-sandbox.example.com/msg/{id}"
        referrerpolicy="no-referrer">
```

```html
<!-- CATASTROPHIC — never write this -->
<iframe sandbox="allow-scripts allow-same-origin" srcdoc="{{ email_html }}">
```

`allow-scripts` and `allow-same-origin` **together** allow the framed document to reach into the
parent, read session state and modify ad scripts. It removes the protection the sandbox exists to
provide.

> The source business plan (§8) proposes `sandbox='allow-same-origin'`. **That is an error.**
> We deliberately do not follow it.

**CSP on the sandbox origin:**

```
default-src 'none'; img-src https: data:; style-src 'unsafe-inline'; frame-ancestors https://example.com
```

**Remote images.** Loading them leaks the user's IP and confirms the address is live — for a privacy
tool, that is a product failure, not a minor leak. Default to **blocked**, with an explicit
"load images" affordance. If loaded, proxy them server-side so the sender never sees the user's IP.

**Links.** Rewrite through an interstitial that strips the referrer and warns on known-phishing
destinations.

---

## 2. Inbox enumeration — the category's classic breach

**Threat.** Domains are public and catch-all. Anyone can guess an address, poll it, and read whatever
lands — routinely password resets and 2FA codes. This is how temp-mail services end up in the news.

**Defence.**

| Control | Requirement |
|---|---|
| Address entropy | **≥ 64 bits** for generated inboxes. Never sequential, never timestamp-derived, never a predictable dictionary pair |
| Access control | Reading requires a **possession token** issued at inbox creation. Knowing the address is not sufficient |
| Rate limits | Per IP and per token, on both reads and creation |
| User-chosen addresses | **Opt-in only**, never the default, and labelled unmistakably as publicly readable |
| Enumeration detection | Alert on bursts of reads against non-existent inboxes |

Use `secrets.token_urlsafe()`. **Never `random`** — it is seeded predictably and is not a CSPRNG.

---

## 3. Inbound-only relay

The platform has no SMTP client, no sending library, no reply and no forwarding. Permanently.

This is what keeps our IPs and hosting accounts off blocklists and prevents the service becoming a
spam or phishing relay. It is enforced structurally: **no sending dependency exists in
`pyproject.toml`.** Any change that would add one requires human sign-off.

---

## 4. Denial of wallet

**Threat.** An attacker floods the domains with millions of messages, or opens and holds hundreds of
thousands of SSE connections. Neither breaches anything — both burn money and degrade service.

**Defence.**

- Postfix connection, rate and message-size caps at the SMTP edge, before any Python runs.
- Drop mail for non-existent inboxes **immediately**, before parsing or storing.
- Per-inbox message cap; extra mail is discarded, not queued.
- Cap concurrent SSE connections per IP; idle-timeout connections whose inbox has expired.
- Cloudflare Turnstile on rapid inbox generation.
- **Hard spend caps and billing alarms on every metered service.** Set these on day one, not after
  the first surprise invoice.

---

## 5. Injection and parser attacks

| Vector | Mitigation |
|---|---|
| ReDoS in OTP regexes | Bound every quantifier. No nested unbounded repetition. Fuzz the patterns in CI |
| Zip / attachment bombs | Size cap before decompression; never auto-extract archives |
| MIME parser CVEs | stdlib `email` — tracked by Python security releases. Keep Python patched |
| SQL injection | SQLAlchemy parameterised queries only. Never f-string SQL |
| SSRF via remote images | Proxy through an allowlist; block private IP ranges and link-local addresses |
| Header injection | Never reflect email headers into HTTP responses unsanitised |

---

## 6. Abuse governance

The service will be used for fraud by some fraction of users. Pretending otherwise is not a posture.

- **Short TTL is the strongest protective control we have.** Data that no longer exists cannot be
  breached, subpoenaed or leaked. Resist every request to extend retention.
- **Abuse contact** published and monitored: `abuse@`.
- **Law-enforcement policy** documented in advance, not improvised under pressure. In practice
  little data exists to hand over — say so plainly.
- **Never log message bodies.** Not in application logs, not in Sentry, not in traces. Scrub before
  emitting.
- **Blocklist inbound senders** that are consistently abusive.

---

## 7. Data protection

A temporary email address is **personal data** under GDPR. Assume it, rather than litigating whether
it is.

| Obligation | How we meet it |
|---|---|
| Data minimisation | Store the message, its TTL and nothing else. No account, no profile, no history |
| Storage limitation | 10–60 minute TTL, enforced by Redis expiry rather than a deletion job we could get wrong |
| Lawful basis (ads) | Consent, collected via a Google-certified TCF v2.2 CMP before any ad or analytics script loads |
| Right to erasure | Effectively automatic. A user can also delete an inbox immediately |
| Processor chain | DPAs on file with every processor — hosting, CDN, ad partners, error tracking |

**Consent gating is a hard requirement**, not a nicety: no ad or analytics script may load before
consent in applicable jurisdictions. Getting this wrong is both a legal exposure and grounds for
losing ad partners.

**Needs a lawyer, not a template:** the operating entity and its jurisdiction, the ad-tech processor
chain, and the law-enforcement response policy.
**Template is fine:** privacy policy, terms of service, cookie policy — reviewed once by counsel.

---

## 8. Secrets and access

- `.env` is gitignored. New config goes in `.env.example` with a placeholder.
- Production secrets live in the platform's secret store, never in the repo, never in CI logs.
- Rotate registrar and ad-network credentials on staff change.
- Least privilege on registrar API tokens — DNS scope only, never account-level.

---

## 9. Reporting a vulnerability

Email `security@` (once the domain is live). Please do not open a public issue.
We aim to acknowledge within 48 hours.
