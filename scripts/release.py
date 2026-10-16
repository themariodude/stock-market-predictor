"""Record and verify immutable images from a successful staging release."""

import argparse
import json
import os
import re
import subprocess
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

SHA_PATTERN = re.compile(r"[0-9a-f]{40}")
DIGEST_PATTERN = re.compile(r"sha256:[0-9a-f]{64}")
RUN_ID_PATTERN = re.compile(r"[1-9][0-9]*")
REPOSITORY_PATTERN = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9-]*/[a-zA-Z0-9][a-zA-Z0-9_.-]*")


def validate_identifiers(repository: str, sha: str, run_id: str) -> None:
    if not REPOSITORY_PATTERN.fullmatch(repository):
        raise ValueError("Invalid repository.")
    if not SHA_PATTERN.fullmatch(sha):
        raise ValueError("A full source commit SHA is required.")
    if not RUN_ID_PATTERN.fullmatch(str(run_id)):
        raise ValueError("A staging run ID is required.")


def image_tag(repository: str, service: str, sha: str) -> str:
    if service not in {"backend", "frontend"}:
        raise ValueError("Invalid image service.")
    owner = repository.split("/")[0].lower()
    return f"ghcr.io/{owner}/stock-market-predictor-{service}:{sha}"


def image_reference(repository: str, service: str, digest: str) -> str:
    if service not in {"backend", "frontend"} or not DIGEST_PATTERN.fullmatch(digest):
        raise ValueError("Invalid image digest.")
    owner = repository.split("/")[0].lower()
    return f"ghcr.io/{owner}/stock-market-predictor-{service}@{digest}"


