
import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.auth import get_db
from app.database import Base
from app.main import app
from app.models.user import User
from app.services.auth import verify_password


@pytest.fixture
def registration_client():
    """Create an isolated database for each registration test."""
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(
        bind=engine,
        tables=[User.__table__],
    )

    def override_get_db():
        with Session(engine) as db:
            yield db

    previous_override = app.dependency_overrides.get(get_db)
    app.dependency_overrides[get_db] = override_get_db

    try:
        with TestClient(app) as client:
            yield client, engine
    finally:
        if previous_override is None:
            app.dependency_overrides.pop(get_db, None)
        else:
            app.dependency_overrides[get_db] = previous_override

        engine.dispose()


def test_registration_creates_account(registration_client):
    client, engine = registration_client

    response = client.post(
        "/auth/register",
        json={
            "name": "Test Investor",
            "email": "newinvestor@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert response.status_code == 201
    assert response.json() == {
        "email": "newinvestor@example.com",
        "name": "Test Investor",
    }

    with Session(engine) as db:
        user = db.query(User).filter_by(
            email="newinvestor@example.com"
        ).one()

        assert user.password_hash != "SecurePassword123!"
        assert verify_password(
            "SecurePassword123!",
            user.password_hash,
        )


def test_registration_rejects_duplicate_email(registration_client):
    client, engine = registration_client

    payload = {
        "name": "Test Investor",
        "email": "duplicate@example.com",
        "password": "SecurePassword123!",
    }

    first = client.post("/auth/register", json=payload)
    second = client.post("/auth/register", json=payload)

    assert first.status_code == 201
    assert second.status_code == 409
    assert second.json() == {
        "detail": "An account with this email already exists."
    }

    with Session(engine) as db:
        assert db.query(User).filter_by(
            email="duplicate@example.com"
        ).count() == 1


@pytest.mark.parametrize(
    "name,email,password",
    [
        ("", "valid@example.com", "SecurePassword123!"),
        ("   ", "valid@example.com", "SecurePassword123!"),
        ("Test Investor", "invalid-email", "SecurePassword123!"),
        ("Test Investor", "valid@example.com", "short"),
    ],
)
def test_registration_rejects_invalid_inputs(
    registration_client,
    name,
    email,
    password,
):
    client, _ = registration_client

    response = client.post(
        "/auth/register",
        json={
            "name": name,
            "email": email,
            "password": password,
        },
    )

    assert response.status_code == 422


def test_registered_investor_can_login_and_access_account(registration_client):
    client, _ = registration_client

    registration = client.post(
        "/auth/register",
        json={
            "name": "New Investor",
            "email": "login@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert registration.status_code == 201

    login = client.post(
        "/auth/login",
        json={
            "email": "login@example.com",
            "password": "SecurePassword123!",
        },
    )

    assert login.status_code == 200
    assert login.json()["token_type"] == "bearer"

    token = login.json()["access_token"]

    account = client.get(
        "/auth/me",
        headers={"Authorization": f"Bearer {token}"},
    )

    assert account.status_code == 200
    assert account.json()["email"] == "login@example.com"
    assert account.json()["name"] == "New Investor"


