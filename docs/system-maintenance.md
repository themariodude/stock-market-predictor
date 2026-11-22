
# SCRUM-54 — System Maintenance Runbook

## Purpose

This runbook documents safe, repeatable maintenance procedures for the Stock Market Predictor, including Docker services, PostgreSQL backups and restoration, Alembic migrations, application updates, model verification, and failure recovery.

The goal is to minimize downtime, preserve existing application data, and verify that critical functionality remains available after maintenance.

## 1. Docker Service Maintenance

### Services

| Service | Purpose | Notes |
|---|---|---|
| db | PostgreSQL database | Must be healthy before dependent services start |
| backend | FastAPI application | Provides API endpoints and health checks |
| frontend | React application | Provides the user interface |
| market-monitor | Market alert worker | Requires a healthy database and may create notification records |

The `market-monitor` worker checks for completed market sessions once per hour. It runs monitoring cycles on weekdays starting at 6:00 PM Eastern Time.

Do not start this worker during routine maintenance testing without verifying its notification behavior.

### Inspect Services

Run these commands from the directory containing the Docker Compose configuration:

```bash
docker compose config --services
docker compose ps
docker compose ps -a
```

Expected results:

- `db` reports healthy.
- `backend` reports healthy.
- `frontend` reports running.
- `market-monitor` is inspected separately because it may not be enabled locally.

Inspect service logs:

```bash
docker compose logs --tail=100 backend
docker compose logs --tail=100 db
```

### Start Services

```bash
docker compose up -d db backend frontend
```

Start the market-monitor worker only when authorized:

```bash
docker compose up -d market-monitor
```

### Stop Services

Stop individual services:

```bash
docker compose stop backend
docker compose stop frontend
```

Stop all services:

```bash
docker compose stop
```

Avoid using `docker compose down -v` during routine maintenance because it removes named volumes and may delete PostgreSQL data.

### Restart Services

```bash
docker compose restart backend
docker compose restart frontend
```

Start a previously stopped service:

```bash
docker compose start backend
```

### Verify Service Recovery

```bash
docker compose ps

curl -i http://localhost:8000/health
curl -i http://localhost:8000/ready
```

Expected results:

- PostgreSQL and backend are healthy.
- `/health` returns HTTP 200.
- `/ready` returns HTTP 200 when the database connection is available.
- Frontend remains accessible at http://localhost:5173.

### Troubleshooting

If a service fails:

1. Inspect container status using `docker compose ps -a`.
2. Review logs using `docker compose logs --tail=100 SERVICE_NAME`.
3. Verify PostgreSQL is healthy.
4. Inspect recent configuration and application changes.
5. Avoid deleting database volumes or modifying production data.
6. Follow the failed-update recovery procedure in Section 5.

## 2. PostgreSQL Backup and Restoration

### Create a Backup

From the `backend` directory, create a local backup directory and protect it from other local users:

```bash
mkdir -p ../backups
chmod 700 ../backups
```

Create a timestamped PostgreSQL backup:

```bash
umask 077
docker compose exec -T db pg_dump -U smp -d smp -Fc > "../backups/smp-maintenance-$(date +%Y%m%d-%H%M%S).dump"
```

Expected result:

- A PostgreSQL custom-format backup archive is created.
- The active `smp` database is not modified.

Database backups may contain user information. Keep them local, restrict permissions, and never commit them to Git or attach them to Jira.

The repository's `.gitignore` must include:

```gitignore
# Local database backups
/backups/
```

Verify exclusion:

```bash
git check-ignore -v ../backups/BACKUP_FILENAME.dump
```

### Verify the Backup Archive

Replace `BACKUP_FILENAME.dump` with the actual filename:

```bash
docker compose exec -T db pg_restore -l < ../backups/BACKUP_FILENAME.dump
```

Expected result:

- PostgreSQL displays the archive contents.
- No archive-reading error occurs.

Archive inspection alone is not sufficient to prove successful recovery. Restoration must also be tested.

### Restore Into an Isolated Database

Never overwrite the active `smp` database during routine verification.

Create a new test database:

```bash
docker compose exec -T db createdb -U smp smp_maintenance_test
```

Restore the verified archive:

```bash
docker compose exec -T db pg_restore -U smp -d smp_maintenance_test --exit-on-error < ../backups/BACKUP_FILENAME.dump
```

Expected result:

- Restoration completes without errors.
- The test database receives the backed-up schema and records.
- The original database remains untouched.

If the test database already exists, use a different unused name. Do not restore into an existing populated database.

### Verify Restored Tables

Inspect the original database:

```bash
docker compose exec -T db psql -U smp -d smp -c "SELECT COUNT(*) AS tables FROM information_schema.tables WHERE table_schema = 'public';"
```

Inspect the restored database:

```bash
docker compose exec -T db psql -U smp -d smp_maintenance_test -c "SELECT COUNT(*) AS tables FROM information_schema.tables WHERE table_schema = 'public';"
```

Compare user record counts:

