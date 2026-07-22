from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass
from pathlib import Path

import typer

# Resolution order for the server URL and API key: CLI flag > env var (both
# handled by typer's envvar= before either value reaches here) > this config
# file > an interactive prompt as the last resort, so the key never has to
# touch shell history or be committed anywhere by accident.
CONFIG_PATH = Path(
    os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))
) / "tessera" / "config.toml"


@dataclass
class ServerConfig:
    url: str
    api_key: str


def _read_config_file() -> dict:
    if not CONFIG_PATH.exists():
        return {}
    with open(CONFIG_PATH, "rb") as f:
        return tomllib.load(f)


def resolve_server_config(cli_url: str | None, cli_key: str | None) -> ServerConfig:
    """Resolve the server URL and API key from (in order): flag/env, config file, prompt."""
    file_data = _read_config_file()

    url = cli_url or file_data.get("server_url")
    if not url:
        url = typer.prompt("Tessera server URL")

    api_key = cli_key or file_data.get("api_key")
    if not api_key:
        api_key = typer.prompt("Tessera API key", hide_input=True)

    return ServerConfig(url=str(url).rstrip("/"), api_key=str(api_key))
