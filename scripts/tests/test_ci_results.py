"""US-56: failed, cancelled, skipped, or missing jobs must block the gate."""

import importlib.util
import itertools
import json
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "ci_gate", ROOT / "scripts/check_ci_results.py"
)
gate = importlib.util.module_from_spec(spec)
spec.loader.exec_module(gate)


@pytest.mark.parametrize(
    "statuses",
    itertools.product(["success", "failure", "cancelled", "skipped"], repeat=3),
)
def test_only_all_successful_jobs_pass(statuses):
    results = {
        job: {"result": status}
        for job, status in zip(gate.REQUIRED_JOBS, statuses, strict=True)
    }
    assert gate.ci_passed(results) is all(status == "success" for status in statuses)


@pytest.mark.parametrize("missing_job", gate.REQUIRED_JOBS)
def test_missing_required_job_fails(missing_job):
    results = {
        job: {"result": "success"} for job in gate.REQUIRED_JOBS if job != missing_job
    }
    assert not gate.ci_passed(results)


@pytest.mark.parametrize("results", [None, [], True, {}, {"backend-checks": "success"}])
def test_malformed_results_fail(results):
    assert not gate.ci_passed(results)


@pytest.mark.parametrize("payload", ["", "invalid json", "null", "[]", "{}"])
def test_cli_fails_for_missing_or_invalid_results(monkeypatch, capsys, payload):
    monkeypatch.setenv("CI_JOB_RESULTS", payload)
    assert gate.main() == 1
    assert "CI gate failed" in capsys.readouterr().out


def test_cli_succeeds_for_all_required_checks(monkeypatch, capsys):
    results = {job: {"result": "success"} for job in gate.REQUIRED_JOBS}
    monkeypatch.setenv("CI_JOB_RESULTS", json.dumps(results))
    assert gate.main() == 0
    assert "All required CI checks passed" in capsys.readouterr().out
