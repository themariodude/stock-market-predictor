# SCRUM-103: Published container image traceability

Verified October 15, 2026 (Pacific time). The source commit is
[`7870cc0994ce96a744beef9c1f0d4e6abd765e3e`](https://github.com/themariodude/stock-market-predictor/commit/7870cc0994ce96a744beef9c1f0d4e6abd765e3e),
the current `develop` head at verification time. Its
[staging Actions run](https://github.com/themariodude/stock-market-predictor/actions/runs/38831438588)
completed `backend-checks`, `build-and-push`, `deploy`, and `smoke-test`
successfully. The existing staging workflow tags both images with
`${{ github.sha }}` from that run.

| Image | Published tag | Verified manifest digest | Retrieved data |
| --- | --- | --- | --- |
| `ghcr.io/themariodude/stock-market-predictor-backend` | `7870cc0994ce96a744beef9c1f0d4e6abd765e3e` | `sha256:7d66db191cd4a19c05b213bd85d1eaef09b4bc7ec13353e6aa959182d31ec314` | Config and 9 layers; 203,083,394 bytes |
| `ghcr.io/themariodude/stock-market-predictor-frontend` | `7870cc0994ce96a744beef9c1f0d4e6abd765e3e` | `sha256:b5b9772e64b57df69f78052c0c37f4529e3cadd03af13adf6c6bcc82d28c4faa` | Config and 8 layers; 117,136,068 bytes |

## Verification results

- **Tags:** Both full-SHA tags resolved to HTTP 200 manifests in GHCR.
- **Retrieval and integrity:** A scoped anonymous GHCR pull token retrieved each
  manifest, config blob, and layer. Every blob matched its declared byte size
  and SHA-256 digest. The manifest bytes hashed to the digest in the table, and
  fetching each manifest again by that digest returned identical bytes.
- **Commit traceability:** The run's `head_sha` equals the Git commit and both
  image tags. The workflow uses that SHA for both image builds, pushes, and the
  staging deployment. Its deploy and smoke-test jobs succeeded after the push.

No local Docker CLI was available, so retrieval was verified through the GHCR
Registry API rather than `docker pull`. To repeat the pull on a Docker host:

```sh
docker pull ghcr.io/themariodude/stock-market-predictor-backend:7870cc0994ce96a744beef9c1f0d4e6abd765e3e
docker pull ghcr.io/themariodude/stock-market-predictor-frontend:7870cc0994ce96a744beef9c1f0d4e6abd765e3e
```

The digests above identify the exact retrieved manifests. These checks verify
the existing `develop` staging publications; they do not publish, rebuild, or
deploy an image.
