# US-56 — Enforce CI Checks Before Merge

The CI workflow supplies the checks. A GitHub ruleset makes those checks mandatory
and requires pull requests into `develop` and `main`. Both parts are necessary:
committing the ruleset JSON does not activate protection on GitHub.

## What this change provides

| File | Purpose |
| --- | --- |
| `.github/workflows/ci.yml` | Runs secret scanning, backend tests/lint, deployment-script tests/lint, and frontend tests/lint/build for PRs into both protected branches |
| `scripts/check_ci_results.py` | Passes only if every required CI job reports success |
| `.github/rulesets/protected-branches.json` | Importable ruleset requiring PRs and passing CI on both branches |
| `scripts/tests/test_ci_results.py` | Tests failure, cancellation, skipped/missing jobs, malformed input, and successful jobs |

The required GitHub check name is **`CI Required Checks`**. Its dependencies are
`secrets-scan`, `backend-checks`, and `frontend-checks`. It runs even when an earlier
job fails, and fails if any dependency fails, is cancelled, is skipped, or is
missing. There are no path filters that could omit checks for a documentation PR.
Frontend CI uses Node 24, matching the existing frontend Docker image.

Keep the workflow's `needs` list and `REQUIRED_JOBS` in the gate script in sync
when adding or renaming a required job. Keep the gate check's display name and
the ruleset's required context in sync if renaming the gate.

## Activate protection on GitHub — repository administrator

This setup does not need AWS credentials or a deployed server. It does need a
repository owner/admin, or a role permitted to manage repository rules. GitHub
plan and repository visibility determine whether rulesets are available.

1. Commit and push this feature branch. Open a PR with base `develop`.
2. Wait for its CI run to finish. Confirm **CI Required Checks** is present and
   green in the PR's checks. Resolve any failed dependency first.
3. In the repository on GitHub, open **Settings → Rules → Rulesets**.
4. Choose **New ruleset → Import a ruleset** and select
   `.github/rulesets/protected-branches.json` from your local checkout. Review any
   existing protections before adding this rule; keep existing protections intact.
5. Confirm the imported configuration:

   | Setting | Required value |
   | --- | --- |
   | Enforcement status | Active |
   | Target branches | `develop` and `main` |
   | Bypass list | Empty, including no administrator or app bypass |
   | Require a pull request before merging | Enabled |
   | Required status checks | `CI Required Checks` |
   | Require branches to be up to date before merging | Enabled |
   | Block force pushes | Enabled |
   | Restrict deletions | Enabled |

6. In the required check's source setting, select **GitHub Actions** when
   available. The JSON leaves the source unspecified because the integration
   binding is selected in GitHub; set it explicitly during this review. Use the
   exact check name shown on the PR, not a workflow title or a deployment check.
7. Click **Create** or **Save changes**, then reopen the ruleset and confirm it
   is active and applies to both branches.

The PR requirement rejects ordinary direct pushes to both branches, including
`main`. No bypass actors are included. Administrators with rule-management
permissions can still edit the rule itself; a committed JSON file cannot prevent
an administrator from changing repository settings.

The template requires a PR but does not require an approving review: its review
count is zero. If the team also wants peer approval, set that count to one or
more in both the JSON and GitHub. Do not enable **Restrict updates** with an empty
bypass list: that separate rule would prevent ordinary PR merges as well.

Do not enable a merge queue with this workflow without first adding and testing
CI support for merge-group events. This configuration uses ordinary PR merges.

## Team merge process

1. Make changes on a feature branch and push it.
2. Open a PR into `develop`, or a production-bound PR into `main`.
3. Wait for CI Required Checks to pass. Fix failures on the feature branch.
4. If the target branch changes, update the feature branch and let CI rerun.
5. Merge through the PR once GitHub reports all required conditions are satisfied.

Deployments are not part of the required CI gate. In this repository, merging
into `develop` separately triggers staging deployment. Coordinate US-60's staging
configuration before merging its deployment changes; US-56 does not configure
AWS or override that requirement.

## Verify the acceptance criteria

Perform behavioral checks on disposable branches and draft PRs, not by pushing
test commits directly to real protected branches. Use an isolated test repository
with the same ruleset targeting its test branches when testing push rejection.

- [ ] `develop` is listed as a targeted branch in an active ruleset.
- [ ] `main` is listed as a targeted branch in that same active ruleset.
- [ ] A draft PR with a deliberate failing frontend test shows a failed frontend
  job and failed CI Required Checks. Inspect the required-check blocker in the
  PR UI; draft status is an additional merge blocker, not evidence of enforcement.
- [ ] Remove the deliberate failure and confirm the tests and gate turn green.
- [ ] Confirm the PR requires its branch to be current with the target branch.
- [ ] Confirm there are no bypass actors and the pull-request rule applies to
  `main`. In an isolated test repository, verify a direct push to a protected test
  branch is rejected and a PR is the available merge path.
- [ ] Record the CI run link and ruleset configuration as nonsecret evidence in
  the story or PR. Do not mark remote protection complete based only on local tests.

## Local verification

From `backend`:

```powershell
.\.venv\Scripts\python.exe -m pytest tests ../scripts/tests -p no:cacheprovider
.\.venv\Scripts\python.exe -m ruff check app tests ../scripts/deploy.py ../scripts/check_ci_results.py ../scripts/tests
.\.venv\Scripts\python.exe -m ruff format --check app tests ../scripts/deploy.py ../scripts/check_ci_results.py ../scripts/tests
```

From `frontend`:

```powershell
npm.cmd test
npm.cmd run lint
npm.cmd run build
```

These checks validate the implementation. Activation and enforcement on GitHub
remain an administrator task until verified against the repository.

References:
[Importing and managing rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/managing-rulesets-for-a-repository),
[Available rules](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/available-rules-for-rulesets),
[Creating rulesets](https://docs.github.com/en/repositories/configuring-branches-and-merges-in-your-repository/managing-rulesets/creating-rulesets-for-a-repository).
