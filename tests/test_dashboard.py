"""The static test dashboard is served at /dashboard."""

from fastapi.testclient import TestClient

from app.main import app


def test_dashboard_is_served():
    with TestClient(app) as client:
        r = client.get("/dashboard/")
        assert r.status_code == 200
        assert "control room" in r.text


def test_root_redirects_to_dashboard():
    with TestClient(app) as client:
        r = client.get("/", follow_redirects=False)
        assert r.status_code == 307
        assert r.headers["location"] == "/dashboard/"
