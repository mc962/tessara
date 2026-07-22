"""Tests for GET/POST /generate."""

import io
import zipfile

SAMPLE_SVG = b"""\
<svg xmlns="http://www.w3.org/2000/svg" width="64" height="64" viewBox="0 0 64 64">
  <rect width="64" height="64" fill="#3366ff"/>
</svg>
"""


class TestGetGenerate:
    def test_no_auth_redirects_to_login(self, unauthed_client):
        resp = unauthed_client.get("/generate", follow_redirects=False)
        assert resp.status_code == 303
        assert resp.headers["location"] == "/admin/login?next=/generate"

    def test_authed_renders_form(self, api_client):
        resp = api_client.get("/generate")
        assert resp.status_code == 200
        assert b"generate-form" in resp.content


class TestPostGenerate:
    def test_no_auth_redirects_to_login(self, unauthed_client):
        resp = unauthed_client.post("/generate", follow_redirects=False)
        assert resp.status_code == 303

    def test_valid_svg_returns_zip(self, api_client):
        resp = api_client.post(
            "/generate",
            data={"preset": "web", "app_name": "Acme"},
            files={"source": ("logo.svg", SAMPLE_SVG, "image/svg+xml")},
        )
        assert resp.status_code == 200
        assert resp.headers["content-type"] == "application/zip"
        assert "Acme-assets.zip" in resp.headers["content-disposition"]

        with zipfile.ZipFile(io.BytesIO(resp.content)) as archive:
            assert set(archive.namelist()) == {
                "favicon-16x16.png",
                "favicon-32x32.png",
                "favicon-48x48.png",
                "favicon.ico",
                "apple-touch-icon.png",
            }

    def test_unsupported_file_type_returns_400(self, api_client):
        resp = api_client.post(
            "/generate",
            data={"preset": "web"},
            files={"source": ("logo.txt", b"not an image", "text/plain")},
        )
        assert resp.status_code == 400
        assert b"Unsupported file type" in resp.content

    def test_unknown_preset_returns_400(self, api_client):
        resp = api_client.post(
            "/generate",
            data={"preset": "not-a-preset"},
            files={"source": ("logo.svg", SAMPLE_SVG, "image/svg+xml")},
        )
        assert resp.status_code == 400
        assert b"Unknown preset" in resp.content
