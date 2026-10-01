"""Fetch FRED macroeconomic series and store them in macro_observations.

Run once, or again at any time (re-runs are idempotent):
    docker compose exec backend python -m app.services.macro_data
"""

import logging
import os
from datetime import date, datetime, timezone
from typing import Any

import pandas as pd
import requests
from pandas.tseries.holiday import USFederalHolidayCalendar
from pandas.tseries.offsets import CustomBusinessDay
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.database import get_session
from app.models.macro import MacroObservation
from app.services.data_source import (
    DataSourceUnavailableError,
    get_status,
    record_failure,
    record_success,
    redact,
    retry_call,
)

# urllib3 logs full request URLs at DEBUG level, and FRED only accepts the API
# key as a URL parameter. Keep urllib3 at INFO or above even when the app logs
# at DEBUG, unless it has deliberately been set higher.
_urllib3_logger = logging.getLogger("urllib3")
if _urllib3_logger.level < logging.INFO:
    _urllib3_logger.setLevel(logging.INFO)

logger = logging.getLogger(__name__)

SOURCE = "fred"

FRED_OBSERVATIONS_URL = "https://api.stlouisfed.org/fred/series/observations"
OBSERVATION_START = "2010-01-01"
FED_BUSINESS_DAY = CustomBusinessDay(calendar=USFederalHolidayCalendar())

# How each series' available_date is determined:
# - FIRST_RELEASE: FRED/ALFRED initial release; available_date = realtime_start.
# - NEXT_FED_BUSINESS_DAY: daily series with too many vintages for ALFRED
#   (FRED allows 2,000 per request); published the next Fed business day.
FIRST_RELEASE = "first_release"
NEXT_FED_BUSINESS_DAY = "next_fed_business_day"

SERIES = {
    "CPIAUCNS": FIRST_RELEASE,  # CPI-U, not seasonally adjusted (inflation)
    "UNRATE": FIRST_RELEASE,  # unemployment rate
    "DFF": NEXT_FED_BUSINESS_DAY,  # effective federal funds rate (daily)
}

# Data is stale when the newest valid value became available more than this
# many days ago. Monthly releases are normally 4-5 weeks apart; DFF is
# published every Fed business day (at most 4 days apart over a holiday).
MAX_DATA_AGE_DAYS = {
    "CPIAUCNS": 45,
    "UNRATE": 45,
    "DFF": 5,
}


TRANSIENT_REQUEST_ERRORS = (
    requests.Timeout,
    requests.ConnectionError,
    requests.exceptions.ChunkedEncodingError,
)


class FredError(RuntimeError):
    """A FRED request failed. Messages never contain the API key.

    transient is True for failures worth retrying (timeouts, connection
    errors, HTTP 429 and 5xx) and False for ones that will not fix
    themselves (bad key, bad series).
    """

    def __init__(self, message: str, transient: bool = False):
        super().__init__(message)
        self.transient = transient


def fetch_series(
    series_id: str,
    api_key: str,
    http: requests.Session | None = None,
) -> list[dict[str, Any]]:
    """Fetch one FRED series and return rows ready to store."""
    method = SERIES[series_id]
    params: dict[str, Any] = {
        "series_id": series_id,
        "api_key": api_key,
        "file_type": "json",
        "observation_start": OBSERVATION_START,
    }
    if method == FIRST_RELEASE:
        params.update(
            {
                "realtime_start": "1776-07-04",
                "realtime_end": "9999-12-31",
                "output_type": 4,  # initial release only
            }
        )

    client = http or requests
    try:
        response = client.get(FRED_OBSERVATIONS_URL, params=params, timeout=60)
    except requests.RequestException as exc:
        # requests' messages include the full URL, and the URL contains the
        # API key, so the original exception is deliberately not chained.
        raise FredError(
            f"FRED request for {series_id} failed: {type(exc).__name__}",
            # ChunkedEncodingError: the connection dropped mid-response.
            transient=isinstance(exc, TRANSIENT_REQUEST_ERRORS),
        ) from None

    if response.status_code != 200:
        try:
            detail = response.json().get("error_message", "")
        except ValueError:
            detail = ""
        detail = redact(str(detail), api_key)
        raise FredError(
            f"FRED request for {series_id} failed "
            f"with HTTP {response.status_code}: {detail}",
            transient=response.status_code == 429 or response.status_code >= 500,
        )

    try:
        observations = response.json()["observations"]
        rows = [_to_row(series_id, method, obs) for obs in observations]
    except (ValueError, KeyError, TypeError) as exc:
        # A 200 with an unexpected body (HTML error page, changed schema, bad
        # value). Not retried: the same request returns the same body.
        raise FredError(
            f"FRED returned an unexpected response for {series_id}: "
            f"{type(exc).__name__}",
            transient=False,
        ) from None

    if not rows:
        # Every series has data since 2010, so an empty list means the
        # response is wrong, not that there is nothing to report.
        raise FredError(
            f"FRED returned no observations for {series_id}", transient=False
        )
    return rows


