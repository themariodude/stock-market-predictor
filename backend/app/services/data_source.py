"""Shared failure handling for external data sources (US-10).

Retries transient failures with exponential backoff and records the outcome
of every fetch in data_source_status.
"""

import logging
import time
from collections.abc import Callable
from datetime import datetime, timezone
from typing import TypeVar

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.source_status import DataSourceStatus

logger = logging.getLogger(__name__)

T = TypeVar("T")

MAX_ERROR_LENGTH = 500


# TODO(US-46): subclass ApplicationServiceError from app.services.errors once
# Allen's US-46 branch merges. Kept out of errors.py to avoid a merge conflict.
class DataSourceUnavailableError(Exception):
    """A source failed and there is no stored data to fall back on."""


def redact(text: str, *secrets: str | None) -> str:
    """Remove secrets (such as API keys) from text before logging or storing."""
    for secret in secrets:
        if secret:
            text = text.replace(secret, "[REDACTED]")
    return text


def retry_call(
    fn: Callable[[], T],
    *,
    is_transient: Callable[[Exception], bool],
    label: str,
    attempts: int = 3,
    base_delay: float = 2.0,
    sleep: Callable[[float], None] = time.sleep,
) -> T:
    """Call fn, retrying transient failures with exponential backoff.

    Permanent failures, and the last transient failure, are re-raised.
    Waits base_delay, 2 * base_delay, ... between attempts.
    Raises ValueError if attempts is less than 1.
    """
    if attempts < 1:
        raise ValueError("attempts must be at least 1")
    for attempt in range(1, attempts + 1):
        try:
            return fn()
        except Exception as exc:
            if not is_transient(exc) or attempt == attempts:
                raise
            delay = base_delay * 2 ** (attempt - 1)
            # Log only the exception type: this helper is shared, and an
            # exception's text can contain URLs or secrets.
            logger.warning(
                "%s failed (attempt %d/%d): %s; retrying in %.0fs",
                label,
                attempt,
                attempts,
                type(exc).__name__,
                delay,
            )
            sleep(delay)
    raise AssertionError("unreachable")


def _get_or_create(session: Session, source: str, key: str) -> DataSourceStatus:
    status = session.scalar(
        select(DataSourceStatus).where(
            DataSourceStatus.source == source,
            DataSourceStatus.source_key == key,
        )
    )
    if status is None:
        status = DataSourceStatus(source=source, source_key=key, consecutive_failures=0)
        session.add(status)
    return status


def record_success(session: Session, source: str, key: str) -> None:
    """Record a successful fetch.

    Commits the session: call it only after the data transaction has
    committed, so no unrelated pending changes are committed with it.
    """
    now = datetime.now(timezone.utc)
    status = _get_or_create(session, source, key)
    status.last_attempt_at = now
    status.last_success_at = now
    status.last_error = None
    status.consecutive_failures = 0
    session.commit()


def record_failure(session: Session, source: str, key: str, error: str) -> None:
    """Record a failed fetch. error must already be redacted.

    Commits the session: call it only when no other changes are pending.
    """
    status = _get_or_create(session, source, key)
    status.last_attempt_at = datetime.now(timezone.utc)
    status.last_error = error[:MAX_ERROR_LENGTH]
    status.consecutive_failures = (status.consecutive_failures or 0) + 1
    session.commit()


def get_status(session: Session, source: str, key: str) -> DataSourceStatus | None:
    return session.scalar(
        select(DataSourceStatus).where(
            DataSourceStatus.source == source,
            DataSourceStatus.source_key == key,
        )
    )
