"""Tests for the password-reset workflow."""

from datetime import datetime, timedelta, timezone
from unittest.mock import patch

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.auth import get_db
from app.database import Base
from app.main import app
from app.models.password_reset import PasswordResetToken
from app.models.user import User
from app.services.auth import verify_password

EMAIL = "resetuser@example.com"
OLD_PASSWORD = "OriginalPassword123!"
NEW_PASSWORD = "NewSecurePassword456!"


@pytest.fixture
def reset_client():
    """Create isolated database and mock email delivery."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(
        bind=engine,
        tables=[User.__table__, PasswordResetToken.__table__],
    )

    def override_get_db():
        with Session(engine) as db:
            yield db

    previous_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_get_db

    try:
        with patch("app.api.auth.send_password_reset_email") as mock_email:
            with TestClient(app) as client:
                registration = client.post(
                    "/auth/register",
                    json={
                        "name": "Reset Test User",
                        "email": EMAIL,
                        "password": OLD_PASSWORD,
                    },
                )
                assert registration.status_code == 201

                yield client, engine, mock_email
    finally:
        if previous_override is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous_override

        engine.dispose()


def request_token(client, mock_email):
    """Request a reset and capture its emailed token."""
    mock_email.reset_mock()

    response = client.post(
        "/auth/password-reset/request",
        json={"email": EMAIL},
    )

    assert response.status_code == 200
    mock_email.assert_called_once()

    return mock_email.call_args.kwargs["token"]


def test_registered_user_can_request_reset(reset_client):
    client, engine, mock_email = reset_client

    token = request_token(client, mock_email)

    assert token
    assert len(token) >= 32

    with Session(engine) as db:
        record = db.scalar(select(PasswordResetToken))

        assert record is not None
        assert record.token_hash != token
        assert record.used_at is None


def test_unknown_email_receives_generic_response(reset_client):
    client, _, mock_email = reset_client

    known = client.post(
        "/auth/password-reset/request",
        json={"email": EMAIL},
    )
    unknown = client.post(
        "/auth/password-reset/request",
        json={"email": "unknown@example.com"},
    )

    assert known.status_code == unknown.status_code == 200
    assert known.json() == unknown.json()

    mock_email.assert_called_once()


def test_valid_token_updates_password(reset_client):
    client, engine, mock_email = reset_client
    token = request_token(client, mock_email)

    response = client.post(
        "/auth/password-reset/confirm",
        json={
            "token": token,
            "new_password": NEW_PASSWORD,
        },
    )

    assert response.status_code == 200
    assert response.json()["message"] == "Password reset successful."

    with Session(engine) as db:
        user = db.scalar(select(User).where(User.email == EMAIL))
        record = db.scalar(select(PasswordResetToken))

        assert verify_password(NEW_PASSWORD, user.password_hash)
        assert not verify_password(OLD_PASSWORD, user.password_hash)
        assert record.used_at is not None

    old_login = client.post(
        "/auth/login",
        json={"email": EMAIL, "password": OLD_PASSWORD},
    )
    new_login = client.post(
        "/auth/login",
        json={"email": EMAIL, "password": NEW_PASSWORD},
    )

    assert old_login.status_code == 401
    assert new_login.status_code == 200


def test_reset_token_cannot_be_reused(reset_client):
    client, _, mock_email = reset_client
    token = request_token(client, mock_email)

    payload = {
        "token": token,
        "new_password": NEW_PASSWORD,
    }

    first = client.post("/auth/password-reset/confirm", json=payload)
    second = client.post("/auth/password-reset/confirm", json=payload)

    assert first.status_code == 200
    assert second.status_code == 400


def test_invalid_token_is_rejected(reset_client):
    client, _, _ = reset_client

    response = client.post(
        "/auth/password-reset/confirm",
        json={
            "token": "not-a-real-token",
            "new_password": NEW_PASSWORD,
        },
    )

    assert response.status_code == 400


def test_expired_token_is_rejected(reset_client):
    client, engine, mock_email = reset_client
    token = request_token(client, mock_email)

    with Session(engine) as db:
        record = db.scalar(select(PasswordResetToken))
        record.expires_at = datetime.now(timezone.utc) - timedelta(minutes=1)
        db.commit()

    response = client.post(
        "/auth/password-reset/confirm",
        json={
            "token": token,
            "new_password": NEW_PASSWORD,
        },
    )

    assert response.status_code == 400


def test_new_request_invalidates_previous_token(reset_client):
    client, _, mock_email = reset_client

    first_token = request_token(client, mock_email)
    second_token = request_token(client, mock_email)

    assert first_token != second_token

    first_response = client.post(
        "/auth/password-reset/confirm",
        json={
            "token": first_token,
            "new_password": NEW_PASSWORD,
        },
    )
    second_response = client.post(
        "/auth/password-reset/confirm",
        json={
            "token": second_token,
            "new_password": NEW_PASSWORD,
        },
    )

    assert first_response.status_code == 400
    assert second_response.status_code == 200


def test_reset_token_cannot_access_protected_account(reset_client):
    client, _, mock_email = reset_client
    token = request_token(client, mock_email)

    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401


def test_email_delivery_failure_keeps_generic_response(reset_client):
    client, _, mock_email = reset_client
    mock_email.side_effect = RuntimeError("SMTP unavailable")

    response = client.post(
        "/auth/password-reset/request",
        json={"email": EMAIL},
    )

    assert response.status_code == 200
    assert "token" not in response.json()
