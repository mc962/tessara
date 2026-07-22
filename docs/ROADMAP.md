# Roadmap

## Done

- `tessera-core`: `favicon`, `apple`, `android`, `opengraph` asset groups, plus
  `webmanifest` (JSON, depends on `android`). Deterministic PNG/ICO output,
  aspect-ratio-preserving SVG/PNG rendering, transparent or opaque-background
  canvas compositing. Presets (`minimal`, `web`, `pwa`, `social`, `everything`)
  plus a `REMOVED_PRESETS` registry so a dropped preset can get a specific
  "this was removed, use X instead" message instead of a generic "unknown
  preset" one.
- `tessera-cli`: `tessera generate <source> --preset <...>` runs locally
  against `tessera-core` (needs the `tessera-cli[local]` extra). `tessera
  presets` lists presets. `tessera web generate <source> --server ...
  --api-key ...` sends the request to a `tessera-server` instead — the CLI's
  base install has no dependency on `tessera-core`/Pillow/cairosvg, so a
  remote-only client (e.g. a Pi) never needs the native image stack. Server
  URL / API key resolve in order: CLI flag > env var > `~/.config/tessera/
  config.toml` > interactive prompt (hidden input) if none of those are set.
- `tessera-server`: FastAPI app with SQLite/Postgres-backed API keys
  (superuser vs. regular), session-cookie auth for the browser UI and Bearer
  auth for the API. `POST /generate` (session, any active key) and `POST
  /api/generate` (Bearer, any active key) both wrap the same
  `service/generation.py` upload -> `BrandAssetBuilder` -> zip path. Only
  `/admin/api-keys` (key management) requires a superuser key — generation
  itself doesn't. htmx-driven admin UI, esbuild-bundled JS/CSS
  (`npm run build` / `npm run watch`).
- Server-side admin CLI: `tessera-server-admin create-key --name ... [--superuser]`
  (`tessera_server.cli`, its own `[project.scripts]` entry, as originally
  planned below — ended up living inside `tessera-server` rather than a
  separate workspace app).
- Upload size caps (regular keys vs. superuser keys get different limits,
  `upload_max_bytes` / `upload_max_bytes_superuser` in settings) and rate
  limiting (`slowapi`, in-memory, keyed by client IP) on `/generate`,
  `/api/generate`, and `/admin/login` — generation being open to any active
  key made both worth doing.
- `tessera-cli` test suite (didn't exist before this): `presets.py`,
  `config.py`'s resolution precedence, `remote.py` (against a real local
  aiohttp test server, not mocks), and `main.py`'s commands via
  `typer.testing.CliRunner` — including the tessera-core-missing and
  rate-limit-agnostic error paths. 24 tests, 99% coverage (the one gap is the
  `if __name__ == "__main__"` guard).
- `tessera-server` deployment, both Docker and systemd/LXC, each in prod and
  dev variants (`apps/tessera-server/deployment/`):
  - `Dockerfile` + `docker-compose.yml` (prod): installs `tessera-core` as a
    real published dependency (`uv sync --no-sources`, build context is just
    `apps/tessera-server`) against Postgres. Doesn't build until
    `tessera-core` is actually published somewhere `UV_INDEX_URL` can reach.
  - `Dockerfile.dev` + `docker-compose.dev.yml`: builds `tessera-core` from
    local workspace source instead (build context is the whole repo),
    SQLite. Fully working today — verified end to end (build, migrate,
    `/health`, `/`, `/favicon.ico`, bundled CSS all serving correctly).
  - Both Dockerfiles have a `HEALTHCHECK` hitting `/health` (stdlib
    `urllib`, no `curl`/`wget` needed in the slim base) — verified
    `docker inspect` reports `"Status": "healthy"`.
- Fixed the broken `tessera-server` console script — `main.py` had no `run()`
  even though `pyproject.toml` pointed `tessera-server = "tessera_server.main:run"`
  at it. Added a thin `uvicorn.run(...)` wrapper for quick local/dev use
  (production still goes through `gunicorn -c gunicorn.conf.py`).
  - `systemd/tessera-server.service` + `.env.example`: LXC-oriented unit
    (matches memrix's LXC hardening profile, not the stricter VM one),
    Postgres by default with a commented SQLite alternative. Assumes a
    published `tessera-core`, same as the prod Docker image — deploy just
    `apps/tessera-server`, not the whole monorepo.
  - Migrations (`alembic upgrade head`) are a deliberate manual/deploy-time
    step in all of these, not run automatically on container/service start.
  - Found and fixed a real bug along the way: `tessera-server`'s
    `PROJECT_ROOT` (`constants.py`) is computed from `__file__` and assumes
    the source tree's original nesting, which only holds for an *editable*
    install — a `--no-editable` wheel install (what a naive prod Dockerfile
    would reach for) puts the package in `site-packages` instead and breaks
    static/template resolution entirely. Since `tessera-server` is never
    meant to be a published wheel anyway (always deployed from a source
    checkout), all the Dockerfiles/systemd docs here use editable installs
    deliberately, not as a workaround.
  - These are starting-point templates, not the only valid way to deploy
    this — real deploy setups vary.

## Open items

- **Rate limiting is keyed by IP, not by API key**, for `/api/generate`. Fine
  for a homelab-scale deployment, but means multiple keys behind the same
  NAT/office IP share a bucket, and a key-holder rotating IPs evades the
  limit entirely. Worth a per-key key_func if this ever needs to be load-bearing.
- **Rate limiter state is in-memory and per-process.** If `tessera-server`
  ever runs with more than one gunicorn worker, each worker has its own
  counter — effectively multiplying the real limit by worker count. Not an
  issue at a single worker; revisit if that changes.

- **Rename project to `tessara`.** `tessera`, `tessera-core`, and `tessera-cli`
  are all already taken on PyPI; `tessara` / `tessara-core` / `tessara-cli`
  are free. Do this before publishing anything — touches package names,
  import paths, CLI command name, and branding/copy that leans on the
  "tessera" wordplay (landing page hero, README). Do after the current batch
  of uncommitted work lands, not mid-flight.
- **`PRESETS` is duplicated** between `packages/tessera-core/src/tessera/presets.py`
  and `apps/tessera-cli/src/tessera_cli/presets.py` (deliberately — keeps the
  CLI's base install free of Pillow/cairosvg). Nothing currently checks the
  two stay in sync; changing presets means editing both by hand. A future
  nice-to-have: have each side's test suite check out and diff the other's
  copy — not needed yet at this scale.
- **CLI config file is read-only.** `tessera_cli/config.py` reads
  `~/.config/tessera/config.toml` if present, but there's no command to write
  one (`tessera web config set ...` or similar) — for now it's edited by hand.
- **Publishing to PyPI/Nexus.** Core and CLI are the two candidates (the
  server stays deployed from source, not published). Naming decision: core
  gets the bare `tessara` distribution name (matches its `import tessara`
  import name — no dist-name/import-name mismatch on the package that's
  actually imported by code), CLI stays `tessara-cli`. The CLI doesn't lose
  anything by not getting the bare name — its console-script command is
  `tessara` either way, set by `[project.scripts]` independent of the
  distribution name (same pattern as `httpie`, `python-dotenv`, etc.).
  `tessera-core` is already pinned (`>=0.1.0,<0.2`) in both
  `tessera-server`'s and `tessera-cli[local]`'s `pyproject.toml` — will need
  updating to whatever `tessara-core`'s first published version ends up
  being, once the rename happens.