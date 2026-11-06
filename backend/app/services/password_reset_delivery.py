"""Password-reset token delivery."""

import os
import smtplib
import ssl
from email.message import EmailMessage
from urllib.parse import urlencode, urlsplit


def send_password_reset_email(email: str, token: str) -> None:
    """Deliver a password-reset link through configured SMTP."""
    smtp_host = os.environ["SMTP_HOST"]
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_username = os.environ["SMTP_USERNAME"]
    smtp_password = os.environ["SMTP_PASSWORD"]
    sender = os.environ["PASSWORD_RESET_FROM_EMAIL"]
    reset_url = os.environ["PASSWORD_RESET_URL"]

    # SCRUM-133: Require HTTPS for deployed password-reset links.
    if os.getenv("APP_ENV", "development").strip().lower() in {
        "staging",
        "production",
    }:
        parsed_url = urlsplit(reset_url)

        if (
            parsed_url.scheme != "https"
            or not parsed_url.hostname
            or parsed_url.username is not None
            or parsed_url.password is not None
        ):
            raise ValueError(
                "PASSWORD_RESET_URL must be a valid HTTPS URL "
                "in deployed environments."
            )

    separator = "&" if "?" in reset_url else "?"
    link = f"{reset_url}{separator}{urlencode({'token': token})}"

    message = EmailMessage()
    message["Subject"] = "Reset your Stock Market Predictor password"
    message["From"] = sender
    message["To"] = email
    message.set_content(
        "A password reset was requested for your account.\n\n"
        f"Reset your password using this link:\n{link}\n\n"
        "This link expires in 30 minutes. "
        "If you did not request a reset, ignore this email."
    )

    with smtplib.SMTP(smtp_host, smtp_port, timeout=10) as smtp:
        smtp.starttls(context=ssl.create_default_context())
        smtp.login(smtp_username, smtp_password)
        smtp.send_message(message)
