"""Tests for GET /health."""


class TestHealth:
    def test_returns_ok(self, api_client):
        resp = api_client.get("/health")
        assert resp.status_code == 200
        assert resp.json() == {"status": "ok"}

    def test_no_auth_required(self, unauthed_client):
        resp = unauthed_client.get("/health")
        assert resp.status_code == 200
