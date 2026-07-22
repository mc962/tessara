from __future__ import annotations

from pathlib import Path

import pytest

SAMPLE_SVG = """\
<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">
  <rect width="64" height="64" fill="#3366ff"/>
</svg>
"""


@pytest.fixture
def sample_svg(tmp_path: Path) -> Path:
    path = tmp_path / "logo.svg"
    path.write_text(SAMPLE_SVG)
    return path
