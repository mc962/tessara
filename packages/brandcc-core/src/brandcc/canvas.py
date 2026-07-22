from __future__ import annotations

from PIL import Image


def pad_to_canvas(
    image: Image.Image,
    width: int,
    height: int,
    padding: float = 0.0,
    background: tuple[int, int, int, int] = (0, 0, 0, 0),
) -> Image.Image:
    """Center `image` on a width x height RGBA canvas.

    The image is fit within the canvas preserving its aspect ratio. `padding`
    is the fraction of the canvas reserved as empty margin on each side
    (0.0 = content may touch the edges, 0.2 = 20% margin on every side).

    `background` fills the canvas before the image is composited on top; it
    defaults to fully transparent. Pass an opaque color (alpha=255) for
    surfaces that render transparency badly, e.g. iOS shows transparent
    apple-touch-icon pixels as black.
    """
    if not 0.0 <= padding < 0.5:
        raise ValueError("padding must be in [0.0, 0.5)")

    content_width = max(1, round(width * (1 - 2 * padding)))
    content_height = max(1, round(height * (1 - 2 * padding)))
    fitted = image.copy()
    fitted.thumbnail((content_width, content_height), Image.LANCZOS)

    canvas = Image.new("RGBA", (width, height), background)
    offset = ((width - fitted.width) // 2, (height - fitted.height) // 2)
    canvas.paste(fitted, offset, fitted)
    if background[3] == 255:
        # Guarantee a fully opaque result even where `fitted` had semi-transparent
        # edge pixels that alpha-blended with the (opaque) background.
        canvas.putalpha(255)
    return canvas


def pad_to_square(
    image: Image.Image,
    size: int,
    padding: float = 0.0,
    background: tuple[int, int, int, int] = (0, 0, 0, 0),
) -> Image.Image:
    """Center `image` on a size x size RGBA canvas. See `pad_to_canvas`."""
    return pad_to_canvas(image, size, size, padding, background)
