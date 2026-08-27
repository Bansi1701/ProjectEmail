# Validation Findings — v0.1

> **Living document — 2026-08-27.** Output of a multi-agent research pass over the business plan:
> seven specialists designed each layer, three adversarial critics attacked the result (63 findings:
> 18 blocker, 32 major, 13 minor).
>
> ⚠️ **These are research findings, not verified fact.** The policy quotations and pricing below need
> checking against primary sources before any of them drives a spending decision. Treat this as a list
> of things to confirm, ranked by how much they matter.

---

## The headline

**The revenue model appears to be 5–14% of plan.** Not the cost model — the cost model is fine, and
in fact over-budgeted. The problem is the numerator.

| | Plan | Researched base | Researched bull |
|---|---|---|---|
| Impressions / session (Y3) | 3.8 | 2.5 | 3.8 |
| Adblock delivery rate | 100% | 50% | 55% |
| Served impressions / mo | 79.8M | 26.3M | 43.9M |
| Blended eCPM | $3.50 | $0.55 | $0.84 |
| Gross ad revenue / mo | **$279,000** | **$14,440** | **$36,900** |
| Less ~18% MCM share | — | $11,840 | $30,260 |
| Affiliate | — | $3,000 | $10,000 |
| **Net / mo** | **$279,000** | **≈ $14,800** | **≈ $40,300** |

The eCPM gap is the crux. $2.80–3.50 is a tier-1, cookied, contextual-content number. This inventory
is the opposite on all three counts: globally distributed and India-weighted, unaddressable by design
(privacy tool), and context-free (an empty inbox has no content to target against).

**This does not necessarily kill the business.** On a $22–33k raise, $8–25k/mo net is a genuinely
good return — it is simply a different proposition from the one in the deck. The recommendation is to
re-run the investor model before spending, not to abandon it.

---

## Blockers worth verifying first

Ordered by cost of being wrong.

### 1. Google may prohibit ads on the inbox screen outright

Researched AdSense policy language: *"Publishers may not place Google ads alongside email messages
when they are the primary focus of the page"* and *"may not place Google ads on screens where private
communication between people is the primary focus."*

