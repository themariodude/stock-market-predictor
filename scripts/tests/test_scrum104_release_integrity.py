"""SCRUM-104: verify the handoff from staging evidence to production images."""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]


def load_script(name):
    spec = importlib.util.spec_from_file_location(name, ROOT / f"scripts/{name}.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


release = load_script("release")
deployment = load_script("deploy")
REPOSITORY = "themariodude/stock-market-predictor"
SHA = "a" * 40
RUN_ID = "12345"
BACKEND = "ghcr.io/themariodude/stock-market-predictor-backend@sha256:" + "b" * 64
FRONTEND = "ghcr.io/themariodude/stock-market-predictor-frontend@sha256:" + "c" * 64


def test_recorded_staging_pair_is_the_exact_production_pair(tmp_path, monkeypatch):
    """A serialized staging record selects both production images by digest."""
    manifest = tmp_path / "release-candidate.json"
    for name, value in {
        "GITHUB_REPOSITORY": REPOSITORY,
        "GITHUB_SHA": SHA,
        "GITHUB_RUN_ID": RUN_ID,
        "BACKEND_IMAGE": BACKEND,
        "FRONTEND_IMAGE": FRONTEND,
    }.items():
        monkeypatch.setenv(name, value)
    monkeypatch.setattr(
        sys, "argv", ["release.py", "record", "--manifest", str(manifest)]
    )

    assert release.main() == 0
    record = json.loads(manifest.read_text(encoding="utf-8"))
    assert record["source_sha"] == SHA
    assert record["staging_run_id"] == int(RUN_ID)
    assert record["staging_validation"] == "passed"

    lookups = []

    def published_pair(repository, sha):
        lookups.append((repository, sha))
        return BACKEND, FRONTEND

    monkeypatch.setattr(release, "image_pair", published_pair)
    approved_pair = release.verify_release_record(record, REPOSITORY, SHA, RUN_ID)
    assert lookups == [(REPOSITORY, SHA)]
    assert approved_pair == (BACKEND, FRONTEND)

    commands = deployment.deployment_commands("production", SHA, *approved_pair)
    script = "\n".join(commands)
    assert f"export BACKEND_IMAGE={BACKEND} FRONTEND_IMAGE={FRONTEND}" in script
    assert f'"{BACKEND}"' in script and f'"{FRONTEND}"' in script
    assert script.count("docker inspect") == 2
    assert "docker build" not in script
    assert "docker push" not in script


@pytest.mark.parametrize("changed_service", ["backend_image", "frontend_image"])
def test_changed_registry_digest_blocks_promotion(monkeypatch, changed_service):
    record = release.release_record(REPOSITORY, SHA, RUN_ID, BACKEND, FRONTEND)
    current = dict(backend_image=BACKEND, frontend_image=FRONTEND)
    current[changed_service] = current[changed_service][:-1] + "d"
    monkeypatch.setattr(
        release,
        "image_pair",
        lambda repository, sha: (current["backend_image"], current["frontend_image"]),
    )

    with pytest.raises(ValueError, match="digests no longer match"):
        release.verify_release_record(record, REPOSITORY, SHA, RUN_ID)
