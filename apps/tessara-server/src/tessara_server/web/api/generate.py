"""POST /api/generate — upload a source image, pick a preset, get a zip back.

Bearer-token only (any active key). This is the machine-facing counterpart to
the session-gated /generate HTML page — used by tessara-cli's `web generate`.
"""

from typing import Annotated

from fastapi import APIRouter, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import Response

from tessara_server.configuration.settings import application_settings
from tessara_server.service.generation import (
    GenerationError,
    UploadTooLargeError,
    generate_zip,
    max_upload_bytes,
)
from tessara_server.web.dependencies.auth import ApiKeyDependency
from tessara_server.web.rate_limit import limiter

router = APIRouter(prefix="/api", tags=["generate"])


@router.post("/generate", response_model=None)
@limiter.limit(application_settings.rate_limit_generate)
async def api_generate(
    request: Request,
    key: ApiKeyDependency,
    source: Annotated[UploadFile, File()],
    preset: Annotated[str, Form()] = "web",
    app_name: Annotated[str, Form()] = "",
    theme_color: Annotated[str, Form()] = "#ffffff",
    background_color: Annotated[str, Form()] = "#ffffff",
) -> Response:
    body = await source.read()
    try:
        zip_bytes, download_name = generate_zip(
            filename=source.filename or "",
            content=body,
            preset=preset,
            app_name=app_name,
            theme_color=theme_color,
            background_color=background_color,
            max_bytes=max_upload_bytes(key.is_superuser),
        )
    except UploadTooLargeError as exc:
        raise HTTPException(status_code=413, detail=str(exc)) from exc
    except GenerationError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    return Response(
        content=zip_bytes,
        media_type="application/zip",
        headers={"Content-Disposition": f'attachment; filename="{download_name}"'},
    )
