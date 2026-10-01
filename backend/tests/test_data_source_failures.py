"""US-10: data-source failure handling for FRED ingestion."""

import logging
from datetime import date, timedelta
from unittest.mock import MagicMock

import pytest
import requests
from sqlalchemy import create_engine, func, select
from sqlalchemy.exc import IntegrityError, OperationalError
from sqlalchemy.orm import Session

from app.models.macro import MacroObservation
from app.models.source_status import DataSourceStatus
from app.services import macro_data
from app.services.data_source import (
    DataSourceUnavailableError,
    get_status,
    redact,
    retry_call,
)

FAKE_KEY = "b" * 32


@pytest.fixture
def db_session():
    engine = create_engine("sqlite+pysqlite:///:memory:")
    MacroObservation.__table__.create(engine)
    DataSourceStatus.__table__.create(engine)
    with Session(engine) as session:
        yield session


@pytest.fixture
def ingest_env(monkeypatch, db_session):
    monkeypatch.setenv("FRED_API_KEY", FAKE_KEY)
    monkeypatch.setattr(macro_data, "get_session", lambda: db_session)
    return db_session


def row(series_id, observation_date, available_date, value):
    return {
        "series_id": series_id,
        "observation_date": observation_date,
        "available_date": available_date,
        "value": value,
        "raw_value": "." if value is None else str(value),
    }


def http_response(status_code, payload=None):
    response = MagicMock(status_code=status_code)
    response.json.return_value = payload or {}
    return response


def fake_fetch_factory(failures):
    """failures maps series_id -> list of exceptions raised before success."""

    def fake_fetch(series_id, api_key, http=None):
        pending = failures.get(series_id, [])
        if pending:
            raise pending.pop(0)
        return [row(series_id, date(2026, 8, 1), date(2026, 9, 10), 1.0)]

    return fake_fetch


# --- retry_call ---------------------------------------------------------


def test_retry_succeeds_after_transient_failure():
    sleeps, calls = [], []

    def flaky():
        calls.append(1)
        if len(calls) == 1:
            raise TimeoutError
        return "ok"

    result = retry_call(
        flaky, is_transient=lambda e: True, label="t", sleep=sleeps.append
    )

    assert result == "ok"
    assert sleeps == [2.0]


def test_retry_does_not_retry_permanent_failure():
    calls = []

    def bad():
        calls.append(1)
        raise ValueError("bad key")

    with pytest.raises(ValueError):
        retry_call(bad, is_transient=lambda e: False, label="t", sleep=lambda s: None)

    assert len(calls) == 1


def test_retry_backs_off_exponentially_then_gives_up():
    sleeps, calls = [], []

    def always_down():
        calls.append(1)
        raise TimeoutError

    with pytest.raises(TimeoutError):
        retry_call(
            always_down, is_transient=lambda e: True, label="t", sleep=sleeps.append
        )

    assert len(calls) == 3
    assert sleeps == [2.0, 4.0]


def test_retry_requires_at_least_one_attempt():
    with pytest.raises(ValueError, match="at least 1"):
        retry_call(lambda: "ok", is_transient=lambda e: True, label="t", attempts=0)


def test_retry_log_shows_exception_type_not_message(caplog):
    calls = []

    def flaky():
        calls.append(1)
        if len(calls) == 1:
            raise RuntimeError(f"GET https://example.test/?api_key={FAKE_KEY}")
        return "ok"

    with caplog.at_level(logging.DEBUG):
        retry_call(flaky, is_transient=lambda e: True, label="t", sleep=lambda s: None)

    assert FAKE_KEY not in caplog.text
    assert "RuntimeError" in caplog.text


def test_urllib3_request_urls_are_not_logged_at_debug(caplog):
    # urllib3 logs request URLs (including the api_key query parameter) at
    # DEBUG; macro_data keeps urllib3 at INFO even when the app logs at DEBUG.
    with caplog.at_level(logging.DEBUG):
        assert not logging.getLogger("urllib3.connectionpool").isEnabledFor(
            logging.DEBUG
        )


def test_redact_removes_secret():
    assert redact(f"url?api_key={FAKE_KEY}", FAKE_KEY) == "url?api_key=[REDACTED]"


# --- transient vs permanent FRED errors ----------------------------------


