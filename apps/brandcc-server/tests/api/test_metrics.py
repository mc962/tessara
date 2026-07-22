"""Tests for GET /metrics."""


class TestMetrics:
    def test_returns_200(self, api_client):
        resp = api_client.get("/metrics")
        assert resp.status_code == 200

    def test_content_type_is_prometheus(self, api_client):
        resp = api_client.get("/metrics")
        assert "text/plain" in resp.headers["content-type"]

    def test_no_auth_required(self, unauthed_client):
        resp = unauthed_client.get("/metrics")
        assert resp.status_code == 200
