# US-04 — Change Historical Time Range

As an investor, I want to select different historical time ranges so that I can examine short- and long-term stock trends.

## Supported ranges

- 1M
- 3M
- 6M
- 1Y
- 5Y
- MAX

## Files

- `backend/app/services/historical_stock_data.py`
- `backend/tests/test_historical_stock_data.py`

## Run tests

From the repository root:

```bash
cd backend
pytest tests/test_historical_stock_data.py
```

Expected result:

```text
5 passed
```

## Test real market data

From `backend/`:

```bash
PYTHONPATH=. python -c "from app.services.historical_stock_data import get_historical_stock_data; result=get_historical_stock_data('LMT','1M'); print(result['ticker'], result['time_range'], result['count']); print(result['data'][-3:])"
```

The unit tests use mocked data. This command uses the real yfinance data source.
