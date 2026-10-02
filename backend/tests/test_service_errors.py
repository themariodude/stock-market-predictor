from app.services.errors import (
    ApplicationServiceError,
    DatabaseUnavailableError,
    InvalidPredictionResponseError,
    ModelLoadError,
    PredictionServiceUnavailableError,
)


def test_prediction_service_error_is_application_error():
    assert issubclass(
        PredictionServiceUnavailableError,
        ApplicationServiceError,
    )


def test_model_load_error_is_application_error():
    assert issubclass(
        ModelLoadError,
        ApplicationServiceError,
    )


def test_invalid_prediction_response_error_is_application_error():
    assert issubclass(
        InvalidPredictionResponseError,
        ApplicationServiceError,
    )


def test_database_unavailable_error_is_application_error():
    assert issubclass(
        DatabaseUnavailableError,
        ApplicationServiceError,
    )


def test_error_preserves_message():
    error = ModelLoadError("Prediction model could not be loaded.")

    assert str(error) == "Prediction model could not be loaded."
