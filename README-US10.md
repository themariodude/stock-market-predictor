# US-10 — Handle Data-Source Failures

As an investor, I want the application to clearly indicate when current data cannot be retrieved and use available historical/cached information when appropriate so that I understand when information may be outdated.

This story covers the data layer for FRED macro data (from US-08).

## What happens when FRED fails

* Short outages (timeouts, dropped connections, HTTP 429/5xx) are retried up to 3 times, waiting 2s then 4s.
* If a series still fails, its stored data is kept, the failure is recorded, and the other series continue.
* An error is raised only when a failed series has no stored data at all.
* Bad or empty FRED responses count as failures, never as successes.

## Is the data current?

`macro_freshness()` reports for each series:

* `as_of` — when the newest value was published
* `is_stale` — older than normal for that series (CPI and UNRATE: 45 days, DFF: 5 days)
* `last_fetch_failed` — the latest download failed

The two flags are separate on purpose: monthly data can still be current even when today's download failed.

## Files

* `backend/app/models/source_status.py`
* `backend/alembic/versions/7fbe46751c72_create_data_source_status.py`
* `backend/app/services/data_source.py`
* `backend/app/services/macro_data.py` (updated)
* `backend/tests/test_data_source_failures.py`

## Setup

Create the new `data_source_status` table (existing data is untouched):

```
docker compose exec backend alembic upgrade head
```

## Run tests

```
docker compose exec backend pytest tests/test_data_source_failures.py
```

Expected result:

```
39 passed
```

## Test real data

```
docker compose exec backend python -m app.services.macro_data
docker compose exec backend python -c "from app.database import get_session; from app.services.macro_data import macro_freshness; import pprint; pprint.pprint(macro_freshness(get_session()))"
```

Prints rows written per series, then each series' freshness.

## Not included

Stock price cache: deferred to keep this story focused on macro data. It would reuse the existing `stocks` / `stock_prices` tables, which need their own migration first.
