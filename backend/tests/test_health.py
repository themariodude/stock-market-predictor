"""Smoke test for the health endpoint. Runs without a database."""

from unittest.mock import MagicMock

from fastapi.testclient import TestClient

from app import main

client = TestClient(main.app)


def test_health_returns_ok():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_health_reports_database_key():
    assert "database" in client.get("/health").json()


def test_ready_returns_ok_when_database_available(monkeypatch):
    engine = MagicMock()
    monkeypatch.setattr(main, "_engine", engine)

    response = client.get("/ready")

    assert response.status_code == 200
    assert response.json() == {"status": "ok", "database": "ok"}
    engine.connect.assert_called_once()


def test_ready_returns_503_when_database_unavailable(monkeypatch):
    engine = MagicMock()
    engine.connect.side_effect = RuntimeError("Database unavailable")
    monkeypatch.setattr(main, "_engine", engine)

    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {"detail": "Database unavailable"}


def test_ready_returns_503_when_database_unconfigured(monkeypatch):
    monkeypatch.setattr(main, "_engine", None)

    response = client.get("/ready")

    assert response.status_code == 503
    assert response.json() == {"detail": "Database unavailable"}
