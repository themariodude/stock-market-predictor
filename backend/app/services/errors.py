"""Application-level exceptions used for controlled error handling."""


class ApplicationServiceError(Exception):
    """Base class for controlled application service failures."""


class PredictionServiceUnavailableError(ApplicationServiceError):
    """Raised when prediction functionality is temporarily unavailable."""


class ModelLoadError(ApplicationServiceError):
    """Raised when a prediction model cannot be loaded."""


class InvalidPredictionResponseError(ApplicationServiceError):
    """Raised when the prediction service produces malformed output."""


class DatabaseUnavailableError(ApplicationServiceError):
    """Raised when required database operations are unavailable."""
