"""Tests for the root landing page and root-served icon/manifest files."""

import pytest

from tessara_server.main import app
from tessara_server.web.dependencies.auth import get_optional_session


class TestIndex:
    def test_returns_200(self, unauthed_client):
        resp = unauthed_client.get("/")
        assert resp.status_code == 200

    def test_shows_sign_in_cta_when_logged_out(self, unauthed_client):
        resp = unauthed_client.get("/")
        assert b"Sign in to generate assets" in resp.content
        assert b">Generate assets<" not in resp.content

    def test_shows_generate_cta_when_logged_in(self, unauthed_client, mock_db):
        async def _session():
            return object()

        app.dependency_overrides[get_optional_session] = _session
        try:
            resp = unauthed_client.get("/")
        finally:
            del app.dependency_overrides[get_optional_session]

        assert b">Generate assets<" in resp.content
        assert b"Sign in to generate assets" not in resp.content


@pytest.mark.parametrize(
    ("path", "content_type"),
    [
        ("/favicon.ico", "image/x-icon"),
        ("/favicon-16x16.png", "image/png"),
        ("/favicon-32x32.png", "image/png"),
        ("/apple-touch-icon.png", "image/png"),
        ("/android-chrome-192x192.png", "image/png"),
        ("/android-chrome-512x512.png", "image/png"),
        ("/opengraph.png", "image/png"),
        ("/site.webmanifest", "application/manifest+json"),
    ],
)
class TestRootAssets:
    def test_served_at_root(self, unauthed_client, path, content_type):
        resp = unauthed_client.get(path)
        assert resp.status_code == 200
        assert resp.headers["content-type"] == content_type
