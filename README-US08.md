# US-08 — Integrate Macroeconomic Data

As an investor, I want stock analysis to incorporate relevant macroeconomic indicators such as inflation, unemployment, and interest rates so that predictions consider factors beyond historical stock prices.

## Indicators (FRED)

* Inflation — `CPIAUCNS` → `cpi_yoy_pct`
* Unemployment — `UNRATE` → `unemployment_rate`
* Interest rate — `DFF` → `fed_funds_rate`

Each value is used only on trading days after it was published (no look-ahead).

## Files

* `backend/app/models/macro.py`
* `backend/alembic/versions/1df55e52506b_create_macro_observations.py`
* `backend/app/services/macro_data.py`
* `backend/app/services/macro_features.py`
* `backend/tests/test_macro_data.py`
* `backend/tests/test_macro_features.py`

## Setup

Add your free FRED key (fred.stlouisfed.org → My Account → API Keys) to `.env`:

```
FRED_API_KEY=your_key_here
```

Then create the table and load the data:

```
docker compose exec backend alembic upgrade head
docker compose exec backend python -m app.services.macro_data
```

## Run tests

```
docker compose exec backend pytest tests/test_macro_data.py tests/test_macro_features.py
```

Expected result:

```
22 passed
```

## Test real data

```
docker compose exec backend python -m app.services.macro_features LMT
```

Prints the last 10 LMT trading days with the macro features attached.

## Defense spending

Investigated (`FDEFX`) and not included this sprint: it is quarterly, published about 30 days after the quarter ends, and revised by up to 1.6% after release.
