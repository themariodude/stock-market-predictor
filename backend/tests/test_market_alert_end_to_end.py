"""US-41: End-to-end market alert notification workflow."""

from datetime import date
from decimal import Decimal

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
from app.services.market_alert_runner import run_verified_market_scan


def test_alert_to_notification_to_read():
    """Verify the complete authenticated notification workflow."""
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
        db.add_all(
            [
                User(
                    name="Investor A",
                    email="e2e-a@example.com",
                    password_hash="test-hash",
                ),
                User(
                    name="Investor B",
                    email="e2e-b@example.com",
                    password_hash="test-hash",
                ),
            ]
        )
        db.commit()

    def override_get_db():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db

    headers_a = {
        "Authorization": (f"Bearer {create_access_token('e2e-a@example.com')}")
    }
    headers_b = {
        "Authorization": (f"Bearer {create_access_token('e2e-b@example.com')}")
    }

    try:
        with TestClient(app) as client:
            # Step 1: Investor A creates an alert.
            created = client.post(
                "/alerts",
                headers=headers_a,
                json={
                    "ticker": "LMT",
                    "threshold_percent": 5.1,
                    "direction": "increase",
                },
            )

            assert created.status_code == 201
            alert_id = created.json()["id"]

            # Step 2: Simulate two completed trading sessions.
            def history_loader(ticker, period):
                assert ticker == "LMT"
                assert period == "1M"

                return {
                    "data": [
                        {"date": "2026-11-17", "close": 100},
                        {"date": "2026-11-18", "close": 106},
                    ]
                }

            with Session(engine) as db:
                notifications_created = run_verified_market_scan(
                    db,
                    date(2026, 11, 18),
                    history_loader=history_loader,
                )

                # Repeated scans must not create duplicates.
                duplicate_count = run_verified_market_scan(
                    db,
                    date(2026, 11, 18),
                    history_loader=history_loader,
                )

            assert notifications_created == 1
            assert duplicate_count == 0

            # Step 3: Investor A retrieves the notification.
            response = client.get(
                "/notifications",
                headers=headers_a,
            )

            assert response.status_code == 200
            assert len(response.json()) == 1

            notification = response.json()[0]

            assert notification["ticker"] == "LMT"
            assert notification["alert_id"] == alert_id
            assert notification["is_read"] is False
            assert Decimal(str(notification["observed_change_percent"])) == Decimal("6")

            notification_id = notification["id"]

            # Step 4: Investor B cannot access Investor A's data.
            other_history = client.get(
                "/notifications",
                headers=headers_b,
            )

            assert other_history.status_code == 200
            assert other_history.json() == []

            forbidden = client.patch(
                f"/notifications/{notification_id}/read",
                headers=headers_b,
            )

            assert forbidden.status_code == 404

            # Step 5: Investor A marks the notification as read.
            marked = client.patch(
                f"/notifications/{notification_id}/read",
                headers=headers_a,
            )

            assert marked.status_code == 200
            assert marked.json()["is_read"] is True

            # Step 6: The read status persists.
            history = client.get(
                "/notifications",
                headers=headers_a,
            )

            assert history.status_code == 200
            assert len(history.json()) == 1
            assert history.json()[0]["is_read"] is True

    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()
