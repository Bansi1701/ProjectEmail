# Database

> **Living document — v0.1.**

For the MVP, Postgres holds the domain pool, API keys, inboxes, and messages. Inbox and message
rows carry `expires_at`; every read filters expired data and a periodic sweeper physically deletes
it. See [ADR 0003](adr/0003-no-redis-for-mvp.md).

Postgres is therefore on the MVP critical path. The application warms Neon on boot, uses
`pool_pre_ping`, and exposes dependency state separately at `/health/ready`.

---

## Connecting to Neon

### 1. Create the project

Sign up at [neon.tech](https://neon.tech), create a project, and pick the region closest to where
the app servers run — this is a network round trip on every query.

### 2. Copy both connection strings

Neon gives you two endpoints and you need both:

| Endpoint | Host contains | Use for |
|---|---|---|
| **Pooled** | `-pooler` | The application. PgBouncer fronts it, so it survives many short-lived connections |
| **Direct** | no `-pooler` | Migrations. DDL through PgBouncer is unreliable |

### 3. Set them — in the right file

**Which file depends on how you run the backend, and getting this wrong fails silently.**

| How you run it | File | Why |
|---|---|---|
| **Docker** (the default) | `infra/docker/.env` | Compose injects `DATABASE_URL` into the container as an environment variable, and pydantic-settings ranks env vars **above** `.env` files. `backend/.env` is not read inside the container at all |
| Natively (`uv run uvicorn`) | `backend/.env` | No container, no injected env var, so the dotenv file is what loads |

```bash
# infra/docker/.env  — Docker
DATABASE_URL=postgresql://USER:PASS@ep-xxx-pooler.REGION.aws.neon.tech/neondb?sslmode=require
MIGRATION_DATABASE_URL=postgresql://USER:PASS@ep-xxx.REGION.aws.neon.tech/neondb?sslmode=require
```

Then `docker compose -f infra/docker/compose.yml up -d api` to pick it up.

Paste both exactly as the Console gives them. No rewriting needed — see below.

**Confirm which database you are actually on** (this is why the silent failure is survivable):

```bash
docker compose -f infra/docker/compose.yml exec api python -c \
  "from app.core.config import get_settings; print(get_settings().database_url[:60])"
```

### 4. Migrate

```bash
docker compose -f infra/docker/compose.yml exec api alembic upgrade head
```

---

## Three Neon gotchas, already handled

Each produces an error that does not obviously point at the cause. All three are dealt with in
[`app/core/db.py`](../backend/app/core/db.py) and covered by
[`test_db_url.py`](../backend/tests/unit/test_db_url.py).

### `sslmode` is not an asyncpg parameter

Neon's dashboard appends `?sslmode=require&channel_binding=require`. Those are **libpq**
parameters, and asyncpg is not libpq:

```
TypeError: connect() got an unexpected keyword argument 'sslmode'
```

`normalize_database_url()` strips them and translates to asyncpg's `ssl` connect arg. You can paste
the URL unmodified.

### PgBouncer breaks prepared statements

The pooled endpoint runs PgBouncer in **transaction mode**, where prepared statements are not safe.
Under concurrency you get:

```
DuplicatePreparedStatementError / InvalidSQLStatementNameError
```

Both caches are disabled automatically when the host contains `-pooler` — asyncpg's
`statement_cache_size` and SQLAlchemy's `prepared_statement_cache_size`. The direct endpoint keeps
caching, because there it is a genuine win.

### Scale-to-zero kills pooled connections

Neon suspends an idle compute. Connections held across a suspend are dead, and without a pre-ping
the first request after idle fails rather than reconnecting. Handled by `pool_pre_ping=True` and a
short `pool_recycle`. The app also touches the database on boot so the first real request does not
pay the cold start.

---

## Local vs Neon

Keep using the Docker Postgres for local work — it is instant, offline, and free. Neon belongs in
staging and production, where the managed backups and branching earn their keep.

Nothing in the code branches on this. `DATABASE_URL` decides, and
[`db.py`](../backend/app/core/db.py) adapts pooling and TLS to whichever it finds.

**Neon database branching** is worth knowing about: `neonctl branches create` gives you a
copy-on-write branch of production data in seconds. Useful for testing a migration against real
data shapes before it runs for real.

---

## Schema

```
domains                          the rotating mail pool
  id, name, status, registrar, expires_at,
  blacklist_hits, last_checked_at, messages_received,
  is_published, created_at, updated_at
  index: (status, created_at)    -- "give me a domain for a new inbox"

api_keys                         public developer API, Phase 2
  id, key_hash, key_prefix, label,
  rate_limit_per_minute, last_used_at, revoked_at
  index: key_hash (unique)

inboxes                          short-lived possession-token protected inboxes
  id, address, token_hash, expires_at, created_at, updated_at
  indexes: address (unique), expires_at

messages                         sanitized short-lived inbound messages
  id, inbox_id, sender, subject, text_body, html_body,
  otp, verification_link, received_at, expires_at
  indexes: (inbox_id, received_at), expires_at
```

`domains.status` runs `warming → active → draining → retired`. Rotation drains rather than cuts:
a degrading domain stops taking new inboxes while existing ones keep working until they expire.

**Only mail domains live here.** The brand domain carrying the site and its SEO authority is never
in this table and never receives mail, so it cannot be blacklisted. Conflating the two would
destroy accumulated rankings on every rotation.

Only the **hash** of an API key is stored. A leaked database must not yield usable keys.

---

## Migrations

```bash
C="docker compose -f infra/docker/compose.yml"

$C exec api alembic revision --autogenerate -m "what changed"
$C exec api alembic upgrade head
$C exec api alembic downgrade -1
$C exec api alembic current
```

Always read a generated migration before applying it. Autogenerate detects type and server-default
changes here (`compare_type` and `compare_server_default` are on), but it does not detect renames —
it sees a drop plus an add, which silently destroys data.
