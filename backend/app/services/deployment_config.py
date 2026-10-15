"""Validate deployed configuration without including secret values in errors."""

import base64
import os

DEPLOYED_ENVIRONMENTS = {"staging", "production"}


def deployment_environment() -> str:
    environment = os.getenv("APP_ENV", "development").strip().lower()
    if environment not in {"development", "test", *DEPLOYED_ENVIRONMENTS}:
        raise RuntimeError("APP_ENV must be development, test, staging, or production.")
    return environment


def validate_deployment_config() -> None:
    if deployment_environment() not in DEPLOYED_ENVIRONMENTS:
        return

    required = ("AUTH_SECRET_KEY", "DEMO_INVESTOR_EMAIL", "DEMO_INVESTOR_PASSWORD_HASH")
    missing = [name for name in required if not os.getenv(name, "").strip()]
    if missing:
        raise RuntimeError("Missing deployment settings: " + ", ".join(missing))

    secret = os.environ["AUTH_SECRET_KEY"]
    if len(secret) < 32 or secret.lower().startswith(("replace-", "change-me")):
        raise RuntimeError(
            "AUTH_SECRET_KEY must be a unique secret of at least 32 characters."
        )

    # A deployment must use a password hash, never the public demo password.
    if os.getenv("DEMO_INVESTOR_PASSWORD"):
        raise RuntimeError("Use DEMO_INVESTOR_PASSWORD_HASH for deployed accounts.")

    try:
        algorithm, iterations, salt, digest = os.environ[
            "DEMO_INVESTOR_PASSWORD_HASH"
        ].split("$")
        decoded_salt = base64.b64decode(
            salt + "=" * (-len(salt) % 4), altchars=b"-_", validate=True
        )
        decoded_digest = base64.b64decode(
            digest + "=" * (-len(digest) % 4), altchars=b"-_", validate=True
        )
        valid_hash = (
            algorithm == "pbkdf2_sha256"
            and int(iterations) >= 390_000
            and len(decoded_salt) >= 16
            and len(decoded_digest) == 32
        )
    except (ValueError, TypeError):
        valid_hash = False
    if not valid_hash:
        raise RuntimeError(
            "DEMO_INVESTOR_PASSWORD_HASH must be a valid PBKDF2-SHA256 hash."
        )
