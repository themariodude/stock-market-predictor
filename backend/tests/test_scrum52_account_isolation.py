"""SCRUM-52: personal account data stays with the authenticated investor."""

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.api.auth import get_db as get_auth_db
from app.api.favorites import get_db as get_favorites_db
from app.database import Base
from app.main import app
from app.models.favorite import Favorite
from app.models.user import User


@pytest.fixture
def account_client():
    engine = create_engine(
        "sqlite://",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    Base.metadata.create_all(bind=engine, tables=[User.__table__, Favorite.__table__])

    def override_get_db():
        with Session(engine) as db:
            yield db

    prior_auth = app.dependency_overrides.get(get_auth_db)
    prior_favorites = app.dependency_overrides.get(get_favorites_db)
    app.dependency_overrides[get_auth_db] = override_get_db
    app.dependency_overrides[get_favorites_db] = override_get_db
    try:
        with TestClient(app) as client:
            yield client
    finally:
        for dependency, prior in (
            (get_auth_db, prior_auth),
            (get_favorites_db, prior_favorites),
        ):
            if prior is None:
                app.dependency_overrides.pop(dependency, None)
            else:
                app.dependency_overrides[dependency] = prior
        engine.dispose()


def test_registered_investors_cannot_read_or_remove_each_others_favorites(
    account_client,
):
    client = account_client
    tokens = {}
    for name, email in (
        ("Investor One", "one@example.invalid"),
        ("Investor Two", "two@example.invalid"),
    ):
        registration = client.post(
            "/auth/register",
            json={"name": name, "email": email, "password": "SecurePassword123!"},
        )
        assert registration.status_code == 201
        login = client.post(
            "/auth/login",
            json={"email": email, "password": "SecurePassword123!"},
        )
        assert login.status_code == 200
        tokens[email] = {"Authorization": f"Bearer {login.json()['access_token']}"}

    first = tokens["one@example.invalid"]
    second = tokens["two@example.invalid"]
    assert client.post("/favorites/LMT", headers=first).status_code == 201
    assert client.get("/favorites", headers=first).json() == [{"ticker": "LMT"}]
    assert client.get("/favorites", headers=second).json() == []
    assert client.delete("/favorites/LMT", headers=second).status_code == 404
    assert client.get("/favorites", headers=first).json() == [{"ticker": "LMT"}]

    assert client.post("/favorites/RTX", headers=second).status_code == 201
    assert client.get("/favorites", headers=second).json() == [{"ticker": "RTX"}]
    assert client.get("/favorites", headers=first).json() == [{"ticker": "LMT"}]
    assert client.get("/favorites").status_code == 401
