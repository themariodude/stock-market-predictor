"""Security and behavior tests for the staging SSM smoke-test runner."""

import importlib.util
import json
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "scripts"))

spec = importlib.util.spec_from_file_location(
    "smoke_ssm_script", ROOT / "scripts/smoke_ssm.py"
)
smoke = importlib.util.module_from_spec(spec)
spec.loader.exec_module(smoke)

INSTANCE_ID = "i-0123456789abcdef0"


def test_ssm_smoke_success(monkeypatch, capsys):
    calls = []

    def fake_aws(*arguments):
        calls.append(arguments)
        return "command-123" if "send-command" in arguments else "Success"

    monkeypatch.setenv("DEPLOY_INSTANCE_ID", INSTANCE_ID)
    monkeypatch.setattr(smoke, "aws", fake_aws)

    assert smoke.main() == 0
    assert "PASS:" in capsys.readouterr().out

    request = calls[0]
    assert "send-command" in request
    assert "AWS-RunShellScript" in request

    parameters = json.loads(request[request.index("--parameters") + 1])
    commands = parameters["commands"]
    script = "\n".join(commands)

    assert "set +x" in script
    assert "umask 077" in script
    assert "staging-smoke.log" in script
    assert script.index("exec >") < script.index("python3 -")

    assert "com.docker.compose.project=stock-market-predictor" in script
    assert "com.docker.compose.service=frontend" in script
    assert "docker port" in script
    assert script.index("docker port") < script.index("python3 -")
    assert "/api/health" in script
    assert "/api/stocks" in script
    assert "http://127.0.0.1" in script
    assert "'id=\"root\"'" in script

    assert all("StandardOutputContent" not in str(call) for call in calls)
    assert calls[1][calls[1].index("--query") + 1] == "Status"


@pytest.mark.parametrize(
    "invalid_id",
    ["", "i-123", "i-123;whoami", "not-an-instance"],
)
def test_rejects_invalid_instance_id(monkeypatch, invalid_id, capsys):
    monkeypatch.setenv("DEPLOY_INSTANCE_ID", invalid_id)
    monkeypatch.setattr(
        smoke,
        "aws",
        lambda *args: pytest.fail("AWS must not be called"),
    )

    assert smoke.main() == 1
    assert "Invalid or missing" in capsys.readouterr().out


def test_ssm_failure_blocks_release(monkeypatch, capsys):
    monkeypatch.setenv("DEPLOY_INSTANCE_ID", INSTANCE_ID)

    def fake_aws(*arguments):
        return "command-123" if "send-command" in arguments else "Failed"

    monkeypatch.setattr(smoke, "aws", fake_aws)

    assert smoke.main() == 1
    assert "FAIL:" in capsys.readouterr().out


def test_ssm_error_does_not_expose_diagnostics(monkeypatch, capsys):
    monkeypatch.setenv("DEPLOY_INSTANCE_ID", INSTANCE_ID)

    def fake_aws(*arguments):
        raise RuntimeError("private-secret-value")

    monkeypatch.setattr(smoke, "aws", fake_aws)

    assert smoke.main() == 1
    output = capsys.readouterr().out

    assert "FAIL:" in output
    assert "private-secret-value" not in output
