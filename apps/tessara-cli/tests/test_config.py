from __future__ import annotations

from pathlib import Path

import pytest

from tessara_cli import config


@pytest.fixture(autouse=True)
def _no_real_config_file(tmp_path: Path, monkeypatch):
    # Never touch the real ~/.config/tessara/config.toml during tests.
    monkeypatch.setattr(config, "CONFIG_PATH", tmp_path / "config.toml")


def test_cli_flags_take_precedence_over_everything(monkeypatch):
    monkeypatch.setattr(config, "_read_config_file", lambda: {"server_url": "http://file", "api_key": "file-key"})
    result = config.resolve_server_config("http://flag", "flag-key")
    assert result.url == "http://flag"
    assert result.api_key == "flag-key"


def test_falls_back_to_config_file_when_no_flags(monkeypatch):
    monkeypatch.setattr(
        config,
        "_read_config_file",
        lambda: {"server_url": "http://file.example", "api_key": "file-key"},
    )
    result = config.resolve_server_config(None, None)
    assert result.url == "http://file.example"
    assert result.api_key == "file-key"


def test_prompts_when_nothing_else_is_set(monkeypatch):
    monkeypatch.setattr(config, "_read_config_file", lambda: {})
    prompts: list[tuple[str, bool]] = []

    def fake_prompt(text: str, hide_input: bool = False) -> str:
        prompts.append((text, hide_input))
        return "prompted-value"

    monkeypatch.setattr(config.typer, "prompt", fake_prompt)

    result = config.resolve_server_config(None, None)

    assert result.url == "prompted-value"
    assert result.api_key == "prompted-value"
    assert prompts == [
        ("Tessara server URL", False),
        ("Tessara API key", True),
    ]


def test_api_key_prompt_hides_input(monkeypatch):
    monkeypatch.setattr(config, "_read_config_file", lambda: {"server_url": "http://ok"})
    hide_input_values = []

    def fake_prompt(text: str, hide_input: bool = False) -> str:
        hide_input_values.append(hide_input)
        return "secret"

    monkeypatch.setattr(config.typer, "prompt", fake_prompt)
    config.resolve_server_config(None, None)

    assert hide_input_values == [True]


def test_trailing_slash_stripped_from_url():
    result = config.resolve_server_config("http://example.com/", "key")
    assert result.url == "http://example.com"


def test_real_config_file_is_read(tmp_path: Path, monkeypatch):
    config_path = tmp_path / "config.toml"
    config_path.write_text('server_url = "http://real-file"\napi_key = "real-key"\n')
    monkeypatch.setattr(config, "CONFIG_PATH", config_path)

    result = config.resolve_server_config(None, None)

    assert result.url == "http://real-file"
    assert result.api_key == "real-key"
