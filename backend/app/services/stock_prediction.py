"""
SCRUM-20 — Generate Stock Prediction

Builds model-ready features from historical stock data, trains an initial
machine learning model, and generates predictions on chronologically held-out
data.
"""

from typing import Any

import numpy as np
from sklearn.linear_model import LinearRegression


class StockPredictionError(Exception):
    """Raised when a stock prediction cannot be generated."""


FEATURE_COLUMNS = ("open", "high", "low", "close", "volume")


def prepare_prediction_data(
    records: list[dict[str, Any]],
) -> tuple[np.ndarray, np.ndarray, list[str]]:
    """
    Convert historical stock records into model-ready features and targets.

    Features from each trading day are used to predict the following day's
    closing price.
    """
    if not records or len(records) < 3:
        raise ValueError(
            "At least three historical stock records are required."
        )

    features: list[list[float]] = []
    targets: list[float] = []
    target_dates: list[str] = []

    for index in range(len(records) - 1):
        current = records[index]
        next_record = records[index + 1]

        try:
            feature_row = [
                float(current[column])
                for column in FEATURE_COLUMNS
            ]
            target = float(next_record["close"])
            target_date = str(next_record["date"])
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(
                "Historical stock records contain invalid or missing data."
            ) from exc

        features.append(feature_row)
        targets.append(target)
        target_dates.append(target_date)

    return (
        np.asarray(features, dtype=float),
        np.asarray(targets, dtype=float),
        target_dates,
    )


def train_and_predict(
    records: list[dict[str, Any]],
    train_ratio: float = 0.8,
) -> dict[str, Any]:
    """
    Train a LinearRegression model and predict chronologically held-out data.
    """
    if not 0 < train_ratio < 1:
        raise ValueError("train_ratio must be between 0 and 1.")

    features, targets, target_dates = prepare_prediction_data(records)

    split_index = int(len(features) * train_ratio)
    
    #Requires at least 2 training examples
    if split_index < 2 or split_index >= len(features):
        raise StockPredictionError(
            "Insufficient data to create training and test sets."
        )

    x_train = features[:split_index]
    x_test = features[split_index:]
    y_train = targets[:split_index]
    y_test = targets[split_index:]

    model = LinearRegression()
    model.fit(x_train, y_train)

    predictions = model.predict(x_test)

    return {
        "model": "LinearRegression",
        "training_count": len(x_train),
        "test_count": len(x_test),
        "dates": target_dates[split_index:],
        "actual": y_test.tolist(),
        "predictions": predictions.tolist(),
    }