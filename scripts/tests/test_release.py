import importlib.util
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "release_script", ROOT / "scripts/release.py"
)
release = importlib.util.module_from_spec(spec)
spec.loader.exec_module(release)

REPOSITORY = "themariodude/stock-market-predictor"
SHA = "a" * 40
RUN_ID = "12345"
BACKEND = "ghcr.io/themariodude/stock-market-predictor-backend@sha256:" + "b" * 64
FRONTEND = "ghcr.io/themariodude/stock-market-predictor-frontend@sha256:" + "c" * 64


def successful_run(workflow):
    return {
        "status": "completed",
        "conclusion": "success",
        "head_sha": SHA,
        "head_branch": "develop",
        "path": f".github/workflows/{workflow}@refs/heads/develop",
        "event": "push",
        "repository": {"full_name": REPOSITORY},
        "head_repository": {"full_name": REPOSITORY},
    }


def test_registry_digest_comes_from_published_manifest(monkeypatch):
    calls = []

    def fake_run(arguments, **kwargs):
        calls.append(arguments)
        return subprocess.CompletedProcess(
            arguments, 0, '{"digest":"sha256:' + "b" * 64 + '"}', ""
        )

    monkeypatch.setattr(release.subprocess, "run", fake_run)
    assert release.registry_digest(release.image_tag(REPOSITORY, "backend", SHA)) == (
        "sha256:" + "b" * 64
    )
    assert calls[0][:4] == ["docker", "buildx", "imagetools", "inspect"]


def test_release_record_contains_both_immutable_images():
    record = release.release_record(REPOSITORY, SHA, RUN_ID, BACKEND, FRONTEND)
    assert record["source_sha"] == SHA
    assert record["staging_run_id"] == int(RUN_ID)
    assert record["staging_validation"] == "passed"
    assert record["backend_image"] == BACKEND
    assert record["frontend_image"] == FRONTEND


@pytest.mark.parametrize(
    "backend,frontend",
    [
        (BACKEND.replace("@sha256:", ":"), FRONTEND),
        (BACKEND, FRONTEND.replace("themariodude", "other-owner")),
        (BACKEND + ";whoami", FRONTEND),
    ],
)
def test_release_record_rejects_untrusted_images(backend, frontend):
    with pytest.raises(ValueError):
        release.release_record(REPOSITORY, SHA, RUN_ID, backend, frontend)


def test_run_verification_requires_successful_staging_and_ci(monkeypatch):
    def fake_api(path, token):
        assert token == "test-token"
        if f"/runs/{RUN_ID}" in path:
            return successful_run("staging.yml")
        return {"workflow_runs": [successful_run("ci.yml")]}

    monkeypatch.setattr(release, "github_json", fake_api)
    monkeypatch.setattr(
        release.subprocess,
        "run",
        lambda arguments, **kwargs: subprocess.CompletedProcess(arguments, 0),
    )
    release.verify_staging_run(REPOSITORY, SHA, RUN_ID, "test-token")


@pytest.mark.parametrize(
    "change",
    [
        {"conclusion": "failure"},
        {"head_sha": "b" * 40},
        {"head_branch": "feature-branch"},
        {"path": ".github/workflows/other.yml@refs/heads/develop"},
        {"repository": {"full_name": "other/repo"}},
    ],
)
def test_run_verification_rejects_wrong_staging_evidence(monkeypatch, change):
    def fake_api(path, token):
        run = successful_run("staging.yml")
        run.update(change)
        return run

    monkeypatch.setattr(release, "github_json", fake_api)
    with pytest.raises(ValueError, match="Staging run"):
        release.verify_staging_run(REPOSITORY, SHA, RUN_ID, "test-token")


def test_run_verification_rejects_missing_ci_or_main_ancestry(monkeypatch):
    monkeypatch.setattr(
        release,
        "github_json",
        lambda path, token: (
            successful_run("staging.yml")
            if f"/runs/{RUN_ID}" in path
            else {"workflow_runs": []}
        ),
    )
    with pytest.raises(ValueError, match="CI run"):
        release.verify_staging_run(REPOSITORY, SHA, RUN_ID, "test-token")

    monkeypatch.setattr(
        release,
        "github_json",
        lambda path, token: (
            successful_run("staging.yml")
            if f"/runs/{RUN_ID}" in path
            else {"workflow_runs": [successful_run("ci.yml")]}
        ),
    )
    monkeypatch.setattr(
        release.subprocess,
        "run",
        lambda arguments, **kwargs: subprocess.CompletedProcess(arguments, 1),
    )
    with pytest.raises(ValueError, match="main"):
        release.verify_staging_run(REPOSITORY, SHA, RUN_ID, "test-token")


def test_record_verification_rejects_mismatch_and_changed_tag(monkeypatch):
    record = release.release_record(REPOSITORY, SHA, RUN_ID, BACKEND, FRONTEND)
    monkeypatch.setattr(
        release, "image_pair", lambda repository, sha: (BACKEND, FRONTEND)
    )
    assert release.verify_release_record(record, REPOSITORY, SHA, RUN_ID) == (
        BACKEND,
        FRONTEND,
    )
    with pytest.raises(ValueError, match="selected staging run"):
        release.verify_release_record(record, REPOSITORY, SHA, "99999")
    monkeypatch.setattr(
        release, "image_pair", lambda repository, sha: (BACKEND, FRONTEND[:-1] + "d")
    )
    with pytest.raises(ValueError, match="digests"):
        release.verify_release_record(record, REPOSITORY, SHA, RUN_ID)


def test_workflow_separates_staging_build_from_production_promotion():
    workflow = (ROOT / ".github/workflows/staging.yml").read_text(encoding="utf-8")
    build = workflow.split("  build-and-push:\n", 1)[1].split("\n  deploy:\n", 1)[0]
    record = workflow.split("  record-release:\n", 1)[1].split(
        "\n  verify-release:\n", 1
    )[0]
    production = workflow.split("  promote-production:\n", 1)[1]
    assert "if: inputs.environment != 'production'" in build
    assert "- frontend-checks" in build
    assert "- smoke-test" in record
    assert "actions/upload-artifact@v4" in record
    assert "needs: verify-release" in production
    assert "environment: production" in production
    assert "docker build" not in production
    assert "scripts/deploy.py --environment production" in production
    assert "actions/download-artifact@v4" in workflow
