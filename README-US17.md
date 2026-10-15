# US-17 — Understand Prediction Factors

As an investor, I want to see the major factors associated with a prediction so that the forecast is not presented as an unexplained black-box result.

## What the forecast uses

The stock page forecast (`/stocks/{ticker}/prediction-direction`) uses only the last month (`1M`) of daily closing prices:

* **Recent trend:** average daily change → sets the direction and predicted price
* **Daily volatility:** typical daily swing → larger swings lower the confidence score

Confidence measures how strong the trend is compared with daily swings. It is not the probability that the forecast is correct.

Trading volume and economic indicators are not forecast inputs. Economic indicators are shown as market context only.

## Response

`/prediction-direction` now includes an `explanation` object. Existing fields are unchanged.

* `method`, `summary`, `horizon`: how the forecast is made
* `window`: dates and closing prices of the period used
* `factors`: each input with its `value`, `unit`, and `role` (`influence` is reserved for a future trained model and is `null`)
* `confidence_basis`, `not_used`, `limitations`: what the forecast does and doesn't consider

## Files

* `backend/app/services/prediction_direction.py`
* `backend/tests/test_prediction_direction.py`
* `frontend/src/pages/StockDetail.jsx`

## Run tests

```
docker compose exec backend pytest tests/test_prediction_direction.py tests/test_stocks_api.py
```

Expected result:

```

```

## Test real data

```
curl -s http://localhost:8000/stocks/LMT/prediction-direction | python3 -m json.tool
```

Prints the LMT forecast with the `explanation` object.

## Not included

* The SCRUM-20 model (`/stocks/{ticker}/prediction`): no page uses it, and its inputs (open, high, low, close, volume) move together too closely to give meaningful per-factor results.
* Ranked share of influence across multiple factors: needs a trained model and is planned as a follow-up ticket.
