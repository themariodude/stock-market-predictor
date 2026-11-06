"""Run staging smoke checks on EC2 through AWS Systems Manager."""

import json
import os
import re
import sys
import time

from deploy import aws

COMPOSE_FRONTEND_CHECK = (
    'frontend_id="$(docker ps -q '
    "--filter label=com.docker.compose.project=stock-market-predictor "
    '--filter label=com.docker.compose.service=frontend)"\n'
    'test -n "$frontend_id"\n'
    "test \"$(docker inspect --format '{{.State.Running}}' "
    '"$frontend_id")" = "true"\n'
    "docker port \"$frontend_id\" 80/tcp | grep -Eq ':80$'\n"
)


REMOTE_CHECK = """python3 - <<'REMOTE_PY'
import json
import time
import urllib.request

base = "http://127.0.0.1"

def get(path):
    with urllib.request.urlopen(base + path, timeout=10) as response:
        assert response.status == 200
        return response.headers.get("Content-Type", ""), response.read().decode()

for attempt in range(20):
    try:
        _, body = get("/api/health")
        health = json.loads(body)
        assert health.get("status") == "ok"
        assert health.get("database") == "ok"

        _, body = get("/api/stocks")
        stocks = json.loads(body)
        assert isinstance(stocks, list) and stocks
        assert isinstance(stocks[0], dict) and "ticker" in stocks[0]

        content_type, body = get("/")
        assert "text/html" in content_type
        assert 'id="root"' in body

        print("PASS: health, stocks, frontend")
        break
    except Exception:
        if attempt == 19:
            raise
        time.sleep(3)
REMOTE_PY"""


def main():
    instance_id = os.getenv("DEPLOY_INSTANCE_ID", "")
    if not re.fullmatch(r"i-[0-9a-f]{8,17}", instance_id):
        print("Invalid or missing DEPLOY_INSTANCE_ID.")
        return 1

    commands = [
        "set +x",
        "set -eu",
        "umask 077",
        "install -d -m 700 /var/log/stock-market-predictor",
        "exec > /var/log/stock-market-predictor/staging-smoke.log 2>&1",
        COMPOSE_FRONTEND_CHECK,
        REMOTE_CHECK,
    ]

    try:
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
                if attempt >= 5:
                    raise
                status = "Pending"

            if status == "Success":
                print("PASS: SEC-13 staging smoke tests through SSM.")
                return 0
            if status not in {"Pending", "InProgress", "Delayed"}:
                raise RuntimeError("SSM smoke checks did not succeed.")
            time.sleep(5)

    except (RuntimeError, OSError):
        print("FAIL: SSM smoke tests. Check protected EC2 diagnostics.")
        return 1

    print("FAIL: SSM smoke tests timed out.")
    return 1


if __name__ == "__main__":
    sys.exit(main())
