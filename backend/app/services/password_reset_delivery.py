"""Password-reset token delivery."""

import os
import smtplib
from email.message import EmailMessage
from urllib.parse import urlencode


def send_password_reset_email(email: str, token: str) -> None:
    """Deliver a password-reset link through configured SMTP."""
    smtp_host = os.environ["SMTP_HOST"]
    smtp_port = int(os.getenv("SMTP_PORT", "587"))
    smtp_username = os.environ["SMTP_USERNAME"]
    smtp_password = os.environ["SMTP_PASSWORD"]
    sender = os.environ["PASSWORD_RESET_FROM_EMAIL"]
    reset_url = os.environ["PASSWORD_RESET_URL"]

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
        smtp.starttls()
        smtp.login(smtp_username, smtp_password)
        smtp.send_message(message)
