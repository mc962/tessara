from __future__ import annotations

import zipfile
from io import BytesIO
from pathlib import Path

import aiohttp


class RemoteGenerationError(RuntimeError):
    """The server rejected the request, or the request otherwise failed."""


async def generate_remote(
    *,
    server_url: str,
    api_key: str,
    source: Path,
    preset: str,
    app_name: str | None,
    theme_color: str,
    background_color: str,
) -> bytes:
    """POST source to {server_url}/api/generate. Returns the response zip bytes."""
    data = aiohttp.FormData()
    data.add_field("source", source.read_bytes(), filename=source.name)
    data.add_field("preset", preset)
    if app_name:
        data.add_field("app_name", app_name)
    data.add_field("theme_color", theme_color)
    data.add_field("background_color", background_color)

    headers = {"Authorization": f"Bearer {api_key}"}
    try:
        async with aiohttp.ClientSession() as http:
            async with http.post(
                f"{server_url}/api/generate", data=data, headers=headers
            ) as resp:
                if resp.status != 200:
                    detail = await resp.text()
                    raise RemoteGenerationError(f"Server returned {resp.status}: {detail}")
                return await resp.read()
    except aiohttp.ClientError as exc:
        raise RemoteGenerationError(str(exc)) from exc


def extract_zip(zip_bytes: bytes, output: Path) -> list[Path]:
    output.mkdir(parents=True, exist_ok=True)
    written: list[Path] = []
    with zipfile.ZipFile(BytesIO(zip_bytes)) as archive:
        for name in archive.namelist():
            path = output / name
            path.write_bytes(archive.read(name))
            written.append(path)
    return written
