# stock-market-predictor
CPSC 491 Stock Market Predictor for defense-sector analysis and forecasting

## Versioned container images

After the secret scan and backend checks pass on a push to `main`, CI builds and
publishes the existing backend and frontend Dockerfiles to GitHub Container
Registry. Each image uses the full source commit SHA:

```text
ghcr.io/themariodude/stock-market-predictor-backend:sha-<full-commit-sha>
ghcr.io/themariodude/stock-market-predictor-frontend:sha-<full-commit-sha>
```

The actual owner and repository name come from `GITHUB_REPOSITORY`, so forked
repositories publish under their own names. Both images include OCI `revision`
and `source` labels. Staging can pin these commit-specific tags to deploy a specific
CI-validated commit. The workflow uses its `GITHUB_TOKEN` with `packages: write`;
no registry credential is stored in the repository. The staging environment
needs read access to the packages if they are private.
