"""Prometheus metrics endpoint."""

from fastapi import APIRouter
from fastapi.responses import Response
from prometheus_client import CONTENT_TYPE_LATEST, generate_latest

from tessera_server.service.metrics import registry

router = APIRouter(tags=["metrics"])


@router.get("/metrics", include_in_schema=False)
async def metrics() -> Response:
    return Response(content=generate_latest(registry), media_type=CONTENT_TYPE_LATEST)
