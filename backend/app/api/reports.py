
"""
US-37 - Export Stock Analysis Report as PDF.

Provides an endpoint for downloading a stock-specific
analysis report.
"""

import logging
from datetime import datetime, timezone

from fastapi import APIRouter, HTTPException
from fastapi.responses import Response

from app.api.stocks import SUPPORTED_STOCKS, validate_supported_ticker
from app.services.current_stock_info import (
    StockDataError,
    get_current_stock_info,
)
from app.services.pdf_report import generate_stock_report_pdf
from app.services.prediction_direction import (
    PredictionDirectionError,
    get_prediction_direction,
)

router = APIRouter(prefix="/reports", tags=["reports"])

log = logging.getLogger(__name__)


@router.get("/stocks/{ticker}/pdf")
def export_stock_report(ticker: str) -> Response:
    """Generate and download a stock analysis PDF report."""

    # Validate the ticker using existing application logic.
    symbol = validate_supported_ticker(ticker)

    # Current market quotes are optional for PDF export.
    try:
        stock = get_current_stock_info(symbol)
    except StockDataError as exc:
        log.warning(
            "Current stock information unavailable for %s: %s",
            symbol,
            exc,
        )
        stock = None

    # Prediction data is required for this report.
    try:
        prediction = get_prediction_direction(symbol)

    except ValueError as exc:
        raise HTTPException(
            status_code=400,
            detail=str(exc),
        ) from exc

    except PredictionDirectionError as exc:
        raise HTTPException(
            status_code=502,
            detail=str(exc),
        ) from exc

    # Generate PDF using Jinja2 and WeasyPrint.
    try:
        pdf_bytes = generate_stock_report_pdf(
            ticker=symbol,
            company_name=SUPPORTED_STOCKS[symbol],
            stock=stock,
            prediction=prediction,
        )

    except Exception as exc:
        log.exception("PDF generation failed for %s", symbol)
        raise HTTPException(
            status_code=500,
            detail="Unable to generate the PDF report.",
        ) from exc

    # Create a meaningful download filename.
    date = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    filename = f"{symbol}_Analysis_{date}.pdf"

    return Response(
        content=pdf_bytes,
        media_type="application/pdf",
        headers={
            "Content-Disposition": f'attachment; filename="{filename}"'
        },
    )
