# SCRUM-104: Production artifact promotion and release integrity

Status: local verification in progress. [SCRUM-89 PR #58](https://github.com/themariodude/stock-market-predictor/pull/58)
merged into `develop` at `917013ac97b93f418babf5d83a4d2160799bc89d`.
No production deployment was requested.

The first [post-merge staging run](https://github.com/themariodude/stock-market-predictor/actions/runs/38833910894)
passed its checks and `build-and-push`, but the `deploy` job failed. As a result,
`smoke-test` and `record-release` were skipped, and the run has **zero release
artifacts**. Its public job result identifies the failed SSM deployment step;
the protected host log must be inspected by the deployment owner to identify
the cause. The updated Compose file on the host is one prerequisite to check.

## Verified locally

The SCRUM-104 test in `scripts/tests/test_scrum104_release_integrity.py`
serializes a staging release record, verifies the recorded backend and frontend
digest references against a simulated registry result, and passes those exact
references to the production deployment command builder. It confirms that the
command pulls and checks both approved images and contains no build or push.
Separate negative cases reject a changed backend or frontend registry digest.

The existing SCRUM-89 tests also check successful staging and CI runs, `main`
ancestry, matching release metadata, digest-only production references, and
workflow ordering. Run from `backend`:

```sh
python -m pytest ../scripts/tests -q
ruff check ../scripts/deploy.py ../scripts/release.py ../scripts/tests
ruff format --check ../scripts/deploy.py ../scripts/release.py ../scripts/tests
```

Result on October 15, 2026: **110 tests passed**; Ruff lint and formatting
passed. These tests mock GitHub, the registry, and AWS; they establish the
handoff logic but are not evidence of a live promotion.

## Evidence needed to finish the card

After staging deployment is repaired and the merged workflow runs successfully,
record:

1. The approved staging run URL, its full `head_sha`, successful CI run, and
   `staging-release-<run-id>` artifact containing `release-candidate.json`.
2. The artifact's `backend_image` and `frontend_image` digest references, plus
   the registry digests for the corresponding SHA tags.
3. Confirmation from the release owner that the protected `production`
   environment, required reviewers, AWS access, and production smoke-test URLs
   are ready before a live dispatch from `main`.
4. The authorized production workflow run URL and successful verification,
   approval, deployment, and smoke-test jobs. Compare the two digest references
   passed to production with the staging record; both must match exactly.

Until those run and artifact links exist, **approved staging artifact,
staging-to-production digest equality, and production release evidence remain
unverified**. Do not mark SCRUM-104 complete based only on the local tests.
