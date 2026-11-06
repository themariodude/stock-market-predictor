"""SCRUM-133: Verify SMTP transport security."""

import ssl
from unittest.mock import MagicMock, patch

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
