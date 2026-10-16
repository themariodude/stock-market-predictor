import importlib.util
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location(
    "deploy_script", ROOT / "scripts/deploy.py"
)
deployment = importlib.util.module_from_spec(spec)
spec.loader.exec_module(deployment)

BACKEND_IMAGE = "ghcr.io/themariodude/stock-market-predictor-backend@sha256:" + "b" * 64
FRONTEND_IMAGE = (
    "ghcr.io/themariodude/stock-market-predictor-frontend@sha256:" + "c" * 64
)


@pytest.mark.parametrize("environment", ["staging", "production"])
def test_remote_deploy_uses_separate_protected_files(environment):
    commands = deployment.deployment_commands(
        environment, "a" * 40, BACKEND_IMAGE, FRONTEND_IMAGE
    )
    script = "\n".join(commands)
    assert f"/etc/stock-market-predictor/{environment}.env" in script
    assert f"export APP_ENV={environment}" in script
    assert "stat -c %a" in script and "= 600" in script
    assert "stat -c %u" in script and "= 0" in script
    assert script.index("exec >") < script.index("docker compose")
    assert "--wait" in script
    assert "sed -i" not in script
    assert "AUTH_SECRET_KEY" not in script
    assert f"BACKEND_IMAGE={BACKEND_IMAGE}" in script
    assert f"FRONTEND_IMAGE={FRONTEND_IMAGE}" in script
    assert "docker inspect" in script


@pytest.mark.parametrize("environment", ["staging", "production"])
def test_database_migrations_run_before_application_deployment(environment):
    commands = deployment.deployment_commands(
        environment, "a" * 40, BACKEND_IMAGE, FRONTEND_IMAGE
    )

    pull_index = next(
        i for i, command in enumerate(commands) if "pull --quiet" in command
    )
    db_index = next(
        i
        for i, command in enumerate(commands)
        if "up -d --wait --wait-timeout 180 db" in command
    )
    migration_index = next(
        i
        for i, command in enumerate(commands)
        if "python -m alembic upgrade head" in command
    )
    deploy_index = next(
        i
        for i, command in enumerate(commands)
        if "up -d --remove-orphans --wait" in command
    )

    assert pull_index < db_index < migration_index < deploy_index
    assert (
        commands.count(
            next(command for command in commands if "alembic upgrade head" in command)
        )
        == 1
    )

    # A failed migration must stop the remote shell before application startup.
    assert "set -eu" in commands


@pytest.mark.parametrize(
    "environment,sha", [("bad", "a" * 40), ("staging", "a;whoami")]
)
def test_deploy_rejects_shell_injection(environment, sha):
    with pytest.raises(ValueError):
        deployment.deployment_commands(environment, sha)


def test_production_rejects_tag_only_promotion():
    # Production must require approved immutable image references.
    with pytest.raises(ValueError):
        deployment.deployment_commands("production", "a" * 40)


@pytest.mark.parametrize(
    "backend,frontend",
    [
        (BACKEND_IMAGE, None),
        (BACKEND_IMAGE.replace("sha256:", "tag:"), FRONTEND_IMAGE),
        (BACKEND_IMAGE + ";whoami", FRONTEND_IMAGE),
        (BACKEND_IMAGE, FRONTEND_IMAGE.replace("themariodude", "other-owner")),
        (FRONTEND_IMAGE, BACKEND_IMAGE),
    ],
)
def test_production_rejects_missing_or_untrusted_images(backend, frontend):
    with pytest.raises(ValueError):
        deployment.deployment_commands("production", "a" * 40, backend, frontend)


def test_staging_preserves_tag_fallback():
    commands = deployment.deployment_commands("staging", "a" * 40)
    assert "BACKEND_IMAGE" not in "\n".join(commands)


def test_deploy_reports_success_without_requesting_remote_output(monkeypatch, capsys):
    calls = []

    def fake_aws(*arguments):
        calls.append(arguments)
        return "command-id" if "send-command" in arguments else "Success"

    monkeypatch.setattr(deployment, "aws", fake_aws)
    deployment.deploy("staging", "a" * 40, "i-0123456789abcdef0")
    assert capsys.readouterr().out == "Deployment succeeded.\n"
    invocation = calls[1]
    assert invocation[invocation.index("--query") + 1] == "Status"
    assert all("StandardOutputContent" not in " ".join(call) for call in calls)


def test_deploy_suppresses_aws_error_output(monkeypatch, capsys):
    def failed_request(*args, **kwargs):
        assert kwargs["capture_output"] is True
        return subprocess.CompletedProcess(args, 1, "private-secret", "private-secret")

    monkeypatch.setattr(deployment.subprocess, "run", failed_request)
    with pytest.raises(RuntimeError) as error:
        deployment.deploy("staging", "a" * 40, "i-0123456789abcdef0")
    assert "private-secret" not in str(error.value)
    assert "private-secret" not in capsys.readouterr().out


def test_git_ignores_credentials_but_keeps_example_templates():
    ignored = [
        ".env",
        ".env.staging",
        ".env.production",
        "frontend/.env.local",
        "backend/.env.production",
        "deploy.pem",
        ".aws/credentials",
    ]
    result = subprocess.run(
        ["git", "check-ignore", "--no-index", "--stdin", "-z"],
        input="\0".join(
            ignored
            + [".env.example", ".env.staging.example", ".env.production.example"]
        ).encode(),
        capture_output=True,
        cwd=ROOT,
        check=False,
    )
    assert result.returncode == 0
    assert set(result.stdout.decode().strip("\0").split("\0")) == set(ignored)


def test_no_real_environment_files_are_tracked():
    result = subprocess.run(
        ["git", "ls-files", "-z"],
        capture_output=True,
        text=True,
        cwd=ROOT,
        check=True,
    )
    for path in result.stdout.split("\0"):
        name = Path(path).name
        assert not (name == ".env" or name.startswith(".env.")) or name.endswith(
            ".example"
        )
