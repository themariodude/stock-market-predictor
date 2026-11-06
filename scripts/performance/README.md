# Backend API performance baseline

## Scenarios

`load_test.py` runs each route independently at concurrency 1, 10, and 25 for
30 seconds. Each scenario maintains up to the selected number of requests in
flight, which makes the run repeatable and makes the concurrency levels
comparable. The routes avoid external market-data providers and state-changing
operations:

| Scenario | Route | Accepted status | Purpose |
| --- | --- | --- | --- |
| `health` | `GET /health` | 200 | Application and database liveness |
| `stocks_list` | `GET /stocks` | 200 | Core stock catalog |
| `model_metrics` | `GET /models/metrics` | 200 or 503 | Model metrics availability behavior |
| `unauthenticated_account` | `GET /auth/me` | 401 | Expected authentication rejection |

For each case the report stores average and p95 latency, throughput, status
counts, and unexpected error rate. A 401 or a documented 503 is reported by
status but is not counted as an unexpected error. Transport failures and any
other status count as errors. Since this runner records endpoint response
latency, server processing, database, and network time are all included.

## Repeat a run

Start the backend and database using the project's normal local setup, then run
from the repository root:

```powershell
python scripts/performance/load_test.py `
  --base-url http://127.0.0.1:8000 `
  --duration 30 `
  --concurrency 1 10 25 `
  --output scripts/performance/results/latest.json
```

Keep the host, backend revision, database configuration, and environment the
same when comparing runs. Use a quiet, dedicated instance; do not point this
write-safe but traffic-generating tool at production without an agreed load
window. Results include the timestamp and URL and should be committed as test
evidence after review. Do not include credentials in the URL.

## Regression rule

Compare each scenario/concurrency pair against the accepted baseline. Treat a
run as a severe regression if p95 is more than 2x baseline, unexpected error
rate exceeds 1%, or throughput falls below 50% of baseline. These are alert
thresholds, not claims of an SLO; investigate a repeat run before attributing a
code regression because host and dependency variance affect results.

## Initial evidence

`results/baseline.json` records the initial measurement attempt and its
environment limitation. It intentionally contains no invented latency values:
the current workspace has no backend process listening on port 8000, and the
Python environment lacks FastAPI. Start the project backend in its configured
environment and run the command above to produce the first numeric baseline.
