"""US-38: prediction context in the generated stock report template."""

import re
from pathlib import Path

from jinja2 import Environment, FileSystemLoader, select_autoescape

TEMPLATE_DIR = Path(__file__).resolve().parents[1] / "app" / "templates"
template = Environment(
    loader=FileSystemLoader(TEMPLATE_DIR),
    autoescape=select_autoescape(["html"]),
).get_template("stock_analysis.html")


def render_report(prediction):
    html = template.render(
        ticker="LMT",
        company_name="Lockheed Martin",
        stock=None,
        prediction=prediction,
        generated_at="2026-11-17 00:00 UTC",
    )
    return re.sub(r"\s+", " ", html)


def sample_prediction():
    return {
        "as_of_date": "2026-11-16",
        "direction_label": "Upward",
        "current_price": 585.21,
        "predicted_price": 587.06,
        "predicted_percent_change": 0.32,
        "prediction_confidence": 9.4,
        "prediction_uncertainty": 90.6,
        "confidence_label": "Low confidence",
        "explanation": {
            "summary": "Momentum prediction based on recent prices.",
            "horizon": "next_trading_day",
            "window": {
                "start_date": "2026-10-16",
                "end_date": "2026-11-16",
            },
            "factors": [
                {
                    "label": "Average daily change (1M)",
                    "value": 1.85,
                    "unit": "USD/day",
                    "role": "Sets the predicted direction",
                }
            ],
            "not_used": ["Trading volume", "Economic indicators"],
            "confidence_basis": "Trend strength, not probability.",
            "limitations": ["Historical data may be delayed."],
        },
    }


def test_report_displays_prediction_context_and_caveats():
    html = render_report(sample_prediction())

    assert "Forecast Horizon" in html
    assert "Next trading day" in html
    assert "2026-10-16 to 2026-11-16" in html
    assert "Average daily change (1M)" in html
    assert "90.6 / 100" in html
    assert "Trading volume; Economic indicators" in html
    assert "not guarantees of future prices" in html
    assert "neither is a calibrated probability" in html
    assert "Historical data may be delayed." in html


def test_report_marks_missing_optional_context_without_hiding_caveat():
    prediction = sample_prediction()
    prediction.update(
        prediction_confidence=None,
        prediction_uncertainty=None,
        confidence_label="Unavailable",
        explanation={},
    )
    html = render_report(prediction)

    assert "Not specified" in html
    assert "Uncertainty Indicator" in html
    assert "Unavailable" in html
    assert "Forecast input window:" not in html
    assert "Not used in this forecast:" not in html
    assert "neither is a calibrated probability" in html
