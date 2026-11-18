"""
US-37 - Tests for stock analysis PDF export.
"""

import pytest
from fastapi.testclient import TestClient

from app.api import reports
from app.main import app
from app.services.current_stock_info import StockDataError
from app.services.pdf_report import (
    generate_stock_report_pdf,
    template_env,
)
from app.services.prediction_direction import PredictionDirectionError


client = TestClient(app)


@pytest.fixture
def sample_stock():
    return {
        "ticker": "LMT",
        "current_price": 585.21,
        "previous_close": 590.00,
        "price_change": -4.79,
        "percent_change": -0.81,
        "volume": 123456,
    }


@pytest.fixture
def sample_prediction():
    return {
        "ticker": "LMT",
        "as_of_date": "2026-11-16",
        "direction_label": "Upward",
        "current_price": 585.21,
        "predicted_price": 587.06,
        "predicted_percent_change": 0.32,
        "prediction_confidence": 9.4,
        "confidence_label": "Low confidence",
        "explanation": {
            "summary": "Momentum prediction based on recent prices.",
            "factors": [
                {
                    "label": "Average daily change (1M)",
                    "value": 1.85,
                    "unit": "USD/day",
                    "role": "Sets the predicted direction",
                }
            ],
            "confidence_basis": "Trend strength, not probability.",
            "limitations": ["Historical data may be delayed."],
        },
    }


@pytest.fixture
def mock_market_data(monkeypatch, sample_stock, sample_prediction):
    monkeypatch.setattr(
        reports,
        "get_current_stock_info",
        lambda ticker: sample_stock,
    )
    monkeypatch.setattr(
        reports,
        "get_prediction_direction",
        lambda ticker: sample_prediction,
    )


def test_pdf_generation(sample_stock, sample_prediction):
    """WeasyPrint produces real PDF bytes."""
    pdf = generate_stock_report_pdf(
        ticker="LMT",
        company_name="Lockheed Martin",
        stock=sample_stock,
        prediction=sample_prediction,
    )

    assert pdf.startswith(b"%PDF-")
    assert len(pdf) > 1000


def test_html_template_content(sample_stock, sample_prediction):
    """The template contains the expected analysis data."""
    template = template_env.get_template("stock_analysis.html")

    html = template.render(
        ticker="LMT",
        company_name="Lockheed Martin",
        stock=sample_stock,
        prediction=sample_prediction,
        generated_at="2026-11-17 00:00 UTC",
    )

    assert "Lockheed Martin" in html
    assert "585.21" in html
    assert "587.06" in html
    assert "Upward" in html
    assert "Low confidence" in html
    assert "Average daily change (1M)" in html


def test_pdf_export_success(monkeypatch, mock_market_data):
    """The endpoint returns a downloadable PDF."""
    monkeypatch.setattr(
        reports,
        "generate_stock_report_pdf",
        lambda **kwargs: b"%PDF-1.7\nmock",
    )

    response = client.get("/reports/stocks/LMT/pdf")

    assert response.status_code == 200
    assert response.headers["content-type"] == "application/pdf"
    assert "attachment;" in response.headers["content-disposition"]
    assert "LMT_Analysis_" in response.headers["content-disposition"]
    assert response.content.startswith(b"%PDF-")


def test_invalid_ticker():
    """Unsupported tickers return HTTP 404."""
    response = client.get("/reports/stocks/INVALID/pdf")

    assert response.status_code == 404


def test_missing_current_data(
    monkeypatch,
    mock_market_data,
    sample_prediction,
):
    """Missing live quotes do not block PDF export."""

    def unavailable(ticker):
        raise StockDataError("Current price unavailable.")

    monkeypatch.setattr(
        reports,
        "get_current_stock_info",
        unavailable,
    )

    received = {}

    def fake_pdf(**kwargs):
        received.update(kwargs)
        return b"%PDF-1.7\nmock"

    monkeypatch.setattr(
        reports,
        "generate_stock_report_pdf",
        fake_pdf,
    )

    response = client.get("/reports/stocks/LMT/pdf")

    assert response.status_code == 200
    assert received["stock"] is None
    assert received["prediction"] == sample_prediction


def test_prediction_failure(monkeypatch, mock_market_data):
    """Prediction service failures return HTTP 502."""

    def unavailable(ticker):
        raise PredictionDirectionError("Prediction unavailable.")

    monkeypatch.setattr(
        reports,
        "get_prediction_direction",
        unavailable,
    )

    response = client.get("/reports/stocks/LMT/pdf")

    assert response.status_code == 502


def test_pdf_generation_failure(monkeypatch, mock_market_data):
    """PDF rendering failures return HTTP 500."""

    def broken_pdf(**kwargs):
        raise RuntimeError("PDF rendering failed.")

    monkeypatch.setattr(
        reports,
        "generate_stock_report_pdf",
        broken_pdf,
    )

    response = client.get("/reports/stocks/LMT/pdf")

    assert response.status_code == 500
    assert response.headers["content-type"].startswith("application/json")


def test_template_handles_missing_quotes(sample_prediction):
    """The HTML report explains unavailable live data."""
    template = template_env.get_template("stock_analysis.html")

    html = template.render(
        ticker="LMT",
        company_name="Lockheed Martin",
        stock=None,
        prediction=sample_prediction,
        generated_at="2026-11-17 00:00 UTC",
    )

    assert "Current market information is temporarily unavailable" in html
    assert "2026-11-16" in html
