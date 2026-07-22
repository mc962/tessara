from __future__ import annotations

import json
import zipfile
from io import BytesIO
from pathlib import Path

import pytest
from PIL import Image

from tessara import BrandAssetBuilder, UnknownAssetGroupError


@pytest.mark.parametrize("source_fixture", ["sample_svg", "sample_png"])
def test_generate_favicon_writes_expected_files(
    source_fixture: str, request: pytest.FixtureRequest, tmp_path: Path
) -> None:
    source_path = request.getfixturevalue(source_fixture)
    output_dir = tmp_path / "output"

    builder = BrandAssetBuilder(source_path)
    builder.generate(["favicon"])
    written = builder.write(output_dir)

    written_names = {p.name for p in written}
    assert written_names == {
        "favicon-16x16.png",
        "favicon-32x32.png",
        "favicon-48x48.png",
        "favicon.ico",
    }
    for path in written:
        assert path.exists()

    with Image.open(output_dir / "favicon-32x32.png") as img:
        assert img.size == (32, 32)
        assert img.mode == "RGBA"

    with Image.open(output_dir / "favicon.ico") as ico:
        assert ico.size == (48, 48)  # Pillow opens an ICO at its largest frame


def test_generate_apple_composites_opaque_white_background(
    sample_png: Path, tmp_path: Path
) -> None:
    output_dir = tmp_path / "output"
    BrandAssetBuilder(sample_png).generate(["apple"]).write(output_dir)

    with Image.open(output_dir / "apple-touch-icon.png") as img:
        assert img.size == (180, 180)
        # sample_png has a transparent border; on the apple icon it must be
        # fully opaque white instead (iOS renders transparency as black).
        assert img.convert("RGBA").getpixel((0, 0)) == (255, 255, 255, 255)


def test_generate_opengraph_writes_1200x630_opaque_image(
    sample_png: Path, tmp_path: Path
) -> None:
    output_dir = tmp_path / "output"
    written = BrandAssetBuilder(sample_png).generate(["opengraph"]).write(output_dir)

    written_names = {p.name for p in written}
    assert written_names == {"opengraph.png"}

    with Image.open(output_dir / "opengraph.png") as img:
        assert img.size == (1200, 630)
        rgba = img.convert("RGBA")
        assert rgba.getpixel((0, 0)) == (255, 255, 255, 255)  # opaque white margin
        assert rgba.getpixel((600, 315))[3] == 255  # opaque wherever content lands


def test_generate_android_writes_both_sizes(sample_svg: Path, tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    written = BrandAssetBuilder(sample_svg).generate(["android"]).write(output_dir)

    written_names = {p.name for p in written}
    assert written_names == {"android-chrome-192x192.png", "android-chrome-512x512.png"}
    with Image.open(output_dir / "android-chrome-512x512.png") as img:
        assert img.size == (512, 512)


def test_webmanifest_pulls_in_android_icons(sample_svg: Path, tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    builder = BrandAssetBuilder(sample_svg, app_name="Acme")
    builder.generate(["webmanifest"])
    written = builder.write(output_dir)

    written_names = {p.name for p in written}
    assert written_names == {
        "android-chrome-192x192.png",
        "android-chrome-512x512.png",
        "site.webmanifest",
    }

    manifest = json.loads((output_dir / "site.webmanifest").read_text())
    assert manifest["name"] == "Acme"
    assert manifest["short_name"] == "Acme"
    assert manifest["display"] == "standalone"
    assert manifest["icons"] == [
        {"src": "/android-chrome-192x192.png", "sizes": "192x192", "type": "image/png"},
        {"src": "/android-chrome-512x512.png", "sizes": "512x512", "type": "image/png"},
    ]


def test_app_name_defaults_to_source_stem(sample_svg: Path, tmp_path: Path) -> None:
    builder = BrandAssetBuilder(sample_svg)
    builder.generate(["webmanifest"])
    builder.write(tmp_path / "output")

    manifest = json.loads((tmp_path / "output" / "site.webmanifest").read_text())
    assert manifest["name"] == sample_svg.stem


def test_html_snippets_are_deduped_and_scoped_to_generated_groups(sample_svg: Path) -> None:
    builder = BrandAssetBuilder(sample_svg)
    builder.generate(["favicon", "apple"])
    snippets = builder.html_snippets()

    assert any("favicon.ico" in line for line in snippets)
    assert any("apple-touch-icon" in line for line in snippets)
    assert not any("android-chrome" in line for line in snippets)
    assert len(snippets) == len(set(snippets))


def test_html_snippets_include_opengraph_meta_tags(sample_svg: Path) -> None:
    builder = BrandAssetBuilder(sample_svg)
    builder.generate(["opengraph"])
    snippets = builder.html_snippets()

    assert any("og:image" in line for line in snippets)
    assert any("twitter:card" in line for line in snippets)


def test_generate_unknown_group_raises(sample_svg: Path) -> None:
    builder = BrandAssetBuilder(sample_svg)
    with pytest.raises(UnknownAssetGroupError):
        builder.generate(["not-a-real-group"])


def test_write_zip_matches_write(sample_svg: Path, tmp_path: Path) -> None:
    output_dir = tmp_path / "output"
    builder = BrandAssetBuilder(sample_svg).generate(["favicon", "apple"])
    written = builder.write(output_dir)

    zip_bytes = BrandAssetBuilder(sample_svg).generate(["favicon", "apple"]).write_zip()
    with zipfile.ZipFile(BytesIO(zip_bytes)) as archive:
        assert set(archive.namelist()) == {p.name for p in written}
        for path in written:
            assert archive.read(path.name) == path.read_bytes()


def test_write_is_deterministic(sample_svg: Path, tmp_path: Path) -> None:
    out_a = tmp_path / "a"
    out_b = tmp_path / "b"

    BrandAssetBuilder(sample_svg).generate(["favicon"]).write(out_a)
    BrandAssetBuilder(sample_svg).generate(["favicon"]).write(out_b)

    for name in ("favicon-16x16.png", "favicon-32x32.png", "favicon-48x48.png", "favicon.ico"):
        assert (out_a / name).read_bytes() == (out_b / name).read_bytes()
