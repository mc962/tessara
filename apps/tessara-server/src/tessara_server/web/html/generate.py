"""Generate UI — upload a source image, pick a preset, download a zip."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, File, Form, Request, UploadFile
from fastapi.responses import HTMLResponse, Response
from tessara import PRESETS

from tessara_server.configuration.settings import application_settings
from tessara_server.service.generation import (
    GenerationError,
    UploadTooLargeError,
    generate_zip,
    max_upload_bytes,
)
from tessara_server.web.csrf import verify_csrf
from tessara_server.web.dependencies.auth import SessionDependency
from tessara_server.web.rate_limit import limiter
from tessara_server.web.templates import templates

logger = logging.getLogger(__name__)

router = APIRouter(tags=["generate"])

_CTX = {"settings": application_settings, "presets": PRESETS}


@router.get("/generate", response_class=HTMLResponse)
async def get_generate(
    request: Request,
    _: SessionDependency,
) -> HTMLResponse:
    return templates.TemplateResponse(request, "generate.html", {**_CTX, "error": None})


@router.post("/generate", response_model=None)
@limiter.limit(application_settings.rate_limit_generate)
async def post_generate(
    request: Request,
    user: SessionDependency,
    _csrf: Annotated[None, Depends(verify_csrf)],
    source: Annotated[UploadFile, File()],
    preset: Annotated[str, Form()] = "web",
    app_name: Annotated[str, Form()] = "",
    theme_color: Annotated[str, Form()] = "#ffffff",
    background_color: Annotated[str, Form()] = "#ffffff",
) -> HTMLResponse | Response:
    body = await source.read()
    try:
        zip_bytes, download_name = generate_zip(
            filename=source.filename or "",
            content=body,
            preset=preset,
            app_name=app_name,
            theme_color=theme_color,
            background_color=background_color,
            max_bytes=max_upload_bytes(user.is_superuser),
        )
    except UploadTooLargeError as exc:
        return templates.TemplateResponse(
            request, "generate.html", {**_CTX, "error": str(exc)}, status_code=413
        )
    except GenerationError as exc:
        return templates.TemplateResponse(
            request, "generate.html", {**_CTX, "error": str(exc)}, status_code=400
        )

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{download_name}"'},
    )
