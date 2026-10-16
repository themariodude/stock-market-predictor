# US-46 — Receive Useful Error Messages

## Overview

**User Story:**  
As an investor, I want clear feedback when an operation fails so that I know whether I should retry, change my input, or wait for updated data.

US-46 improves backend reliability by validating ticker input and returning controlled, useful error responses instead of allowing invalid requests or internal exceptions to propagate through the application.

## Implementation

Ticker validation is centralized in:

```text
backend/app/services/ticker_validation.py
```

The validator supports the project's current defense-sector tickers:

```text
LMT, RTX, NOC, GD, LHX, BA
```

Ticker input is normalized before validation:

```text
"lmt"     -> "LMT"
" LmT "   -> "LMT"
"AAPL"    -> UnsupportedTickerError
"INVALID" -> UnsupportedTickerError
```

The shared validator is integrated with:

```text
backend/app/services/prediction_direction.py
backend/app/api/stocks.py
```

This ensures unsupported tickers are rejected before historical-data or prediction processing occurs.

At the API layer, `UnsupportedTickerError` is converted into a controlled HTTP `404` response:

```http
GET /stocks/AAPL/prediction-direction
```

```json
{
  "detail": "Unsupported ticker: AAPL"
}
```

Prediction and data-source failures are also handled through controlled HTTP responses rather than exposing internal exceptions.

## Testing

Automated coverage is provided by:

```text
backend/tests/test_ticker_validation.py
backend/tests/test_prediction_direction.py
backend/tests/test_stocks_api.py
```

Tests verify:

- supported and unsupported tickers
- lowercase, mixed-case, and whitespace normalization
- invalid and empty ticker input
- `UnsupportedTickerError` behavior
- HTTP 404 responses for unsupported tickers
- prediction-direction integration
- API health after invalid requests
- existing functionality through regression testing

Run the complete backend test suite with:

```bash
docker compose exec backend python -m pytest
```

Run linting with:

```bash
docker compose exec backend ruff check app tests
```

These tests also run through the project's GitHub Actions CI pipeline.

## Status

- [x] Centralized ticker validation and normalization
- [x] Unsupported ticker detection
- [x] Controlled service-level exceptions
- [x] Prediction-direction integration
- [x] Useful HTTP error responses
- [x] Automated unit and API tests
- [x] Regression and CI coverage
- [ ] Missing-model handling
- [ ] Model-loading failure handling

The final two cases depend on trained-model loading infrastructure that is not currently available. They can be added when the prediction model is integrated with the backend.