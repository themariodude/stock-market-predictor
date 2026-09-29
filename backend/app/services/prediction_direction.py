"""
US-07 - View Prediction Direction

Provides an easy-to-read movement direction from a lightweight forecast.
"""

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
        history = get_historical_stock_data(symbol, "1M")
        closes = [
            float(record["close"])
            for record in history["data"]
            if record.get("close") is not None
        ]

        if len(closes) < 2:
            raise PredictionDirectionError(
                f"At least two closing prices are required for {symbol}."
            )

        daily_changes = [
            closes[index] - closes[index - 1]
            for index in range(1, len(closes))
        ]
        average_change = sum(daily_changes) / len(daily_changes)

        current_price = closes[-1]
        predicted_price = current_price + average_change
        predicted_change = predicted_price - current_price
        predicted_percent_change = (
            (predicted_change / current_price) * 100
            if current_price != 0
            else 0
        )
        direction = classify_prediction_direction(
            current_price,
            predicted_price,
        )

        return {
            "ticker": symbol,
            "prediction_direction": direction,
            "direction_label": DIRECTION_LABELS[direction],
            "current_price": round(current_price, 2),
            "predicted_price": round(predicted_price, 2),
            "predicted_change": round(predicted_change, 2),
            "predicted_percent_change": round(predicted_percent_change, 2),
        }

    except PredictionDirectionError:
        raise
    except (HistoricalStockDataError, KeyError, TypeError, ValueError) as exc:
        raise PredictionDirectionError(
            f"Unable to calculate prediction direction for {symbol}."
        ) from exc
