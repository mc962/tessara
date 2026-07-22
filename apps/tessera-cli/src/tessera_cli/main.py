from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Annotated

import typer

from tessera_cli.config import resolve_server_config
from tessera_cli.presets import PRESETS, describe_unknown_preset
from tessera_cli.remote import RemoteGenerationError, extract_zip, generate_remote

app = typer.Typer(help="tessera: generate platform-specific brand assets from a source image.")
web_app = typer.Typer(help="Commands that talk to a remote tessera-server instead of running locally.")
app.add_typer(web_app, name="web")


@app.command()
def generate(
    source: Annotated[Path, typer.Argument(help="Path to the source logo (.svg or .png).")],
    output: Annotated[
        Path, typer.Option("--output", "-o", help="Directory to write generated assets to.")
    ] = Path("./output"),
    preset: Annotated[
        str, typer.Option("--preset", help=f"One of: {', '.join(sorted(PRESETS))}.")
    ] = "web",
    app_name: Annotated[
        str | None,
        typer.Option(
            "--app-name", help="Used in site.webmanifest. Defaults to the source file's name."
        ),
    ] = None,
    theme_color: Annotated[
        str, typer.Option("--theme-color", help="Used in site.webmanifest.")
    ] = "#ffffff",
    background_color: Annotated[
        str, typer.Option("--background-color", help="Used in site.webmanifest.")
    ] = "#ffffff",
) -> None:
    """Generate brand assets for SOURCE and write them to --output."""
    if preset not in PRESETS:
        typer.secho(describe_unknown_preset(preset), fg=typer.colors.RED)
        raise typer.Exit(code=1)

    try:
        from tessera import (
            BrandAssetBuilder,
            UnknownAssetGroupError,
            UnsupportedSourceFormatError,
        )
    except (ImportError, OSError) as exc:
        # ImportError: tessera-core itself isn't installed (no [local] extra).
        # OSError: tessera-core is installed but cairosvg's native dependency,
        # libcairo2, isn't on the system — common on a stripped-down Pi that
        # only has the pip wheels, not the apt package.
        typer.secho(
            "Local generation needs tessera-core, which isn't fully available:\n"
            f"  {exc}\n"
            "Install it with: pip install tessera-cli[local]\n"
            "If that's already installed, this machine is likely missing the "
            "libcairo2 system library that cairosvg needs.",
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=1) from exc

    try:
        builder = BrandAssetBuilder(
            source,
            app_name=app_name,
            theme_color=theme_color,
            background_color=background_color,
        )
        builder.generate(PRESETS[preset])
        written = builder.write(output)
    except (FileNotFoundError, UnsupportedSourceFormatError, UnknownAssetGroupError) as exc:
        typer.secho(str(exc), fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc

    typer.secho(f"Generated {len(written)} file(s) in {output}/", fg=typer.colors.GREEN)
    for path in sorted(written):
        typer.echo(f"  {path.relative_to(output) if path.is_relative_to(output) else path}")

    snippets = builder.html_snippets()
    if snippets:
        typer.echo()
        typer.echo("Add to your HTML <head>:")
        for line in snippets:
            typer.echo(f"  {line}")


@web_app.command("generate")
def web_generate(
    source: Annotated[Path, typer.Argument(help="Path to the source logo (.svg or .png).")],
    output: Annotated[
        Path, typer.Option("--output", "-o", help="Directory to write generated assets to.")
    ] = Path("./output"),
    preset: Annotated[
        str, typer.Option("--preset", help=f"One of: {', '.join(sorted(PRESETS))}.")
    ] = "web",
    app_name: Annotated[
        str | None,
        typer.Option(
            "--app-name", help="Used in site.webmanifest. Defaults to the source file's name."
        ),
    ] = None,
    theme_color: Annotated[
        str, typer.Option("--theme-color", help="Used in site.webmanifest.")
    ] = "#ffffff",
    background_color: Annotated[
        str, typer.Option("--background-color", help="Used in site.webmanifest.")
    ] = "#ffffff",
    server: Annotated[
        str | None,
        typer.Option(
            "--server",
            envvar="TESSERA_SERVER_URL",
            help="tessera-server base URL. Falls back to the config file, then a prompt.",
        ),
    ] = None,
    api_key: Annotated[
        str | None,
        typer.Option(
            "--api-key",
            envvar="TESSERA_API_KEY",
            help="API key, sent as a Bearer token. Falls back to the config file, then a prompt.",
        ),
    ] = None,
) -> None:
    """Generate brand assets for SOURCE by sending it to a remote tessera-server."""
    if preset not in PRESETS:
        typer.secho(describe_unknown_preset(preset), fg=typer.colors.RED)
        raise typer.Exit(code=1)
    if not source.exists():
        typer.secho(f"Source image not found: {source}", fg=typer.colors.RED)
        raise typer.Exit(code=1)

    config = resolve_server_config(server, api_key)

    try:
        zip_bytes = asyncio.run(
            generate_remote(
                server_url=config.url,
                api_key=config.api_key,
                source=source,
                preset=preset,
                app_name=app_name,
                theme_color=theme_color,
                background_color=background_color,
            )
        )
    except RemoteGenerationError as exc:
        typer.secho(f"Request to {config.url} failed: {exc}", fg=typer.colors.RED)
        raise typer.Exit(code=1) from exc

    written = extract_zip(zip_bytes, output)
    typer.secho(f"Generated {len(written)} file(s) in {output}/", fg=typer.colors.GREEN)
    for path in sorted(written):
        typer.echo(f"  {path.relative_to(output)}")


@app.command()
def presets() -> None:
    """List available presets and the asset groups each one generates."""
    for name in sorted(PRESETS):
        typer.echo(f"{name}: {', '.join(PRESETS[name])}")


if __name__ == "__main__":
    app()
