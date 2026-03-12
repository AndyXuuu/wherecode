#!/usr/bin/env python3
import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


DEFAULT_MODULE_HINTS = ["crawl", "sentiment", "theme", "industry", "risk"]


def utc_stamp() -> str:
    return datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def normalize_module_hints(value: Any) -> list[str]:
    if not isinstance(value, list):
        return DEFAULT_MODULE_HINTS.copy()
    hints = [str(item).strip() for item in value if str(item).strip()]
    return hints or DEFAULT_MODULE_HINTS.copy()


def load_config(config_path: str) -> dict[str, Any]:
    payload = json.loads(Path(config_path).read_text(encoding="utf-8"))
    max_modules = payload.get("max_modules")
    if not isinstance(max_modules, int) or max_modules < 1 or max_modules > 20:
        max_modules = 6
    strategy = str(payload.get("strategy") or "balanced").strip().lower()
    if strategy not in {"speed", "balanced", "safe"}:
        strategy = "balanced"
    execute = payload.get("execute")
    return {
        "project_name_prefix": str(payload.get("project_name_prefix") or "subproject").strip(),
        "task_title": str(payload.get("task_title") or "autonomous task").strip(),
        "requirements": str(payload.get("requirements") or "").strip(),
        "module_hints": normalize_module_hints(payload.get("module_hints")),
        "max_modules": max_modules,
        "strategy": strategy,
        "requested_by": str(payload.get("requested_by") or "subproject-runtime").strip(),
        "execute": True if execute is True else False,
    }


class ApiClient:
    def __init__(self, control_url: str, token: str) -> None:
        self.control_url = control_url.rstrip("/")
        self.headers = {
            "X-WhereCode-Token": token,
            "Content-Type": "application/json",
        }

    def request(self, method: str, path: str, payload: Any = None) -> tuple[int, Any]:
        data = None
        if payload is not None:
            data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(self.control_url + path, method=method, data=data)
        for key, value in self.headers.items():
            req.add_header(key, value)
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                body = resp.read().decode("utf-8")
                return resp.status, (json.loads(body) if body else {})
        except urllib.error.HTTPError as exc:
            body = exc.read().decode("utf-8")
            try:
                parsed = json.loads(body) if body else {}
            except Exception:
                parsed = {"detail": body}
            return exc.code, parsed


def ensure_control_center_reachable(control_url: str, timeout: int = 2) -> None:
    req = urllib.request.Request(control_url.rstrip("/") + "/openapi.json", method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout):
            return
    except Exception as exc:
        raise RuntimeError(f"control-center is unreachable at {control_url}: {exc}") from exc


def read_workflow_run_id_from_seed(latest_seed_path: str) -> str:
    payload = json.loads(Path(latest_seed_path).read_text(encoding="utf-8"))
    run_id = str(payload.get("workflow_run_id") or "").strip()
    return run_id