def _to_row(series_id: str, method: str, obs: dict[str, str]) -> dict[str, Any]:
    observation_date = date.fromisoformat(obs["date"])
    if method == FIRST_RELEASE:
        available_date = date.fromisoformat(obs["realtime_start"])
    else:
        available_date = (pd.Timestamp(observation_date) + FED_BUSINESS_DAY).date()

    raw_value = obs["value"]
    return {
        "series_id": series_id,
        "observation_date": observation_date,
        "available_date": available_date,
        "value": None if raw_value == "." else float(raw_value),
        "raw_value": raw_value,
    }


def store_macro_observations(
    session: Session,
    series_id: str,
    rows: list[dict[str, Any]],
) -> int:
    """Insert new rows and update changed ones. Returns the number written."""
    existing = {
        (obs.observation_date, obs.available_date): obs
        for obs in session.scalars(
            select(MacroObservation).where(MacroObservation.series_id == series_id)
        )
    }
    now = datetime.now(timezone.utc)
    written = 0

    try:
        for row in rows:
            key = (row["observation_date"], row["available_date"])
            obs = existing.get(key)
            if obs is None:
                obs = MacroObservation(**row, fetched_at=now)
                session.add(obs)
                existing[key] = obs
                written += 1
            elif (obs.value, obs.raw_value) != (row["value"], row["raw_value"]):
                obs.value = row["value"]
                obs.raw_value = row["raw_value"]
                obs.fetched_at = now
                written += 1

        session.commit()
        return written

    except Exception:
        session.rollback()
        raise


def _is_transient(exc: Exception) -> bool:
    return isinstance(exc, FredError) and exc.transient


def _has_stored_data(session: Session, series_id: str) -> bool:
    return (
        session.scalar(
            select(MacroObservation.id)
            .where(
                MacroObservation.series_id == series_id,
                MacroObservation.value.is_not(None),
            )
            .limit(1)
        )
        is not None
    )


def ingest_macro_data(sleep=None) -> dict[str, int | None]:
    """Fetch and store every configured series.

    Returns rows written per series, or None for a series whose fetch failed.
    A failed series keeps its stored data, which the pipeline falls back on.
    Raises DataSourceUnavailableError only when a failed series has no
    stored data at all.
    """
    api_key = os.getenv("FRED_API_KEY")
    if not api_key:
        raise RuntimeError("FRED_API_KEY is not set.")

    retry_options = {} if sleep is None else {"sleep": sleep}
    results: dict[str, int | None] = {}
    unavailable = []

    with requests.Session() as http:
        for series_id in SERIES:
            try:
                rows = retry_call(
                    lambda: fetch_series(series_id, api_key, http),
                    is_transient=_is_transient,
                    label=f"FRED {series_id}",
                    **retry_options,
                )
            except FredError as exc:
                error = redact(str(exc), api_key)
                logger.error("FRED %s unavailable: %s", series_id, error)
                with get_session() as session:
                    record_failure(session, SOURCE, series_id, error)
                    if not _has_stored_data(session, series_id):
                        unavailable.append(series_id)
                results[series_id] = None
                continue

            # TODO(US-46): wrap database errors here in Allen's
            # DatabaseUnavailableError once US-46 merges.
            with get_session() as session:
                results[series_id] = store_macro_observations(session, series_id, rows)
                record_success(session, SOURCE, series_id)

    if unavailable:
        raise DataSourceUnavailableError(
            "FRED fetch failed with no stored data to fall back on: "
            + ", ".join(unavailable)
        )
    return results


# TODO(US-10-API): the backend owner exposes this through the API as the
# as_of / is_stale fields agreed in docs/api-contract.md.
def macro_freshness(session: Session, today: date | None = None) -> dict[str, dict]:
    """Report how current each series is, and whether its last fetch failed.

    is_stale reflects data age against the series' release cadence.
    last_fetch_failed reflects the most recent fetch, so a failed download is
    distinguishable from a normal gap between releases.
    """
    today = today or date.today()
    report = {}
    for series_id, max_age in MAX_DATA_AGE_DAYS.items():
        latest = session.scalar(
            select(func.max(MacroObservation.available_date)).where(
                MacroObservation.series_id == series_id,
                MacroObservation.value.is_not(None),
            )
        )
        status = get_status(session, SOURCE, series_id)
        age_days = (today - latest).days if latest else None
        report[series_id] = {
            "as_of": latest,
            "age_days": age_days,
            "is_stale": age_days is None or age_days > max_age,
            "last_success_at": status.last_success_at if status else None,
            "last_fetch_failed": bool(status and status.consecutive_failures),
            "consecutive_failures": status.consecutive_failures if status else 0,
        }
    return report


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    for series_id, count in ingest_macro_data().items():
        if count is None:
            print(f"{series_id}: fetch failed, using stored data")
        else:
            print(f"{series_id}: {count} rows written")
