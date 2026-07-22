import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from starlette.requests import Request
from starlette.responses import RedirectResponse
from starlette.staticfiles import StaticFiles
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from tessera_server.client.http import aiohttp_tcp_client
from tessera_server.configuration.logging_config import configure_logging
from tessera_server.configuration.settings import application_settings
from tessera_server.constants import PROJECT_ROOT
from tessera_server.data.database.connection import get_sessionmanager
from tessera_server.web.api import api_keys as api_keys_router
from tessera_server.web.api import health as health_router
from tessera_server.web.api import metrics as metrics_router
from tessera_server.web.dependencies.auth import AdminLoginRequired
from tessera_server.web.html import admin as admin_router
from tessera_server.web.html import landings as landings_router


configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await aiohttp_tcp_client.initialize()
    logger.info(
        "Tessera started on %s:%s",
        application_settings.host,
        application_settings.port,
    )
    yield
    await get_sessionmanager().close()
    await aiohttp_tcp_client.close()


app = FastAPI(
    title=application_settings.project_name,
    description="Brand Imagery Generator",
    version=application_settings.application_version,
    docs_url="/docs",
    redoc_url="/redoc",
    lifespan=lifespan,
)

app.add_middleware(
    ProxyHeadersMiddleware, trusted_hosts=[application_settings.trusted_proxy_ip]
)


@app.exception_handler(AdminLoginRequired)
async def admin_login_redirect(_: Request, __: AdminLoginRequired) -> RedirectResponse:
    return RedirectResponse("/admin/login", status_code=303)


app.include_router(health_router.router)
app.include_router(metrics_router.router)
app.include_router(api_keys_router.router)
app.include_router(admin_router.router)
app.include_router(landings_router.router)


app.mount(
    "/static",
    StaticFiles(directory=os.path.join(PROJECT_ROOT, "static")),
    name="static",
)