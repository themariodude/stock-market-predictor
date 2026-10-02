import pytest

from app.services.model_metrics_validation import (
    InvalidModelMetricsError,
    validate_model_metrics,
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


def test_valid_model_metrics():
    metrics = valid_metrics()

    assert validate_model_metrics(metrics) == metrics


def test_metrics_must_be_dictionary():
    with pytest.raises(
        InvalidModelMetricsError,
        match="must be an object",
    ):
        validate_model_metrics("invalid")


@pytest.mark.parametrize(
    "section",
    [
        "baseline",
        "model",
    ],
)
def test_required_model_sections(section):
    metrics = valid_metrics()
    del metrics[section]

    with pytest.raises(
        InvalidModelMetricsError,
        match="missing required sections",
    ):
        validate_model_metrics(metrics)


@pytest.mark.parametrize(
    "section",
    [
        "baseline",
        "model",
    ],
)
def test_model_section_must_be_dictionary(section):
    metrics = valid_metrics()
    metrics[section] = "invalid"

    with pytest.raises(
        InvalidModelMetricsError,
        match="must be an object",
    ):
        validate_model_metrics(metrics)


@pytest.mark.parametrize(
    ("section", "metric"),
    [
        ("baseline", "mae"),
        ("baseline", "rmse"),
        ("model", "mae"),
        ("model", "rmse"),
    ],
)
def test_required_metrics(section, metric):
    metrics = valid_metrics()
    del metrics[section][metric]

    with pytest.raises(
        InvalidModelMetricsError,
        match="are missing",
    ):
        validate_model_metrics(metrics)


@pytest.mark.parametrize(
    ("section", "metric"),
    [
        ("baseline", "mae"),
        ("baseline", "rmse"),
        ("model", "mae"),
        ("model", "rmse"),
    ],
)
def test_metrics_must_be_numeric(section, metric):
    metrics = valid_metrics()
    metrics[section][metric] = "invalid"

    with pytest.raises(
        InvalidModelMetricsError,
        match="must be numeric",
    ):
        validate_model_metrics(metrics)


@pytest.mark.parametrize(
    ("section", "metric"),
    [
        ("baseline", "mae"),
        ("baseline", "rmse"),
        ("model", "mae"),
        ("model", "rmse"),
    ],
)
def test_metrics_cannot_be_negative(section, metric):
    metrics = valid_metrics()
    metrics[section][metric] = -1.0

    with pytest.raises(
        InvalidModelMetricsError,
        match="cannot be negative",
    ):
        validate_model_metrics(metrics)


def test_boolean_is_not_valid_metric():
    metrics = valid_metrics()
    metrics["model"]["mae"] = True

    with pytest.raises(
        InvalidModelMetricsError,
        match="must be numeric",
    ):
        validate_model_metrics(metrics)
