#!/usr/bin/env bash
set -euo pipefail

CONTROL_URL="${1:-http://127.0.0.1:8000}"
RUN_COUNT="${2:-6}"
MAX_WORKERS="${3:-3}"
MAX_LOOPS="${MAX_LOOPS:-80}"
AUTH_TOKEN="${WHERECODE_TOKEN:-change-me}"
MODULES_CSV="${PROBE_MODULES:-auth,billing}"
STRICT_MODE="${PROBE_STRICT:-true}"

export CONTROL_URL RUN_COUNT MAX_WORKERS MAX_LOOPS AUTH_TOKEN MODULES_CSV STRICT_MODE

python3 <<'PY'
import json
import os
import sys
import time
import urllib.error
import urllib.request
from concurrent.futures import ThreadPoolExecutor, as_completed
from collections import Counter


CONTROL_URL = os.environ["CONTROL_URL"].rstrip("/")
RUN_COUNT = int(os.environ["RUN_COUNT"])
MAX_WORKERS = int(os.environ["MAX_WORKERS"])
MAX_LOOPS = int(os.environ["MAX_LOOPS"])
AUTH_TOKEN = os.environ["AUTH_TOKEN"]
MODULES = [item.strip() for item in os.environ["MODULES_CSV"].split(",") if item.strip()]
STRICT_MODE = os.environ["STRICT_MODE"].lower() == "true"

if RUN_COUNT < 1:
    raise SystemExit("RUN_COUNT must be >= 1")
if MAX_WORKERS < 1:
    raise SystemExit("MAX_WORKERS must be >= 1")
if MAX_LOOPS < 1:
    raise SystemExit("MAX_LOOPS must be >= 1")
if not MODULES:
    raise SystemExit("PROBE_MODULES must contain at least one module")


def request(method: str, path: str, payload: dict | None = None) -> dict:
    data = None if payload is None else json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(
        f"{CONTROL_URL}{path}",
        data=data,
        method=method,
        headers={
            "Content-Type": "application/json",
            "X-WhereCode-Token": AUTH_TOKEN,
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            body = resp.read().decode("utf-8")
            return json.loads(body) if body else {}
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="ignore")
        raise RuntimeError(f"{method} {path} -> {exc.code}: {body}") from exc


def execute_to_terminal(run_id: str) -> dict:
    for _ in range(MAX_LOOPS):
        payload = request("POST", f"/v3/workflows/runs/{run_id}/execute", {"max_loops": 40})
        status = payload.get("run_status")
        if status in {"succeeded", "failed", "canceled"}:
            return payload
        if status == "blocked":
            waiting = payload.get("waiting_discussion_workitem_ids") or []
            if not waiting:
                return payload
            request(
                "POST",
                f"/v3/workflows/workitems/{waiting[0]}/discussion/resolve",
                {"decision": "probe-default", "resolved_by": "chief-architect"},
            )
            continue
        if status == "waiting_approval":
            waiting = payload.get("waiting_approval_workitem_ids") or []
            if not waiting:
                return payload
            request(
                "POST",
                f"/v3/workflows/workitems/{waiting[0]}/approve",
                {"approved_by": "probe-owner"},
            )
            continue
        if status == "running":
            continue
        return payload
    return request("GET", f"/v3/workflows/runs/{run_id}")


def run_probe(index: int) -> dict:
    started = time.perf_counter()
    run = request(
        "POST",
        "/v3/workflows/runs",
        {"project_id": f"proj_parallel_probe_{index}", "requested_by": "parallel-probe"},
    )
    run_id = run["id"]
    request("POST", f"/v3/workflows/runs/{run_id}/bootstrap", {"modules": MODULES})
    execute_payload = execute_to_terminal(run_id)
    final_run = request("GET", f"/v3/workflows/runs/{run_id}")
    gates = request("GET", f"/v3/workflows/runs/{run_id}/gates")
    artifacts = request("GET", f"/v3/workflows/runs/{run_id}/artifacts")
    return {
        "index": index,
        "run_id": run_id,
        "status": final_run.get("status", execute_payload.get("run_status", "unknown")),
        "duration_ms": int((time.perf_counter() - started) * 1000),
        "gates": len(gates) if isinstance(gates, list) else -1,
        "artifacts": len(artifacts) if isinstance(artifacts, list) else -1,
    }


print(
    f"parallel probe start: runs={RUN_COUNT}, workers={MAX_WORKERS}, "
    f"modules={','.join(MODULES)}"
)

results: list[dict] = []
errors: list[str] = []
with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
    futures = {executor.submit(run_probe, i): i for i in range(1, RUN_COUNT + 1)}
    for future in as_completed(futures):
        idx = futures[future]
        try:
            result = future.result()
            results.append(result)
            print(
                f"run#{result['index']} status={result['status']} "
                f"duration_ms={result['duration_ms']} gates={result['gates']} "
                f"artifacts={result['artifacts']}"
            )
        except Exception as exc:  # noqa: BLE001
            msg = f"run#{idx} error={exc}"
            errors.append(msg)
            print(msg)

status_counts = Counter(result["status"] for result in results)
avg_duration = 0
if results:
    avg_duration = int(sum(item["duration_ms"] for item in results) / len(results))

summary = {
    "runs_requested": RUN_COUNT,
    "runs_finished": len(results),
    "error_count": len(errors),
    "status_counts": dict(status_counts),
    "avg_duration_ms": avg_duration,
}
print("summary=" + json.dumps(summary, ensure_ascii=False))

if errors:
    raise SystemExit(1)
if STRICT_MODE and status_counts.get("succeeded", 0) != RUN_COUNT:
    raise SystemExit(1)
PY