If accurate, this is not a sandbox problem — our iframe isolation ([`SECURITY.md` §1](SECURITY.md#1-untrusted-email-html))
addresses a *different* policy about ad adjacency to UGC and confers no protection here. Enforcement
appears lax (competitors run AdSense on inbox screens today), but 100% of revenue would ride on that
continuing.

**Suggested response:** route-split the ad stack — Google demand on content and SEO routes,
non-Google demand on the inbox route. Or get a written determination from a GAM/MCM representative
first; a two-week email exercise de-risks ten weeks of build.

### 2. Timer-based ad refresh may be prohibited, and AdX is not directly obtainable

Researched: *"Publishers are not permitted to refresh a page or an element of a page without the user
requesting a refresh."* The 30-second declared-refresh regime reportedly exists only in Google Ad
Manager, not AdSense — and direct AdX access is not granted to new publishers. It requires a Google
Certified Publishing Partner or an MCM "Manage Inventory" parent.

The plan's 3.8 impressions/session depends on the 35-second auto-refresh in §4 of the business plan.
If this holds, that number is unreachable until an MCM relationship exists, which has a multi-week
approval cycle.

**Suggested response:** apply to MCM partners in week 0, before writing ad code. Switch to
user-action-triggered refresh as the default.

### 3. The pSEO plan may match two named Google spam policies

2,000 pages × 25 locales reportedly matches **scaled content abuse** and **doorway abuse**
simultaneously, and a separate clause names *"text translated by an automated tool without human
review"* as spam. Publisher Policies apply the same low-value test to ad eligibility, so one adverse
determination could remove the traffic and the demand source together.

**Suggested response:** start with ~40 hand-written English pages of genuine standalone utility.
Expand only on measured indexation. This matches the caution already in [`ROADMAP.md`](ROADMAP.md)
Phase 2 but is a sharper cut than "start with 50".

Also noted: **Google does not support IndexNow.** Sitemaps and Search Console only. IndexNow remains
valid for Bing and Yandex.

### 4. The build is 22–64% funded

Realistic scope after the cuts above is **~28–34 dev-weeks**. A $12–18k budget buys roughly 7.5
dev-weeks at $60/hr or 18 at $25/hr. The plan's `$5,000/mo maintenance/DevOps/SEO tools` line is
~93% labour; actual tooling is closer to $1,200/mo, and $5,000/mo does not buy the ~1.5 FTE this
platform needs at Year-3 scale.

**Suggested response:** present the raise as funding an MVP plus a monetization experiment, not a
24-week full-scope build.

---

## What this confirms in our design

Two of our [non-negotiable rules](../CLAUDE.md#4-non-negotiable-rules) came back independently confirmed:

- **Rule 1 (origin isolation).** Confirmed, with a useful addition: `sandbox=""` with *zero* tokens
  silently breaks verification-link clicks, which is the core product function. Our
  `allow-popups allow-popups-to-escape-sandbox` is the correct middle ground. Also confirmed:
  `allow-same-origin` + `allow-scripts` lets the frame delete its own `sandbox` attribute in two
  lines of JS.
- **Rule 2 (unguessable addresses).** Confirmed and sharpened. Reads must key on an opaque inbox ID
  plus a possession token, **never on the address** — because handing the address to a third party
  *is the product*. The signup site, its ESP, every middlebox and every data broker downstream has
  it. A public API endpoint that reads an inbox by address alone would be a mass-OTP-disclosure
  endpoint.

Our [`addresses.py`](../backend/app/services/addresses.py) and
[`MessageViewer.tsx`](../frontend/src/components/inbox/MessageViewer.tsx) already implement both.

---

## Note on the stack recommendation

The research pass independently recommended **keeping the Cloudflare Workers architecture** from the
business plan's §7, on cost and operational-load grounds for a small team.

We chose Python/FastAPI anyway — see [ADR 0001](adr/0001-python-fastapi-over-cloudflare-workers.md).
The deciding reason was team fit, which no external analysis can weigh. That decision stands, and is
worth revisiting only if the team composition changes.

One finding is worth recording because it **validates the choice**: on Cloudflare, holding SSE
connections open on a Durable Object is billed as in-flight request duration against a flat 128 MB,
which works out to roughly **$10,000/mo at Year-3 volume** — and lets an attacker hold 1M idle
connections for an hour on your budget. The documented fix is the WebSocket Hibernation API, which
drops it to ~$65/mo. It is invisible at MVP scale and detonates in Year 2.

**Our Redis pub/sub + `sse-starlette` design has no equivalent trap** — an idle connection costs a
file descriptor and some memory, not metered duration.

---

## Week 0 — before any code

Every external approval below has a 2–12 week cycle. Starting them costs no dev capacity and they
gate later phases.

- [ ] Register the brand `.com` at a **separate registrar from the mail pool**
- [ ] Verify Google Search Console + Bing; **switch on GSC Bulk Data Export immediately** — it is
      forward-only and does not backfill
- [ ] Open the AdSense application
- [ ] Start pre-application conversations with MCM partners
- [ ] Ask your inbound-mail provider, in writing, about the disposable-email use case at
      ~25–35M msgs/mo — get the answer before you depend on it
- [ ] Register a DMCA agent; engage counsel
- [ ] Pay the $5 Chrome developer fee, create the AMO account

---

## Open questions for a human

These are genuine forks where risk appetite or business context decides, not technical questions:

1. **Does the investment case clear at ~$15–40k/mo instead of $279k?** Re-run the model first.
2. **Accept the AdSense placement risk on the inbox route, or route-split now?**
3. **Publish the domain pool?** Publishing burned domains only is the default. Full publication buys
   goodwill but converts domain life from months to days.
4. **Does a user-chosen public address namespace exist at all?** It is a real UX expectation and
   structurally a public bulletin board.
5. **Reserve a paid tier?** Don't build billing now, but keep a `plan` column. ~50% of the audience is
   unmonetizable by adblock. If it happens, a merchant of record (Paddle) beats a PSP — VAT/GST
   registration across 25 countries is not a 3-person-team task.
6. **Who owns the Cloudflare and registrar accounts, and what is the recovery path if that person is
   unavailable?** For a team this size, single-person credential control is a more probable cause of
   total loss than any technical failure in this repo.

---

## The full output

Both raw documents are archived in [`research/`](research/):

| File | What |
|---|---|
| [`2026-08-27-stack-synthesis.md`](research/2026-08-27-stack-synthesis.md) | Full synthesis — stack tables, cost arithmetic line by line, revised 24-week sequence |
| [`2026-08-27-critique-findings.md`](research/2026-08-27-critique-findings.md) | All 63 adversarial findings with evidence and suggested fixes |

Both carry a header explaining that they recommend the Cloudflare stack we did not choose. Read them
for the reasoning, not the recommendations.
