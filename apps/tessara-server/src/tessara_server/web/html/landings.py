"""Root landing page — service status overview."""

import logging
import os

from fastapi import APIRouter, Request
from fastapi.responses import FileResponse, HTMLResponse, Response
from tessara import PRESETS

from tessara_server.configuration.settings import application_settings
from tessara_server.constants import PROJECT_ROOT
from tessara_server.web.dependencies.auth import OptionalSessionDependency
from tessara_server.web.templates import templates

logger = logging.getLogger(__name__)

router = APIRouter(include_in_schema=False, tags=["ui"])

_CTX = {"settings": application_settings, "presets": PRESETS}

# Icon/manifest files that browsers and OSes request at the site root by
# convention (not under /static/), matching the paths tessara-core's
# html_snippets() bakes into the <link>/<meta> tags in base.html.


def _static_image(filename: str, media_type: str) -> FileResponse:
    return FileResponse(
        os.path.join(PROJECT_ROOT, "static", "images", filename), media_type=media_type
    )


@router.get("/favicon.ico", include_in_schema=False)
async def favicon() -> FileResponse:
    return _static_image("favicon.ico", "image/x-icon")


@router.get("/favicon-16x16.png", include_in_schema=False)
async def favicon_16() -> FileResponse:
    return _static_image("favicon-16x16.png", "image/png")


@router.get("/favicon-32x32.png", include_in_schema=False)
async def favicon_32() -> FileResponse:
    return _static_image("favicon-32x32.png", "image/png")


@router.get("/apple-touch-icon.png", include_in_schema=False)
async def apple_touch_icon() -> FileResponse:
    return _static_image("apple-touch-icon.png", "image/png")


@router.get("/android-chrome-192x192.png", include_in_schema=False)
async def android_chrome_192() -> FileResponse:
    return _static_image("android-chrome-192x192.png", "image/png")


@router.get("/android-chrome-512x512.png", include_in_schema=False)
async def android_chrome_512() -> FileResponse:
    return _static_image("android-chrome-512x512.png", "image/png")


@router.get("/opengraph.png", include_in_schema=False)
async def opengraph_image() -> FileResponse:
    return _static_image("opengraph.png", "image/png")


@router.get("/site.webmanifest", include_in_schema=False)
async def webmanifest() -> FileResponse:
    return _static_image("site.webmanifest", "application/manifest+json")


@router.get("/", response_class=HTMLResponse)
async def index(request: Request, session: OptionalSessionDependency) -> Response:
    return templates.TemplateResponse(
        request,
        "index.html",
        {
            **_CTX,
            "is_authenticated": session is not None,
        },
    )
