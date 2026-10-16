import base64
import hashlib
import hmac
import json

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.auth import get_db
from app.database import Base
from app.main import app
from app.models.user import User
from app.services.auth import (
    TOKEN_TTL_SECONDS,
    AuthenticationError,
    _auth_secret,
    create_access_token,
    verify_access_token,
)

client = TestClient(app)


@pytest.fixture(autouse=True)
def isolated_auth_database():
    """Provide an isolated database for authentication API tests."""
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(bind=engine, tables=[User.__table__])

    def override_get_db():
        with Session(engine) as db:
            yield db

    app.dependency_overrides[get_db] = override_get_db

    try:
        yield
    finally:
        app.dependency_overrides.pop(get_db, None)
        engine.dispose()


def test_login_returns_token_and_saved_account_information():
    response = client.post(
        "/auth/login",
        json={
            "email": "investor@example.com",
            "password": "SecurePass123!",
        },
    )

    assert response.status_code == 200

    data = response.json()
    assert data["token_type"] == "bearer"
    assert data["expires_in"] == 3600
    assert data["access_token"]
    assert data["user"] == {
        "email": "investor@example.com",
        "name": "Registered Investor",
        "saved_stocks": ["LMT", "RTX", "NOC"],
        "investment_focus": "Defense-sector equities",
    }


def test_login_rejects_invalid_credentials():
    response = client.post(
        "/auth/login",
        json={
            "email": "investor@example.com",
            "password": "wrong-password",
        },
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid email or password."}


def test_current_account_requires_bearer_token():
    response = client.get("/auth/me")

    assert response.status_code == 401
    assert response.json() == {"detail": "Authentication required."}


def test_current_account_returns_saved_information_with_valid_token():
    token = create_access_token("investor@example.com")

    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 200
    assert response.json()["saved_stocks"] == ["LMT", "RTX", "NOC"]


def test_current_account_rejects_tampered_token():
    token = f"{create_access_token('investor@example.com')}tampered"

    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid access token."}


def test_current_account_rejects_signed_token_with_invalid_payload():
    """A correctly signed token with invalid claims must return 401."""

    # The payload is valid JSON, but not a token claims object.
    payload = json.dumps(["not", "a", "valid", "payload"])
    encoded_payload = (
        base64.urlsafe_b64encode(payload.encode("utf-8")).rstrip(b"=").decode("ascii")
    )

    # Sign the malformed payload using the application's signing key.
    signature = hmac.new(
        _auth_secret(),
        encoded_payload.encode("ascii"),
        hashlib.sha256,
    ).digest()

    encoded_signature = base64.urlsafe_b64encode(signature).rstrip(b"=").decode("ascii")

    token = f"{encoded_payload}.{encoded_signature}"

    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid access token."}


@pytest.mark.parametrize(
    "authorization",
    ["Basic credentials", "Bearer", "Bearer invalid.token", "Bearer a.b.c"],
)
def test_current_account_rejects_invalid_authorization(authorization):
    response = client.get("/auth/me", headers={"Authorization": authorization})

    assert response.status_code == 401
    assert "saved_stocks" not in response.json()


def test_current_account_rejects_expired_token():
    token = create_access_token("investor@example.com", issued_at=1)

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
    assert "saved_stocks" not in response.json()


def test_current_account_rejects_unknown_subject():
    token = create_access_token("unknown@example.invalid")

    response = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})

    assert response.status_code == 401
    assert "saved_stocks" not in response.json()


def test_access_token_expires_at_expiration_boundary():
    issued_at = 1_700_000_000
    token = create_access_token("investor@example.com", issued_at=issued_at)

    with pytest.raises(AuthenticationError, match="expired"):
        verify_access_token(token, current_time=issued_at + TOKEN_TTL_SECONDS)


def test_registered_accounts_cannot_read_each_others_information():
    for name, email in (
        ("Investor One", "one@example.invalid"),
        ("Investor Two", "two@example.invalid"),
    ):
        response = client.post(
            "/auth/register",
            json={"name": name, "email": email, "password": "SecurePassword123!"},
        )
        assert response.status_code == 201

    for name, email in (
        ("Investor One", "one@example.invalid"),
        ("Investor Two", "two@example.invalid"),
    ):
        login = client.post(
            "/auth/login",
            json={"email": email, "password": "SecurePassword123!"},
        )
        assert login.status_code == 200
        token = login.json()["access_token"]
        account = client.get("/auth/me", headers={"Authorization": f"Bearer {token}"})
        assert account.status_code == 200
        assert account.json() == {
            "email": email,
            "name": name,
            "saved_stocks": [],
            "investment_focus": "",
        }
