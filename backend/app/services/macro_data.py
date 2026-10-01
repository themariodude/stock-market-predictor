"""Fetch FRED macroeconomic series and store them in macro_observations.

Run once, or again at any time (re-runs are idempotent):
    docker compose exec backend python -m app.services.macro_data
"""

import os
from datetime import date, datetime, timezone
from typing import Any

import pandas as pd
import requests
from pandas.tseries.holiday import USFederalHolidayCalendar
from pandas.tseries.offsets import CustomBusinessDay
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.database import get_session
from app.models.macro import MacroObservation

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


class FredError(RuntimeError):
    """A FRED request failed. Messages never contain the API key."""


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
            f"FRED request for {series_id} failed: {type(exc).__name__}"
        ) from None

    if response.status_code != 200:
        try:
            detail = response.json().get("error_message", "")
        except ValueError:
            detail = ""
        raise FredError(
            f"FRED request for {series_id} failed "
            f"with HTTP {response.status_code}: {detail}"
        )

    return [_to_row(series_id, method, obs) for obs in response.json()["observations"]]


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


def ingest_macro_data() -> dict[str, int]:
    """Fetch and store every configured series."""
    api_key = os.getenv("FRED_API_KEY")
    if not api_key:
        raise RuntimeError("FRED_API_KEY is not set.")

    results = {}
    with requests.Session() as http:
        for series_id in SERIES:
            rows = fetch_series(series_id, api_key, http)
            with get_session() as session:
                results[series_id] = store_macro_observations(session, series_id, rows)
    return results


if __name__ == "__main__":
    for series_id, count in ingest_macro_data().items():
        print(f"{series_id}: {count} rows written")
