import base64
import hashlib
import hmac
import json
import os
import secrets
import time
from dataclasses import dataclass
from typing import Any

TOKEN_TTL_SECONDS = 60 * 60
PASSWORD_HASH_ALGORITHM = "pbkdf2_sha256"
PASSWORD_HASH_ITERATIONS = 390_000
DEMO_PASSWORD = "SecurePass123!"


class AuthenticationError(Exception):
    """Raised when credentials or bearer tokens cannot be authenticated."""


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
    return os.getenv("AUTH_SECRET_KEY", "development-auth-secret").encode("utf-8")


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
        password_hash=os.getenv(
            "DEMO_INVESTOR_PASSWORD_HASH",
            _default_password_hash(),
        ),
        saved_stocks=("LMT", "RTX", "NOC"),
        investment_focus="Defense-sector equities",
    )


def authenticate_investor(email: str, password: str) -> RegisteredInvestor:
    """Authenticate a registered investor with email and password."""
    investor = get_registered_investor(email)
    if investor is None or not verify_password(password, investor.password_hash):
        raise AuthenticationError("Invalid email or password.")

    return investor


def create_access_token(email: str, issued_at: int | None = None) -> str:
    """Create a signed bearer token for a registered investor."""
    now = issued_at or int(time.time())
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
    except (ValueError, json.JSONDecodeError):
        raise AuthenticationError("Invalid access token.") from None

    now = current_time or int(time.time())
    if int(payload.get("exp", 0)) < now:
        raise AuthenticationError("Access token has expired.")

    investor = get_registered_investor(str(payload.get("sub", "")))
    if investor is None:
        raise AuthenticationError("Invalid access token.")

    return investor
