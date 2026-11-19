"""US-41: Integration tests for market alert APIs."""

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.favorites import get_db
from app.database import Base
from app.main import app
from app.models.market_alert import MarketAlert
from app.models.user import User
from app.services.auth import create_access_token


@pytest.fixture
def alert_client():
    """Provide two investors and an isolated SQLite database."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(
        bind=engine,
        tables=[User.__table__, MarketAlert.__table__],
    )

    with Session(engine) as db:
        db.add_all(
            [
                User(
                    name="Investor A",
                    email="investor-a@example.com",
                    password_hash="unused-test-hash",
                ),
                User(
                    name="Investor B",
                    email="investor-b@example.com",
                    password_hash="unused-test-hash",
                ),
            ]
        )
        db.commit()

    def override_get_db():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db

    headers = {
        "a": {
            "Authorization": (f"Bearer {create_access_token('investor-a@example.com')}")
        },
        "b": {
            "Authorization": (f"Bearer {create_access_token('investor-b@example.com')}")
        },
    }

    try:
        with TestClient(app) as client:
            yield client, headers
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()


def test_create_market_alert(alert_client):
    client, headers = alert_client

    response = client.post(
        "/market-alerts",
        headers=headers["a"],
        json={
            "ticker": "LMT",
            "threshold_percent": 5,
            "direction": "increase",
        },
    )

    assert response.status_code == 201

    data = response.json()
    assert data["id"] > 0
    assert data["ticker"] == "LMT"
    assert Decimal(str(data["threshold_percent"])) == Decimal("5")
    assert data["direction"] == "increase"
    assert data["is_active"] is True
    assert data["created_at"]
    assert data["updated_at"]


def test_alert_persists_across_requests(alert_client):
    client, headers = alert_client

    created = client.post(
        "/market-alerts",
        headers=headers["a"],
        json={
            "ticker": "NOC",
            "threshold_percent": 3,
            "direction": "decrease",
        },
    )

    assert created.status_code == 201

    response = client.get("/market-alerts", headers=headers["a"])

    assert response.status_code == 200
    assert len(response.json()) == 1
    assert response.json()[0]["ticker"] == "NOC"
    assert response.json()[0]["id"] == created.json()["id"]


def test_investors_only_see_their_own_alerts(alert_client):
    client, headers = alert_client

    first = client.post(
        "/market-alerts",
        headers=headers["a"],
        json={
            "ticker": "LMT",
            "threshold_percent": 5,
            "direction": "increase",
        },
    )

    second = client.post(
        "/market-alerts",
        headers=headers["b"],
        json={
            "ticker": "RTX",
            "threshold_percent": 2,
            "direction": "either",
        },
    )

    assert first.status_code == 201
    assert second.status_code == 201

    alerts_a = client.get("/market-alerts", headers=headers["a"]).json()

    alerts_b = client.get("/market-alerts", headers=headers["b"]).json()

    assert len(alerts_a) == 1
    assert len(alerts_b) == 1

    assert alerts_a[0]["ticker"] == "LMT"
    assert alerts_b[0]["ticker"] == "RTX"


def test_alerts_require_authentication(alert_client):
    client, _ = alert_client

    get_response = client.get("/market-alerts")

    post_response = client.post(
        "/market-alerts",
        json={
            "ticker": "LMT",
            "threshold_percent": 5,
            "direction": "increase",
        },
    )

    assert get_response.status_code == 401
    assert post_response.status_code == 401


@pytest.mark.parametrize("threshold", [0, -1, 101])
def test_rejects_invalid_thresholds(alert_client, threshold):
    client, headers = alert_client

    response = client.post(
        "/market-alerts",
        headers=headers["a"],
        json={
            "ticker": "LMT",
            "threshold_percent": threshold,
            "direction": "increase",
        },
    )

    assert response.status_code == 422


def test_rejects_invalid_direction(alert_client):
    client, headers = alert_client

    response = client.post(
        "/market-alerts",
        headers=headers["a"],
        json={
            "ticker": "LMT",
            "threshold_percent": 5,
            "direction": "upward",
        },
    )

    assert response.status_code == 422


def test_rejects_empty_ticker(alert_client):
    client, headers = alert_client

    response = client.post(
        "/market-alerts",
        headers=headers["a"],
        json={
            "ticker": "",
            "threshold_percent": 5,
            "direction": "increase",
        },
    )

    assert response.status_code == 422


def test_update_alert_threshold_and_direction(alert_client):
    client, headers = alert_client

    created = client.post(
        "/market-alerts",
        headers=headers["a"],
        json={
            "ticker": "LMT",
            "threshold_percent": 5,
            "direction": "increase",
        },
    )
    assert created.status_code == 201
    alert_id = created.json()["id"]

    response = client.patch(
        f"/market-alerts/{alert_id}",
        headers=headers["a"],
        json={
            "threshold_percent": 7,
            "direction": "decrease",
        },
    )

    assert response.status_code == 200
    assert Decimal(str(response.json()["threshold_percent"])) == Decimal("7")
    assert response.json()["direction"] == "decrease"

    saved = client.get("/market-alerts", headers=headers["a"])
    assert saved.status_code == 200
    assert saved.json()[0]["direction"] == "decrease"


def test_disable_and_reenable_alert(alert_client):
    client, headers = alert_client

    created = client.post(
        "/market-alerts",
        headers=headers["a"],
        json={
            "ticker": "NOC",
            "threshold_percent": 3,
            "direction": "either",
        },
    )
    assert created.status_code == 201
    alert_id = created.json()["id"]

    disabled = client.patch(
        f"/market-alerts/{alert_id}",
        headers=headers["a"],
        json={"is_active": False},
    )

    assert disabled.status_code == 200
    assert disabled.json()["is_active"] is False

    enabled = client.patch(
        f"/market-alerts/{alert_id}",
        headers=headers["a"],
        json={"is_active": True},
    )

    assert enabled.status_code == 200
    assert enabled.json()["is_active"] is True


@pytest.mark.parametrize(
    "payload",
    [
        {},
        {"threshold_percent": None},
        {"is_active": None},
    ],
)
def test_rejects_empty_or_null_updates(alert_client, payload):
    client, headers = alert_client

    created = client.post(
        "/market-alerts",
        headers=headers["a"],
        json={
            "ticker": "LMT",
            "threshold_percent": 5,
            "direction": "increase",
        },
    )
    assert created.status_code == 201

    response = client.patch(
        f"/market-alerts/{created.json()['id']}",
        headers=headers["a"],
        json=payload,
    )

    assert response.status_code == 422


@pytest.mark.parametrize("threshold", [0, 101])
def test_rejects_invalid_updated_threshold(alert_client, threshold):
    client, headers = alert_client

    created = client.post(
        "/market-alerts",
        headers=headers["a"],
        json={
            "ticker": "RTX",
            "threshold_percent": 5,
            "direction": "increase",
        },
    )
    assert created.status_code == 201

    response = client.patch(
        f"/market-alerts/{created.json()['id']}",
        headers=headers["a"],
        json={"threshold_percent": threshold},
    )

    assert response.status_code == 422


def test_investor_cannot_modify_or_delete_another_users_alert(alert_client):
    client, headers = alert_client

    created = client.post(
        "/market-alerts",
        headers=headers["a"],
        json={
            "ticker": "LMT",
            "threshold_percent": 5,
            "direction": "increase",
        },
    )
    assert created.status_code == 201
    alert_id = created.json()["id"]

    update = client.patch(
        f"/market-alerts/{alert_id}",
        headers=headers["b"],
        json={"is_active": False},
    )

    delete = client.delete(
        f"/market-alerts/{alert_id}",
        headers=headers["b"],
    )

    assert update.status_code == 404
    assert delete.status_code == 404

    owner_alerts = client.get("/market-alerts", headers=headers["a"])

    assert owner_alerts.status_code == 200
    assert len(owner_alerts.json()) == 1
    assert owner_alerts.json()[0]["is_active"] is True


def test_delete_own_alert(alert_client):
    client, headers = alert_client

    created = client.post(
        "/market-alerts",
        headers=headers["a"],
        json={
            "ticker": "NOC",
            "threshold_percent": 4,
            "direction": "decrease",
        },
    )
    assert created.status_code == 201
    alert_id = created.json()["id"]

    response = client.delete(
        f"/market-alerts/{alert_id}",
        headers=headers["a"],
    )

    assert response.status_code == 204

    remaining = client.get("/market-alerts", headers=headers["a"])
    assert remaining.status_code == 200
    assert remaining.json() == []

    repeated = client.delete(
        f"/market-alerts/{alert_id}",
        headers=headers["a"],
    )
    assert repeated.status_code == 404


def test_update_and_delete_require_authentication(alert_client):
    client, _ = alert_client

    update = client.patch(
        "/market-alerts/1",
        json={"is_active": False},
    )

    delete = client.delete("/market-alerts/1")

    assert update.status_code == 401
    assert delete.status_code == 401