def seed(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    if not cfg["requirements"]:
        print(f"requirements in {args.config} cannot be empty")
        return 1

    try:
        ensure_control_center_reachable(args.control_url)
    except RuntimeError as exc:
        print(str(exc))
        print("set WHERECODE_CONTROL_URL / start control-center, then rerun.")
        return 1

    stamp = args.stamp or utc_stamp()
    project_name = f"{cfg['project_name_prefix']}-{stamp}"
    execute_flag = "true" if cfg["execute"] else "false"
    command_text = (
        f"/orchestrate {cfg['requirements']} "
        f"--module-hints={','.join(cfg['module_hints'])} "
        f"--max-modules={cfg['max_modules']} "
        f"--strategy={cfg['strategy']} "
        f"--execute={execute_flag} "
        "--force-redecompose=false "
        "--confirmed-by=owner"
    )
    requested_by = args.requested_by or cfg["requested_by"] or "subproject-seed"
    client = ApiClient(args.control_url, args.token)

    print("[1/5] create project")
    code_project, project_resp = client.request("POST", "/projects", {"name": project_name})
    if code_project >= 300 or not isinstance(project_resp, dict) or "id" not in project_resp:
        print(f"create project failed: code={code_project} detail={project_resp}")
        return 1
    project_id = str(project_resp["id"])
    print(f"project_id={project_id}")

    print("[2/5] create task")
    code_task, task_resp = client.request("POST", f"/projects/{project_id}/tasks", {"title": cfg["task_title"]})
    if code_task >= 300 or not isinstance(task_resp, dict) or "id" not in task_resp:
        print(f"create task failed: code={code_task} detail={task_resp}")
        return 1
    task_id = str(task_resp["id"])
    print(f"task_id={task_id}")

    print("[3/5] submit orchestrate command")
    code_cmd, cmd_resp = client.request(
        "POST",
        f"/tasks/{task_id}/commands",
        {"text": command_text, "requested_by": requested_by},
    )
    if code_cmd >= 300 or not isinstance(cmd_resp, dict) or "command_id" not in cmd_resp:
        print(f"submit command failed: code={code_cmd} detail={cmd_resp}")
        return 1
    command_id = str(cmd_resp["command_id"])
    print(f"command_id={command_id}")

    print("[4/5] poll command terminal status")
    deadline_epoch = int(time.time()) + int(args.poll_timeout)
    terminal_status = ""
    terminal_payload: dict[str, Any] = {}
    while True:
        code_status, status_payload = client.request("GET", f"/commands/{command_id}")
        if code_status >= 300 or not isinstance(status_payload, dict):
            print(f"poll command failed: code={code_status} detail={status_payload}")
            return 1
        status_value = str(status_payload.get("status") or "")
        print(f"status={status_value}")
        if status_value in {"success", "failed", "canceled"}:
            terminal_status = status_value
            terminal_payload = status_payload
            break
        if int(time.time()) >= deadline_epoch:
            print(f"timeout waiting command={command_id}")
            return 1
        time.sleep(1)

    metadata = terminal_payload.get("metadata") if isinstance(terminal_payload, dict) else None
    if not isinstance(metadata, dict):
        metadata = {}
    state = metadata.get("workflow_state_latest")
    if not isinstance(state, dict):
        state = {}

    workflow_run_id = str(metadata.get("workflow_run_id") or "").strip()
    orchestration_status = str(metadata.get("orchestration_status") or "").strip()
    workflow_next_action = str(state.get("next_action") or "").strip()
    primary_recovery_action = str(state.get("primary_recovery_action") or "").strip()

    print("[5/5] write seed summary")
    report_dir = Path(args.report_dir)
    report_dir.mkdir(parents=True, exist_ok=True)
    report_path = report_dir / f"{utc_stamp()}-seed.json"
    latest_summary = Path(args.latest_summary)

    payload = {
        "captured_at": now_iso(),
        "control_url": args.control_url,
        "project_id": project_id,
        "task_id": task_id,
        "command_id": command_id,
        "terminal_status": terminal_status,
        "workflow_run_id": workflow_run_id,
        "orchestration_status": orchestration_status,
        "workflow_next_action": workflow_next_action,
        "primary_recovery_action": primary_recovery_action,
        "command_text": command_text,
    }
    report_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    latest_summary.parent.mkdir(parents=True, exist_ok=True)
    latest_summary.write_text(
        json.dumps({"updated_at": now_iso(), "report_path": str(report_path), **payload}, ensure_ascii=False, indent=2) + "\n",
        encoding="utf-8",
    )

    print(f"report_written={report_path}")
    print(f"latest_summary={latest_summary}")
    print(f"workflow_run_id={workflow_run_id}")
    if not workflow_run_id:
        print("seed failed: workflow_run_id missing")
        return 1
    if terminal_status != "success":
        print("seed finished with non-success command status; continue with autoevolve.")
    return 0


def autoevolve(args: argparse.Namespace) -> int:
    cfg = load_config(args.config)
    run_id = (args.run_id or "").strip()
    if not run_id:
        if not args.latest_seed:
            print("run_id is required when latest_seed is not provided")
            return 1
        run_id = read_workflow_run_id_from_seed(args.latest_seed)
    if not run_id:
        print("workflow_run_id missing; run seed first")
        return 1

    client = ApiClient(args.control_url, args.token)
    requirements = cfg["requirements"]
    module_hints = cfg["module_hints"]
    requested_by = args.requested_by or "subproject-autoevolve"

    ops: list[dict[str, Any]] = []

    def add(op: str, **kwargs: Any) -> None:
        row: dict[str, Any] = {"op": op}
        row.update(kwargs)
        ops.append(row)

    code_bootstrap, bootstrap_resp = client.request(
        "POST",
        f"/v3/workflows/runs/{run_id}/bootstrap",
        {"modules": module_hints},
    )
    add(
        "bootstrap",
        code=code_bootstrap,
        workitems_count=(len(bootstrap_resp) if isinstance(bootstrap_resp, list) else None),
        detail=(bootstrap_resp.get("detail") if isinstance(bootstrap_resp, dict) else None),
    )

    for round_idx in range(1, int(args.max_rounds) + 1):
        code_run, run_payload = client.request("GET", f"/v3/workflows/runs/{run_id}")
        run_status = run_payload.get("status") if isinstance(run_payload, dict) else None
        add("run_status", round=round_idx, code=code_run, status=run_status)
        if run_status in {"succeeded", "failed", "canceled"}:
            break

        client.request("POST", f"/v3/workflows/runs/{run_id}/tick")
        code_items, items_payload = client.request("GET", f"/v3/workflows/runs/{run_id}/workitems")
        if code_items != 200 or not isinstance(items_payload, list):
            add(
                "workitems_fetch_error",
                round=round_idx,
                code=code_items,
                detail=(items_payload.get("detail") if isinstance(items_payload, dict) else None),
            )
            time.sleep(0.1)
            continue

        touched = 0
        for item in items_payload:
            if not isinstance(item, dict):
                continue
            workitem_id = item.get("id")
            workitem_status = item.get("status")
            if not workitem_id or not workitem_status:
                continue

            if workitem_status == "waiting_approval":
                code, body = client.request(
                    "POST",
                    f"/v3/workflows/workitems/{workitem_id}/approve",
                    {"approved_by": "owner"},
                )
                add(
                    "approve_workitem",
                    workitem_id=workitem_id,
                    code=code,
                    status=(body.get("status") if isinstance(body, dict) else None),
                )
                touched += 1
            elif workitem_status == "needs_discussion":
                code_d, discussions = client.request(
                    "GET",
                    f"/v3/workflows/workitems/{workitem_id}/discussions",
                )
                discussion_id = None
                if code_d == 200 and isinstance(discussions, list):
                    for row in reversed(discussions):
                        if isinstance(row, dict) and row.get("status") == "open":
                            discussion_id = row.get("id")
                            break
                resolve_payload: dict[str, Any] = {"decision": "proceed", "resolved_by": "owner"}
                if discussion_id:
                    resolve_payload["discussion_id"] = discussion_id
                code, body = client.request(
                    "POST",
                    f"/v3/workflows/workitems/{workitem_id}/discussion/resolve",
                    resolve_payload,
                )
                add(
                    "resolve_discussion",
                    workitem_id=workitem_id,
                    code=code,
                    status=(body.get("status") if isinstance(body, dict) else None),
                )
                touched += 1
            elif workitem_status == "ready":
                code_start, _ = client.request("POST", f"/v3/workflows/workitems/{workitem_id}/start")
                code_complete, body = client.request(
                    "POST",
                    f"/v3/workflows/workitems/{workitem_id}/complete",
                    {"success": True},
                )
                add(
                    "complete_workitem",
                    workitem_id=workitem_id,
                    start_code=code_start,
                    complete_code=code_complete,
                    final_status=(body.get("status") if isinstance(body, dict) else None),
                )
                touched += 1
            elif workitem_status == "running":
                code_complete, body = client.request(
                    "POST",
                    f"/v3/workflows/workitems/{workitem_id}/complete",
                    {"success": True},
                )
                add(
                    "complete_running",
                    workitem_id=workitem_id,
                    complete_code=code_complete,
                    final_status=(body.get("status") if isinstance(body, dict) else None),
                )
                touched += 1

        if touched == 0:
            code_exec, exec_payload = client.request(
                "POST",
                f"/v3/workflows/runs/{run_id}/execute",
                {
                    "max_loops": 30,
                    "auto_advance_decompose": True,
                    "auto_advance_max_steps": 20,
                    "decompose_confirmed_by": "owner",
                },
            )
            add(
                "execute_fallback",
                code=code_exec,
                run_status=(exec_payload.get("run_status") if isinstance(exec_payload, dict) else None),
            )

            code_recover, recover_payload = client.request(
                "POST",
                f"/v3/workflows/runs/{run_id}/orchestrate/recover",
                {
                    "action": "retry_with_decompose_payload",
                    "strategy": cfg["strategy"],
                    "requirements": requirements,
                    "module_hints": module_hints,
                    "max_modules": max(len(module_hints), 4),
                    "requested_by": requested_by,
                    "execute": True,
                    "confirmed_by": "owner",
                    "execute_max_loops": 30,
                    "auto_advance_decompose": True,
                    "auto_advance_max_steps": 20,
                },
            )
            add(
                "recover_fallback",
                code=code_recover,
                action_status=(recover_payload.get("action_status") if isinstance(recover_payload, dict) else None),
                selected_action=(recover_payload.get("selected_action") if isinstance(recover_payload, dict) else None),
                reason=(recover_payload.get("reason") if isinstance(recover_payload, dict) else None),
            )

        time.sleep(0.05)

    code_final, final_run = client.request("GET", f"/v3/workflows/runs/{run_id}")
    code_items, final_items = client.request("GET", f"/v3/workflows/runs/{run_id}/workitems")
    counts: dict[str, int] = {}
    if code_items == 200 and isinstance(final_items, list):
        for item in final_items:
            if not isinstance(item, dict):
                continue
            status = item.get("status")
            if isinstance(status, str):
                counts[status] = counts.get(status, 0) + 1

    summary = {
        "run_id": run_id,
        "final_code": code_final,
        "final_status": (final_run.get("status") if isinstance(final_run, dict) else None),
        "workitem_counts": counts,
        "ops_count": len(ops),
        "ops": ops,
    }

    report_path = Path(args.report_path)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")

    latest_path = Path(args.latest_path)
    latest_path.parent.mkdir(parents=True, exist_ok=True)
    latest_path.write_text(
        json.dumps(
            {
                "updated_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "run_id": run_id,
                "final_status": summary["final_status"],
                "report_path": str(report_path.resolve()),
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )

    print(str(report_path))
    print(
        json.dumps(
            {"run_id": run_id, "final_status": summary["final_status"], "workitem_counts": counts},
            ensure_ascii=False,
        )
    )
    if summary["final_status"] != "succeeded":
        return 4
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Shared runtime for requirement-driven subproject flow.")
    sub = parser.add_subparsers(dest="command", required=True)

    parser_seed = sub.add_parser("seed", help="Create project/task, submit orchestrate command, persist seed summary.")
    parser_seed.add_argument("--config", required=True, help="Path to evolve.json")
    parser_seed.add_argument("--report-dir", required=True, help="Output directory for seed report files")
    parser_seed.add_argument("--latest-summary", required=True, help="Path to latest seed pointer file")
    parser_seed.add_argument("--control-url", default=os.getenv("WHERECODE_CONTROL_URL", "http://127.0.0.1:8000"))
    parser_seed.add_argument("--token", default=os.getenv("WHERECODE_TOKEN", "change-me"))
    parser_seed.add_argument("--stamp", default="")
    parser_seed.add_argument("--requested-by", default="")
    parser_seed.add_argument("--poll-timeout", type=int, default=180)
    parser_seed.set_defaults(handler=seed)

    parser_auto = sub.add_parser("autoevolve", help="Drive workflow run to succeeded and persist summary.")
    parser_auto.add_argument("--config", required=True, help="Path to evolve.json")
    parser_auto.add_argument("--latest-seed", default="", help="Path to latest_seed.json (used when run-id is empty)")
    parser_auto.add_argument("--run-id", default="", help="Workflow run id")
    parser_auto.add_argument("--report-path", required=True, help="Output autoevolve report path")
    parser_auto.add_argument("--latest-path", required=True, help="Path to latest autoevolve pointer file")
    parser_auto.add_argument("--control-url", default=os.getenv("WHERECODE_CONTROL_URL", "http://127.0.0.1:8000"))
    parser_auto.add_argument("--token", default=os.getenv("WHERECODE_TOKEN", "change-me"))
    parser_auto.add_argument("--requested-by", default="subproject-autoevolve")
    parser_auto.add_argument("--max-rounds", type=int, default=200)
    parser_auto.set_defaults(handler=autoevolve)
    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.handler(args))


if __name__ == "__main__":
    sys.exit(main())
