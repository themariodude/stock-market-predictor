# SCRUM-101 — Container image verification

Tested October 15, 2026 against a real `develop` staging candidate.

- Source commit: `466db6bde47e3305a73ca2596cfe1a644abe90bb`
- [Successful staging run](https://github.com/themariodude/stock-market-predictor/actions/runs/38824774683): `build-and-push`, `deploy`, and `smoke-test` all succeeded.
- [Successful CI push run](https://github.com/themariodude/stock-market-predictor/actions/runs/38824774701): same commit on `develop`.

| Case | Expected | Actual | Result |
| --- | --- | --- | --- |
| TC-101-01: candidate | Staging builds and deploys the selected SHA successfully | Both image publishing and staging smoke test jobs succeeded | Pass |
| TC-101-02: backend tag and digest | SHA tag and immutable digest resolve | Manifest HTTP 200; manifest bytes hash to `sha256:1a05703a341fe745f2ab51f52d145bc4691d2c0ca3d01799c03563bc2050e394`; digest reference also returned 200 | Pass |
| TC-101-03: frontend tag and digest | SHA tag and immutable digest resolve | Manifest HTTP 200; manifest bytes hash to `sha256:b450ed4e31ce78de7bbccd6960de6399b645b5ea38a3cee4a7d51560560629bd`; digest reference also returned 200 | Pass |
| TC-101-04: registry pull access | Both images' config and layers are retrievable without corruption | Anonymous GHCR pull scope succeeded; backend config plus 9 layers (203,080,481 bytes) and frontend config plus 8 layers (117,135,005 bytes) downloaded; every blob matched its declared size and SHA-256 digest | Pass |
| TC-101-05: deployment compatibility | Expected image architecture, ports, and startup commands are present | Both configs are `linux/amd64`; backend exposes `8000/tcp` and starts Uvicorn; frontend exposes `5173/tcp` and starts Vite. Compose references both images with `${IMAGE_TAG}`; staging sets it to the source SHA. | Pass |
| TC-101-06: missing tag | A nonexistent test tag fails cleanly | Backend `scrum-101-nonexistent-20261015-466db6b` returned HTTP 404 | Pass |

The tracked staging Compose file and `.env.staging.example` define the image
selection variables `GHCR_OWNER` and `IMAGE_TAG`, plus the backend and frontend
configuration keys used at deployment. This checks the interface only; protected
host values were not inspected.

## Image references

```text
ghcr.io/themariodude/stock-market-predictor-backend:466db6bde47e3305a73ca2596cfe1a644abe90bb
ghcr.io/themariodude/stock-market-predictor-frontend:466db6bde47e3305a73ca2596cfe1a644abe90bb
ghcr.io/themariodude/stock-market-predictor-backend@sha256:1a05703a341fe745f2ab51f52d145bc4691d2c0ca3d01799c03563bc2050e394
ghcr.io/themariodude/stock-market-predictor-frontend@sha256:b450ed4e31ce78de7bbccd6960de6399b645b5ea38a3cee4a7d51560560629bd
```

## Verification method and limits

GitHub's public Actions API supplied the run and job results. The GHCR Registry
API supplied a scoped anonymous pull token, the two manifests, and each manifest's
config and layers. A local Python HTTP client streamed each blob and checked its
declared length and SHA-256 digest without storing image data. The missing-tag
test sent `HEAD /v2/themariodude/stock-market-predictor-backend/manifests/scrum-101-nonexistent-20261015-466db6b`.

Docker is unavailable on the local verification machine, so a local `docker pull`
or container start was not run. The successful staging `deploy` and `smoke-test`
jobs provide separate evidence that the published images ran in staging. Actual
host environment values and production deployment were outside this test.

On a machine with Docker, repeat the pull check with:

```sh
docker pull ghcr.io/themariodude/stock-market-predictor-backend:466db6bde47e3305a73ca2596cfe1a644abe90bb
docker pull ghcr.io/themariodude/stock-market-predictor-frontend:466db6bde47e3305a73ca2596cfe1a644abe90bb
```
