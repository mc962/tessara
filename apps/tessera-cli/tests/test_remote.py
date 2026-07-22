from __future__ import annotations

import asyncio
import zipfile
from io import BytesIO
from pathlib import Path
from typing import Awaitable, Callable

import pytest
from aiohttp import web
from aiohttp.test_utils import TestServer

from tessera_cli.remote import RemoteGenerationError, extract_zip, generate_remote


def test_extract_zip_writes_all_files(tmp_path: Path):
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("favicon.ico", b"fake-ico-bytes")
        archive.writestr("site.webmanifest", b"{}")

    output = tmp_path / "out"
    written = extract_zip(buffer.getvalue(), output)

    assert {p.name for p in written} == {"favicon.ico", "site.webmanifest"}
    assert (output / "favicon.ico").read_bytes() == b"fake-ico-bytes"
    assert (output / "site.webmanifest").read_bytes() == b"{}"


def test_extract_zip_creates_output_dir(tmp_path: Path):
    buffer = BytesIO()
    with zipfile.ZipFile(buffer, "w") as archive:
        archive.writestr("a.png", b"x")

    output = tmp_path / "nested" / "out"
    extract_zip(buffer.getvalue(), output)

    assert output.is_dir()


async def _serve_and_call(
    handler: Callable[[web.Request], Awaitable[web.Response]],
    call: Callable[[str], Awaitable[bytes]],
) -> bytes:
    """Start a real local aiohttp server running `handler`, call `call(url)` against it."""
    app = web.Application()
    app.router.add_post("/api/generate", handler)
    server = TestServer(app)
    await server.start_server()
    try:
        return await call(f"http://{server.host}:{server.port}")
    finally:
        await server.close()


def test_generate_remote_returns_body_on_200(tmp_path: Path):
    source = tmp_path / "logo.svg"
    source.write_text("<svg/>")

    async def handler(request: web.Request) -> web.Response:
        await request.post()
        return web.Response(body=b"zip-bytes", status=200)

    async def call(url: str) -> bytes:
        return await generate_remote(
            server_url=url,
            api_key="tsr_test",
            source=source,
            preset="web",
            app_name="Acme",
            theme_color="#ffffff",
            background_color="#ffffff",
        )

    result = asyncio.run(_serve_and_call(handler, call))
    assert result == b"zip-bytes"


def test_generate_remote_sends_bearer_header(tmp_path: Path):
    source = tmp_path / "logo.svg"
    source.write_text("<svg/>")
    seen_auth: dict[str, str | None] = {}

    async def handler(request: web.Request) -> web.Response:
        seen_auth["value"] = request.headers.get("Authorization")
        await request.post()
        return web.Response(body=b"ok", status=200)

    async def call(url: str) -> bytes:
        return await generate_remote(
            server_url=url,
            api_key="tsr_secret",
            source=source,
            preset="web",
            app_name=None,
            theme_color="#ffffff",
            background_color="#ffffff",
        )

    asyncio.run(_serve_and_call(handler, call))
    assert seen_auth["value"] == "Bearer tsr_secret"


def test_generate_remote_raises_on_non_200(tmp_path: Path):
    source = tmp_path / "logo.svg"
    source.write_text("<svg/>")

    async def handler(request: web.Request) -> web.Response:
        await request.post()
        return web.Response(text="Unknown preset 'x'", status=400)

    async def call(url: str) -> bytes:
        return await generate_remote(
            server_url=url,
            api_key="tsr_test",
            source=source,
            preset="x",
            app_name=None,
            theme_color="#ffffff",
            background_color="#ffffff",
        )

    with pytest.raises(RemoteGenerationError, match="400"):
        asyncio.run(_serve_and_call(handler, call))


def test_generate_remote_wraps_connection_errors(tmp_path: Path):
    source = tmp_path / "logo.svg"
    source.write_text("<svg/>")

    async def dead_url() -> str:
        app = web.Application()
        server = TestServer(app)
        await server.start_server()
        url = f"http://{server.host}:{server.port}"
        await server.close()  # nothing listens here anymore
        return url

    async def call() -> bytes:
        url = await dead_url()
        return await generate_remote(
            server_url=url,
            api_key="tsr_test",
            source=source,
            preset="web",
            app_name=None,
            theme_color="#ffffff",
            background_color="#ffffff",
        )

    with pytest.raises(RemoteGenerationError):
        asyncio.run(call())
