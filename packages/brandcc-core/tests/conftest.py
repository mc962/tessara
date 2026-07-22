from __future__ import annotations

from pathlib import Path

import pytest
from PIL import Image

# A simple non-square SVG (wider than tall) so tests can verify aspect-ratio
# preservation, not just "it produced a PNG".
SAMPLE_SVG = """\
<svg xmlns="http://www.w3.org/2000/svg" width="200" height="100" viewBox="0 0 200 100">
  <rect width="200" height="100" fill="#3366ff"/>
  <circle cx="100" cy="50" r="40" fill="#ffffff"/>
</svg>
"""


@pytest.fixture
def sample_svg(tmp_path: Path) -> Path:
    path = tmp_path / "logo.svg"
    path.write_text(SAMPLE_SVG)
    return path


@pytest.fixture
def sample_png(tmp_path: Path) -> Path:
    path = tmp_path / "logo.png"
    # Non-square, RGBA source with a transparent border to exercise real alpha.
    image = Image.new("RGBA", (300, 150), (0, 0, 0, 0))
    solid = Image.new("RGBA", (200, 100), (51, 102, 255, 255))
    image.paste(solid, (50, 25))
    image.save(path, format="PNG")
    return path
