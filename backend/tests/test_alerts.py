"""Tests for US-39 and US-40 stock alerts."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.favorites import (
    get_current_user_email,
    get_db,
)
from app.database import Base
from app.main import app
from app.models.alert import Alert

# --------------------------------------------------
# Test Database and Authentication Setup
# --------------------------------------------------


@pytest.fixture
def client():
    """Create an isolated test database for each test."""

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(
        bind=engine,
        tables=[Alert.__table__],
    )

    TestSession = sessionmaker(
        bind=engine,
        expire_on_commit=False,
    )

    current_user = {"email": "user1@example.com"}

    def override_get_db():
        with TestSession() as session:
            yield session

    def override_current_user():
        return current_user["email"]

    app.dependency_overrides[get_db] = override_get_db
    app.dependency_overrides[get_current_user_email] = override_current_user

    try:
        with TestClient(app) as test_client:
            yield test_client, current_user
    finally:
        app.dependency_overrides.pop(get_db, None)
        app.dependency_overrides.pop(get_current_user_email, None)
        Base.metadata.drop_all(
            bind=engine,
            tables=[Alert.__table__],
        )
        engine.dispose()


# --------------------------------------------------
# US-39: Create Stock Alert
# --------------------------------------------------


def test_create_alert_success(client):
    api, _ = client

    response = api.post(
        "/alerts",
        json={
            "ticker": "LMT",
            "condition": "above",
            "threshold": 500.0,
        },
    )

    assert response.status_code == 201

    data = response.json()

    assert data["id"] > 0
    assert data["ticker"] == "LMT"
    assert data["condition"] == "above"
    assert data["threshold"] == 500.0
    assert "created_at" in data


def test_create_below_alert(client):
    api, _ = client

    response = api.post(
        "/alerts",
        json={
            "ticker": "RTX",
            "condition": "below",
            "threshold": 100.0,
        },
    )

    assert response.status_code == 201
    assert response.json()["condition"] == "below"


def test_ticker_normalization(client):
    api, _ = client

    response = api.post(
        "/alerts",
        json={
            "ticker": " lmt ",
            "condition": "above",
            "threshold": 500,
        },
    )

    assert response.status_code == 201
    assert response.json()["ticker"] == "LMT"


@pytest.mark.parametrize(
    "ticker",
    ["INVALID", "XYZ", "123", ""],
)
def test_invalid_ticker(client, ticker):
    api, _ = client

    response = api.post(
        "/alerts",
        json={
            "ticker": ticker,
            "condition": "above",
            "threshold": 500,
        },
    )

    assert response.status_code == 422


@pytest.mark.parametrize(
    "threshold",
    [-100, 0, -0.01, "NaN", "Infinity"],
)
def test_invalid_threshold(client, threshold):
    api, _ = client

    response = api.post(
        "/alerts",
        json={
            "ticker": "LMT",
            "condition": "above",
            "threshold": threshold,
        },
    )

    assert response.status_code == 422


def test_invalid_condition(client):
    api, _ = client

    response = api.post(
        "/alerts",
        json={
            "ticker": "LMT",
            "condition": "between",
            "threshold": 500,
        },
    )

    assert response.status_code == 422


def test_missing_required_fields(client):
    api, _ = client

    response = api.post(
        "/alerts",
        json={"ticker": "LMT"},
    )

    assert response.status_code == 422


# --------------------------------------------------
# US-40: View and Manage Alerts
# --------------------------------------------------


def test_list_alerts_empty(client):
    api, _ = client

    response = api.get("/alerts")

    assert response.status_code == 200
    assert response.json() == []


def test_list_multiple_alerts(client):
    api, _ = client

    for ticker in ["LMT", "RTX", "NOC"]:
        response = api.post(
            "/alerts",
            json={
                "ticker": ticker,
                "condition": "above",
                "threshold": 200,
            },
        )

        assert response.status_code == 201

    response = api.get("/alerts")

    assert response.status_code == 200
    assert len(response.json()) == 3

    tickers = {alert["ticker"] for alert in response.json()}

    assert tickers == {"LMT", "RTX", "NOC"}


def test_alert_persistence(client):
    api, _ = client

    created = api.post(
        "/alerts",
        json={
            "ticker": "GD",
            "condition": "below",
            "threshold": 250,
        },
    )

    assert created.status_code == 201

    alert_id = created.json()["id"]

    response = api.get("/alerts")

    assert response.status_code == 200

    assert any(alert["id"] == alert_id for alert in response.json())


def test_delete_alert_success(client):
    api, _ = client

    created = api.post(
        "/alerts",
        json={
            "ticker": "LMT",
            "condition": "above",
            "threshold": 500,
        },
    )

    assert created.status_code == 201

    alert_id = created.json()["id"]

    response = api.delete(f"/alerts/{alert_id}")

    assert response.status_code == 204

    listed = api.get("/alerts")

    assert listed.status_code == 200
    assert listed.json() == []


def test_delete_nonexistent_alert(client):
    api, _ = client

    response = api.delete("/alerts/99999")

    assert response.status_code == 404
    assert response.json()["detail"] == "Alert not found."


def test_delete_same_alert_twice(client):
    api, _ = client

    created = api.post(
        "/alerts",
        json={
            "ticker": "LMT",
            "condition": "above",
            "threshold": 500,
        },
    )

    assert created.status_code == 201

    alert_id = created.json()["id"]

    first = api.delete(f"/alerts/{alert_id}")
    second = api.delete(f"/alerts/{alert_id}")

    assert first.status_code == 204
    assert second.status_code == 404


# --------------------------------------------------
# Security: User Isolation
# --------------------------------------------------


def test_users_only_see_their_alerts(client):
    api, current_user = client

    response = api.post(
        "/alerts",
        json={
            "ticker": "LMT",
            "condition": "above",
            "threshold": 500,
        },
    )

    assert response.status_code == 201

    current_user["email"] = "user2@example.com"

    response = api.get("/alerts")

    assert response.status_code == 200
    assert response.json() == []


def test_user_cannot_delete_another_users_alert(client):
    api, current_user = client

    created = api.post(
        "/alerts",
        json={
            "ticker": "LMT",
            "condition": "above",
            "threshold": 500,
        },
    )

    assert created.status_code == 201

    alert_id = created.json()["id"]

    current_user["email"] = "user2@example.com"

    response = api.delete(f"/alerts/{alert_id}")

    assert response.status_code == 404

    current_user["email"] = "user1@example.com"

    response = api.get("/alerts")

    assert response.status_code == 200
    assert len(response.json()) == 1


# --------------------------------------------------
# API Route Registration
# --------------------------------------------------


def test_alert_routes_registered():
    routes = {
        (route.path, method)
        for route in app.routes
        for method in getattr(route, "methods", [])
    }

    assert ("/alerts", "POST") in routes
    assert ("/alerts", "GET") in routes
    assert ("/alerts/{alert_id}", "DELETE") in routes
