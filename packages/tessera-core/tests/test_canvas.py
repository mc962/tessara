from __future__ import annotations

import pytest
from PIL import Image

from tessera.canvas import pad_to_canvas, pad_to_square


def test_pad_to_square_centers_and_preserves_transparency() -> None:
    # 64x32 opaque image -> 64x64 canvas, centered with transparent bars top/bottom.
    content = Image.new("RGBA", (64, 32), (255, 0, 0, 255))
    result = pad_to_square(content, 64)

    assert result.size == (64, 64)
    assert result.getpixel((32, 32)) == (255, 0, 0, 255)
    assert result.getpixel((0, 0))[3] == 0  # corner is transparent
    assert result.getpixel((32, 0))[3] == 0  # top-center margin is transparent


def test_pad_to_square_applies_padding_margin() -> None:
    content = Image.new("RGBA", (64, 64), (0, 255, 0, 255))
    result = pad_to_square(content, 100, padding=0.25)

    # 25% margin on each side -> content should not reach within 25px of any edge.
    assert result.getpixel((10, 50))[3] == 0
    assert result.getpixel((50, 50))[3] != 0


def test_pad_to_square_rejects_invalid_padding() -> None:
    content = Image.new("RGBA", (10, 10), (0, 0, 0, 255))
    with pytest.raises(ValueError):
        pad_to_square(content, 32, padding=0.5)


def test_pad_to_square_opaque_background_fills_margin_and_stays_opaque() -> None:
    # 32x16 content on a 32x32 canvas with an opaque white background: the
    # top/bottom margin should be solid white, not transparent.
    content = Image.new("RGBA", (32, 16), (255, 0, 0, 255))
    result = pad_to_square(content, 32, background=(255, 255, 255, 255))

    assert result.getpixel((16, 0)) == (255, 255, 255, 255)
    assert result.getpixel((16, 16)) == (255, 0, 0, 255)


def test_pad_to_square_opaque_background_flattens_semi_transparent_edges() -> None:
    # A source with a semi-transparent pixel shouldn't leave any residual
    # transparency once composited onto an opaque background.
    content = Image.new("RGBA", (4, 4), (255, 0, 0, 128))
    result = pad_to_square(content, 4, background=(255, 255, 255, 255))

    assert all(result.getpixel((x, y))[3] == 255 for x in range(4) for y in range(4))


def test_pad_to_canvas_supports_non_square_dimensions() -> None:
    # Square content on a wide 1200x630 canvas: should be centered horizontally
    # and vertically, not stretched to fill the whole rectangle.
    content = Image.new("RGBA", (64, 64), (255, 0, 0, 255))
    result = pad_to_canvas(content, 1200, 630, background=(255, 255, 255, 255))

    assert result.size == (1200, 630)
    assert result.getpixel((600, 315)) == (255, 0, 0, 255)  # center is content
    assert result.getpixel((0, 0)) == (255, 255, 255, 255)  # corners are background
