import base64
import binascii
import hashlib
import hmac
import json
import os
import secrets
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from typing import Any

from sqlalchemy import select, update
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.models.password_reset import PasswordResetToken
from app.models.user import User
from app.services.deployment_config import validate_deployment_config

TOKEN_TTL_SECONDS = 60 * 60
PASSWORD_RESET_TTL_MINUTES = 30
PASSWORD_HASH_ALGORITHM = "pbkdf2_sha256"
PASSWORD_HASH_ITERATIONS = 390_000
DEMO_PASSWORD = "SecurePass123!"
# Development tokens expire on process restart when no key is configured.
_DEVELOPMENT_AUTH_SECRET = secrets.token_bytes(32)


class AuthenticationError(Exception):
    """Raised when credentials or bearer tokens cannot be authenticated."""


class DuplicateAccountError(Exception):
    """Raised when an investor email is already registered."""


class PasswordResetError(Exception):
    """Raised when a password reset token is invalid or expired."""


@dataclass(frozen=True)
class RegisteredInvestor:
    email: str
    name: str
    password_hash: str
    saved_stocks: tuple[str, ...]
    investment_focus: str


def _base64url_encode(value: bytes) -> str:
    return base64.urlsafe_b64encode(value).rstrip(b"=").decode("ascii")


def _base64url_decode(value: str) -> bytes:
    padding = "=" * (-len(value) % 4)
    return base64.urlsafe_b64decode(f"{value}{padding}")


def _auth_secret() -> bytes:
    validate_deployment_config()
    configured_secret = os.getenv("AUTH_SECRET_KEY")
    return (
        configured_secret.encode("utf-8")
        if configured_secret
        else _DEVELOPMENT_AUTH_SECRET
    )


def hash_password(password: str, salt: bytes | None = None) -> str:
    """Hash a password with PBKDF2-SHA256 and a per-password salt."""
    password_salt = salt or secrets.token_bytes(16)
    password_hash = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        password_salt,
        PASSWORD_HASH_ITERATIONS,
    )

    return "$".join(
        [
            PASSWORD_HASH_ALGORITHM,
            str(PASSWORD_HASH_ITERATIONS),
            _base64url_encode(password_salt),
            _base64url_encode(password_hash),
        ]
    )


def verify_password(password: str, encoded_hash: str) -> bool:
    """Verify a plaintext password against a stored PBKDF2 hash."""
    try:
        algorithm, iterations, salt, expected_hash = encoded_hash.split("$", 3)
        if algorithm != PASSWORD_HASH_ALGORITHM:
            return False

        actual_hash = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            _base64url_decode(salt),
            int(iterations),
        )
    except (TypeError, ValueError):
        return False

    return hmac.compare_digest(
        _base64url_encode(actual_hash),
        expected_hash,
    )


def _default_password_hash() -> str:
    return hash_password(
        os.getenv("DEMO_INVESTOR_PASSWORD", DEMO_PASSWORD),
        salt=b"stock-market-demo",
    )


def get_registered_investor(email: str) -> RegisteredInvestor | None:
    """Return the configured registered investor account, if the email matches."""
    validate_deployment_config()
    normalized_email = email.strip().lower()
    registered_email = os.getenv(
        "DEMO_INVESTOR_EMAIL",
        "investor@example.com",
    ).lower()

    if normalized_email != registered_email:
        return None

    return RegisteredInvestor(
        email=registered_email,
        name=os.getenv("DEMO_INVESTOR_NAME", "Registered Investor"),
        password_hash=os.getenv("DEMO_INVESTOR_PASSWORD_HASH")
        or _default_password_hash(),
        saved_stocks=("LMT", "RTX", "NOC"),
        investment_focus="Defense-sector equities",
    )


def register_investor(
    db: Session,
    name: str,
    email: str,
    password: str,
) -> User:
    """Create a new investor account in PostgreSQL."""
    normalized_email = email.strip().lower()

    # Prevent duplicate database accounts.
    existing_user = db.scalar(select(User).where(User.email == normalized_email))

    # Reserve the existing demo investor email.
    demo_email = (
        os.getenv(
            "DEMO_INVESTOR_EMAIL",
            "investor@example.com",
        )
        .strip()
        .lower()
    )

    if existing_user is not None or normalized_email == demo_email:
        raise DuplicateAccountError("An account with this email already exists.")

    # Store a hashed password rather than plaintext.
    user = User(
        name=name.strip(),
        email=normalized_email,
        password_hash=hash_password(password),
    )

    try:
        db.add(user)
        db.commit()
        db.refresh(user)
    except IntegrityError as exc:
        db.rollback()
        raise DuplicateAccountError(
            "An account with this email already exists."
        ) from exc

    return user


