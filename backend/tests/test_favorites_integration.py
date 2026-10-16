import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.pool import StaticPool

from app.api.favorites import get_db
from app.database import Base
from app.main import app
from app.models.favorite import Favorite
from app.services.auth import create_access_token


@pytest.fixture
def authenticated_client():
    """Create an authenticated client with an isolated test database."""

    # Temporary SQLite database; does not modify PostgreSQL.
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )

    Base.metadata.create_all(
        bind=engine,
        tables=[Favorite.__table__],
    )

    TestSession = sessionmaker(
        bind=engine,
        autoflush=False,
        expire_on_commit=False,
    )

    def override_get_db():
        db = TestSession()
        try:
            yield db
        finally:
            db.close()

    app.dependency_overrides[get_db] = override_get_db

    token = create_access_token("investor@example.com")

    try:
        with TestClient(app) as client:
            client.headers.update({"Authorization": f"Bearer {token}"})
            yield client
    finally:
        app.dependency_overrides.pop(get_db, None)
        Base.metadata.drop_all(
            bind=engine,
            tables=[Favorite.__table__],
        )
        engine.dispose()


def test_add_remove_and_persist_favorite(authenticated_client):
    """Verify favorites persist across requests and can be removed."""

    client = authenticated_client

    # Add LMT to favorites.
    response = client.post("/favorites/LMT")

    assert response.status_code in (200, 201)
    assert response.json()["ticker"] == "LMT"

    # Verify LMT appears in the saved favorites.
    response = client.get("/favorites")

    assert response.status_code == 200
    assert "LMT" in [stock["ticker"] for stock in response.json()]

    # Remove LMT.
    response = client.delete("/favorites/LMT")

    assert response.status_code == 204

    # Verify removal persists.
    response = client.get("/favorites")

    assert response.status_code == 200
    assert "LMT" not in [stock["ticker"] for stock in response.json()]


def test_favorites_require_authentication(authenticated_client):
    """Verify favorites cannot be accessed without a token."""

    client = authenticated_client

    # Temporarily remove the authentication header.
    client.headers.pop("Authorization", None)

    response = client.get("/favorites")

    assert response.status_code == 401


def test_duplicate_favorite_is_not_stored_twice(authenticated_client):
    """Verify duplicate favorites do not create duplicate records."""

    client = authenticated_client

    first = client.post("/favorites/LMT")
    second = client.post("/favorites/LMT")

    assert first.status_code in (200, 201)
    assert second.status_code in (200, 201, 409)

    response = client.get("/favorites")

    assert response.status_code == 200

    saved_lmt = [stock for stock in response.json() if stock["ticker"] == "LMT"]

    assert len(saved_lmt) == 1
