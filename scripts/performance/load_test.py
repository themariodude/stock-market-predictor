"""Small, repeatable HTTP load runner for the backend performance baseline.

Run from the repository root with:
  python scripts/performance/load_test.py --base-url http://127.0.0.1:8000
"""

from __future__ import annotations

import argparse
import concurrent.futures
import json
import statistics
import time
import urllib.error
import urllib.request
from datetime import UTC, datetime
from pathlib import Path

SCENARIOS = {
    "health": ("GET", "/health", None, {200}),
    "stocks_list": ("GET", "/stocks", None, {200}),
    # No model-metrics artifact is committed in every deployment; 503 is a
    # documented service response and should not be mistaken for load failure.
    "model_metrics": ("GET", "/models/metrics", None, {200, 503}),
    "unauthenticated_account": ("GET", "/auth/me", None, {401}),
}


def request(base_url: str, scenario: tuple) -> tuple[float, int | None, str | None]:
    method, path, body, _ = scenario
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(
        base_url.rstrip("/") + path,
        data=data,
        method=method,
        headers={"Content-Type": "application/json"},
    )
    started = time.perf_counter()
    try:
        with urllib.request.urlopen(req, timeout=15) as response:
            response.read()
            return time.perf_counter() - started, response.status, None
    except urllib.error.HTTPError as exc:
        exc.read()
        return time.perf_counter() - started, exc.code, None
    except Exception as exc:  # Network and timeout failures are measured errors.
        return time.perf_counter() - started, None, type(exc).__name__


def percentile(values: list[float], percentile_value: float) -> float:
    ordered = sorted(values)
    index = max(0, min(len(ordered) - 1, int((len(ordered) - 1) * percentile_value)))
    return ordered[index]


def run_scenario(base_url: str, name: str, concurrency: int, duration: float) -> dict:
    scenario = SCENARIOS[name]
    results: list[tuple[float, int | None, str | None]] = []
    stop_at = time.perf_counter() + duration
    with concurrent.futures.ThreadPoolExecutor(max_workers=concurrency) as pool:
        pending = set()
        while time.perf_counter() < stop_at or pending:
            while time.perf_counter() < stop_at and len(pending) < concurrency:
                pending.add(pool.submit(request, base_url, scenario))
            done, pending = concurrent.futures.wait(
                pending, return_when=concurrent.futures.FIRST_COMPLETED
            )
            results.extend(future.result() for future in done)

    latencies = [item[0] for item in results]
    expected = scenario[3]
    unexpected = sum(status not in expected for _, status, _ in results)
    status_counts: dict[str, int] = {}
    for _, status, error in results:
        key = str(status) if status is not None else f"transport:{error}"
        status_counts[key] = status_counts.get(key, 0) + 1
    return {
        "requests": len(results),
        "duration_seconds": duration,
        "concurrency": concurrency,
        "average_ms": round(statistics.fmean(latencies) * 1000, 3),
        "p95_ms": round(percentile(latencies, 0.95) * 1000, 3),
        "requests_per_second": round(len(results) / duration, 3),
        "unexpected_error_rate": round(unexpected / len(results), 6),
        "status_counts": status_counts,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8000")
    parser.add_argument("--duration", type=float, default=30)
    parser.add_argument("--concurrency", type=int, nargs="+", default=[1, 10, 25])
    parser.add_argument("--output", type=Path)
    args = parser.parse_args()
    if args.duration <= 0 or any(value <= 0 for value in args.concurrency):
        parser.error("duration and concurrency values must be positive")

    report = {
        "schema_version": 1,
        "recorded_at_utc": datetime.now(UTC).isoformat(),
        "base_url": args.base_url.rstrip("/"),
        "duration_seconds_per_scenario": args.duration,
        "scenarios": {},
    }
    for concurrency in args.concurrency:
        for name in SCENARIOS:
            key = f"{name}_c{concurrency}"
            report["scenarios"][key] = run_scenario(
                args.base_url, name, concurrency, args.duration
            )

    rendered = json.dumps(report, indent=2) + "\n"
    if args.output:
        args.output.parent.mkdir(parents=True, exist_ok=True)
        args.output.write_text(rendered, encoding="utf-8")
    print(rendered, end="")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
