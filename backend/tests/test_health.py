"""Smoke test for the health endpoint. Runs without a database."""

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_reports_database_key():
    assert "database" in client.get("/health").json()
