# SCRUM-89 — Promote Tested Releases to Production

The existing **Deployment** workflow builds backend and frontend images on a
`develop` staging run. Both images use the same full source commit SHA as their
GHCR tag. After required backend, frontend, and secret checks, staging deploys
the registry digests of those images and runs the existing smoke tests. Only
after the smoke tests pass does the workflow upload a `staging-release-<run-id>`
artifact containing `release-candidate.json`. The record contains the source
SHA, staging run ID and URL, and both immutable `@sha256:` image references.

## Select a tested candidate

Find a **successful** Deployment run for `develop` in GitHub Actions. Record its
full `head_sha` and numeric run ID. Confirm that the separate **CI** workflow
also succeeded for that commit. The candidate commit must be included in the
`main` history before it can be promoted. The workflow requests 90 days of
artifact retention; repository policy may allow less. An expired or missing
artifact cannot be promoted.

From the `main` branch, manually run **Deployment** with:

- `environment`: `production`
- `release_sha`: the staging run's full 40-character source SHA
- `staging_run_id`: the successful staging Deployment run ID

The production path checks the staging run, successful CI on `develop`, commit
ancestry in `main`, the downloaded release record, and the current GHCR tag
digests. It fails if either image has disappeared or its SHA tag now resolves
to a different digest. After those checks, GitHub's `production` environment
gate applies. The production job deploys the recorded backend and frontend
digests through the existing SSM script and runs smoke tests. It contains no
Docker build or image push. The SSM script confirms the running containers
were created from the approved digest references.

Example image references:

```text
ghcr.io/OWNER/stock-market-predictor-backend@sha256:<64 hex characters>
ghcr.io/OWNER/stock-market-predictor-frontend@sha256:<64 hex characters>
```

The record's `source_sha` maps both images to the staged Git commit. The
production workflow run identifies the release request and environment approval.

## Required configuration

An administrator must restrict the `production` GitHub environment to `main`
and configure required reviewers before authorizing a live promotion. Keep its
AWS OIDC role, EC2 instance, smoke-test URLs, and application secrets separate
from staging, as described in [US-60](README-US60.md). The workflow needs
`actions: read` to inspect runs and download the staging artifact,
`packages: read` to inspect GHCR images, and `id-token: write` only for the
production deployment job. The host needs secure GHCR read access if packages
are private.

Install the updated `docker-compose.staging.yml` on **both** hosts at
`/opt/stock-market-predictor` before the first digest-pinned run. The workflow
does not update that host file. Existing protected environment files remain in
`/etc/stock-market-predictor`; the deploy script supplies the selected digest
references only for the duration of its command. A tag-only staging command
remains supported for local/backward compatibility; production rejects it.

Local validation can verify release selection, digest matching, SSM command
construction, and workflow structure. It does not prove GitHub environment
rules, GHCR permissions, AWS roles, or a live production deployment. Release
owner approval is required before a live production dispatch.
