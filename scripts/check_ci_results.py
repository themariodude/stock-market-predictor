"""Report success only when every required CI job completed successfully."""

import json
import os
import sys

REQUIRED_JOBS = ("secrets-scan", "backend-checks", "frontend-checks")


def ci_passed(results: object) -> bool:
    if not isinstance(results, dict):
        return False
    return all(
        isinstance(results.get(job), dict) and results[job].get("result") == "success"
        for job in REQUIRED_JOBS
    )


def main() -> int:
    try:
        results = json.loads(os.getenv("CI_JOB_RESULTS", ""))
    except ValueError:
        results = None
    if not ci_passed(results):
        print("CI gate failed: every required job must finish successfully.")
        return 1
    print("All required CI checks passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
