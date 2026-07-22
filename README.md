# tessara

Developer-focused brand asset generator. Give it a source logo (SVG or PNG)
and it generates the platform-specific assets a web/app project needs:
favicons, Apple touch icons, Android/PWA icons, OpenGraph images, web
manifests, and the HTML snippets to wire them up.

## Layout

This is a [uv workspace](https://docs.astral.sh/uv/concepts/projects/workspaces/)
with one reusable core library and two thin interfaces on top of it:

```
packages/
  tessara-core/     Image generation logic (Pillow + CairoSVG). No CLI/web deps.
apps/
  tessara-cli/      Typer CLI: `tessara generate logo.svg --preset web`
  tessara-server/   FastAPI server: upload -> generate -> download zip
```

`tessara-core` exposes a plain Python API:

```python
from tessara import BrandAssetBuilder

builder = BrandAssetBuilder("logo.svg")
builder.generate(["favicon"])
builder.write("./output")
```

## Setup

```bash
uv sync --all-packages
```

Note: a plain `uv sync` only installs the workspace root's own dependencies
(this root package has no code, it just declares the workspace). Use
`--all-packages` to install every app/package, or `cd` into a specific
package/app and run `uv sync` there.

## Usage

```bash
uv run --package tessara-cli tessara generate logo.svg --preset web --output ./out
uv run --package tessara-cli tessara presets
```

## Tests

```bash
uv run --package tessara-core pytest packages/tessara-core/tests
```

## Status

Early scaffolding. Only the `favicon` asset group is implemented so far
(16x16/32x32/48x48 PNGs + a multi-resolution favicon.ico). `apple`,
`android`, and `opengraph` groups, the webmanifest, and the server app are
not yet implemented.
