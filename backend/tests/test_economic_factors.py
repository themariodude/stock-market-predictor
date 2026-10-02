from datetime import date

import pytest
from fastapi.testclient import TestClient
from sqlalchemy import create_engine
from sqlalchemy.orm import Session
from sqlalchemy.pool import StaticPool

from app.main import app
from app.models.macro import MacroObservation
from app.services import economic_factors


@pytest.fixture
def macro_engine(monkeypatch):
    engine = create_engine(
        "sqlite+pysqlite:///:memory:",
        connect_args={"check_same_thread": False},
        poolclass=StaticPool,
    )
    MacroObservation.__table__.create(engine)
    monkeypatch.setattr(economic_factors, "get_session", lambda: Session(engine))
    return engine


def store_observation(session, series_id, observed, published, value):
    session.add(
        MacroObservation(
            series_id=series_id,
            observation_date=observed,
            available_date=published,
            value=value,
            raw_value=str(value),
        )
    )


def populate_macro_data(engine):
    with Session(engine) as session:
        store_observation(
            session, "CPIAUCNS", date(2025, 8, 1), date(2025, 9, 10), 300.0
        )
        store_observation(
            session, "CPIAUCNS", date(2026, 8, 1), date(2026, 9, 10), 309.0
        )
        store_observation(session, "UNRATE", date(2026, 8, 1), date(2026, 9, 4), 4.1)
        store_observation(session, "DFF", date(2026, 9, 9), date(2026, 9, 10), 3.5)
        session.commit()


def test_factors_are_available_only_after_publication(macro_engine):
    populate_macro_data(macro_engine)

    release_day = economic_factors.get_economic_factors("2026-09-10")
    assert [factor["id"] for factor in release_day] == ["unemployment_rate"]
    assert release_day[0]["value"] == 4.1
    assert release_day[0]["published_on"] == "2026-09-04"

    next_day = economic_factors.get_economic_factors("2026-09-11")
    assert [factor["id"] for factor in next_day] == [
        "cpi_yoy_pct",
        "unemployment_rate",
        "fed_funds_rate",
    ]
    assert next_day[0] == {
        "id": "cpi_yoy_pct",
        "name": "Inflation (CPI, year over year)",
        "value": 3.0,
        "unit": "%",
        "published_on": "2026-09-10",
        "age_days": 1,
    }
    assert next_day[2]["value"] == 3.5


def test_missing_data_or_database_does_not_block_context(macro_engine, monkeypatch):
    assert economic_factors.get_economic_factors("2026-09-11") == []
    assert economic_factors.get_economic_factors(None) == []
    assert economic_factors.get_economic_factors("invalid") == []

    MacroObservation.__table__.drop(macro_engine)
    assert economic_factors.get_economic_factors("2026-09-11") == []

    def unavailable_session():
        raise RuntimeError("DATABASE_URL is not configured")

    monkeypatch.setattr(economic_factors, "get_session", unavailable_session)
    assert economic_factors.get_economic_factors("2026-09-11") == []


def test_prediction_api_adds_context_without_changing_forecast(
    macro_engine, monkeypatch
):
    populate_macro_data(macro_engine)
    forecast = {
        "ticker": "LMT",
        "as_of_date": "2026-09-11",
        "prediction_direction": "UP",
        "direction_label": "Upward",
        "current_price": 100.0,
        "predicted_price": 101.0,
        "predicted_change": 1.0,
        "predicted_percent_change": 1.0,
    }
    monkeypatch.setattr(
        "app.api.stocks.get_prediction_direction", lambda ticker: forecast
    )

    response = TestClient(app).get("/stocks/LMT/prediction-direction")

    assert response.status_code == 200
    data = response.json()
    assert {key: data[key] for key in forecast} == forecast
    assert data["company_name"] == "Lockheed Martin"
    assert len(data["economic_factors"]) == 3


def test_prediction_api_still_returns_forecast_when_macro_database_is_unavailable(
    monkeypatch,
):
    def unavailable_session():
        raise RuntimeError("DATABASE_URL is not configured")

    monkeypatch.setattr(economic_factors, "get_session", unavailable_session)
    monkeypatch.setattr(
        "app.api.stocks.get_prediction_direction",
        lambda ticker: {
            "ticker": ticker,
            "as_of_date": "2026-09-11",
            "prediction_direction": "UP",
        },
    )

    response = TestClient(app).get("/stocks/LMT/prediction-direction")

    assert response.status_code == 200
    assert response.json()["prediction_direction"] == "UP"
    assert response.json()["economic_factors"] == []
