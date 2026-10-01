import pytest

from src.models.evaluation import (
    mean_absolute_error,
    root_mean_squared_error, compare_model_to_baseline
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

from src.models.evaluation import compare_model_to_baseline


def test_compare_model_to_baseline():
    prices = [100, 102, 101, 105]
    model_predictions = [101, 101, 104]

    results = compare_model_to_baseline(prices, model_predictions)

    assert results["baseline"]["mae"] == pytest.approx(7 / 3)
    assert results["baseline"]["rmse"] == pytest.approx(7 ** 0.5)

    assert results["model"]["mae"] == pytest.approx(2 / 3)
    assert results["model"]["rmse"] == pytest.approx((2 / 3) ** 0.5)


def test_compare_model_to_baseline_requires_aligned_predictions():
    prices = [100, 102, 101, 105]
    model_predictions = [101, 103]

    with pytest.raises(ValueError):
        compare_model_to_baseline(prices, model_predictions)