def registry_digest(tag: str) -> str:
    result = subprocess.run(
        [
            "docker",
            "buildx",
            "imagetools",
            "inspect",
            tag,
            "--format",
            "{{json .Manifest}}",
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    if result.returncode:
        raise RuntimeError("Unable to inspect a published image.")
    try:
        digest = json.loads(result.stdout)["digest"]
    except (KeyError, TypeError, ValueError) as exc:
        raise ValueError("Registry returned an invalid image manifest.") from exc
    if not isinstance(digest, str) or not DIGEST_PATTERN.fullmatch(digest):
        raise ValueError("Registry returned an invalid image digest.")
    return digest


def image_pair(repository: str, sha: str) -> tuple[str, str]:
    return tuple(
        image_reference(
            repository, service, registry_digest(image_tag(repository, service, sha))
        )
        for service in ("backend", "frontend")
    )


def validate_pair(repository: str, backend: str, frontend: str) -> None:
    owner = repository.split("/")[0].lower()
    for service, image in (("backend", backend), ("frontend", frontend)):
        prefix = f"ghcr.io/{owner}/stock-market-predictor-{service}@"
        if not isinstance(image, str) or not image.startswith(prefix):
            raise ValueError("Image does not belong to the expected repository.")
        digest = image.removeprefix(prefix)
        if not DIGEST_PATTERN.fullmatch(digest):
            raise ValueError("An immutable image digest is required.")


def release_record(
    repository: str, sha: str, run_id: str, backend: str, frontend: str
) -> dict:
    validate_identifiers(repository, sha, run_id)
    validate_pair(repository, backend, frontend)
    return {
        "schema_version": 1,
        "repository": repository.lower(),
        "source_sha": sha,
        "staging_run_id": int(run_id),
        "staging_run_url": f"https://github.com/{repository}/actions/runs/{run_id}",
        "staging_validation": "passed",
        "backend_image": backend,
        "frontend_image": frontend,
    }


def github_json(path: str, token: str) -> dict:
    if not token:
        raise ValueError("GitHub token is required to verify release evidence.")
    request = Request(
        "https://api.github.com" + path,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": f"Bearer {token}",
            "X-GitHub-Api-Version": "2022-11-28",
        },
    )
    try:
        with urlopen(request, timeout=20) as response:
            return json.load(response)
    except (HTTPError, URLError, ValueError) as exc:
        raise RuntimeError("GitHub release evidence could not be verified.") from exc


def is_expected_run(run: dict, repository: str, sha: str, workflow: str) -> bool:
    return (
        run.get("status") == "completed"
        and run.get("conclusion") == "success"
        and run.get("head_sha") == sha
        and run.get("head_branch") == "develop"
        and (run.get("path") or "").split("@")[0] == f".github/workflows/{workflow}"
        and run.get("event") in {"push", "workflow_dispatch"}
        and ((run.get("repository") or {}).get("full_name") or "").lower()
        == repository.lower()
        and ((run.get("head_repository") or {}).get("full_name") or "").lower()
        == repository.lower()
    )


def verify_staging_run(repository: str, sha: str, run_id: str, token: str) -> None:
    validate_identifiers(repository, sha, run_id)
    base = f"/repos/{repository}/actions"
    run = github_json(f"{base}/runs/{run_id}", token)
    if not is_expected_run(run, repository, sha, "staging.yml"):
        raise ValueError("Staging run did not validate the selected commit.")
    ci = github_json(
        f"{base}/workflows/ci.yml/runs?head_sha={sha}&branch=develop&event=push&per_page=100",
        token,
    )
    if not any(
        is_expected_run(candidate, repository, sha, "ci.yml")
        and candidate.get("event") == "push"
        for candidate in ci.get("workflow_runs", [])
    ):
        raise ValueError("The selected commit has no successful required CI run.")
    ancestry = subprocess.run(
        ["git", "merge-base", "--is-ancestor", sha, "HEAD"],
        capture_output=True,
        check=False,
    )
    if ancestry.returncode:
        raise ValueError("The selected staging commit is not contained in main.")


def verify_release_record(
    record: dict, repository: str, sha: str, run_id: str
) -> tuple[str, str]:
    validate_identifiers(repository, sha, run_id)
    expected = {
        "schema_version": 1,
        "repository": repository.lower(),
        "source_sha": sha,
        "staging_run_id": int(run_id),
        "staging_run_url": f"https://github.com/{repository}/actions/runs/{run_id}",
        "staging_validation": "passed",
    }
    if not isinstance(record, dict) or any(
        record.get(key) != value for key, value in expected.items()
    ):
        raise ValueError("Release record does not match the selected staging run.")
    backend, frontend = record.get("backend_image"), record.get("frontend_image")
    validate_pair(repository, backend, frontend)
    current_backend, current_frontend = image_pair(repository, sha)
    if (backend, frontend) != (current_backend, current_frontend):
        raise ValueError("Published image digests no longer match staging evidence.")
    return backend, frontend


def append_outputs(**values: str) -> None:
    output = os.getenv("GITHUB_OUTPUT")
    if not output:
        raise ValueError("GitHub output path is required.")
    with open(output, "a", encoding="utf-8") as handle:
        for key, value in values.items():
            handle.write(f"{key}={value}\n")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "action", choices=["capture", "record", "verify-run", "verify-record"]
    )
    parser.add_argument("--manifest", default="release-candidate.json")
    args = parser.parse_args()
    repository = os.getenv("GITHUB_REPOSITORY", "")
    sha = os.getenv("RELEASE_SHA", os.getenv("GITHUB_SHA", ""))
    run_id = os.getenv("STAGING_RUN_ID", os.getenv("GITHUB_RUN_ID", ""))
    try:
        validate_identifiers(repository, sha, run_id)
        if args.action == "capture":
            backend, frontend = image_pair(repository, sha)
            append_outputs(backend_image=backend, frontend_image=frontend)
        elif args.action == "record":
            record = release_record(
                repository,
                sha,
                run_id,
                os.getenv("BACKEND_IMAGE", ""),
                os.getenv("FRONTEND_IMAGE", ""),
            )
            Path(args.manifest).write_text(
                json.dumps(record, indent=2) + "\n", encoding="utf-8"
            )
        elif args.action == "verify-run":
            verify_staging_run(repository, sha, run_id, os.getenv("GITHUB_TOKEN", ""))
        else:
            record = json.loads(Path(args.manifest).read_text(encoding="utf-8"))
            backend, frontend = verify_release_record(record, repository, sha, run_id)
            append_outputs(backend_image=backend, frontend_image=frontend)
    except (RuntimeError, ValueError, OSError, TypeError):
        print("Release evidence verification failed.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
