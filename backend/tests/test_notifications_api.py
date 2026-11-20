"""US-41: Notification history integration tests."""

from decimal import Decimal

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, event
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.favorites import get_db
from app.database import Base
from app.main import app
from app.models.market_alert import MarketAlert
from app.models.notification_event import NotificationEvent
from app.models.user import User
from app.services.auth import create_access_token


@pytest.fixture
def notification_client():
    """Create two investors with separate notification histories."""

    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    @event.listens_for(engine, "connect")
    def enable_foreign_keys(connection, _record):
        connection.execute("PRAGMA foreign_keys=ON")

    Base.metadata.create_all(
        bind=engine,
        tables=[
            User.__table__,
            MarketAlert.__table__,
            NotificationEvent.__table__,
        ],
    )

    with Session(engine) as db:
        investor_a = User(
            name="Investor A",
            email="investor-a@example.com",
            password_hash="unused-test-hash",
        )
        investor_b = User(
            name="Investor B",
            email="investor-b@example.com",
            password_hash="unused-test-hash",
        )

        db.add_all([investor_a, investor_b])
        db.flush()

        alert_a = MarketAlert(
            user_id=investor_a.id,
            ticker="LMT",
            threshold_percent=Decimal("5"),
            direction="increase",
            is_active=True,
        )
        alert_b = MarketAlert(
            user_id=investor_b.id,
            ticker="RTX",
            threshold_percent=Decimal("3"),
            direction="decrease",
            is_active=True,
        )

        db.add_all([alert_a, alert_b])
        db.flush()

        notification_a = NotificationEvent(
            alert_id=alert_a.id,
            user_id=investor_a.id,
            ticker="LMT",
            threshold_percent=Decimal("5"),
            observed_change_percent=Decimal("6"),
            observed_price=Decimal("106"),
            reference_price=Decimal("100"),
            deduplication_key="test-alert-a-2026-11-18",
        )

        notification_b = NotificationEvent(
            alert_id=alert_b.id,
            user_id=investor_b.id,
            ticker="RTX",
            threshold_percent=Decimal("3"),
            observed_change_percent=Decimal("-4"),
            observed_price=Decimal("96"),
            reference_price=Decimal("100"),
            deduplication_key="test-alert-b-2026-11-18",
        )

        db.add_all([notification_a, notification_b])
        db.flush()

        ids = {
            "alert_a": alert_a.id,
            "notification_a": notification_a.id,
            "notification_b": notification_b.id,
        }

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
            yield client, headers, ids
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()


def test_list_own_notifications(notification_client):
    client, headers, ids = notification_client

    response = client.get(
        "/notifications",
        headers=headers["a"],
    )

    assert response.status_code == 200
    assert len(response.json()) == 1

    notification = response.json()[0]

    assert notification["id"] == ids["notification_a"]
    assert notification["ticker"] == "LMT"
    assert notification["is_read"] is False
    assert notification["triggered_at"]


def test_notification_history_is_private(notification_client):
    client, headers, ids = notification_client

    response_a = client.get(
        "/notifications",
        headers=headers["a"],
    )
    response_b = client.get(
        "/notifications",
        headers=headers["b"],
    )

    assert response_a.status_code == 200
    assert response_b.status_code == 200

    assert [item["id"] for item in response_a.json()] == [ids["notification_a"]]
    assert [item["id"] for item in response_b.json()] == [ids["notification_b"]]


def test_notifications_require_authentication(notification_client):
    client, _, ids = notification_client

    history = client.get("/notifications")

    update = client.patch(f"/notifications/{ids['notification_a']}/read")

    assert history.status_code == 401
    assert update.status_code == 401


def test_mark_notification_read_persists(notification_client):
    client, headers, ids = notification_client

    response = client.patch(
        f"/notifications/{ids['notification_a']}/read",
        headers=headers["a"],
    )

    assert response.status_code == 200
    assert response.json()["is_read"] is True

    history = client.get(
        "/notifications",
        headers=headers["a"],
    )

    assert history.status_code == 200
    assert history.json()[0]["is_read"] is True


def test_investor_cannot_modify_another_notification(notification_client):
    client, headers, ids = notification_client

    response = client.patch(
        f"/notifications/{ids['notification_a']}/read",
        headers=headers["b"],
    )

    assert response.status_code == 404

    original = client.get(
        "/notifications",
        headers=headers["a"],
    )

    assert original.status_code == 200
    assert original.json()[0]["is_read"] is False


def test_nonexistent_notification_returns_404(notification_client):
    client, headers, _ = notification_client

    response = client.patch(
        "/notifications/999999/read",
        headers=headers["a"],
    )

    assert response.status_code == 404


def test_deleting_alert_preserves_notification_history(
    notification_client,
):
    client, headers, ids = notification_client

    deleted = client.delete(
        f"/market-alerts/{ids['alert_a']}",
        headers=headers["a"],
    )

    assert deleted.status_code == 204

    response = client.get(
        "/notifications",
        headers=headers["a"],
    )

    assert response.status_code == 200
    assert len(response.json()) == 1

    notification = response.json()[0]

    assert notification["id"] == ids["notification_a"]
    assert notification["alert_id"] is None
    assert notification["ticker"] == "LMT"
    assert Decimal(str(notification["observed_change_percent"])) == Decimal("6")
