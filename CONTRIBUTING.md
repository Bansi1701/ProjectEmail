# Contributing

## Before you start

Read [`CLAUDE.md`](CLAUDE.md). It is the source of truth for stack decisions, the
non-negotiable security rules, and conventions — for humans and AI assistants alike.

## Workflow

1. Branch: `feat/short-description` or `fix/short-description`
2. Commit with [Conventional Commits](https://www.conventionalcommits.org/): `feat:`, `fix:`, `docs:`, `refactor:`, `test:`, `chore:`
3. Run the checks for the side you touched:

```bash
C="docker compose -f infra/docker/compose.yml"

# Backend
$C exec api ruff check --fix . && $C exec api mypy app/ && $C exec api pytest

# Frontend
$C exec web pnpm check && $C exec web pnpm typecheck && $C exec web pnpm test
```

Without Docker: `cd backend && uv run ruff check --fix . && uv run mypy app/ && uv run pytest`
and `cd frontend && pnpm check && pnpm typecheck && pnpm test`.

4. Open a PR describing what changed and why.

## Rules that override tickets

The [non-negotiable rules](CLAUDE.md#4-non-negotiable-rules) encode failure modes that have
killed real services in this category. If a task conflicts with one, follow the rule and raise
the conflict. In particular:

- Never combine `allow-scripts` with `allow-same-origin` on the email iframe.
- Never add an SMTP client or sending library. The platform is inbound-only, permanently.
- Never weaken a security control or disable a type check to make something pass.

If a security test fails, fix the code — not the test.

## Architectural decisions

Changing something in the [stack table](CLAUDE.md#3-the-stack--current-defaults)
needs an ADR in [`docs/adr/`](docs/adr/). Copy the format of an existing one: context, decision,
rationale, consequences, alternatives considered.

## Ask a human about

- Anything that would send email, extend data retention, or weaken the iframe sandbox
- Ad network integration and SSP configuration — policy violations can demonetize the whole site
- Adding an inbound-mail provider or moving domains
