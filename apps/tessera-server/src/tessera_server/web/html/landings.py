"""Root landing page — service status overview."""

import logging
import os

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, HTMLResponse, Response

from tessera_server.configuration.settings import application_settings
from tessera_server.constants import PROJECT_ROOT
from tessera_server.web.templates import templates

logger = logging.getLogger(__name__)

router = APIRouter(include_in_schema=False, tags=["ui"])

_CTX = {"settings": application_settings}


@router.get("/favicon.ico", include_in_schema=False)
async def favicon() -> FileResponse:
    return FileResponse(os.path.join(PROJECT_ROOT, "static", "images", "favicon.ico"))


@router.get("/", response_class=HTMLResponse)
async def index(request: Request) -> Response:
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            **_CTX,
        },
    )
