"""Post-deployment smoke tests (US-59).

Did the application we just deployed start and respond?
It does not test features; the full test suites do that.

Uses only the Python standard library, so it runs anywhere Python 3 does.

Usage:
    python scripts/smoke_test.py
    python scripts/smoke_test.py --backend-url http://host:8000 --frontend-url http://host:5173

Exits 0 when every check passes, 1 otherwise.
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

REQUEST_TIMEOUT = 10  # seconds per HTTP request


def get(url: str) -> tuple[int, str, str]:
    """Return (status, content type, body). Status 0 means no response."""
    try:
        with urllib.request.urlopen(url, timeout=REQUEST_TIMEOUT) as response:
            body = response.read().decode("utf-8", errors="replace")
            return response.status, response.headers.get("Content-Type", ""), body
    except urllib.error.HTTPError as exc:
        return exc.code, exc.headers.get("Content-Type", ""), ""
    except (urllib.error.URLError, OSError):
        return 0, "", ""


def health_problem(status: int, body: str) -> str | None:
    """What keeps /health from being ready, or None when it is ready."""
    if status != 200:
        return f"/health returned {status or 'no response'}, expected 200"
    try:
        data = json.loads(body)
    except ValueError:
        return "/health did not return JSON"
    if not isinstance(data, dict):
        return "/health did not return a JSON object"
    if data.get("status") != "ok":
        return f"/health status is {data.get('status')!r}, expected 'ok'"
    if data.get("database") != "ok":
        return f"/health database is {data.get('database')!r}, expected 'ok'"
    return None


def check_health(backend_url: str, wait_seconds: int) -> str | None:
    """Backend is up and can reach its database. Returns an error or None.

    Polls until ready: a deploy has just restarted the containers, so the
    backend or its database connection may need a moment. Ready means HTTP 200
    with status "ok" and database "ok", not just HTTP 200, because /health
    answers 200 even when the database is down.
    """
    deadline = time.monotonic() + wait_seconds
    while True:
        status, _, body = get(f"{backend_url}/health")
        problem = health_problem(status, body)
        if problem is None:
            return None
        if time.monotonic() >= deadline:
            return f"{problem} (still not ready after {wait_seconds}s)"
        time.sleep(3)


def check_stock_list(backend_url: str) -> str | None:
    """One real API request. /stocks needs no Yahoo Finance call."""
    status, _, body = get(f"{backend_url}/stocks")
    if status != 200:
        return f"/stocks returned {status or 'no response'}, expected 200"
    try:
        stocks = json.loads(body)
    except ValueError:
        return "/stocks did not return JSON"
    if (
        not isinstance(stocks, list)
        or not stocks
        or not isinstance(stocks[0], dict)
        or "ticker" not in stocks[0]
    ):
        return "/stocks did not return a list of stocks"
    return None


def check_frontend(frontend_url: str) -> str | None:
    """The frontend serves the application page."""
    status, content_type, body = get(f"{frontend_url}/")
    if status != 200:
        return f"frontend returned {status or 'no response'}, expected 200"
    if "text/html" not in content_type:
        return f"frontend returned {content_type!r}, expected text/html"
    if 'id="root"' not in body:
        return 'frontend page has no id="root" element'
    return None


def main() -> int:
    parser = argparse.ArgumentParser(description="Post-deployment smoke tests")
    parser.add_argument(
        "--backend-url",
        default=os.getenv("SMOKE_BACKEND_URL", "http://localhost:8000"),
    )
    parser.add_argument(
        "--frontend-url",
        default=os.getenv("SMOKE_FRONTEND_URL", "http://localhost:5173"),
    )
    parser.add_argument(
        "--wait",
        type=int,
        default=60,
        help="seconds to wait for the backend to come up (default 60)",
    )
    args = parser.parse_args()
    backend_url = args.backend_url.rstrip("/")
    frontend_url = args.frontend_url.rstrip("/")

    checks = [
        ("backend /health, database ok", lambda: check_health(backend_url, args.wait)),
        ("backend /stocks", lambda: check_stock_list(backend_url)),
        ("frontend page", lambda: check_frontend(frontend_url)),
    ]

    failures = 0
    for name, check in checks:
        error = check()
        if error is None:
            print(f"PASS  {name}")
        else:
            failures += 1
            print(f"FAIL  {name}: {error}")

    print(f"\n{len(checks) - failures} of {len(checks)} checks passed")
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main())
