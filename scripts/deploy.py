"""Deploy through SSM without returning remote stdout/stderr to CI logs."""

import argparse
import json
import os
import re
import subprocess
import sys
import time

IMAGE_REF_PATTERN = re.compile(
    r"ghcr\.io/([a-z0-9]+(?:[.-][a-z0-9]+)*)/"
    r"stock-market-predictor-(backend|frontend)@sha256:[0-9a-f]{64}"
)


def deployment_commands(
    environment: str,
    image_tag: str,
    backend_image: str | None = None,
    frontend_image: str | None = None,
) -> list[str]:
    if environment not in {"staging", "production"}:
        raise ValueError("Unsupported deployment environment.")
    if not re.fullmatch(r"[0-9a-f]{40}", image_tag):
        raise ValueError("IMAGE_TAG must be a full Git commit SHA.")
    if bool(backend_image) != bool(frontend_image):
        raise ValueError("Both image digests are required together.")
    if environment == "production" and not backend_image:
        raise ValueError("Production requires approved digest-pinned images.")
    if backend_image:
        backend_match = IMAGE_REF_PATTERN.fullmatch(backend_image)
        frontend_match = IMAGE_REF_PATTERN.fullmatch(frontend_image)
        if (
            not backend_match
            or not frontend_match
            or backend_match.group(2) != "backend"
            or frontend_match.group(2) != "frontend"
            or backend_match.group(1) != frontend_match.group(1)
        ):
            raise ValueError("Invalid backend or frontend image digest reference.")

    # Preserve the existing staging Compose project and its database volume.
    project = "stock-market-predictor"
    if environment == "production":
        project += "-production"
    env_file = f"/etc/stock-market-predictor/{environment}.env"
    compose = (
        f"docker compose --project-name {project} --env-file {env_file} "
        "-f docker-compose.staging.yml"
    )
    commands = [
        "set +x",
        "set -eu",
        "umask 077",
        # Remote errors can contain derived secrets that GitHub cannot mask.
        # Keep diagnostics only on the host; report status alone to the runner.
        "install -d -m 700 /var/log/stock-market-predictor",
        f"exec > /var/log/stock-market-predictor/{environment}-deploy.log 2>&1",
        "cd /opt/stock-market-predictor",
        f"test -f {env_file} && test ! -L {env_file}",
        f'test "$(stat -c %a {env_file})" = 600',
        f'test "$(stat -c %u {env_file})" = 0',
        f"export APP_ENV={environment} IMAGE_TAG={image_tag}",
    ]
    if backend_image:
        commands.append(
            f"export BACKEND_IMAGE={backend_image} FRONTEND_IMAGE={frontend_image}"
        )
    commands.extend(
        [
            f"{compose} pull --quiet",
            # Start the existing database and wait until it is healthy.
            f"{compose} up -d --wait --wait-timeout 180 db",
            # Apply migrations once, using the selected backend image.
            # A failure stops deployment because the remote script uses set -eu.
            f"{compose} run --rm --no-deps backend python -m alembic upgrade head",
            # Start the updated application only after migrations succeed.
            f"{compose} up -d --remove-orphans --wait --wait-timeout 180",
        ]
    )
    if backend_image:
        for service, image in (
            ("backend", backend_image),
            ("frontend", frontend_image),
        ):
            commands.append(
                f'test "$(docker inspect --format "{{{{.Config.Image}}}}" '
                f'"$({compose} ps -q {service})")" = "{image}"'
            )
    return commands


def aws(*arguments: str) -> str:
    result = subprocess.run(
        ["aws", *arguments], capture_output=True, text=True, check=False
    )
    if result.returncode:
        # AWS error text and remote output must never be echoed to CI.
        raise RuntimeError("AWS deployment request failed; inspect the AWS console.")
    return result.stdout.strip()


def deploy(
    environment: str,
    image_tag: str,
    instance_id: str,
    backend_image: str | None = None,
    frontend_image: str | None = None,
) -> None:
    commands = deployment_commands(
        environment, image_tag, backend_image, frontend_image
    )
    if not re.fullmatch(r"i-[0-9a-f]{8,17}", instance_id):
        raise ValueError("DEPLOY_INSTANCE_ID must be an EC2 instance ID.")
    command_id = aws(
        "ssm",
        "send-command",
        "--instance-ids",
        instance_id,
        "--document-name",
        "AWS-RunShellScript",
        "--parameters",
        json.dumps({"commands": commands}),
        "--timeout-seconds",
        "600",
        "--query",
        "Command.CommandId",
        "--output",
        "text",
    )
    for attempt in range(120):
        try:
            status = aws(
                "ssm",
                "get-command-invocation",
                "--command-id",
                command_id,
                "--instance-id",
                instance_id,
                "--query",
                "Status",
                "--output",
                "text",
            )
        except RuntimeError:
            # SSM invocation records are eventually consistent after send-command.
            if attempt >= 5:
                raise
            status = "Pending"
        if status == "Success":
            print("Deployment succeeded.")
            return
        if status not in {"Pending", "InProgress", "Delayed"}:
            raise RuntimeError(
                "Deployment did not succeed; inspect the deployment host."
            )
        time.sleep(5)
    raise RuntimeError("Deployment timed out; inspect the deployment host.")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--environment", choices=["staging", "production"], required=True
    )
    args = parser.parse_args()
    try:
        deploy(
            args.environment,
            os.getenv("IMAGE_TAG", ""),
            os.getenv("DEPLOY_INSTANCE_ID", ""),
            os.getenv("BACKEND_IMAGE") or None,
            os.getenv("FRONTEND_IMAGE") or None,
        )
    except (RuntimeError, ValueError, OSError):
        print("Deployment failed. Check configuration and protected host diagnostics.")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
