# Backend API contracts

`tests/test_api_contract.py` pins the JSON response fields and JSON types for
the backend's critical stock, prediction, model-metrics, and health routes.
The tests call the FastAPI app through its HTTP test client. External market
data and metrics are replaced with stable fixtures, so the contract suite does
not need a database, network access, or a market-data provider account.

The response key sets are checked exactly. A removed, renamed, or added field
requires an intentional update to the tests and this document. Nullable values
are called out below and are type-checked when present.

## Success responses

| Route | Status | Response fields and types |
| --- | --- | --- |
| `GET /health` | `200` | `status: string`; `database: string` (`ok`, `error`, or `unconfigured`) |
| `GET /stocks` | `200` | Array of `{ticker: string, company_name: string}` |
| `GET /stocks/{ticker}` | `200` | `company_name: string`; `ticker: string`; `current_price`, `previous_close`, `price_change`, `percent_change`: number or `null`; `volume`: integer or `null` |
| `GET /stocks/{ticker}/history` | `200` | `ticker`, `time_range`, `period`: string; `count: integer`; `data: array` of `{date: string, open: number, high: number, low: number, close: number, volume: integer}` |
| `GET /stocks/{ticker}/prediction-direction` | `200` | `company_name`, `ticker`, `as_of_date`, `prediction_direction`, `direction_label`, `confidence_label`: string; current/predicted price and change fields: number; `prediction_confidence`, `prediction_uncertainty`: number or `null`; `explanation`: object; `economic_factors`: array |
| `GET /stocks/{ticker}/prediction` | `200` | `company_name`, `ticker`, `model`: string; `training_count`, `test_count`: integer; `dates`: string array; `actual`, `predictions`: number arrays. These arrays have equal length, matching `test_count`. |
| `GET /models/metrics` | `200` | Object with `baseline` and `model` sections; each has numeric `mae` and `rmse` fields |

The prediction-direction `explanation` object contains `method`, `summary`,
`horizon`, `confidence_basis` strings; a `window` object with range and date
strings, numeric closing prices, and an integer closing-price count; a `factors`
array; and string arrays `not_used` and `limitations`. Each factor has string
`name`, `label`, `unit`, and `role`, a numeric or nullable `value`, and nullable
`influence`. Economic factor entries, when present, contain string `id`,
`name`, `unit`, and `published_on`, a numeric `value`, and integer `age_days`.

## Error responses

| Request condition | Status | JSON body |
| --- | --- | --- |
| Unsupported ticker on stock or prediction routes | `404` | `{"detail":"Unsupported ticker: {ticker}"}` |
| Unsupported history range | `400` | `{"detail":"Unsupported time range '{range}'. Supported ranges are: 1M, 3M, 6M, 1Y, 5Y, MAX."}` |
| Market data or prediction service failure | `502` | `{"detail":"{service error message}"}` |
| Model metrics unavailable | `503` | `{"detail":"Model performance metrics are not available."}` |
| Invalid model metrics payload | `502` | `{"detail":"{validation error message}"}` |

## Running and CI

Run the dedicated contract checks from `backend`:

```sh
python -m pytest tests/test_api_contract.py
```

GitHub Actions runs this named step in both `.github/workflows/ci.yml` and
`.github/workflows/staging.yml`, followed by the full backend test suite. The
CI job fails if any status, exact field set, value type, or expected error
response changes without updating the contract.

## Verification result

Local verification for this change: **PASS**. The dedicated contract suite
passed all 10 tests; the full backend suite passed all 267 tests; Ruff lint
passed and all 58 backend app/test files passed the formatting check. Pytest
reported only the existing Starlette deprecation and local cache-permission
warnings.
