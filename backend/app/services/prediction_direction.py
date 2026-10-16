"""
US-07 - View Prediction Direction

Provides an easy-to-read movement direction from a lightweight forecast.

US-17 - Understand Prediction Factors

Each forecast includes an explanation built from the same values that
produced it.
"""

from math import sqrt
from typing import Any

from app.services.historical_stock_data import (
    HistoricalStockDataError,
    get_historical_stock_data,
)


class PredictionDirectionError(Exception):
    """Raised when a prediction direction cannot be calculated."""


DIRECTION_LABELS = {
    "UP": "Upward",
    "DOWN": "Downward",
    "FLAT": "Flat",
}

CONFIDENCE_LABELS = {
    "HIGH": "High confidence",
    "MEDIUM": "Medium confidence",
    "LOW": "Low confidence",
}

HISTORY_RANGE = "1M"

EXPLANATION_METHOD = "momentum"
EXPLANATION_SUMMARY = (
    "Extends the average daily price change over the last month by one trading day."
)
EXPLANATION_HORIZON = "next_trading_day"
CONFIDENCE_BASIS = (
    "How strong the recent trend is compared with day-to-day price swings. "
    "It is not the probability that the forecast is correct."
)
NOT_USED = [
    "Trading volume",
    "Economic indicators (shown as market context only)",
]
LIMITATIONS = [
    "Uses only the last month of closing prices; news, earnings, and market "
    "events are not considered.",
    "The direction depends only on the first and last closes of the window.",
    "Closing prices are not adjusted for dividends or splits.",
    "The confidence score is not calibrated against past forecast accuracy.",
]


def classify_prediction_direction(
    current_price: float,
    predicted_price: float,
) -> str:
    """Return UP, DOWN, or FLAT for a predicted price movement."""
    if current_price is None or predicted_price is None:
        raise ValueError("Current and predicted prices are required.")

    current = float(current_price)
    predicted = float(predicted_price)

    if predicted > current:
        return "UP"

    if predicted < current:
        return "DOWN"

    return "FLAT"


def classify_prediction_confidence(confidence_score: float) -> str:
    """Return a readable confidence label for a 0-100 confidence score."""
    if confidence_score >= 70:
        return CONFIDENCE_LABELS["HIGH"]

    if confidence_score >= 40:
        return CONFIDENCE_LABELS["MEDIUM"]

    return CONFIDENCE_LABELS["LOW"]


def calculate_daily_volatility(daily_changes: list[float]) -> float | None:
    """
    Return the population standard deviation of daily changes.

    Returns None when fewer than two daily changes exist, the same condition
    under which confidence is unavailable.
    """
    if len(daily_changes) < 2:
        return None

    average_change = sum(daily_changes) / len(daily_changes)
    variance = sum((change - average_change) ** 2 for change in daily_changes) / len(
        daily_changes
    )
    return sqrt(variance)


def calculate_prediction_confidence(
    daily_changes: list[float],
) -> dict[str, float | str | None]:
    """
    Estimate confidence from trend strength relative to recent variability.

    Confidence is available when at least two recent daily changes exist. A
    steadier trend receives a higher score, while choppy movement increases
    uncertainty.
    """
    if len(daily_changes) < 2:
        return {
            "prediction_confidence": None,
            "prediction_uncertainty": None,
            "confidence_label": "Unavailable",
        }

    average_change = sum(daily_changes) / len(daily_changes)
    volatility = calculate_daily_volatility(daily_changes)
    signal_strength = abs(average_change)

    if signal_strength == 0 and volatility == 0:
        confidence_score = 100.0
    else:
        confidence_score = (signal_strength / (signal_strength + volatility)) * 100

    confidence_score = round(confidence_score, 1)
    uncertainty_score = round(100 - confidence_score, 1)

    return {
        "prediction_confidence": confidence_score,
        "prediction_uncertainty": uncertainty_score,
        "confidence_label": classify_prediction_confidence(confidence_score),
    }


def build_prediction_explanation(
    priced_records: list[dict[str, Any]],
    closes: list[float],
    daily_changes: list[float],
    average_change: float,
) -> dict[str, Any]:
    """
    Describe the inputs behind a momentum forecast.

    Every value comes from the same records and changes used to compute the
    forecast, so the explanation cannot drift from the prediction.
    """
    volatility = calculate_daily_volatility(daily_changes)

    return {
        "method": EXPLANATION_METHOD,
        "summary": EXPLANATION_SUMMARY,
        "horizon": EXPLANATION_HORIZON,
        "window": {
            "range": HISTORY_RANGE,
            "start_date": priced_records[0].get("date"),
            "end_date": priced_records[-1].get("date"),
            "start_close": round(closes[0], 2),
            "end_close": round(closes[-1], 2),
            "closing_prices": len(closes),
        },
        "factors": [
            {
                "name": "recent_trend",
                "label": f"Average daily change ({HISTORY_RANGE})",
                "value": round(average_change, 2),
                "unit": "USD/day",
                "role": "Sets the direction and predicted price",
                "influence": None,
            },
            {
                "name": "daily_volatility",
                "label": f"Typical daily swing ({HISTORY_RANGE})",
                "value": round(volatility, 2) if volatility is not None else None,
                "unit": "USD",
                "role": "Larger swings lower the confidence score",
                "influence": None,
            },
        ],
        "confidence_basis": CONFIDENCE_BASIS,
        "not_used": list(NOT_USED),
        "limitations": list(LIMITATIONS),
    }


def get_prediction_direction(ticker: str) -> dict[str, Any]:
    """
    Retrieve a short-term prediction direction for a stock ticker.

    The current implementation uses recent daily closes as a simple momentum
    forecast. A trained model can replace this calculation while preserving
    the response shape used by the API and frontend.
    """
    if not ticker or not ticker.strip():
        raise ValueError("Ticker symbol is required.")

    symbol = ticker.strip().upper()

    try:
        history = get_historical_stock_data(symbol, HISTORY_RANGE)
        priced_records = [
            record for record in history["data"] if record.get("close") is not None
        ]
        closes = [float(record["close"]) for record in priced_records]

        if len(closes) < 2:
            raise PredictionDirectionError(
                f"At least two closing prices are required for {symbol}."
            )

        daily_changes = [
            closes[index] - closes[index - 1] for index in range(1, len(closes))
        ]
        average_change = sum(daily_changes) / len(daily_changes)
        confidence = calculate_prediction_confidence(daily_changes)

        current_price = closes[-1]
        predicted_price = current_price + average_change
        predicted_change = predicted_price - current_price
        predicted_percent_change = (
            (predicted_change / current_price) * 100 if current_price != 0 else 0
        )
        direction = classify_prediction_direction(
            current_price,
            predicted_price,
        )

        return {
            "ticker": symbol,
            "as_of_date": priced_records[-1].get("date"),
            "prediction_direction": direction,
            "direction_label": DIRECTION_LABELS[direction],
            "current_price": round(current_price, 2),
            "predicted_price": round(predicted_price, 2),
            "predicted_change": round(predicted_change, 2),
            "predicted_percent_change": round(predicted_percent_change, 2),
            **confidence,
            "explanation": build_prediction_explanation(
                priced_records,
                closes,
                daily_changes,
                average_change,
            ),
        }

    except PredictionDirectionError:
        raise
    except (HistoricalStockDataError, KeyError, TypeError, ValueError) as exc:
        raise PredictionDirectionError(
            f"Unable to calculate prediction direction for {symbol}."
        ) from exc
