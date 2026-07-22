# PRODUCTION image — installs tessera-core as a real published dependency
# (PyPI or a private index) instead of building it from local workspace
# source, and is meant to run against Postgres. This does NOT build until
# tessera-core is actually published somewhere `uv` can reach — see
# Dockerfile.dev for a fully-working local/SQLite alternative today.
#
# Build context is THIS package only (apps/tessera-server) — no monorepo
# checkout needed, unlike Dockerfile.dev.
#
# Build from apps/tessera-server/ with:
#   docker build -f deployment/Dockerfile \
#     --build-arg UV_INDEX_URL=https://your-index.example/simple \
#     -t tessera-server .
#
# If your index requires auth, pass credentials as a BuildKit secret rather
# than a build-arg (build-args land in image history):
#   docker build -f deployment/Dockerfile \
#     --secret id=uv_index_password,env=UV_INDEX_PASSWORD ...
# and uncomment the --mount=type=secret line below.

# ======================================
# Stage 1: frontend assets (esbuild)
# ======================================
FROM node:22-slim AS frontend

WORKDIR /app

COPY package.json package-lock.json ./
RUN npm ci

COPY build.mjs ./
COPY static/js/src static/js/src
RUN npm run build

# ======================================
# Stage 2: Python dependencies (uv)
# ======================================
FROM python:3.13-slim AS python-deps

COPY --from=ghcr.io/astral-sh/uv:0.9 /uv /uvx /bin/

ARG UV_INDEX_URL=https://pypi.org/simple
ENV UV_INDEX_URL=${UV_INDEX_URL} \
    UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

# cairosvg (a tessera-core dependency) needs libcairo2's headers to build its
# native extension at install time — the runtime stage below only needs the
# shared library itself, not the -dev headers.
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential libcairo2-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

# --no-sources: ignore [tool.uv.sources]'s workspace-path override for
# tessera-core (that only makes sense inside the monorepo checkout) and
# resolve it from UV_INDEX_URL instead, using the version pin in
# pyproject.toml's dependencies list.
#
# Editable, not --no-editable: tessera-server's PROJECT_ROOT (constants.py)
# is computed from __file__ and assumes the source tree's original nesting
# (src/tessera_server/.. == this directory, where static/ and templates/
# actually live) — that only holds for an editable install. A --no-editable
# wheel install puts tessera_server in site-packages instead, which breaks
# static/template resolution entirely. tessera-server is never meant to be a
# published wheel anyway (always deployed from a source checkout), so
# editable is the correct mode here, not a workaround.
# RUN --mount=type=secret,id=uv_index_password,env=UV_INDEX_PASSWORD \
RUN uv sync --no-dev --no-sources \
    --extra postgres --extra metrics

# ======================================
# Stage 3: runtime
# ======================================
FROM python:3.13-slim AS runtime

# Just the shared library cairosvg loads at import time — no compiler needed.
RUN apt-get update && apt-get install -y --no-install-recommends \
    libcairo2 \
    && rm -rf /var/lib/apt/lists/*

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PATH="/app/.venv/bin:$PATH"

WORKDIR /app

COPY --from=python-deps /app /app
COPY --from=frontend /app/static/js/dist static/js/dist

EXPOSE 8000

# No curl/wget in python:3.13-slim — stdlib urllib instead of adding a package.
HEALTHCHECK --interval=30s --timeout=3s --start-period=10s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=2)" || exit 1

# Migrations are a deliberate deploy step, not something that happens
# implicitly on every container start/restart — run them yourself, e.g.:
#   docker compose run --rm tessera-server alembic upgrade head
CMD ["gunicorn", "-c", "gunicorn.conf.py"]
