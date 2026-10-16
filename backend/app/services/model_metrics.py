"""Service for loading saved model-performance metrics."""

import json
import os
from pathlib import Path

from app.services.model_metrics_validation import (
    validate_model_metrics,
)


class ModelMetricsUnavailableError(Exception):
    """Raised when model-performance metrics cannot be loaded."""


DEFAULT_METRICS_PATH = Path("artifacts/model_metrics.json")


def get_metrics_path() -> Path:
    """Return the configured model-metrics artifact path."""
    configured_path = os.getenv("MODEL_METRICS_PATH")

    if configured_path:
        return Path(configured_path)

    return DEFAULT_METRICS_PATH


def load_model_metrics(path: Path | None = None) -> dict:
    """Load and validate saved model-performance metrics."""
    metrics_path = path or get_metrics_path()

    if not metrics_path.exists():
        raise ModelMetricsUnavailableError(
            "Model performance metrics are not available."
        )

    try:
        with metrics_path.open("r", encoding="utf-8") as file:
            metrics = json.load(file)
    except (OSError, json.JSONDecodeError) as exc:
        raise ModelMetricsUnavailableError(
            "Model performance metrics could not be loaded."
        ) from exc

    return validate_model_metrics(metrics)