```bash
docker compose exec -T db psql -U smp -d smp -c "SELECT COUNT(*) FROM users;"
docker compose exec -T db psql -U smp -d smp_maintenance_test -c "SELECT COUNT(*) FROM users;"
```

For stronger data-integrity verification, compare exact record counts for every table, rather than relying solely on PostgreSQL's estimated statistics.

### Verified Backup and Restoration Test

Date: November 19, 2026

Environment: Local Docker Compose

- Original database: `smp`
- Backup: `smp-maintenance-20261119-175604.dump`
- Backup size: approximately 74 KB
- Restoration database: `smp_maintenance_test`
- Original tables: 9
- Restored tables: 9
- Original user records: 4
- Restored user records: 4
- Original economic observations: approximately 6,570
- Restored economic observations: approximately 6,570
- PostgreSQL archive inspection: passed
- Isolated restoration: completed without reported errors
- Alembic version: matched between databases

The recorded row counts were based partly on PostgreSQL statistics and therefore should be treated as estimates rather than proof of row-by-row equality.

## 3. Alembic Migration Maintenance

### Purpose

Alembic manages database schema changes. Maintenance procedures must verify the current migration state before applying changes.

Do not run migrations on a shared staging or production database without coordination, a verified backup, and an approved maintenance plan.

### Inspect Current Migration Versions

Check the active database:

```bash
docker compose exec -T db psql -U smp -d smp -c "SELECT version_num FROM alembic_version;"
```

Check the isolated restoration database:

```bash
docker compose exec -T db psql -U smp -d smp_maintenance_test -c "SELECT version_num FROM alembic_version;"
```

Inspect Alembic history from the backend environment:

```bash
python -m alembic history
python -m alembic heads
python -m alembic current
```

Note: `alembic current` reports the database configured in the active Alembic environment. It does not automatically inspect the isolated test database.

### Safe Migration Procedure

1. Identify the current database migration version.
2. Review pending migration scripts and dependencies.
3. Create and verify a database backup.
4. Restore the backup into an isolated database.
5. Configure Alembic to use the isolated database.
6. Confirm the configured connection does not target the active `smp` database.
7. Run pending migrations only against the isolated database.
8. Verify the resulting migration version and expected tables.
9. Run database and application regression tests.
10. Request approval before applying migrations to shared staging or production environments.

Example commands, only after confirming that Alembic is configured for the isolated database:

```bash
python -m alembic current
python -m alembic upgrade head
python -m alembic current
```

Never assume that changing a shell variable automatically redirects Alembic. Verify how the project's `alembic/env.py` obtains its database connection first.

### Verified Migration State

On November 19, 2026, both the original and restored databases reported:

```text
1c969e1fde6f
```

This demonstrates that the backup preserved the recorded Alembic migration version.

Limitation: Applying a pending migration to an isolated database has not yet been demonstrated as part of this maintenance test.

## 4. Application and Model Verification

### Post-Maintenance Health Checks

```bash
docker compose ps

curl -i http://localhost:8000/health
curl -i http://localhost:8000/ready
```

Expected results:

- Backend reports healthy.
- PostgreSQL reports healthy.
- Both API health endpoints return HTTP 200.

### Verify Existing User Data

```bash
docker compose exec -T db psql -U smp -d smp -c "SELECT COUNT(*) AS user_count FROM users;"
```

Verified result:

- Four existing user records remained after the controlled backend restart.

### Verify Supported Stock Predictions

The Stock Market Predictor supports six defense-sector tickers:

- LMT — Lockheed Martin
- RTX — RTX Corporation
- NOC — Northrop Grumman
- GD — General Dynamics
- LHX — L3Harris Technologies
- BA — Boeing

Test the momentum prediction endpoint:

```bash
curl -i http://localhost:8000/stocks/LMT/prediction-direction
```

Test the ML prediction endpoint:

```bash
curl -i http://localhost:8000/stocks/LMT/prediction
```

Expected results for fully operational predictions:

- HTTP 200
- Valid prediction data
- Required price fields populated
- No unexpected model or data retrieval errors

### Observed Prediction Limitations

The following observations were recorded during maintenance verification:

**Momentum predictions:**

- LMT returned HTTP 200.
- RTX returned HTTP 200.
- Both returned `FLAT` with null calculated prices and confidence.
- Economic indicators remained available.

**ML prediction:**

- LMT returned HTTP 502.
- The backend logged that yfinance could not retrieve historical LMT pricing data for the requested period.

The log message does not establish that LMT was actually delisted.

The missing prediction data was also observed before the controlled backend restart. There is no evidence establishing that the restart caused the issue.

Live prediction functionality therefore remains an outstanding limitation requiring investigation.

### Automated Prediction Regression Tests

Run from the `backend` directory:

```bash
python -m pytest tests/test_prediction_direction.py tests/test_prediction_explanation.py tests/test_stock_prediction.py tests/test_prediction_validation.py -q
```

Verified result:

```text
53 passed, 1 warning in 2.30s
```

The warning concerned a deprecated dependency interface in Starlette/AnyIO and did not fail the tests.

These tests provide evidence that the covered prediction logic passes regression testing. They do not prove that the external market-data provider is available.

## 5. Failed Update Recovery

### Identify a Failed Update

Possible symptoms include:

- Docker services repeatedly restarting or exiting.
- Backend health checks failing.
- `/ready` returning HTTP 503.
- API endpoints returning unexpected errors.
- Database connectivity failures.
- Missing application or model functionality.

Inspect the environment:

```bash
docker compose ps -a
docker compose logs --tail=100 backend
docker compose logs --tail=100 db
```

### Recover From a Service Failure

1. Stop further maintenance changes.
2. Record the failed operation and relevant error messages.
3. Verify the database is healthy.
4. Check the application's environment and service dependencies.
5. Restart only the affected service when appropriate.
6. Recheck `/health` and `/ready`.
7. Run critical API and user-data verification tests.

Example:

```bash
docker compose restart backend
docker compose ps backend
curl -i http://localhost:8000/ready
```

### Recover From a Failed Application Update

1. Stop the failed rollout.
2. Identify the previously working application image or Git release.
3. Preserve database volumes and backups.
4. Review compatibility between the prior application and the current database schema.
5. Restore the previously working application image using the approved deployment procedure.
6. Verify service health, database connectivity, and critical functionality.
7. Record the failure and recovery results.

For staging and production deployments, use the team's approved immutable image references and deployment configuration.

Do not assume that rolling back application code also rolls back database migrations.

### Recover From a Database Failure

1. Stop application changes that could worsen the failure.
2. Preserve the current database and diagnostic information.
3. Identify a verified PostgreSQL backup.
4. Restore the backup into an isolated environment first.
5. Verify the schema, migration state, and required application records.
6. Coordinate any recovery of the active database with the team.
7. Recheck application and model functionality after recovery.

Never overwrite the active database or delete PostgreSQL volumes without an approved recovery plan.

### Escalation

Escalate to the development or deployment team when:

- PostgreSQL cannot recover.
- Migration results are inconsistent.
- Data integrity is uncertain.
- Application rollback is incompatible with the database schema.
- Critical API or prediction functionality remains unavailable.

Do not continue a failed deployment solely because Docker containers appear healthy.

## 6. Maintenance Testing Evidence

### Test Environment

- Application: Stock Market Predictor
- Story: SCRUM-54 / US-49
- Environment: Local development
- Platform: Docker Compose, FastAPI, PostgreSQL
- Date: November 19, 2026

### Verification Summary

| Test | Result | Evidence |
|---|---|---|
| Docker service discovery | Passed | Four configured services |
| Docker health inspection | Passed | Backend and database healthy |
| Controlled backend restart | Passed | Backend returned to healthy state |
| Pre-maintenance readiness | Passed | HTTP 200 |
| Post-maintenance readiness | Passed | HTTP 200 |
| PostgreSQL backup | Passed | 74 KB custom-format archive |
| Backup archive inspection | Passed | pg_restore archive listing |
| Isolated database restoration | Passed | Restored into smp_maintenance_test |
| Table verification | Passed | 9 tables in both databases |
| Estimated record comparison | Passed | Matching estimates |
| User data count after restart | Passed | 4 users retained |
| Alembic version comparison | Passed | Matching version 1c969e1fde6f |
| Isolated migration upgrade | Not yet tested | Requires verified isolated Alembic configuration |
| Momentum prediction endpoint | Partial | HTTP 200 with missing calculated values |
| ML prediction endpoint | Failed | HTTP 502 due to historical data retrieval failure |
| Prediction regression tests | Passed | 53 tests passed, 1 warning |
| Market-monitor restart | Not tested | Notification side effects avoided |
| Full deployment rollback | Not tested | Requires separate approved recovery exercise |

### Outstanding Limitations

1. Live market-data retrieval prevents successful ML predictions in the tested environment.
2. Momentum predictions return null price and confidence values for the tested defense stocks.
3. An actual Alembic upgrade has not been performed against the isolated test database.
4. The market-monitor worker was intentionally not started to avoid unintended notifications.
5. Full application rollback and active database recovery have not been demonstrated.
6. The evidence verifies local maintenance operations, not production availability or zero-downtime deployment.

### Jira Evidence Requirements

Attach sanitized screenshots or terminal transcripts showing:

- Docker container status before and after maintenance.
- Backup file creation and archive verification.
- Successful restoration into the isolated test database.
- Original and restored table counts.
- Matching Alembic migration versions.
- HTTP 200 readiness before and after restart.
- Preserved user record count.
- Prediction regression test results.
- Documented prediction failure and known limitations.

Include timestamps and the environment used.

Do not attach database dumps, credentials, API keys, or sensitive user records.

### Completion Criteria

SCRUM-54 can be considered complete when:

- Maintenance procedures are documented and reviewed.
- Required representative maintenance and recovery operations have been tested.
- Database preservation and restoration evidence is available.
- Critical application functionality is verified or outstanding failures are explicitly reviewed and accepted.
- Remaining limitations are documented.
- Timestamped evidence is attached to Jira.
- The completed runbook is submitted through a pull request targeting `develop`.
