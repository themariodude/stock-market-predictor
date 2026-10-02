import traceback
from datetime import date
from unittest.mock import MagicMock

import pytest
import requests
from sqlalchemy import create_engine, func, select
from sqlalchemy.orm import Session

from app.models.macro import MacroObservation
from app.models.source_status import DataSourceStatus
from app.services import macro_data

FAKE_KEY = "a" * 32


def fred_response(status_code, payload):
    response = MagicMock(status_code=status_code)
    response.json.return_value = payload
    return response


def mock_http(status_code=200, payload=None):
    http = MagicMock()
    http.get.return_value = fred_response(status_code, payload or {})
    return http


@pytest.fixture
def db_session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    MacroObservation.__table__.create(engine)
    DataSourceStatus.__table__.create(engine)

    with Session(engine) as session:
        yield session


UNRATE_PAYLOAD = {
    "observations": [
        {"date": "2025-10-01", "realtime_start": "2025-12-16", "value": "."},
        {"date": "2025-11-01", "realtime_start": "2025-12-16", "value": "4.6"},
        {"date": "2026-08-01", "realtime_start": "2026-09-04", "value": "4.1"},
    ]
}


def test_monthly_series_request_first_release_data():
    http = mock_http(payload=UNRATE_PAYLOAD)

    macro_data.fetch_series("UNRATE", FAKE_KEY, http)

    params = http.get.call_args.kwargs["params"]
    assert params["output_type"] == 4
    assert params["realtime_start"] == "1776-07-04"
    assert params["realtime_end"] == "9999-12-31"


def test_first_release_rows_use_realtime_start_and_store_dot_as_null():
    rows = macro_data.fetch_series(
        "UNRATE", FAKE_KEY, mock_http(payload=UNRATE_PAYLOAD)
    )

    assert rows[0]["observation_date"] == date(2025, 10, 1)
    assert rows[0]["available_date"] == date(2025, 12, 16)
    assert rows[0]["value"] is None
    assert rows[0]["raw_value"] == "."
    assert rows[2]["available_date"] == date(2026, 9, 4)
    assert rows[2]["value"] == 4.1


# Real FRED publication dates for DFF around Labor Day 2026
# (probe: output_type=4, realtime_start=2026-08-01).
DFF_ACTUAL_RELEASES = [
    ("2026-09-01", "2026-09-02"),
    ("2026-09-02", "2026-09-03"),
    ("2026-09-03", "2026-09-04"),
    ("2026-09-04", "2026-09-08"),
    ("2026-09-05", "2026-09-08"),
    ("2026-09-06", "2026-09-08"),
    ("2026-09-07", "2026-09-08"),
    ("2026-09-08", "2026-09-09"),
]


def test_dff_available_date_matches_real_fred_release_dates():
    payload = {
        "observations": [
            {"date": obs, "realtime_start": "2026-09-29", "value": "3.63"}
            for obs, _ in DFF_ACTUAL_RELEASES
        ]
    }
    http = mock_http(payload=payload)

    rows = macro_data.fetch_series("DFF", FAKE_KEY, http)

    params = http.get.call_args.kwargs["params"]
    assert "output_type" not in params
    assert [row["available_date"].isoformat() for row in rows] == [
        released for _, released in DFF_ACTUAL_RELEASES
    ]


def test_store_is_idempotent(db_session):
    rows = macro_data.fetch_series(
        "UNRATE", FAKE_KEY, mock_http(payload=UNRATE_PAYLOAD)
    )

    assert macro_data.store_macro_observations(db_session, "UNRATE", rows) == 3
    assert macro_data.store_macro_observations(db_session, "UNRATE", rows) == 0
    count = db_session.scalar(select(func.count()).select_from(MacroObservation))
    assert count == 3


def test_store_updates_changed_values(db_session):
    rows = macro_data.fetch_series(
        "UNRATE", FAKE_KEY, mock_http(payload=UNRATE_PAYLOAD)
    )
    macro_data.store_macro_observations(db_session, "UNRATE", rows)

    rows[2] = {**rows[2], "value": 4.2, "raw_value": "4.2"}

    assert macro_data.store_macro_observations(db_session, "UNRATE", rows) == 1
    stored = db_session.scalar(
        select(MacroObservation.value).where(
            MacroObservation.observation_date == date(2026, 8, 1)
        )
    )
    assert stored == 4.2


def test_duplicate_rows_in_one_fetch_are_stored_once(db_session):
    rows = macro_data.fetch_series(
        "UNRATE", FAKE_KEY, mock_http(payload=UNRATE_PAYLOAD)
    )

    written = macro_data.store_macro_observations(db_session, "UNRATE", rows + rows[:1])

    assert written == 3


def test_network_error_never_exposes_api_key():
    http = MagicMock()
    http.get.side_effect = requests.ConnectionError(
        f"Max retries exceeded with url: /fred/series/observations?api_key={FAKE_KEY}"
    )

    with pytest.raises(macro_data.FredError) as excinfo:
        macro_data.fetch_series("UNRATE", FAKE_KEY, http)

    full_traceback = "".join(traceback.format_exception(excinfo.value))
    assert FAKE_KEY not in full_traceback


def test_http_error_shows_fred_message_without_api_key():
    payload = {"error_message": "The value for variable api_key is not registered."}
    http = mock_http(status_code=400, payload=payload)

    with pytest.raises(macro_data.FredError) as excinfo:
        macro_data.fetch_series("UNRATE", FAKE_KEY, http)

    assert "not registered" in str(excinfo.value)
    assert FAKE_KEY not in str(excinfo.value)


def test_missing_api_key_raises_clear_error(monkeypatch):
    monkeypatch.delenv("FRED_API_KEY", raising=False)

    with pytest.raises(RuntimeError, match="FRED_API_KEY is not set"):
        macro_data.ingest_macro_data()


def test_ingest_fetches_and_stores_every_series(monkeypatch, db_session):
    monkeypatch.setenv("FRED_API_KEY", FAKE_KEY)
    fetched, stored = [], []

    def fake_fetch(series_id, api_key, http=None):
        fetched.append(series_id)
        return []

    def fake_store(session, series_id, rows):
        stored.append(series_id)
        return 0

    monkeypatch.setattr(macro_data, "fetch_series", fake_fetch)
    monkeypatch.setattr(macro_data, "store_macro_observations", fake_store)
    monkeypatch.setattr(macro_data, "get_session", lambda: db_session)

    result = macro_data.ingest_macro_data()

    assert fetched == stored == ["CPIAUCNS", "UNRATE", "DFF"]
    assert result == {"CPIAUCNS": 0, "UNRATE": 0, "DFF": 0}
