from fastapi.testclient import TestClient

from app.main import app
from app.services.auth import create_access_token

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
