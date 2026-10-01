#First Version
import math
from src.models.baseline import persistence_baseline


def mean_absolute_error(actual, predicted):
    """
    Calculate Mean Absolute Error (MAE).

    Args:
        actual: Sequence of actual observed values.
        predicted: Sequence of predicted values.

    Returns:
        The mean absolute error.

    Raises:
        ValueError: If the sequences are empty or have different lengths.
    """
    if len(actual) == 0 or len(predicted) == 0:
        raise ValueError("Actual and predicted values cannot be empty.")

    if len(actual) != len(predicted):
        raise ValueError("Actual and predicted values must have the same length.")

    absolute_errors = [
        abs(actual_value - predicted_value)
        for actual_value, predicted_value in zip(actual, predicted)
    ]

    return sum(absolute_errors) / len(absolute_errors)


def root_mean_squared_error(actual, predicted):
    """
    Calculate Root Mean Squared Error (RMSE).

    Args:
        actual: Sequence of actual observed values.
        predicted: Sequence of predicted values.

    Returns:
        The root mean squared error.

    Raises:
        ValueError: If the sequences are empty or have different lengths.
    """
    if len(actual) == 0 or len(predicted) == 0:
        raise ValueError("Actual and predicted values cannot be empty.")

    if len(actual) != len(predicted):
        raise ValueError("Actual and predicted values must have the same length.")

    squared_errors = [
        (actual_value - predicted_value) ** 2
        for actual_value, predicted_value in zip(actual, predicted)
    ]

    return math.sqrt(sum(squared_errors) / len(squared_errors))



def compare_model_to_baseline(prices, model_predictions):
    """
    Compare trained model predictions against the persistence baseline.

    Args:
        prices: Sequence of actual stock prices.
        model_predictions: Predictions produced by the trained ML model.

    Returns:
        Dictionary containing MAE and RMSE for both the baseline
        and the trained model.

    Raises:
        ValueError: If model predictions do not align with the
        expected number of actual values.
    """
    actual = prices[1:]
    baseline_predictions = persistence_baseline(prices)

    if len(model_predictions) != len(actual):
        raise ValueError(
            "Model predictions must match the number of actual values."
        )

    return {
        "baseline": {
            "mae": mean_absolute_error(actual, baseline_predictions),
            "rmse": root_mean_squared_error(actual, baseline_predictions),
        },
        "model": {
            "mae": mean_absolute_error(actual, model_predictions),
            "rmse": root_mean_squared_error(actual, model_predictions),
        },
    }

def format_comparison_report(results):
    """
    Format model-versus-baseline evaluation results into a readable report.

    Args:
        results: Dictionary returned by compare_model_to_baseline().

    Returns:
        A formatted string containing baseline and model MAE and RMSE values.

    Raises:
        ValueError: If the expected result structure is missing.
    """
    try:
        baseline = results["baseline"]
        model = results["model"]

        baseline_mae = baseline["mae"]
        baseline_rmse = baseline["rmse"]
        model_mae = model["mae"]
        model_rmse = model["rmse"]

    except (KeyError, TypeError):
        raise ValueError(
            "Results must contain baseline and model MAE/RMSE values."
        )

    return (
        f"Baseline MAE: {baseline_mae:.4f}\n"
        f"Baseline RMSE: {baseline_rmse:.4f}\n"
        f"Model MAE: {model_mae:.4f}\n"
        f"Model RMSE: {model_rmse:.4f}"
    )

def evaluate_and_report(prices, model_predictions):
    """
    Evaluate trained model predictions against the persistence baseline
    and return both structured metrics and a readable report.

    Args:
        prices: Sequence of actual stock prices ordered chronologically.
        model_predictions: Predictions produced by a trained ML model.

    Returns:
        A tuple containing:
            - comparison results dictionary
            - formatted comparison report
    """
    results = compare_model_to_baseline(prices, model_predictions)
    report = format_comparison_report(results)

    return results, report