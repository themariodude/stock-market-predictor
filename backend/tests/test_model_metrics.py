import json

import pytest

from app.services.model_metrics import (
    ModelMetricsUnavailableError,
    load_model_metrics,
)
from app.services.model_metrics_validation import (
    InvalidModelMetricsError,
)


def valid_metrics():
    return {
        "baseline": {
            "mae": 2.0,
            "rmse": 3.0,
        },
        "model": {
            "mae": 1.5,
            "rmse": 2.5,
        },
    }


def test_load_valid_metrics(tmp_path):
    path = tmp_path / "model_metrics.json"

    metrics = valid_metrics()

    path.write_text(
        json.dumps(metrics),
        encoding="utf-8",
    )

    assert load_model_metrics(path) == metrics


def test_missing_metrics_file(tmp_path):
    path = tmp_path / "missing.json"

    with pytest.raises(
        ModelMetricsUnavailableError,
        match="not available",
    ):
        load_model_metrics(path)


def test_invalid_json(tmp_path):
    path = tmp_path / "model_metrics.json"

    path.write_text(
        "{invalid json",
        encoding="utf-8",
    )

    with pytest.raises(
        ModelMetricsUnavailableError,
        match="could not be loaded",
    ):
        load_model_metrics(path)


def test_invalid_metrics_content(tmp_path):
    path = tmp_path / "model_metrics.json"

    path.write_text(
        json.dumps(
            {
                "baseline": {
                    "mae": 2.0,
                    "rmse": 3.0,
                }
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(
        InvalidModelMetricsError,
        match="missing required sections",
    ):
        load_model_metrics(path)
