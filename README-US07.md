# US-07 - View Prediction Direction

As an investor, I want to see whether the model predicts an upward or downward
movement so that the forecast is easy to interpret.

## Files

- `backend/app/services/prediction_direction.py`
- `backend/app/api/stocks.py`
- `backend/tests/test_prediction_direction.py`
- `backend/tests/test_stocks_api.py`
- `frontend/src/pages/StockDetail.jsx`
- `frontend/src/index.css`

## API

```text
GET /stocks/{ticker}/prediction-direction
```

Returns the normalized ticker, company name, prediction direction, label,
predicted price, predicted change, and predicted percent change.

## Run tests

From the repository root:

```bash
cd backend
pytest tests/test_prediction_direction.py tests/test_stocks_api.py
```
