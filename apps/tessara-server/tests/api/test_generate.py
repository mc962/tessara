"""Tests for GET/POST /generate."""

import io
import zipfile

from tessara_server.configuration.settings import application_settings


class TestGetGenerate:
    def test_no_auth_redirects_to_login(self, unauthed_client):
        resp = unauthed_client.get("/generate", follow_redirects=False)
        assert resp.status_code == 303
        assert resp.headers["location"] == "/login?next=/generate"

    def test_authed_renders_form(self, api_client):
        resp = api_client.get("/generate")
        assert resp.status_code == 200
        assert b"generate-form" in resp.content


class TestPostGenerate:
    def test_no_auth_redirects_to_login(self, unauthed_client):
        resp = unauthed_client.post("/generate", follow_redirects=False)
        assert resp.status_code == 303

    def test_valid_svg_returns_zip(self, api_client, sample_svg_bytes, csrf_headers):
        resp = api_client.post(
            "/generate",
            data={"preset": "web", "app_name": "Acme"},
            files={"source": ("logo.svg", sample_svg_bytes, "image/svg+xml")},
            headers=csrf_headers(api_client),
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

    def test_unsupported_file_type_returns_400(self, api_client, csrf_headers):
        resp = api_client.post(
            "/generate",
            data={"preset": "web"},
            files={"source": ("logo.txt", b"not an image", "text/plain")},
            headers=csrf_headers(api_client),
        )
        assert resp.status_code == 400
        assert b"Unsupported file type" in resp.content

    def test_unknown_preset_returns_400(self, api_client, sample_svg_bytes, csrf_headers):
        resp = api_client.post(
            "/generate",
            data={"preset": "not-a-preset"},
            files={"source": ("logo.svg", sample_svg_bytes, "image/svg+xml")},
            headers=csrf_headers(api_client),
        )
        assert resp.status_code == 400
        assert b"Unknown preset" in resp.content

    def test_missing_csrf_token_returns_403(self, api_client, sample_svg_bytes):
        resp = api_client.post(
            "/generate",
            data={"preset": "web"},
            files={"source": ("logo.svg", sample_svg_bytes, "image/svg+xml")},
        )
        assert resp.status_code == 403

    def test_oversized_upload_rejected_for_regular_key(
        self, regular_api_client, sample_svg_bytes, monkeypatch, csrf_headers
    ):
        monkeypatch.setattr(application_settings, "upload_max_bytes", 10)
        resp = regular_api_client.post(
            "/generate",
            data={"preset": "web"},
            files={"source": ("logo.svg", sample_svg_bytes, "image/svg+xml")},
            headers=csrf_headers(regular_api_client),
        )
        assert resp.status_code == 413
        assert b"over the 10-byte limit" in resp.content

    def test_same_upload_allowed_for_superuser_key(
        self, api_client, sample_svg_bytes, monkeypatch, csrf_headers
    ):
        # api_client's key is a superuser, so it gets upload_max_bytes_superuser
        # instead of the regular (tiny, patched-down) limit.
        monkeypatch.setattr(application_settings, "upload_max_bytes", 10)
        resp = api_client.post(
            "/generate",
            data={"preset": "minimal"},
            files={"source": ("logo.svg", sample_svg_bytes, "image/svg+xml")},
            headers=csrf_headers(api_client),
        )
        assert resp.status_code == 200


class TestApiGenerate:
    def test_no_auth_returns_401(self, unauthed_client, sample_svg_bytes):
        resp = unauthed_client.post(
            "/api/generate",
            data={"preset": "web"},
            files={"source": ("logo.svg", sample_svg_bytes, "image/svg+xml")},
        )
        assert resp.status_code == 401

    def test_valid_svg_returns_zip(self, api_client, sample_svg_bytes):
        resp = api_client.post(
            "/api/generate",
            data={"preset": "minimal", "app_name": "Acme"},
            files={"source": ("logo.svg", sample_svg_bytes, "image/svg+xml")},
            headers={"Authorization": "Bearer tsa_test"},
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
            }

    def test_unknown_preset_returns_400_json(self, api_client, sample_svg_bytes):
        resp = api_client.post(
            "/api/generate",
            data={"preset": "not-a-preset"},
            files={"source": ("logo.svg", sample_svg_bytes, "image/svg+xml")},
            headers={"Authorization": "Bearer tsa_test"},
        )
        assert resp.status_code == 400
        assert "Unknown preset" in resp.json()["detail"]
