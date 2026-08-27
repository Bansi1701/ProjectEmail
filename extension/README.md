# Browser Extension — Phase 2

A "1-Click Temp Mail" extension for Chrome, Firefox and Edge. Not yet started.

**Planned stack:** [WXT](https://wxt.dev/) — Vite-based, one codebase targeting all three
browsers on Manifest V3.

## Verify before building

The business plan proposes serving ads inside a framed window in the extension. **Check that
against Chrome Web Store policy and Google publisher policy first** — extension surfaces are
treated differently from web pages, and this may not be permitted.

The compliant pattern, if it isn't: the extension opens a real tab on the main domain, which
is where the ads live. That also keeps ad revenue attached to the domain accumulating SEO
authority.

See [`docs/ROADMAP.md`](../docs/ROADMAP.md) Phase 2.