@pytest.mark.parametrize(
    "side_effect, transient",
    [
        (requests.Timeout("slow"), True),
        (requests.ConnectionError("down"), True),
        (requests.exceptions.ChunkedEncodingError("connection dropped"), True),
        (http_response(500), True),
        (http_response(502), True),
        (http_response(503), True),
        (http_response(429), True),
        (http_response(400, {"error_message": "Bad series"}), False),
    ],
)
def test_fred_errors_are_classified(side_effect, transient):
    http = MagicMock()
    if isinstance(side_effect, Exception):
        http.get.side_effect = side_effect
    else:
        http.get.return_value = side_effect

    with pytest.raises(macro_data.FredError) as excinfo:
        macro_data.fetch_series("UNRATE", FAKE_KEY, http)

    assert excinfo.value.transient is transient


@pytest.mark.parametrize(
    "configure",
    [
        pytest.param(
            lambda r: setattr(
                r.json,
                "side_effect",
                requests.JSONDecodeError("Expecting value", "<html>", 0),
            ),
            id="html-instead-of-json",
        ),
        pytest.param(
            lambda r: setattr(r.json, "return_value", {"error": "x"}),
            id="missing-observations",
        ),
        pytest.param(
            lambda r: setattr(
                r.json,
                "return_value",
                {
                    "observations": [
                        {
                            "date": "2026-08-01",
                            "realtime_start": "2026-09-04",
                            "value": "abc",
                        }
                    ]
                },
            ),
            id="non-numeric-value",
        ),
        pytest.param(
            lambda r: setattr(r.json, "return_value", {"observations": []}),
            id="empty-observations",
        ),
    ],
)
def test_malformed_success_response_is_a_permanent_fred_error(configure):
    response = MagicMock(status_code=200)
    configure(response)
    http = MagicMock()
    http.get.return_value = response

    with pytest.raises(macro_data.FredError) as excinfo:
        macro_data.fetch_series("UNRATE", FAKE_KEY, http)

    assert excinfo.value.transient is False


def test_malformed_response_falls_back_instead_of_crashing(monkeypatch, ingest_env):
    session = ingest_env
    for series_id in macro_data.SERIES:
        macro_data.store_macro_observations(
            session, series_id, [row(series_id, date(2026, 7, 1), date(2026, 8, 7), 1)]
        )
    html_page = MagicMock(status_code=200)
    html_page.json.side_effect = requests.JSONDecodeError("Expecting value", "<", 0)
    http = MagicMock()
    http.get.return_value = html_page
    real_fetch = macro_data.fetch_series
    monkeypatch.setattr(
        macro_data,
        "fetch_series",
        lambda series_id, api_key, http_=None: real_fetch(series_id, api_key, http),
    )

    result = macro_data.ingest_macro_data(sleep=lambda s: None)

    assert result == {"CPIAUCNS": None, "UNRATE": None, "DFF": None}
    status = get_status(session, "fred", "UNRATE")
    assert status.consecutive_failures == 1
    assert "unexpected response" in status.last_error


def test_empty_response_is_recorded_as_failure_not_success(monkeypatch, ingest_env):
    session = ingest_env
    for series_id in macro_data.SERIES:
        macro_data.store_macro_observations(
            session, series_id, [row(series_id, date(2026, 7, 1), date(2026, 8, 7), 1)]
        )
    empty = MagicMock(status_code=200)
    empty.json.return_value = {"observations": []}
    http = MagicMock()
    http.get.return_value = empty
    real_fetch = macro_data.fetch_series
    monkeypatch.setattr(
        macro_data,
        "fetch_series",
        lambda series_id, api_key, http_=None: real_fetch(series_id, api_key, http),
    )

    result = macro_data.ingest_macro_data(sleep=lambda s: None)

    assert result == {"CPIAUCNS": None, "UNRATE": None, "DFF": None}
    status = get_status(session, "fred", "CPIAUCNS")
    assert status.last_success_at is None
    assert status.consecutive_failures == 1
    assert "no observations" in status.last_error


# --- ingestion fallback ------------------------------------------------


def test_failed_series_keeps_stored_data_and_records_failure(monkeypatch, ingest_env):
    session = ingest_env
    macro_data.store_macro_observations(
        session, "UNRATE", [row("UNRATE", date(2026, 7, 1), date(2026, 8, 7), 4.2)]
    )
    failures = {"UNRATE": [macro_data.FredError("HTTP 503", transient=True)] * 3}
    monkeypatch.setattr(macro_data, "fetch_series", fake_fetch_factory(failures))

    result = macro_data.ingest_macro_data(sleep=lambda s: None)

    assert result == {"CPIAUCNS": 1, "UNRATE": None, "DFF": 1}
    stored = session.scalars(
        select(MacroObservation).where(MacroObservation.series_id == "UNRATE")
    ).all()
    assert [obs.value for obs in stored] == [4.2]
    status = get_status(session, "fred", "UNRATE")
    assert status.consecutive_failures == 1
    assert status.last_success_at is None
    assert "503" in status.last_error


