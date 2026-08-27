# syntax=docker/dockerfile:1
#
# Multi-stage. `dev` mounts source and hot-reloads; `runner` is the deployable image.
# Build a specific stage with:  docker build --target runner .

# ---------------------------------------------------------------- base
FROM python:3.12-slim-bookworm AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    UV_LINK_MODE=copy \
    UV_COMPILE_BYTECODE=1 \
    PATH="/app/.venv/bin:$PATH"

COPY --from=ghcr.io/astral-sh/uv:0.5.11 /uv /uvx /bin/
WORKDIR /app

# ---------------------------------------------------------------- deps
# Dependencies resolve from the lockfile alone, so this layer is cached until
# pyproject.toml or uv.lock actually change — not on every source edit.
FROM base AS deps
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# ---------------------------------------------------------------- dev
FROM deps AS dev
# Dev dependencies (pytest, ruff, mypy, aiosmtpd) on top of the cached runtime layer.
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen
COPY . .
EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000", "--reload"]

# ---------------------------------------------------------------- runner
FROM base AS runner

# Never run as root. If the MIME parser is ever exploited, this is what stands
# between a parser bug and the container. See docs/SECURITY.md section 5.
RUN groupadd --system --gid 1001 app \
 && useradd --system --uid 1001 --gid app --create-home app

COPY --from=deps --chown=app:app /app/.venv /app/.venv
COPY --chown=app:app . .

USER app
EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://127.0.0.1:8000/health').status==200 else 1)"

# Uvicorn workers under Gunicorn — see CLAUDE.md section 3.
CMD ["gunicorn", "app.main:app", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--workers", "4", \
     "--bind", "0.0.0.0:8000", \
     "--access-logfile", "-"]
