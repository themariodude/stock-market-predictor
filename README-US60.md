# US-60 — Secure Deployment Credentials and Secrets

Real credentials belong in the deployment host's protected environment file or
GitHub environment secrets. Commit only the example templates. Local development
still supports the public demo login; staging and production require an explicit
signing key and configured investor password hash.

## Repository protections

- Git ignores `.env`, `.env.*`, AWS credential folders, and private key files at
  any directory depth. The `.env*.example` templates remain tracked.
- Docker build contexts exclude private environment files and credential files,
  including files nested under `backend` and `frontend`.
- CI and deployment scan with Gitleaks, including complete Git history, with
  redacted findings. Reports are not posted as comments or uploaded as artifacts.
- Never put secrets in `VITE_*` settings: they are accessible to browser clients.
  `VITE_API_BASE_URL` is a public address, not a credential.

Git ignore rules do not remove files already committed. The tests reject tracked
private environment files. A real credential found in history must be revoked
and replaced before cleaning history; deleting its current file is insufficient.
Do not paste unredacted findings into an issue, PR, or chat.

## Configure GitHub environments

In repository **Settings → Environments**, create `staging` and `production`.
Restrict staging deployments to `develop` and production to `main`. Protect
production with required reviewers where supported by the repository's plan.

Create these **environment secrets** independently in each environment:

| Name | Purpose |
| --- | --- |
| `AWS_ROLE_ARN` | The environment's AWS deployment role |
| `AWS_REGION` | Region containing that environment's instance |
| `DEPLOY_INSTANCE_ID` | That environment's EC2 instance |
| `SMOKE_BACKEND_URL` | That environment's backend URL |
| `SMOKE_FRONTEND_URL` | That environment's frontend URL |

Migrate the old `STAGING_INSTANCE_ID`, `STAGING_BACKEND_URL`, and
`STAGING_FRONTEND_URL` entries to the corresponding names above in the staging
environment. Move deployment entries out of repository-level secrets so missing
environment settings cannot fall back to shared values. `GITHUB_TOKEN` is supplied
automatically and is used only to scan/read the repository and publish images.

Use a separate AWS role for each environment. Configure the GitHub OIDC provider
with audience `sts.amazonaws.com`. Restrict each role's trust policy to the exact
repository and environment, for example:

```json
{
  "StringEquals": {
    "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
    "token.actions.githubusercontent.com:sub": "repo:OWNER/REPOSITORY:environment:staging"
  }
}
```

Use `environment:production` for the production role. The deployment role needs
`ssm:SendCommand` only for `AWS-RunShellScript` and its environment's instance,
and `ssm:GetCommandInvocation` to poll status. Apply resource restrictions where
the AWS API supports them. Do not grant it access to the other environment's
instance. No AWS access key, secret access key, SSH key, or application secret is
needed in the Actions runner.

## Configure the deployment hosts

Use separate staging and production hosts. Each needs Docker Compose v2 with
`up --wait`, the SSM agent and instance role, access to pull the GHCR images, and
the current `docker-compose.staging.yml` at `/opt/stock-market-predictor`.
Despite its historical filename, this Compose definition serves both deployment
environments. Sync this nonsecret file before the first deployment of US-60;
the workflow updates images, not the host checkout.

For staging, provision `/etc/stock-market-predictor/staging.env` from
`.env.staging.example`; for production, use
`/etc/stock-market-predictor/production.env` from `.env.production.example`.
Keep `/etc/stock-market-predictor` root-owned with mode `0700`, and each file
root-owned with mode `0600`. The deploy script rejects missing files, symlinks,
incorrect ownership, and incorrect file permissions.

Replace every placeholder. Generate a different database password, signing key,
investor password/hash, and API key for each environment. Never copy staging's
secret values into production. Keep `POSTGRES_PASSWORD` and the password in
`DATABASE_URL` consistent; URL-encode a database password when it is embedded in
the connection URL. Changing the password in this file does not change an
existing PostgreSQL user's password: rotate that database credential separately.

Generate a signing key locally, outside CI:

```powershell
cd backend
.\.venv\Scripts\python.exe -c "import secrets; print(secrets.token_urlsafe(48))"
```

Generate the investor password hash locally with a hidden password prompt:

```powershell
.\.venv\Scripts\python.exe -c "from getpass import getpass; from app.services.auth import hash_password; print(hash_password(getpass('New investor password: ')))"
```

Transfer generated values through your approved secret-management channel into
the protected host file. Do not add them to this document or a terminal command
in CI. Surround hashes with single quotes in the environment file so Compose
preserves their `$` characters. Keep API keys and signing keys out of frontend
container settings.

Staging and production refuse to start without `AUTH_SECRET_KEY`,
`DEMO_INVESTOR_EMAIL`, and a valid `DEMO_INVESTOR_PASSWORD_HASH`. The signing key
must be at least 32 characters and cannot use the template placeholder. Deployed
plaintext `DEMO_INVESTOR_PASSWORD` is rejected. Development uses a random signing
key per backend process when none is configured, so development sessions expire
after a backend restart.

## Deployment and log behavior

Pushing `develop` deploys staging. For production, manually run **Deployment**
from the `main` branch and select `production`. This adds environment selection
and credential isolation; the existing frontend image still uses Vite's dev
server, so this story does not establish production readiness for the whole app.

The workflow obtains short-lived AWS credentials via OIDC and uses environment
secrets for its target. The runner sends only fixed commands, the environment
name, and a commit SHA through SSM. It never receives application secret values.
The host supplies them to containers from its protected environment file.

The script disables shell tracing before deployment and redirects remote command
output to a root-only directory at
`/var/log/stock-market-predictor/<environment>-deploy.log`. Actions polls only
SSM's status and prints a generic success or failure. Failed AWS command output
is also suppressed. Diagnose failures on the host; do not upload raw deployment
logs, `.env` contents, `docker inspect`, or expanded `docker compose config` to CI.
Treat host diagnostics as sensitive and redact them before sharing.

Database health-check failures log a generic message, without connection URLs or
exception text. GitHub masks its own secrets, but transformed/derived values may
not be masked, so the workflow avoids printing them in the first place.

Keep the existing staging Compose project name `stock-market-predictor` to
preserve its database volume. Production uses `stock-market-predictor-production`.
Both hosts retain their own environment files. Rotating a signing key invalidates
existing login tokens. Restrict and rotate any host-side GHCR read credential
separately; never commit Docker's credential store.

## Verification

From `backend`:

```powershell
.\.venv\Scripts\python.exe -m pytest tests ../scripts/tests -p no:cacheprovider
.\.venv\Scripts\python.exe -m ruff check app tests ../scripts/deploy.py ../scripts/tests
.\.venv\Scripts\python.exe -m ruff format --check app tests ../scripts/deploy.py ../scripts/tests
```

Tests cover deployed startup, missing and invalid secrets, authentication,
credential-safe database logging, separate host files, shell-input rejection,
SSM status-only polling, suppressed AWS errors, Git exclusions, and tracked
environment files. CI additionally runs the full-history Gitleaks scan.

Acceptance on real infrastructure requires an administrator to complete the
GitHub environment and AWS role setup, provision independent host secrets, run
staging, and verify the job logs before authorizing production. Local tests cannot
prove that remote settings exist or that independently supplied values differ.

References: [GitHub environment secrets](https://docs.github.com/en/actions/how-tos/write-workflows/choose-what-workflows-do/use-secrets),
[GitHub OIDC with AWS](https://docs.github.com/en/actions/how-tos/secure-your-work/security-harden-deployments/oidc-in-aws).
