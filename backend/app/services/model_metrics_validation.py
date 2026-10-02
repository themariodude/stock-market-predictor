"""Validation helpers for model-performance metrics."""

from numbers import Real


class InvalidModelMetricsError(ValueError):
    """Raised when model-performance metrics are malformed."""


REQUIRED_MODELS = frozenset(
    {
        "baseline",
        "model",
    }
)

REQUIRED_METRICS = frozenset(
    {
        "mae",
        "rmse",
    }
)


def validate_model_metrics(metrics: dict) -> dict:
    """Validate model-versus-baseline performance metrics."""
    if not isinstance(metrics, dict):
        raise InvalidModelMetricsError(
            "Model metrics response must be an object."
        )

    missing_models = REQUIRED_MODELS - metrics.keys()

    if missing_models:
        missing = ", ".join(sorted(missing_models))
        raise InvalidModelMetricsError(
            f"Model metrics are missing required sections: {missing}"
        )

    for model_name in REQUIRED_MODELS:
        model_metrics = metrics[model_name]

        if not isinstance(model_metrics, dict):
            raise InvalidModelMetricsError(
                f"Metrics for '{model_name}' must be an object."
            )

        missing_metrics = REQUIRED_METRICS - model_metrics.keys()

        if missing_metrics:
            missing = ", ".join(sorted(missing_metrics))
            raise InvalidModelMetricsError(
                f"Metrics for '{model_name}' are missing: {missing}"
            )

        for metric_name in REQUIRED_METRICS:
            value = model_metrics[metric_name]

            if isinstance(value, bool) or not isinstance(value, Real):
                raise InvalidModelMetricsError(
                    f"Metric '{model_name}.{metric_name}' must be numeric."
                )

            if value < 0:
                raise InvalidModelMetricsError(
                    f"Metric '{model_name}.{metric_name}' cannot be negative."
                )

    return metrics