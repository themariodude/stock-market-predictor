"""Validation helpers for prediction service output."""

from numbers import Real

from app.services.errors import InvalidPredictionResponseError

VALID_DIRECTIONS = frozenset({"UP", "DOWN"})


def validate_prediction_response(prediction: dict) -> dict:
    """
    Validate prediction output before it is returned by the API.

    Expected fields:
        ticker
        direction
        confidence
        expected_change
    """
    if not isinstance(prediction, dict):
        raise InvalidPredictionResponseError("Prediction response must be an object.")

    required_fields = {
        "ticker",
        "direction",
        "confidence",
        "expected_change",
    }

    missing_fields = required_fields - prediction.keys()

    if missing_fields:
        missing = ", ".join(sorted(missing_fields))
        raise InvalidPredictionResponseError(
            f"Prediction response is missing required fields: {missing}"
        )

    ticker = prediction["ticker"]
    direction = prediction["direction"]
    confidence = prediction["confidence"]
    expected_change = prediction["expected_change"]

    if not isinstance(ticker, str) or not ticker.strip():
        raise InvalidPredictionResponseError(
            "Prediction ticker must be a non-empty string."
        )

    if direction not in VALID_DIRECTIONS:
        raise InvalidPredictionResponseError("Prediction direction must be UP or DOWN.")

    if (
        isinstance(confidence, bool)
        or not isinstance(confidence, Real)
        or not 0 <= confidence <= 1
    ):
        raise InvalidPredictionResponseError(
            "Prediction confidence must be between 0 and 1."
        )

    if isinstance(expected_change, bool) or not isinstance(
        expected_change,
        Real,
    ):
        raise InvalidPredictionResponseError("Expected change must be numeric.")

    return prediction
