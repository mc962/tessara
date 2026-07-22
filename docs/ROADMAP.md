# Roadmap

## Done

- `brandcc-core`: `favicon`, `apple`, `android`, `opengraph` asset groups, plus
  `webmanifest` (JSON, depends on `android`). Deterministic PNG/ICO output,
  aspect-ratio-preserving SVG/PNG rendering, transparent or opaque-background
  canvas compositing.
- `brandcc-cli`: `brandcc generate <source> --preset <web|pwa|social|everything>`,
  runs entirely locally against `brandcc-core`. `brandcc presets` lists presets.

## Next: `brandcc-server`

Minimal FastAPI app: upload an image, pick a preset/options, get a zip back.
No auth, no database, no users. Nail down the request/response contract here
first — the CLI's remote mode (below) is a thin client built on top of it, so
building both at once risks reworking the client every time the API shape
changes mid-flight.

## After that: CLI remote mode

The CLI becomes a dual-mode client for `brandcc-core`, not just a local
wrapper:

- **Local mode** (current behavior): `brandcc generate ...` calls
  `brandcc-core` directly in-process. Requires Pillow/CairoSVG installed
  locally.
- **Remote mode**: commands prefixed with `web` (e.g. `brandcc web generate
  ...`) send the request to a configured `brandcc-server` instead — same
  options/flags as the local command. Lets a low-power/thin client (e.g. a
  Raspberry Pi) offload the actual image processing to a bigger machine
  running the server, without installing the full processing stack locally.
- Server URL is configurable via env var and/or a config file (exact
  mechanism TBD when this is implemented).
- HTTP client: **aiohttp**.

Implementation order: finish `brandcc-server`'s API first, confirm it with
real round-trips (including error cases), then add the `web`-prefixed
commands to `brandcc-cli` against the settled contract.

## Later: server-side admin CLI

`brandcc-server` will eventually need basic user provisioning (accounts,
API access, etc.), backed by a real database with migrations. That brings a
small on-server admin CLI — separate from `brandcc-cli`, which stays the
user-facing local/remote asset-generation tool. The admin CLI is about
server-side ops (provisioning, maintenance), not asset generation.

Leaning towards: a submodule inside `brandcc-server` (e.g.
`brandcc_server.cli`, exposed via its own `[project.scripts]` entry) rather
than a separate workspace app, unless it turns out to need independent
deployment/versioning from the server itself.
