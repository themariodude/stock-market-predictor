import pytest

from app.services.errors import InvalidPredictionResponseError
from app.services.prediction_validation import (
    validate_prediction_response,
)


def valid_prediction():
    return {
        "ticker": "LMT",
        "direction": "UP",
        "confidence": 0.73,
        "expected_change": 1.4,
    }


def test_valid_prediction_response():
    prediction = valid_prediction()

    assert validate_prediction_response(prediction) == prediction


def test_prediction_must_be_dictionary():
    with pytest.raises(
        InvalidPredictionResponseError,
        match="must be an object",
    ):
        validate_prediction_response("invalid")


@pytest.mark.parametrize(
    "field",
    [
        "ticker",
        "direction",
        "confidence",
        "expected_change",
    ],
)
def test_missing_required_prediction_field(field):
    prediction = valid_prediction()
    del prediction[field]

    with pytest.raises(InvalidPredictionResponseError):
        validate_prediction_response(prediction)


@pytest.mark.parametrize(
    "ticker",
    [
        "",
        "   ",
        None,
        123,
    ],
)
def test_invalid_prediction_ticker(ticker):
    prediction = valid_prediction()
    prediction["ticker"] = ticker

    with pytest.raises(
        InvalidPredictionResponseError,
        match="ticker",
    ):
        validate_prediction_response(prediction)


@pytest.mark.parametrize(
    "direction",
    [
        "SIDEWAYS",
        "",
        None,
        "up",
    ],
)
def test_invalid_prediction_direction(direction):
    prediction = valid_prediction()
    prediction["direction"] = direction

    with pytest.raises(
        InvalidPredictionResponseError,
        match="direction",
    ):
        validate_prediction_response(prediction)


@pytest.mark.parametrize(
    "confidence",
    [
        -0.01,
        1.01,
        "0.73",
        None,
        True,
    ],
)
def test_invalid_prediction_confidence(confidence):
    prediction = valid_prediction()
    prediction["confidence"] = confidence

    with pytest.raises(
        InvalidPredictionResponseError,
        match="confidence",
    ):
        validate_prediction_response(prediction)


@pytest.mark.parametrize(
    "expected_change",
    [
        "1.4",
        None,
        True,
    ],
)
def test_invalid_expected_change(expected_change):
    prediction = valid_prediction()
    prediction["expected_change"] = expected_change

    with pytest.raises(
        InvalidPredictionResponseError,
        match="Expected change",
    ):
        validate_prediction_response(prediction)
