import base64
import hashlib
import hmac
import json

from fastapi.testclient import TestClient

from app.main import app
from app.services.auth import _auth_secret, create_access_token

client = TestClient(app)


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
    encoded_payload = base64.urlsafe_b64encode(
        payload.encode("utf-8")
    ).rstrip(b"=").decode("ascii")

    # Sign the malformed payload using the application's signing key.
    signature = hmac.new(
        _auth_secret(),
        encoded_payload.encode("ascii"),
        hashlib.sha256,
    ).digest()

    encoded_signature = base64.urlsafe_b64encode(
        signature
    ).rstrip(b"=").decode("ascii")

    token = f"{encoded_payload}.{encoded_signature}"

    response = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert response.status_code == 401
    assert response.json() == {"detail": "Invalid access token."}

