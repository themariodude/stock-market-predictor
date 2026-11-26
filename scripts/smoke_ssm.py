"""Run staging smoke checks on EC2 through AWS Systems Manager."""

import json
import os
import re
import sys
import time

from deploy import aws


COMPOSE_FRONTEND_CHECK = (
    'caddy_id="$(docker ps -q '
    "--filter label=com.docker.compose.project=stock-market-predictor "
    '--filter label=com.docker.compose.service=caddy)"\n'
    'test -n "$caddy_id"\n'
    "test \"$(docker inspect --format '{{.State.Running}}' "
    '"$caddy_id")" = "true"\n'
    "docker port \"$caddy_id\" 80/tcp | grep -Eq ':80$'\n"
    "docker port \"$caddy_id\" 443/tcp | grep -Eq ':443$'\n"
)




REMOTE_CHECK = """python3 - <<'REMOTE_PY'
import json
import subprocess
import time

host = "stockmarketpredictor.duckdns.org"

def request(path):
    return subprocess.check_output(
        [
            "curl", "--silent", "--show-error", "--fail",
            "--max-time", "10",
            "--resolve", f"{host}:443:127.0.0.1",
            f"https://{host}{path}",
        ],
        text=True,
    )

def check_redirect():
    result = subprocess.run(
        [
            "curl", "--silent", "--show-error",
            "--max-time", "10",
            "--resolve", f"{host}:80:127.0.0.1",
            "--dump-header", "-",
            "--output", "/dev/null",
            f"http://{host}/",
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    headers = result.stdout.lower()
    assert any(
        headers.startswith(f"http/1.1 {status}")
        or headers.startswith(f"http/2 {status}")
        for status in (301, 308)
    )
    assert f"location: https://{host}/" in headers

for attempt in range(20):
    try:
        health = json.loads(request("/api/health"))
        assert health.get("status") == "ok"
        assert health.get("database") == "ok"

        stocks = json.loads(request("/api/stocks"))
        assert isinstance(stocks, list) and stocks
        assert isinstance(stocks[0], dict) and "ticker" in stocks[0]

        frontend = request("/")
        assert 'id="root"' in frontend

        check_redirect()

        print("PASS: HTTPS, redirect, health, stocks, frontend")
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
