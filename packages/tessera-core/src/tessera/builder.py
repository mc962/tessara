from __future__ import annotations

import json
from pathlib import Path

from PIL import Image

from .canvas import pad_to_canvas, pad_to_square
from .groups import ASSET_GROUPS, GROUP_DEPENDENCIES, KNOWN_GROUPS
from .snippets import html_snippets
from .source import Source
from .specs import CanvasImageSpec, IcoSpec, ImageSpec

# Fixed so PNG output bytes are identical across runs given the same input and
# Pillow version (no timestamp or platform-dependent compression heuristics).
PNG_COMPRESS_LEVEL = 9

ANDROID_ICON_SIZES: tuple[int, ...] = (192, 512)


class UnknownAssetGroupError(ValueError):
    """Raised when `generate()` is asked for a group tessera doesn't know about."""


class BrandAssetBuilder:
    """Generates platform-specific brand assets from a single source image.

    Usage:
        builder = BrandAssetBuilder("logo.svg", app_name="Acme")
        builder.generate(["favicon", "apple", "android", "webmanifest"])
        builder.write("./output")
    """

    def __init__(
        self,
        source_path: str | Path,
        *,
        app_name: str | None = None,
        theme_color: str = "#ffffff",
        background_color: str = "#ffffff",
    ) -> None:
        self.source = Source(source_path)
        self.app_name = app_name or self.source.path.stem
        self.theme_color = theme_color
        self.background_color = background_color

        self._generated: dict[str, Image.Image] = {}
        self._ico_sizes: dict[str, tuple[int, ...]] = {}
        self._files: dict[str, bytes] = {}
        self._groups: list[str] = []

    def generate(self, groups: list[str]) -> "BrandAssetBuilder":
        for group_name in self._expand_groups(groups):
            if group_name not in self._groups:
                self._groups.append(group_name)
            if group_name == "webmanifest":
                self._generate_webmanifest()
                continue
            for spec in ASSET_GROUPS[group_name]:
                self._generate_one(spec)
        return self

    def _expand_groups(self, groups: list[str]) -> list[str]:
        expanded: list[str] = []
        for name in groups:
            if name not in KNOWN_GROUPS:
                raise UnknownAssetGroupError(
                    f"Unknown asset group {name!r}; available: {sorted(KNOWN_GROUPS)}"
                )
            for dependency in GROUP_DEPENDENCIES.get(name, ()):
                if dependency not in expanded:
                    expanded.append(dependency)
            if name not in expanded:
                expanded.append(name)
        return expanded

    def _generate_one(self, spec: ImageSpec | IcoSpec | CanvasImageSpec) -> None:
        if isinstance(spec, ImageSpec):
            rendered = self.source.render(spec.size)
            self._generated[spec.filename] = pad_to_square(
                rendered, spec.size, spec.padding, spec.background
            )
        elif isinstance(spec, IcoSpec):
            largest = max(spec.sizes)
            rendered = self.source.render(largest)
            self._generated[spec.filename] = pad_to_square(rendered, largest, spec.padding)
            self._ico_sizes[spec.filename] = spec.sizes
        elif isinstance(spec, CanvasImageSpec):
            rendered = self.source.render(max(spec.width, spec.height))
            self._generated[spec.filename] = pad_to_canvas(
                rendered, spec.width, spec.height, spec.padding, spec.background
            )
        else:  # pragma: no cover - defensive, specs are exhaustive today
            raise TypeError(f"Unsupported spec type: {type(spec)!r}")

    def _generate_webmanifest(self) -> None:
        manifest = {
            "name": self.app_name,
            "short_name": self.app_name,
            "icons": [
                {
                    "src": f"/android-chrome-{size}x{size}.png",
                    "sizes": f"{size}x{size}",
                    "type": "image/png",
                }
                for size in ANDROID_ICON_SIZES
            ],
            "theme_color": self.theme_color,
            "background_color": self.background_color,
            "display": "standalone",
        }
        self._files["site.webmanifest"] = json.dumps(manifest, indent=2).encode("utf-8") + b"\n"

    def html_snippets(self) -> list[str]:
        """HTML <head> tags for every group generated so far, deduped and ordered."""
        return html_snippets(self._groups)

    def write(self, output_dir: str | Path) -> list[Path]:
        """Write all generated assets to `output_dir`, creating it if needed."""
        output_dir = Path(output_dir)
        output_dir.mkdir(parents=True, exist_ok=True)

        written: list[Path] = []
        for filename in sorted(set(self._generated) | set(self._files)):
            path = output_dir / filename
            if filename in self._generated:
                image = self._generated[filename]
                if filename in self._ico_sizes:
                    sizes = sorted(self._ico_sizes[filename])
                    image.save(path, format="ICO", sizes=[(s, s) for s in sizes])
                else:
                    image.save(
                        path, format="PNG", optimize=True, compress_level=PNG_COMPRESS_LEVEL
                    )
            else:
                path.write_bytes(self._files[filename])
            written.append(path)
        return written
