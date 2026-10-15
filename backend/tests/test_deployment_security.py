"""US-60: fail closed in deployed environments and keep secrets out of logs."""

import logging
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from app import main
from app.services import auth
from app.services.deployment_config import validate_deployment_config


@pytest.fixture
def deployed_env(monkeypatch):
    monkeypatch.setenv("APP_ENV", "staging")
    monkeypatch.setenv("AUTH_SECRET_KEY", "s" * 48)
    monkeypatch.setenv("DEMO_INVESTOR_EMAIL", "configured@example.invalid")
    monkeypatch.setenv(
        "DEMO_INVESTOR_PASSWORD_HASH", auth.hash_password("test-only-password")
    )
    monkeypatch.delenv("DEMO_INVESTOR_PASSWORD", raising=False)


@pytest.mark.parametrize("environment", ["staging", "production"])
def test_deployed_app_accepts_explicit_configuration(
    monkeypatch, deployed_env, environment
):
    monkeypatch.setenv("APP_ENV", environment)
    with TestClient(main.app) as client:
        assert client.get("/health").status_code == 200
    assert (
        auth.authenticate_investor(
            "configured@example.invalid", "test-only-password"
        ).email
        == "configured@example.invalid"
    )
    with pytest.raises(auth.AuthenticationError):
        auth.authenticate_investor("configured@example.invalid", auth.DEMO_PASSWORD)


@pytest.mark.parametrize(
    "setting", ["AUTH_SECRET_KEY", "DEMO_INVESTOR_EMAIL", "DEMO_INVESTOR_PASSWORD_HASH"]
)
def test_deployed_startup_rejects_missing_secrets(monkeypatch, deployed_env, setting):
    monkeypatch.delenv(setting)
    with pytest.raises(RuntimeError, match=setting) as error:
        with TestClient(main.app):
            pass
    assert "s" * 48 not in str(error.value)


@pytest.mark.parametrize("secret", ["short", "replace-with-a-unique-random-secret"])
def test_rejects_weak_or_placeholder_signing_key(monkeypatch, deployed_env, secret):
    monkeypatch.setenv("AUTH_SECRET_KEY", secret)
    with pytest.raises(RuntimeError, match="AUTH_SECRET_KEY"):
        validate_deployment_config()


def test_rejects_unknown_environment(monkeypatch):
    monkeypatch.setenv("APP_ENV", "prodution")
    with pytest.raises(RuntimeError, match="APP_ENV"):
        validate_deployment_config()


def test_rejects_plaintext_deployed_password(monkeypatch, deployed_env):
    monkeypatch.setenv("DEMO_INVESTOR_PASSWORD", "private-password")
    with pytest.raises(RuntimeError) as error:
        validate_deployment_config()
    assert "private-password" not in str(error.value)


@pytest.mark.parametrize(
    "invalid_hash", ["private-malformed-hash", "pbkdf2_sha256$1$c2FsdA$eA"]
)
def test_rejects_invalid_hash_without_echoing_it(
    monkeypatch, deployed_env, invalid_hash
):
    monkeypatch.setenv("DEMO_INVESTOR_PASSWORD_HASH", invalid_hash)
    with pytest.raises(RuntimeError) as error:
        validate_deployment_config()
    assert invalid_hash not in str(error.value)


def test_database_failure_logs_no_connection_credentials(monkeypatch, caplog):
    engine = MagicMock()
    engine.connect.side_effect = RuntimeError(
        "postgresql://user:private-password@db/name"
    )
    monkeypatch.setattr(main, "_engine", engine)
    with caplog.at_level(logging.WARNING):
        assert main.health()["database"] == "error"
    assert "Database health check failed" in caplog.text
    assert "private-password" not in caplog.text
    assert "postgresql" not in caplog.text
