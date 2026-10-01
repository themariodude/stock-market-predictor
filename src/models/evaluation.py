#First Version
import math


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