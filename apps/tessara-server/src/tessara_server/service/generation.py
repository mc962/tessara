"""Shared upload -> BrandAssetBuilder -> zip logic for the HTML and API generate routes."""

import re
import tempfile
from pathlib import Path

from tessara import (
    PRESETS,
    BrandAssetBuilder,
    UnknownAssetGroupError,
    UnsupportedSourceFormatError,
    describe_unknown_preset,
)

from tessara_server.configuration.settings import application_settings

SUPPORTED_SUFFIXES = (".svg", ".png")
_SAFE_NAME = re.compile(r"[^a-zA-Z0-9_-]+")


def max_upload_bytes(is_superuser: bool) -> int:
    return (
        application_settings.upload_max_bytes_superuser
        if is_superuser
        else application_settings.upload_max_bytes
    )


class GenerationError(ValueError):
    """A user-correctable input problem: bad file type, unknown preset, bad source image."""


class UploadTooLargeError(GenerationError):
    """The uploaded file exceeds the caller's size limit."""


def generate_zip(
    *,
    filename: str,
    content: bytes,
    preset: str,
    app_name: str,
    theme_color: str,
    background_color: str,
    max_bytes: int,
) -> tuple[bytes, str]:
    """Run BrandAssetBuilder over an uploaded file. Returns (zip_bytes, download_filename)."""
    if len(content) > max_bytes:
        raise UploadTooLargeError(
            f"File is {len(content)} bytes, which is over the {max_bytes}-byte limit for this key."
        )

    suffix = Path(filename).suffix.lower()
    if suffix not in SUPPORTED_SUFFIXES:
        raise GenerationError(f"Unsupported file type {suffix or '(none)'!r}; expected .svg or .png.")
    if preset not in PRESETS:
        raise GenerationError(describe_unknown_preset(preset))

    with tempfile.NamedTemporaryFile(suffix=suffix) as tmp:
        tmp.write(content)
        tmp.flush()
        try:
            builder = BrandAssetBuilder(
                tmp.name,
                app_name=app_name or Path(filename).stem or "logo",
                theme_color=theme_color,
                background_color=background_color,
            )
            builder.generate(PRESETS[preset])
            zip_bytes = builder.write_zip()
        except (UnsupportedSourceFormatError, UnknownAssetGroupError) as exc:
            raise GenerationError(str(exc)) from exc

    safe_name = _SAFE_NAME.sub("-", builder.app_name).strip("-") or "tessara"
    return zip_bytes, f"{safe_name}-assets.zip"
