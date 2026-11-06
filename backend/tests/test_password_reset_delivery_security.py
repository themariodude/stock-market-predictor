"""SCRUM-133: Verify SMTP transport security."""

import ssl
from unittest.mock import MagicMock, patch

import pytest

from app.services.password_reset_delivery import send_password_reset_email


def test_smtp_uses_verified_tls_before_authentication(monkeypatch):
    """Verify certificate checking and TLS-before-login ordering."""
    monkeypatch.setenv("SMTP_HOST", "smtp.example.invalid")
    monkeypatch.setenv("SMTP_PORT", "587")
    monkeypatch.setenv("SMTP_USERNAME", "test-user")
    monkeypatch.setenv("SMTP_PASSWORD", "test-only-password")
    monkeypatch.setenv("PASSWORD_RESET_FROM_EMAIL", "reset@example.invalid")
    monkeypatch.setenv(
        "PASSWORD_RESET_URL",
        "https://app.example.invalid/reset-password",
    )

    smtp = MagicMock()
    smtp.__enter__.return_value = smtp

    with patch(
        "app.services.password_reset_delivery.smtplib.SMTP",
        return_value=smtp,
    ):
        send_password_reset_email(
            "user@example.invalid",
            "synthetic-reset-token",
        )

    smtp.starttls.assert_called_once()

    context = smtp.starttls.call_args.kwargs["context"]

    assert isinstance(context, ssl.SSLContext)
    assert context.verify_mode == ssl.CERT_REQUIRED
    assert context.check_hostname is True

    calls = [call[0] for call in smtp.mock_calls]

    assert calls.index("starttls") < calls.index("login")
    assert calls.index("login") < calls.index("send_message")


@pytest.mark.parametrize("environment", ["staging", "production"])
@pytest.mark.parametrize(
    "reset_url",
    [
        "http://app.example.invalid/reset-password",
        "ftp://app.example.invalid/reset-password",
        "https://user:password@app.example.invalid/reset-password",
    ],
)
def test_deployed_environments_reject_insecure_reset_urls(
    monkeypatch, environment, reset_url
):
    """Reject insecure reset links before contacting SMTP."""
    monkeypatch.setenv("APP_ENV", environment)
    monkeypatch.setenv("PASSWORD_RESET_URL", reset_url)
    monkeypatch.setenv("SMTP_HOST", "smtp.example.invalid")
    monkeypatch.setenv("SMTP_USERNAME", "test-user")
    monkeypatch.setenv("SMTP_PASSWORD", "test-only-password")
    monkeypatch.setenv("PASSWORD_RESET_FROM_EMAIL", "reset@example.invalid")

    with patch("app.services.password_reset_delivery.smtplib.SMTP") as smtp:
        with pytest.raises(ValueError, match="HTTPS URL"):
            send_password_reset_email(
                "user@example.invalid",
                "synthetic-reset-token",
            )

    smtp.assert_not_called()


def test_development_allows_local_http_reset_url(monkeypatch):
    """Preserve HTTP support for local development."""
    monkeypatch.setenv("APP_ENV", "development")
    monkeypatch.setenv(
        "PASSWORD_RESET_URL",
        "http://localhost:5173/reset-password",
    )
    monkeypatch.setenv("SMTP_HOST", "smtp.example.invalid")
    monkeypatch.setenv("SMTP_USERNAME", "test-user")
    monkeypatch.setenv("SMTP_PASSWORD", "test-only-password")
    monkeypatch.setenv("PASSWORD_RESET_FROM_EMAIL", "reset@example.invalid")

    smtp = MagicMock()
    smtp.__enter__.return_value = smtp

    with patch(
        "app.services.password_reset_delivery.smtplib.SMTP",
        return_value=smtp,
    ):
        send_password_reset_email(
            "user@example.invalid",
            "synthetic-reset-token",
        )

    smtp.send_message.assert_called_once()
