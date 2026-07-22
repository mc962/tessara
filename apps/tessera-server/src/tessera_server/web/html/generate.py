"""Generate UI — upload a source image, pick a preset, download a zip."""

import logging
import re
import tempfile
from pathlib import Path
from typing import Annotated

from fastapi import APIRouter, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, Response
from tessera import (
    PRESETS,
    BrandAssetBuilder,
    UnknownAssetGroupError,
    UnsupportedSourceFormatError,
)

from tessera_server.configuration.settings import application_settings
from tessera_server.web.dependencies.auth import SuperuserSessionDependency
from tessera_server.web.templates import templates

logger = logging.getLogger(__name__)

router = APIRouter(tags=["generate"])

_CTX = {"settings": application_settings, "presets": PRESETS}

_SUPPORTED_SUFFIXES = (".svg", ".png")
_SAFE_NAME = re.compile(r"[^a-zA-Z0-9_-]+")


@router.get("/generate", response_class=HTMLResponse)
async def get_generate(
    request: Request,
    _: SuperuserSessionDependency,
) -> HTMLResponse:
    return templates.TemplateResponse(request, "generate.html", {**_CTX, "error": None})


@router.post("/generate", response_model=None)
async def post_generate(
    request: Request,
    _: SuperuserSessionDependency,
    source: Annotated[UploadFile, File()],
    preset: Annotated[str, Form()] = "web",
    app_name: Annotated[str, Form()] = "",
    theme_color: Annotated[str, Form()] = "#ffffff",
    background_color: Annotated[str, Form()] = "#ffffff",
) -> HTMLResponse | Response:
    def error(message: str) -> HTMLResponse:
        return templates.TemplateResponse(
            request, "generate.html", {**_CTX, "error": message}, status_code=400
        )

    suffix = Path(source.filename or "").suffix.lower()
    if suffix not in _SUPPORTED_SUFFIXES:
        return error(f"Unsupported file type {suffix or '(none)'!r}; expected .svg or .png.")
    if preset not in PRESETS:
        return error(f"Unknown preset {preset!r}.")

    body = await source.read()

    with tempfile.NamedTemporaryFile(suffix=suffix) as tmp:
        tmp.write(body)
        tmp.flush()
        try:
            builder = BrandAssetBuilder(
                tmp.name,
                app_name=app_name or Path(source.filename or "logo").stem,
                theme_color=theme_color,
                background_color=background_color,
            )
            builder.generate(PRESETS[preset])
            zip_bytes = builder.write_zip()
        except (UnsupportedSourceFormatError, UnknownAssetGroupError) as exc:
            return error(str(exc))

    safe_name = _SAFE_NAME.sub("-", builder.app_name).strip("-") or "tessera"
    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{safe_name}-assets.zip"'},
    )