def test_failed_series_without_stored_data_raises_after_other_series(
    monkeypatch, ingest_env
):
    session = ingest_env
    # CPIAUCNS is fetched first, so this proves ingestion continues past it.
    failures = {"CPIAUCNS": [macro_data.FredError("HTTP 400", transient=False)]}
    monkeypatch.setattr(macro_data, "fetch_series", fake_fetch_factory(failures))

    with pytest.raises(DataSourceUnavailableError, match="CPIAUCNS"):
        macro_data.ingest_macro_data(sleep=lambda s: None)

    assert get_status(session, "fred", "CPIAUCNS").consecutive_failures == 1
    for series_id in ("UNRATE", "DFF"):
        assert get_status(session, "fred", series_id).last_success_at is not None
        stored = session.scalar(
            select(func.count(MacroObservation.id)).where(
                MacroObservation.series_id == series_id
            )
        )
        assert stored == 1


def test_stored_null_values_do_not_count_as_fallback_data(monkeypatch, ingest_env):
    session = ingest_env
    macro_data.store_macro_observations(
        session, "DFF", [row("DFF", date(2026, 9, 1), date(2026, 9, 2), None)]
    )
    failures = {"DFF": [macro_data.FredError("HTTP 400", transient=False)]}
    monkeypatch.setattr(macro_data, "fetch_series", fake_fetch_factory(failures))

    with pytest.raises(DataSourceUnavailableError, match="DFF"):
        macro_data.ingest_macro_data(sleep=lambda s: None)


def test_older_value_counts_as_fallback_when_newest_is_null(monkeypatch, ingest_env):
    session = ingest_env
    macro_data.store_macro_observations(
        session,
        "DFF",
        [
            row("DFF", date(2026, 8, 31), date(2026, 9, 1), 4.33),
            row("DFF", date(2026, 9, 1), date(2026, 9, 2), None),
        ],
    )
    failures = {"DFF": [macro_data.FredError("HTTP 400", transient=False)]}
    monkeypatch.setattr(macro_data, "fetch_series", fake_fetch_factory(failures))

    result = macro_data.ingest_macro_data(sleep=lambda s: None)

    assert result["DFF"] is None


def test_database_errors_propagate_instead_of_counting_as_source_failure(
    monkeypatch, ingest_env
):
    session = ingest_env
    monkeypatch.setattr(macro_data, "fetch_series", fake_fetch_factory({}))

    def broken_store(session, series_id, rows):
        raise OperationalError("INSERT", {}, Exception("database is down"))

    monkeypatch.setattr(macro_data, "store_macro_observations", broken_store)

    with pytest.raises(OperationalError):
        macro_data.ingest_macro_data(sleep=lambda s: None)

    # Not recorded as a FRED failure: the source worked, the database did not.
    assert get_status(session, "fred", "CPIAUCNS") is None


def test_success_after_retry_resets_failure_count(monkeypatch, ingest_env):
    session = ingest_env
    down = {"CPIAUCNS": [macro_data.FredError("HTTP 400", transient=False)]}
    macro_data.store_macro_observations(
        session, "CPIAUCNS", [row("CPIAUCNS", date(2026, 7, 1), date(2026, 8, 12), 1.0)]
    )
    monkeypatch.setattr(macro_data, "fetch_series", fake_fetch_factory(down))
    macro_data.ingest_macro_data(sleep=lambda s: None)
    assert get_status(session, "fred", "CPIAUCNS").consecutive_failures == 1

    flaky = {"CPIAUCNS": [macro_data.FredError("Timeout", transient=True)]}
    monkeypatch.setattr(macro_data, "fetch_series", fake_fetch_factory(flaky))
    result = macro_data.ingest_macro_data(sleep=lambda s: None)

    assert result["CPIAUCNS"] == 1
    status = get_status(session, "fred", "CPIAUCNS")
    assert status.consecutive_failures == 0
    assert status.last_error is None
    assert status.last_success_at is not None


def test_failed_store_writes_no_partial_data(db_session):
    rows = [
        row("UNRATE", date(2026, 7, 1), date(2026, 8, 7), 4.2),
        # available before observed: violates the table's check constraint
        row("UNRATE", date(2026, 8, 1), date(2026, 7, 1), 4.3),
    ]

    with pytest.raises(IntegrityError):
        macro_data.store_macro_observations(db_session, "UNRATE", rows)

    assert db_session.scalar(select(func.count(MacroObservation.id))) == 0


