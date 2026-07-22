from __future__ import annotations

from pathlib import Path
from typing import Annotated

import typer
from tessera import BrandAssetBuilder, UnknownAssetGroupError, UnsupportedSourceFormatError

app = typer.Typer(help="tessera: generate platform-specific brand assets from a source image.")

# Preset -> asset groups.
PRESETS: dict[str, list[str]] = {
    "web": ["favicon", "apple"],
    "pwa": ["favicon", "apple", "android", "webmanifest"],
    "social": ["favicon", "opengraph"],
    "everything": ["favicon", "apple", "android", "webmanifest", "opengraph"],
}


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
        typer.secho(
            f"Unknown preset {preset!r}; available: {', '.join(sorted(PRESETS))}",
            fg=typer.colors.RED,
        )
        raise typer.Exit(code=1)

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


@app.command()
def presets() -> None:
    """List available presets and the asset groups each one generates."""
    for name in sorted(PRESETS):
        typer.echo(f"{name}: {', '.join(PRESETS[name])}")


if __name__ == "__main__":
    app()
