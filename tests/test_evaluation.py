import pytest

from src.models.evaluation import (
    mean_absolute_error,
    root_mean_squared_error,
)


def test_mean_absolute_error():
    actual = [102, 101, 105]
    predicted = [100, 102, 101]

    result = mean_absolute_error(actual, predicted)

    assert result == pytest.approx(7 / 3)


def test_root_mean_squared_error():
    actual = [102, 101, 105]
    predicted = [100, 102, 101]

    result = root_mean_squared_error(actual, predicted)

    assert result == pytest.approx((21 / 3) ** 0.5)


def test_metrics_require_matching_lengths():
    actual = [102, 101, 105]
    predicted = [100, 102]

    with pytest.raises(ValueError):
        mean_absolute_error(actual, predicted)

    with pytest.raises(ValueError):
        root_mean_squared_error(actual, predicted)


def test_metrics_reject_empty_sequences():
    with pytest.raises(ValueError):
        mean_absolute_error([], [])

    with pytest.raises(ValueError):
        root_mean_squared_error([], [])