def test_fred_ingestion_never_logs_or_stores_api_key(monkeypatch, ingest_env, caplog):
    # Scope: the FRED ingestion path. record_failure() expects its caller to
    # pass an already-redacted message.
    session = ingest_env
    for series_id in macro_data.SERIES:
        macro_data.store_macro_observations(
            session, series_id, [row(series_id, date(2026, 7, 1), date(2026, 8, 7), 1)]
        )
    echoing = MagicMock()
    echoing.get.return_value = http_response(
        500, {"error_message": f"Internal error for api_key={FAKE_KEY}"}
    )
    real_fetch = macro_data.fetch_series
    monkeypatch.setattr(
        macro_data,
        "fetch_series",
        lambda series_id, api_key, http=None: real_fetch(series_id, api_key, echoing),
    )

    with caplog.at_level(logging.DEBUG):
        macro_data.ingest_macro_data(sleep=lambda s: None)

    assert FAKE_KEY not in caplog.text
    for status in session.scalars(select(DataSourceStatus)):
        assert FAKE_KEY not in status.last_error
        assert "[REDACTED]" in status.last_error


# --- freshness -----------------------------------------------------------


def test_freshness_uses_each_series_cadence(db_session):
    today = date(2026, 10, 1)
    for series_id, available in [
        ("CPIAUCNS", date(2026, 9, 11)),  # 20 days: normal for monthly
        ("UNRATE", date(2026, 8, 7)),  # 55 days: a release was missed
        ("DFF", date(2026, 9, 24)),  # 7 days: stale for daily
    ]:
        macro_data.store_macro_observations(
            db_session, series_id, [row(series_id, date(2026, 8, 1), available, 1.0)]
        )

    report = macro_data.macro_freshness(db_session, today=today)

    assert report["CPIAUCNS"]["is_stale"] is False
    assert report["UNRATE"]["is_stale"] is True
    assert report["DFF"]["is_stale"] is True
    assert report["CPIAUCNS"]["as_of"] == date(2026, 9, 11)
    assert report["DFF"]["age_days"] == 7


def test_freshness_ignores_missing_values(db_session):
    macro_data.store_macro_observations(
        db_session,
        "UNRATE",
        [
            row("UNRATE", date(2026, 7, 1), date(2026, 8, 7), 4.2),
            row("UNRATE", date(2026, 8, 1), date(2026, 9, 4), None),
        ],
    )

    report = macro_data.macro_freshness(db_session, today=date(2026, 9, 10))

    assert report["UNRATE"]["as_of"] == date(2026, 8, 7)


def test_failed_fetch_is_distinct_from_normal_release_gap(monkeypatch, ingest_env):
    session = ingest_env
    for series_id in macro_data.SERIES:
        macro_data.store_macro_observations(
            session,
            series_id,
            [row(series_id, date(2026, 8, 1), date(2026, 9, 11), 1.0)],
        )
    failures = {"CPIAUCNS": [macro_data.FredError("HTTP 400", transient=False)]}
    monkeypatch.setattr(macro_data, "fetch_series", fake_fetch_factory(failures))
    macro_data.ingest_macro_data(sleep=lambda s: None)

    report = macro_data.macro_freshness(session, today=date(2026, 9, 20))

    # Data age is normal for a monthly series, but the last fetch failed.
    assert report["CPIAUCNS"]["is_stale"] is False
    assert report["CPIAUCNS"]["last_fetch_failed"] is True
    assert report["UNRATE"]["last_fetch_failed"] is False


def test_never_fetched_series_is_stale(db_session):
    report = macro_data.macro_freshness(db_session, today=date(2026, 10, 1))

    for series_id in macro_data.SERIES:
        assert report[series_id]["as_of"] is None
        assert report[series_id]["is_stale"] is True
        assert report[series_id]["last_fetch_failed"] is False


@pytest.mark.parametrize(
    "series_id, age_days, stale",
    [
        ("CPIAUCNS", 45, False),
        ("CPIAUCNS", 46, True),
        ("UNRATE", 45, False),
        ("UNRATE", 46, True),
        ("DFF", 5, False),
        ("DFF", 6, True),
    ],
)
def test_stale_threshold_boundary_per_series(db_session, series_id, age_days, stale):
    available = date(2026, 8, 7)
    macro_data.store_macro_observations(
        db_session, series_id, [row(series_id, date(2026, 7, 1), available, 4.2)]
    )

    report = macro_data.macro_freshness(
        db_session, today=available + timedelta(days=age_days)
    )

    assert report[series_id]["age_days"] == age_days
    assert report[series_id]["is_stale"] is stale
