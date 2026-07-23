# Roadmap

## Done

- `tessara-server`: replaced the single `ApiKey` model (which doubled as both
  a human login credential and a machine Bearer token) with a proper
  two-tier scheme — `User` accounts (email + Argon2 password,
  `is_superuser`/`is_active`/`is_verified`) for browser/admin login, and a
  separate `ApiToken` model (FK'd to a user, up to `max_api_tokens_per_user`
  = 20 by default) for CLI/API Bearer access. Self-service signup requires
  email verification; the admin UI and `tessara-server-admin` CLI can also
  create pre-verified users directly. Any logged-in user manages their own
  tokens at `/account/tokens`; a superuser can additionally manage any
  user's tokens at `/admin/users/{id}/tokens`. No `fastapi-users` dependency
  — it's in maintainer-declared maintenance mode (Oct 2025 notice: critical
  bug fixes only, no new features, unreleased successor), so this is
  hand-rolled on the existing FastAPI/SQLAlchemy/itsdangerous/argon2-cffi
  stack instead. Email verification and password-reset links are signed,
  stateless tokens (itsdangerous, embedding a nonce derived from the
  user's current password hash) — no token table, and a password
  change/reset invalidates outstanding links and sessions for free. SMTP is
  optional: unset `smtp_host` degrades to logging the verification/reset
  link instead of failing, so the server works out of the box without a
  mail server configured (homelab use). Clean-cutover migration — the old
  `api_keys` table is dropped, no backward compatibility, since there was
  no real deployment yet to migrate. `tessara-cli`/`/api/generate` needed
  no changes — a token is still just an opaque `tsa_`-prefixed Bearer
  string from their point of view.

- `tessara-server`: CSRF protection for every cookie-session-authenticated
  state-changing route (`web/csrf.py`) — double-submit cookie pattern.
  `CsrfCookieMiddleware` ensures a `tessara_csrf` cookie exists on every
  request and exposes it as `request.state.csrf_token` for templates;
  plain HTML forms embed it as a hidden `csrf_token` field, htmx requests
  (bare `hx-post` buttons with no form body) get it via a global
  `X-CSRF-Token` header set in `base.html`'s `htmx:configRequest` handler.
  The `verify_csrf` dependency, added explicitly to each mutating route
  (not router-wide, since GET routes and Bearer/JSON API routes must not be
  checked), requires the submitted value to match the cookie. Bearer-token
  routes (`/api/generate`, `/api/api-tokens`) are exempt by design — no
  ambient cookie credential means no CSRF exposure there. Previously the
  only mitigation was `SameSite=Lax` on the session cookie, identified
  earlier as a gap and closed once cookie-session login became the primary
  browser auth path (see the `User`/`ApiToken` entry above). Also restored
  the "Sign out" control, which had been dropped from the nav when the old
  `admin/api_keys.html` (which used to host it) was replaced.

- `tessara-core`: `favicon`, `apple`, `android`, `opengraph` asset groups, plus
  `webmanifest` (JSON, depends on `android`). Deterministic PNG/ICO output,
  aspect-ratio-preserving SVG/PNG rendering, transparent or opaque-background
  canvas compositing. Presets (`minimal`, `web`, `pwa`, `social`, `everything`)
  plus a `REMOVED_PRESETS` registry so a dropped preset can get a specific
  "this was removed, use X instead" message instead of a generic "unknown
  preset" one.
- `tessara-cli`: `tessara generate <source> --preset <...>` runs locally
  against `tessara-core` (needs the `tessara-cli[local]` extra). `tessara
  presets` lists presets. `tessara web generate <source> --server ...
  --api-key ...` sends the request to a `tessara-server` instead — the CLI's
  base install has no dependency on `tessara-core`/Pillow/cairosvg, so a
  remote-only client (e.g. a Pi) never needs the native image stack. Server
  URL / API key resolve in order: CLI flag > env var > `~/.config/tessara/
  config.toml` > interactive prompt (hidden input) if none of those are set.
- `tessara-server`: FastAPI app with SQLite/Postgres-backed API keys
  (superuser vs. regular), session-cookie auth for the browser UI and Bearer
  auth for the API. `POST /generate` (session, any active key) and `POST
  /api/generate` (Bearer, any active key) both wrap the same
  `service/generation.py` upload -> `BrandAssetBuilder` -> zip path. Only
  `/admin/api-keys` (key management) requires a superuser key — generation
  itself doesn't. htmx-driven admin UI, esbuild-bundled JS/CSS
  (`npm run build` / `npm run watch`).
- Server-side admin CLI: `tessara-server-admin create-key --name ... [--superuser]`
  (`tessara_server.cli`, its own `[project.scripts]` entry, as originally
  planned below — ended up living inside `tessara-server` rather than a
  separate workspace app).
- Upload size caps (regular keys vs. superuser keys get different limits,
  `upload_max_bytes` / `upload_max_bytes_superuser` in settings) and rate
  limiting (`slowapi`, in-memory, keyed by client IP) on `/generate`,
  `/api/generate`, and `/admin/login` — generation being open to any active
  key made both worth doing.
- `tessara-cli` test suite (didn't exist before this): `presets.py`,
  `config.py`'s resolution precedence, `remote.py` (against a real local
  aiohttp test server, not mocks), and `main.py`'s commands via
  `typer.testing.CliRunner` — including the tessara-core-missing and
  rate-limit-agnostic error paths. 24 tests, 99% coverage (the one gap is the
  `if __name__ == "__main__"` guard).
- `tessara-server` deployment, both Docker and systemd/LXC, each in prod and
  dev variants (`apps/tessara-server/deployment/`):
  - `Dockerfile` + `docker-compose.yml` (prod): installs `tessara-core` as a
    real published dependency (`uv sync --no-sources`, build context is just
    `apps/tessara-server`) against Postgres. Doesn't build until
    `tessara-core` is actually published somewhere `UV_INDEX_URL` can reach.
  - `Dockerfile.dev` + `docker-compose.dev.yml`: builds `tessara-core` from
    local workspace source instead (build context is the whole repo),
    SQLite. Fully working today — verified end to end (build, migrate,
    `/health`, `/`, `/favicon.ico`, bundled CSS all serving correctly).
  - Both Dockerfiles have a `HEALTHCHECK` hitting `/health` (stdlib
    `urllib`, no `curl`/`wget` needed in the slim base) — verified
    `docker inspect` reports `"Status": "healthy"`.
- Fixed the broken `tessara-server` console script — `main.py` had no `run()`
  even though `pyproject.toml` pointed `tessara-server = "tessara_server.main:run"`
  at it. Added a thin `uvicorn.run(...)` wrapper for quick local/dev use
  (production still goes through `gunicorn -c gunicorn.conf.py`).
  - `systemd/tessara-server.service` + `.env.example`: LXC-oriented unit
    (matches memrix's LXC hardening profile, not the stricter VM one),
    Postgres by default with a commented SQLite alternative. Assumes a
    published `tessara-core`, same as the prod Docker image — deploy just
    `apps/tessara-server`, not the whole monorepo.
  - Migrations (`alembic upgrade head`) are a deliberate manual/deploy-time
    step in all of these, not run automatically on container/service start.
  - Found and fixed a real bug along the way: `tessara-server`'s
    `PROJECT_ROOT` (`constants.py`) is computed from `__file__` and assumes
    the source tree's original nesting, which only holds for an *editable*
    install — a `--no-editable` wheel install (what a naive prod Dockerfile
    would reach for) puts the package in `site-packages` instead and breaks
    static/template resolution entirely. Since `tessara-server` is never
    meant to be a published wheel anyway (always deployed from a source
    checkout), all the Dockerfiles/systemd docs here use editable installs
    deliberately, not as a workaround.
  - These are starting-point templates, not the only valid way to deploy
    this — real deploy setups vary.
- **Renamed the whole project from `tessera` to `tessara`.** The original
  name (and `tessera-core`/`tessera-cli`) was already taken on PyPI by an
  old, unrelated, abandoned package; `tessara`/`tessara-cli` were free. Core
  publishes as bare `tessara` (not `tessara-core` — matches its `import
  tessara` name), CLI as `tessara-cli`, server stays `tessara-server`
  (unpublished, deployed from source). Touched: both workspace directory
  names and the Python import packages inside them
  (`packages/tessera-core/src/tessera` -> `packages/tessara-core/src/tessara`,
  same pattern for `tessera_cli`/`tessera_server`), every `pyproject.toml`
  (including the `--no-sources` production dependency pin, now
  `tessara>=0.1.0,<0.2`), `uv.lock` and `package-lock.json` (regenerated,
  not hand-edited), the `TESSERA_SERVER_URL`/`TESSERA_API_KEY` env vars and
  the CLI's config dir (`~/.config/tessara/`), the `tsr_` API key prefix
  (now `tsa_`), and all branding copy/docstrings/comments. Verified after:
  full test suite (106 tests, all three packages), a real local `tessara
  generate` run, and a real `tessara-server` startup serving `/health`,
  `/`, and `/favicon.ico`. `.idea/` project files weren't touched (gitignored
  IDE-local state — JetBrains will resync on its own).

## Open items

- **Rate limiting is keyed by IP, not by API key**, for `/api/generate`. Fine
  for a homelab-scale deployment, but means multiple keys behind the same
  NAT/office IP share a bucket, and a key-holder rotating IPs evades the
  limit entirely. Worth a per-key key_func if this ever needs to be load-bearing.
- **Rate limiter state is in-memory and per-process.** If `tessara-server`
  ever runs with more than one gunicorn worker, each worker has its own
  counter — effectively multiplying the real limit by worker count. Not an
  issue at a single worker; revisit if that changes.

- **`PRESETS` is duplicated** between `packages/tessara-core/src/tessara/presets.py`
  and `apps/tessara-cli/src/tessara_cli/presets.py` (deliberately — keeps the
  CLI's base install free of Pillow/cairosvg). Nothing currently checks the
  two stay in sync; changing presets means editing both by hand. A future
  nice-to-have: have each side's test suite check out and diff the other's
  copy — not needed yet at this scale.
- **CLI config file is read-only.** `tessara_cli/config.py` reads
  `~/.config/tessara/config.toml` if present, but there's no command to write
  one (`tessara web config set ...` or similar) — for now it's edited by hand.
- **Publishing to PyPI/Nexus.** Core and CLI are the two candidates (the
  server stays deployed from source, not published). Naming already settled
  and in place: core publishes as bare `tessara` (matches its `import
  tessara` name — no dist-name/import-name mismatch), CLI as `tessara-cli`.
  The CLI doesn't lose anything by not getting the bare name — its
  console-script command is `tessara` either way, set by `[project.scripts]`
  independent of the distribution name (same pattern as `httpie`,
  `python-dotenv`, etc.). `tessara` is already pinned (`>=0.1.0,<0.2`) as a
  dependency in both `tessara-server`'s and `tessara-cli[local]`'s
  `pyproject.toml` — will need bumping to match whatever version actually
  gets published first.