from __future__ import annotations

from io import BytesIO
from pathlib import Path

import cairosvg
from PIL import Image

SUPPORTED_SUFFIXES = (".svg", ".png")


class UnsupportedSourceFormatError(ValueError):
    """Raised when the source file extension isn't one tessera knows how to render."""


class Source:
    """A brand source image that can render itself at a target size.

    Rendering always preserves the original aspect ratio: the longest side is
    scaled to `size` pixels, the other side scales proportionally. Callers that
    need a square result should pass the render through `canvas.pad_to_square`.
    """

    def __init__(self, path: str | Path) -> None:
        self.path = Path(path)
        if not self.path.exists():
            raise FileNotFoundError(f"Source image not found: {self.path}")
        self._suffix = self.path.suffix.lower()
        if self._suffix not in SUPPORTED_SUFFIXES:
            raise UnsupportedSourceFormatError(
                f"Unsupported source format {self._suffix!r}; expected one of {SUPPORTED_SUFFIXES}"
            )

    @property
    def is_vector(self) -> bool:
        return self._suffix == ".svg"

    def render(self, size: int) -> Image.Image:
        """Render the source as an RGBA image whose longest side is `size` pixels."""
        if self.is_vector:
            return self._render_svg(size)
        return self._render_raster(size)

    def _render_svg(self, size: int) -> Image.Image:
        # Probe the SVG's natural pixel size first so we can request an exact
        # width/height from cairosvg and preserve aspect ratio precisely,
        # rather than relying on it to infer scaling from a single dimension.
        probe_bytes = cairosvg.svg2png(url=str(self.path))
        with Image.open(BytesIO(probe_bytes)) as probe:
            natural_width, natural_height = probe.size

        scale = size / max(natural_width, natural_height)
        target_width = max(1, round(natural_width * scale))
        target_height = max(1, round(natural_height * scale))

        png_bytes = cairosvg.svg2png(
            url=str(self.path),
            output_width=target_width,
            output_height=target_height,
        )
        with Image.open(BytesIO(png_bytes)) as img:
            return img.convert("RGBA")

    def _render_raster(self, size: int) -> Image.Image:
        with Image.open(self.path) as img:
            rendered = img.convert("RGBA")
        rendered.thumbnail((size, size), Image.LANCZOS)
        return rendered
