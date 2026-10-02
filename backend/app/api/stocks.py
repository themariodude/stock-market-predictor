"""
US-01 — View Supported Stocks

Defines the API endpoints for retrieving
information about supported defense-sector stocks.
It provides functionality to list supported stocks,
retrieve historical stock data, and get current
market information for a specific stock ticker.
"""

from fastapi import APIRouter, HTTPException, Query

from app.services.current_stock_info import (
    StockDataError,
    get_current_stock_info,
)
from app.services.historical_stock_data import (
    HistoricalStockDataError,
    get_historical_stock_data,
)
from app.services.prediction_direction import (
    PredictionDirectionError,
    get_prediction_direction,
)

from app.services.stock_prediction import (
    StockPredictionError,
    get_stock_prediction,
)

router = APIRouter(prefix="/stocks", tags=["stocks"])


SUPPORTED_STOCKS = {
    "LMT": "Lockheed Martin",
    "RTX": "RTX Corporation",
    "NOC": "Northrop Grumman",
    "GD": "General Dynamics",
    "LHX": "L3Harris Technologies",
    "BA": "Boeing",
}


def validate_supported_ticker(ticker: str) -> str:
    symbol = ticker.strip().upper()

    if symbol not in SUPPORTED_STOCKS:
        raise HTTPException(
            status_code=404,
            detail=f"Unsupported stock ticker: {symbol}",
        )

    return symbol


@router.get("")
def list_supported_stocks() -> list[dict[str, str]]:
    """Return the defense-sector stocks supported by the application."""
    return [
        {
            "ticker": ticker,
            "company_name": company_name,
        }
        for ticker, company_name in SUPPORTED_STOCKS.items()
    ]


@router.get("/{ticker}/history")
def stock_history(
    ticker: str,
    time_range: str = Query(default="1Y"),
) -> dict:
    """Return historical data for a supported stock."""
    symbol = validate_supported_ticker(ticker)

    try:
        return get_historical_stock_data(symbol, time_range)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except HistoricalStockDataError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc


@router.get("/{ticker}/prediction-direction")
def stock_prediction_direction(ticker: str) -> dict:
    """Return the predicted movement direction for a supported stock."""
    symbol = validate_supported_ticker(ticker)

    try:
        result = get_prediction_direction(symbol)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except PredictionDirectionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {
        "company_name": SUPPORTED_STOCKS[symbol],
        **result,
    }

@router.get("/{ticker}/prediction")
def stock_prediction(ticker: str) -> dict:
    """Generate ML stock-price predictions for a supported stock."""
    symbol = validate_supported_ticker(ticker)

    try:
        result = get_stock_prediction(symbol)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except StockPredictionError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {
        "company_name": SUPPORTED_STOCKS[symbol],
        **result,
    }

@router.get("/{ticker}")
def stock_details(ticker: str) -> dict:
    """Return current market information for a supported stock."""
    symbol = validate_supported_ticker(ticker)

    try:
        result = get_current_stock_info(symbol)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except StockDataError as exc:
        raise HTTPException(status_code=502, detail=str(exc)) from exc

    return {
        "company_name": SUPPORTED_STOCKS[symbol],
        **result,
    }



