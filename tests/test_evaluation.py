import pytest

from src.models.evaluation import (
    compare_model_to_baseline, evaluate_and_report ,
    format_comparison_report,
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

def test_format_comparison_report():
    results = {
        "baseline": {"mae": 2.0, "rmse": 3.0},
        "model": {"mae": 1.5, "rmse": 2.5},
    }

    report = format_comparison_report(results)

    assert "Baseline MAE: 2.0000" in report
    assert "Baseline RMSE: 3.0000" in report
    assert "Model MAE: 1.5000" in report
    assert "Model RMSE: 2.5000" in report

def test_format_comparison_report_rejects_invalid_results():
    with pytest.raises(ValueError):
        format_comparison_report({})

def test_evaluate_and_report():
    prices = [100, 102, 101, 105]
    model_predictions = [101, 101, 104]

    results, report = evaluate_and_report(
        prices,
        model_predictions,
    )

    assert results["baseline"]["mae"] == pytest.approx(7 / 3)
    assert results["model"]["mae"] == pytest.approx(2 / 3)

    assert "Baseline MAE:" in report
    assert "Baseline RMSE:" in report
    assert "Model MAE:" in report
    assert "Model RMSE:" in report