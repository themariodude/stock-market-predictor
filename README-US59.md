# US-59 — Run Post-Deployment Smoke Tests

After each deploy, answer one question: did the application we just deployed start and respond?

This is not a feature test. The full test suites cover features.

## What it checks

* Backend `/health` returns 200 with `status: ok` **and** `database: ok`
* Backend `/stocks` returns a list of stocks (no Yahoo Finance call, so Yahoo can't fail it)
* Frontend returns the app page

It waits up to 60 seconds for the backend and database to be ready, because a deploy has just restarted the containers.

## File

* `scripts/smoke_test.py` (Python standard library only, nothing to install)

## Run locally

```
docker compose up -d
python3 scripts/smoke_test.py
```

Expected result:

```
3 of 3 checks passed
```

Exit code is 0 when everything passes and 1 when anything fails, so a deploy job turns red on failure.

## Run against another environment

```
python3 scripts/smoke_test.py --backend-url http://<host>:8000 --frontend-url http://<host>:5173
```

`--wait 30` changes how long it waits for the backend.

## In the deployment pipeline

The `smoke-test` job in `.github/workflows/staging.yml` runs after `deploy` on every push to `develop`, and on manual runs for `staging` or `production`.

It reads the URLs from the target environment's secrets (Settings → Environments):

* `SMOKE_BACKEND_URL` — for example `http://<host>:8000`
* `SMOKE_FRONTEND_URL` — for example `http://<host>:5173`

If either secret is missing, the job fails before sending any request. Both URLs appear as `***` in the log.

A failed smoke test fails the workflow run but does not roll back the deploy. Check the `smoke-test` job log to see which check failed.
