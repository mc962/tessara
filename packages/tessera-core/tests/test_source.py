from __future__ import annotations

from pathlib import Path

import pytest

from tessera.source import Source, UnsupportedSourceFormatError


def test_render_svg_preserves_aspect_ratio(sample_svg: Path) -> None:
    source = Source(sample_svg)
    rendered = source.render(64)

    assert rendered.mode == "RGBA"
    # Source SVG is 200x100 (2:1) -> longest side (width) hits the target size.
    assert rendered.width == 64
    assert rendered.height == 32


def test_render_png_preserves_aspect_ratio(sample_png: Path) -> None:
    source = Source(sample_png)
    rendered = source.render(64)

    assert rendered.mode == "RGBA"
    # Source PNG is 300x150 (2:1) -> longest side (width) hits the target size.
    assert rendered.width == 64
    assert rendered.height == 32


def test_missing_file_raises(tmp_path: Path) -> None:
    with pytest.raises(FileNotFoundError):
        Source(tmp_path / "missing.svg")


def test_unsupported_format_raises(tmp_path: Path) -> None:
    bogus = tmp_path / "logo.gif"
    bogus.write_bytes(b"not a real gif")
    with pytest.raises(UnsupportedSourceFormatError):
        Source(bogus)
