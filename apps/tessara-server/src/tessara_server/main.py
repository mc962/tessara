import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from starlette.requests import Request
from starlette.responses import RedirectResponse
from starlette.staticfiles import StaticFiles
from uvicorn.middleware.proxy_headers import ProxyHeadersMiddleware

from tessara_server.client.http import aiohttp_tcp_client
from tessara_server.configuration.logging_config import configure_logging
from tessara_server.configuration.settings import application_settings
from tessara_server.constants import PROJECT_ROOT
from tessara_server.data.database.connection import get_sessionmanager
from tessara_server.web.api import api_keys as api_keys_router
from tessara_server.web.api import generate as generate_api_router
from tessara_server.web.api import health as health_router
from tessara_server.web.api import metrics as metrics_router
from tessara_server.web.dependencies.auth import AdminLoginRequired
from tessara_server.web.html import admin as admin_router
from tessara_server.web.html import generate as generate_router
from tessara_server.web.html import landings as landings_router
from tessara_server.web.rate_limit import limiter


configure_logging()
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    await aiohttp_tcp_client.initialize()
    logger.info(
        "Tessara started on %s:%s",
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

app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)


@app.exception_handler(AdminLoginRequired)
async def admin_login_redirect(request: Request, __: AdminLoginRequired) -> RedirectResponse:
    next_path = request.url.path
    if next_path and next_path != "/admin/login":
        return RedirectResponse(f"/admin/login?next={next_path}", status_code=303)
    return RedirectResponse("/admin/login", status_code=303)


app.include_router(health_router.router)
app.include_router(metrics_router.router)
app.include_router(api_keys_router.router)
app.include_router(generate_api_router.router)
app.include_router(admin_router.router)
app.include_router(generate_router.router)
app.include_router(landings_router.router)


app.mount(
    "/static",
    StaticFiles(directory=os.path.join(PROJECT_ROOT, "static")),
    name="static",
)


def run() -> None:
    """Run the app directly with uvicorn — for quick local/dev use. Production
    deployments use `gunicorn -c gunicorn.conf.py` instead (see deployment/)."""
    import uvicorn

    uvicorn.run(
        "tessara_server.main:app",
        host=application_settings.host or "127.0.0.1",
        port=application_settings.port,
        reload=os.environ.get("debug", "false").lower() == "true",
    )