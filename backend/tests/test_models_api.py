from fastapi.testclient import TestClient

from app.main import app
from app.services.model_metrics import (
    ModelMetricsUnavailableError,
)
from app.services.model_metrics_validation import (
    InvalidModelMetricsError,
)

client = TestClient(app)


def test_model_metrics_success(monkeypatch):
    expected = {
        "baseline": {
            "mae": 2.0,
            "rmse": 3.0,
        },
        "model": {
            "mae": 1.5,
            "rmse": 2.5,
        },
    }

    monkeypatch.setattr(
        "app.api.models.load_model_metrics",
        lambda: expected,
    )

    response = client.get("/models/metrics")

    assert response.status_code == 200
    assert response.json() == expected


def test_model_metrics_unavailable(monkeypatch):
    def unavailable():
        raise ModelMetricsUnavailableError(
            "Model performance metrics are not available."
        )

    monkeypatch.setattr(
        "app.api.models.load_model_metrics",
        unavailable,
    )

    response = client.get("/models/metrics")

    assert response.status_code == 503
    assert response.json() == {
        "detail": "Model performance metrics are not available."
    }


def test_invalid_model_metrics(monkeypatch):
    def invalid():
        raise InvalidModelMetricsError(
            "Model metrics are malformed."
        )

    monkeypatch.setattr(
        "app.api.models.load_model_metrics",
        invalid,
    )

    response = client.get("/models/metrics")

    assert response.status_code == 502
    assert response.json() == {
        "detail": "Model metrics are malformed."
    }


def test_metrics_failure_does_not_break_api(monkeypatch):
    def unavailable():
        raise ModelMetricsUnavailableError(
            "Model performance metrics are not available."
        )

    monkeypatch.setattr(
        "app.api.models.load_model_metrics",
        unavailable,
    )

    response = client.get("/models/metrics")
    assert response.status_code == 503

    health_response = client.get("/health")
    assert health_response.status_code == 200