def get_database_investor(
    db: Session,
    email: str,
) -> RegisteredInvestor | None:
    """Retrieve a registered investor from PostgreSQL."""
    normalized_email = email.strip().lower()

    user = db.scalar(select(User).where(User.email == normalized_email))

    if user is None:
        return None

    return RegisteredInvestor(
        email=user.email,
        name=user.name,
        password_hash=user.password_hash,
        saved_stocks=(),
        investment_focus="",
    )


def authenticate_investor(
    email: str,
    password: str,
    db: Session | None = None,
) -> RegisteredInvestor:
    """Authenticate a demo or database-backed investor."""
    investor = get_registered_investor(email)

    if investor is None and db is not None:
        investor = get_database_investor(db, email)

    if investor is None or not verify_password(password, investor.password_hash):
        raise AuthenticationError("Invalid email or password.")

    return investor


def create_access_token(email: str, issued_at: int | None = None) -> str:
    """Create a signed bearer token for a registered investor."""
    now = issued_at if issued_at is not None else int(time.time())
    payload = {
        "sub": email.strip().lower(),
        "iat": now,
        "exp": now + TOKEN_TTL_SECONDS,
    }
    payload_bytes = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    encoded_payload = _base64url_encode(payload_bytes)
    signature = hmac.new(
        _auth_secret(),
        encoded_payload.encode("ascii"),
        hashlib.sha256,
    ).digest()

    return f"{encoded_payload}.{_base64url_encode(signature)}"


def verify_access_token(
    token: str,
    current_time: int | None = None,
    db: Session | None = None,
) -> RegisteredInvestor:
    """Validate a bearer token and return the associated registered investor."""
    try:
        encoded_payload, encoded_signature = token.split(".", 1)
        expected_signature = hmac.new(
            _auth_secret(),
            encoded_payload.encode("ascii"),
            hashlib.sha256,
        ).digest()

        if not hmac.compare_digest(
            _base64url_encode(expected_signature),
            encoded_signature,
        ):
            raise AuthenticationError("Invalid access token.")

        payload: dict[str, Any] = json.loads(_base64url_decode(encoded_payload))
        if not isinstance(payload, dict):
            raise AuthenticationError("Invalid access token.")

        email = payload.get("sub")
        issued_at = payload.get("iat")
        expires_at = payload.get("exp")

        if (
            not isinstance(email, str)
            or not email.strip()
            or type(issued_at) is not int
            or type(expires_at) is not int
            or expires_at <= issued_at
        ):
            raise AuthenticationError("Invalid access token.")

    except (ValueError, TypeError, UnicodeDecodeError, OverflowError, binascii.Error):
        raise AuthenticationError("Invalid access token.") from None

    now = current_time if current_time is not None else int(time.time())
    if expires_at <= now:
        raise AuthenticationError("Access token has expired.")

    investor_email = str(payload.get("sub", ""))
    investor = get_registered_investor(investor_email)

    if investor is None and db is not None:
        investor = get_database_investor(db, investor_email)

    if investor is None:
        raise AuthenticationError("Invalid access token.")

    return investor


def create_password_reset_token(
    db: Session,
    email: str,
) -> str | None:
    """Generate a single-use reset token for a database user."""
    normalized_email = email.strip().lower()

    user = db.scalar(select(User).where(User.email == normalized_email))

    if user is None:
        return None

    now = datetime.now(timezone.utc)

    raw_token = secrets.token_urlsafe(32)
    token_hash = hashlib.sha256(raw_token.encode("utf-8")).hexdigest()

    # Invalidate previously issued reset tokens.
    db.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.user_id == user.id,
            PasswordResetToken.used_at.is_(None),
        )
        .values(used_at=now)
    )

    reset_record = PasswordResetToken(
        user_id=user.id,
        token_hash=token_hash,
        expires_at=now + timedelta(minutes=PASSWORD_RESET_TTL_MINUTES),
    )

    db.add(reset_record)
    db.commit()

    return raw_token


def confirm_password_reset(
    db: Session,
    token: str,
    new_password: str,
) -> None:
    """Validate a reset token and persist the new password."""
    now = datetime.now(timezone.utc)

    token_hash = hashlib.sha256(token.encode("utf-8")).hexdigest()

    # Consume the token atomically.
    claim = db.execute(
        update(PasswordResetToken)
        .where(
            PasswordResetToken.token_hash == token_hash,
            PasswordResetToken.used_at.is_(None),
            PasswordResetToken.expires_at > now,
        )
        .values(used_at=now)
    )

    if claim.rowcount != 1:
        db.rollback()
        raise PasswordResetError("Invalid or expired password reset token.")

    reset_record = db.scalar(
        select(PasswordResetToken).where(PasswordResetToken.token_hash == token_hash)
    )

    if reset_record is None:
        db.rollback()
        raise PasswordResetError("Invalid or expired password reset token.")

    user = db.get(User, reset_record.user_id)

    if user is None:
        db.rollback()
        raise PasswordResetError("Invalid or expired password reset token.")

    user.password_hash = hash_password(new_password)
    db.commit()
