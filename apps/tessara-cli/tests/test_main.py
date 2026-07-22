from __future__ import annotations

import sys
from pathlib import Path

from typer.testing import CliRunner

from tessara_cli.config import ServerConfig
from tessara_cli.main import app
from tessara_cli.remote import RemoteGenerationError
from tessara_cli.presets import PRESETS

runner = CliRunner()


class TestPresets:
    def test_lists_all_presets(self):
        result = runner.invoke(app, ["presets"])
        assert result.exit_code == 0
        for name in PRESETS:
            assert name in result.stdout


class TestGenerate:
    def test_generates_files_locally(self, sample_svg: Path, tmp_path: Path):
        output = tmp_path / "out"
        result = runner.invoke(
            app, ["generate", str(sample_svg), "--preset", "minimal", "-o", str(output)]
        )
        assert result.exit_code == 0
        assert (output / "favicon.ico").exists()
        assert "Generated" in result.stdout

    def test_unknown_preset_exits_nonzero(self, sample_svg: Path, tmp_path: Path):
        result = runner.invoke(
            app,
            ["generate", str(sample_svg), "--preset", "not-a-preset", "-o", str(tmp_path / "out")],
        )
        assert result.exit_code == 1
        assert "Unknown preset" in result.stdout

    def test_missing_source_exits_nonzero(self, tmp_path: Path):
        result = runner.invoke(
            app, ["generate", str(tmp_path / "nope.svg"), "-o", str(tmp_path / "out")]
        )
        assert result.exit_code == 1

    def test_missing_tessara_core_gives_friendly_message(
        self, sample_svg: Path, tmp_path: Path, monkeypatch
    ):
        monkeypatch.setitem(sys.modules, "tessara", None)
        result = runner.invoke(
            app, ["generate", str(sample_svg), "-o", str(tmp_path / "out")]
        )
        assert result.exit_code == 1
        assert "tessara-cli[local]" in result.stdout


class TestWebGenerate:
    def test_unknown_preset_exits_before_touching_network(self, sample_svg: Path, tmp_path: Path):
        result = runner.invoke(
            app,
            [
                "web",
                "generate",
                str(sample_svg),
                "--preset",
                "not-a-preset",
                "-o",
                str(tmp_path / "out"),
            ],
        )
        assert result.exit_code == 1
        assert "Unknown preset" in result.stdout

    def test_missing_source_exits_nonzero(self, tmp_path: Path):
        result = runner.invoke(
            app,
            ["web", "generate", str(tmp_path / "nope.svg"), "-o", str(tmp_path / "out")],
        )
        assert result.exit_code == 1
        assert "not found" in result.stdout

    def test_successful_run_writes_files_and_reports_them(
        self, sample_svg: Path, tmp_path: Path, monkeypatch
    ):
        import tessara_cli.main as main_module

        monkeypatch.setattr(
            main_module, "resolve_server_config", lambda url, key: ServerConfig("http://x", "k")
        )

        async def fake_generate_remote(**kwargs):
            return b"fake-zip-bytes"

        monkeypatch.setattr(main_module, "generate_remote", fake_generate_remote)
        monkeypatch.setattr(
            main_module, "extract_zip", lambda zip_bytes, output: [output / "favicon.ico"]
        )

        result = runner.invoke(
            app,
            ["web", "generate", str(sample_svg), "-o", str(tmp_path / "out")],
        )

        assert result.exit_code == 0
        assert "Generated 1 file(s)" in result.stdout

    def test_remote_failure_exits_nonzero_with_message(
        self, sample_svg: Path, tmp_path: Path, monkeypatch
    ):
        import tessara_cli.main as main_module

        monkeypatch.setattr(
            main_module,
            "resolve_server_config",
            lambda url, key: ServerConfig("http://unreachable", "k"),
        )

        async def failing_generate_remote(**kwargs):
            raise RemoteGenerationError("Server returned 500: boom")

        monkeypatch.setattr(main_module, "generate_remote", failing_generate_remote)

        result = runner.invoke(
            app, ["web", "generate", str(sample_svg), "-o", str(tmp_path / "out")]
        )

        assert result.exit_code == 1
        assert "Request to http://unreachable failed" in result.stdout

    def test_server_and_api_key_flags_are_forwarded(
        self, sample_svg: Path, tmp_path: Path, monkeypatch
    ):
        import tessara_cli.main as main_module

        seen = {}

        def fake_resolve(url, key):
            seen["url"], seen["key"] = url, key
            return ServerConfig("http://from-flags", "flag-key")

        monkeypatch.setattr(main_module, "resolve_server_config", fake_resolve)

        async def fake_generate_remote(**kwargs):
            return b"zip"

        monkeypatch.setattr(main_module, "generate_remote", fake_generate_remote)
        monkeypatch.setattr(main_module, "extract_zip", lambda zip_bytes, output: [])

        runner.invoke(
            app,
            [
                "web",
                "generate",
                str(sample_svg),
                "-o",
                str(tmp_path / "out"),
                "--server",
                "http://cli-flag",
                "--api-key",
                "cli-flag-key",
            ],
        )

        assert seen == {"url": "http://cli-flag", "key": "cli-flag-key"}
