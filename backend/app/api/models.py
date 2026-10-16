"""API endpoints for model-performance information."""

from fastapi import APIRouter, HTTPException

from app.services.model_metrics import (
    ModelMetricsUnavailableError,
    load_model_metrics,
)
from app.services.model_metrics_validation import (
    InvalidModelMetricsError,
)

router = APIRouter(
    prefix="/models",
    tags=["models"],
)


@router.get("/metrics")
def model_metrics() -> dict:
    """Return model-versus-baseline performance metrics."""
    try:
        return load_model_metrics()

    except ModelMetricsUnavailableError as exc:
        raise HTTPException(
            status_code=503,
            detail=str(exc),
        ) from exc

    except InvalidModelMetricsError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc
