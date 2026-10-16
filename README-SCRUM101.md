# SCRUM-101: Docker build and configuration failure verification

Verified October 15, 2026 against `develop` at commit
`7870cc0994ce96a744beef9c1f0d4e6abd765e3e`.

The [SCRUM-101 Actions run](https://github.com/themariodude/stock-market-predictor/actions/runs/38831629956)
used a temporary branch at commit `e565dfbfb99d5080d599340fd4c2e9c00a96df46`.
Its validation job ran the checks below on a GitHub-hosted runner. The job and
the repository's backend, frontend, secret-scan, and required-check jobs all
finished successfully. The temporary branch and its workflow change were
deleted after the run; neither is part of this PR.

| Requirement | Check performed | Result |
| --- | --- | --- |
| Backend image builds | `docker build -f infra/docker/Dockerfile.backend -t scrum101-backend:validation .` | Passed |
| Frontend image builds | `docker build -f infra/docker/Dockerfile.frontend -t scrum101-frontend:validation .` | Passed |
| Build failure detected | A Dockerfile containing the invalid instruction `NOT_A_VALID_DOCKERFILE` made `docker build` return a nonzero exit code. | Passed |
| Required configuration verified | `docker compose --env-file /dev/null -f docker-compose.staging.yml config --quiet` returned a nonzero exit code when required settings were absent. | Passed |
| Missing deployed configuration rejected | The built backend image ran `validate_deployment_config()` with only `APP_ENV=staging` and returned a nonzero exit code. | Passed |
| Invalid configuration rejected | The existing `backend/tests/test_deployment_security.py` tests check missing secrets, weak keys, invalid password hashes, and unknown environments. | Passed locally: 12 tests |

The negative Actions steps asserted **nonzero exit status**; the run's public
job summary does not expose the exact error text. The existing backend tests
assert the specific setting names or error types for invalid configuration.
No image was pushed and no environment was deployed by the temporary job.

## Repeat the checks

Run the two `docker build` commands in the table from the repository root.
Then run the existing configuration tests from `backend`:

```sh
python -m pytest tests/test_deployment_security.py -v
```

To repeat the missing Compose configuration check on Linux or a GitHub runner:

```sh
docker compose --env-file /dev/null -f docker-compose.staging.yml config --quiet
```

That last command is expected to fail because the staging Compose file
requires values such as `POSTGRES_PASSWORD`, `APP_ENV`, and `DATABASE_URL`.
The test uses an empty environment file and does not read deployed secrets.
