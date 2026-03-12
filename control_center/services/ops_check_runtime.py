from __future__ import annotations

import json
import subprocess
import threading
import time
from pathlib import Path
from typing import Any
from uuid import uuid4

from control_center.models.hierarchy import now_utc
from control_center.services.sqlite_state_store import SQLiteStateStore


class OpsCheckRuntime:
    ENTITY_TYPE = "ops_check_run"
    DEFAULT_ALLOWED_SCOPES = {
        "quick",
        "dev",
        "release",
        "ops",
        "evolve",
        "main",
        "v2",
        "all",
        "backend",
        "backend-quick",
        "backend-full",
        "llm-check",
        "frontend",
        "projects",
    }
    TERMINAL_STATUSES = {"success", "failed", "canceled"}

    def __init__(
        self,
        *,
        state_store: SQLiteStateStore | None,
        root_dir: Path,
        script_path: Path,
        log_dir: Path,
        report_dir: Path,
        allowed_scopes: set[str] | None = None,
    ) -> None:
        self._state_store = state_store
        self._root_dir = root_dir
        self._script_path = script_path
        self._log_dir = log_dir
        self._report_dir = report_dir
        self._allowed_scopes = (
            set(allowed_scopes) if allowed_scopes is not None else set(self.DEFAULT_ALLOWED_SCOPES)
        )

        self._runs: dict[str, dict[str, Any]] = {}
        self._runs_lock = threading.Lock()

        self._log_dir.mkdir(parents=True, exist_ok=True)
        self._report_dir.mkdir(parents=True, exist_ok=True)
        self._load_runs_from_state()

    def list_scopes(self) -> list[str]:
        return sorted(self._allowed_scopes)

    def list_runs(
        self,
        *,
        scope: str | None = None,
        run_status: str | None = None,
        limit: int = 20,
    ) -> dict[str, object]:
        with self._runs_lock:
            items = [self._snapshot_run(item) for item in self._runs.values()]

        if scope is not None and scope.strip():
            normalized_scope = scope.strip().lower()
            items = [item for item in items if str(item.get("scope", "")).lower() == normalized_scope]

        if run_status is not None and run_status.strip():
            normalized_status = run_status.strip().lower()
            items = [
                item for item in items if str(item.get("status", "")).lower() == normalized_status
            ]

        items = sorted(
            items,
            key=lambda item: str(item.get("created_at", "")),
            reverse=True,
        )
        bounded_limit = max(1, min(limit, 200))
        return {
            "total": len(items),
            "limit": bounded_limit,
            "items": items[:bounded_limit],
        }

    def get_latest_run(self, *, scope: str | None = None) -> dict[str, object] | None:
        with self._runs_lock:
            items = [self._snapshot_run(item) for item in self._runs.values()]

        if scope is not None and scope.strip():
            normalized_scope = scope.strip().lower()
            items = [item for item in items if str(item.get("scope", "")).lower() == normalized_scope]

        if not items:
            return None
        return max(items, key=lambda item: str(item.get("created_at", "")))

    def get_run(self, run_id: str) -> dict[str, object] | None:
        return self._get_run_snapshot(run_id)

    def create_run(
        self,
        *,
        scope: str,
        requested_by: str,
        wait_seconds: int,
    ) -> dict[str, object]:
        normalized_scope = scope.strip().lower()
        if normalized_scope not in self._allowed_scopes:
            raise ValueError(f"invalid scope: {normalized_scope}")
        if not self._script_path.exists():
            raise ValueError(f"check script not found: {self._script_path}")

        run_id = f"chk_{uuid4().hex[:12]}"
        created_at = now_utc().isoformat()
        log_path = self._log_dir / f"{run_id}.log"
        command = ["bash", str(self._script_path), normalized_scope]
        run: dict[str, Any] = {
            "run_id": run_id,
            "scope": normalized_scope,
            "status": "queued",
            "message": "queued",
            "requested_by": requested_by.strip() or "api",
            "created_at": created_at,
            "started_at": None,
            "finished_at": None,
            "updated_at": created_at,
            "wait_seconds": max(wait_seconds, 0),
            "command": command,
            "command_text": " ".join(command),
            "exit_code": None,
            "pid": None,
            "log_path": str(log_path),
            "report_path": "",
            "last_output": "",
        }
        with self._runs_lock:
            self._runs[run_id] = run
        self._persist_run(run)

        thread = threading.Thread(
            target=self._execute_run,
            args=(run_id,),
            name=f"ops-check-{run_id}",
            daemon=True,
        )
        thread.start()

        if wait_seconds <= 0:
            return self._get_run_snapshot(run_id) or run

        deadline = time.time() + wait_seconds
        while time.time() < deadline:
            snapshot = self._get_run_snapshot(run_id)
            if snapshot is None:
                break
            if str(snapshot.get("status", "")).lower() in self.TERMINAL_STATUSES:
                return snapshot
            time.sleep(1)

        timeout_snapshot = self._get_run_snapshot(run_id)
        if timeout_snapshot is None:
            return run
        timeout_snapshot["message"] = "wait timeout; run still in progress"
        self._set_run(run_id, timeout_snapshot)
        return self._get_run_snapshot(run_id) or timeout_snapshot

    def _persist_run(self, run: dict[str, Any]) -> None:
        if self._state_store is None:
            return
        run_id = str(run.get("run_id", "")).strip()
        if not run_id:
            return
        self._state_store.upsert(self.ENTITY_TYPE, run_id, run)

    def _snapshot_run(self, run: dict[str, Any]) -> dict[str, Any]:
        return json.loads(json.dumps(run, ensure_ascii=False))

    def _set_run(self, run_id: str, updates: dict[str, Any]) -> dict[str, Any]:
        with self._runs_lock:
            run = self._runs.get(run_id)
            if run is None:
                raise KeyError(f"ops check run not found: {run_id}")
            run.update(updates)
            run["updated_at"] = now_utc().isoformat()
            self._runs[run_id] = run
            snapshot = self._snapshot_run(run)
        self._persist_run(snapshot)
        return snapshot

    def _get_run_snapshot(self, run_id: str) -> dict[str, Any] | None:
        with self._runs_lock:
            run = self._runs.get(run_id)
            if run is None:
                return None
            return self._snapshot_run(run)

    @staticmethod
    def _tail_file(path: Path, limit: int = 80) -> str:
        if not path.exists():
            return ""
        try:
            lines = path.read_text(encoding="utf-8", errors="replace").splitlines()
        except Exception:  # noqa: BLE001
            return ""
        if len(lines) <= limit:
            return "\n".join(lines)
        return "\n".join(lines[-limit:])

    def _write_run_report(self, run: dict[str, Any]) -> str:
        report_path = self._report_dir / f"{run['run_id']}.json"
        payload = {
            "captured_at": now_utc().isoformat(),
            "run_id": run.get("run_id"),
            "scope": run.get("scope"),
            "status": run.get("status"),
            "requested_by": run.get("requested_by"),
            "started_at": run.get("started_at"),
            "finished_at": run.get("finished_at"),
            "exit_code": run.get("exit_code"),
            "log_path": run.get("log_path"),
            "command_text": run.get("command_text"),
            "message": run.get("message"),
            "last_output": run.get("last_output"),
        }
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(
            json.dumps(payload, ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )
        return str(report_path)

    def _execute_run(self, run_id: str) -> None:
        snapshot = self._get_run_snapshot(run_id)
        if snapshot is None:
            return

        log_path = Path(str(snapshot.get("log_path", "")))
        command = snapshot.get("command")
        if not isinstance(command, list):
            command = ["bash", str(self._script_path), str(snapshot.get("scope", "quick"))]

        try:
            self._set_run(
                run_id,
                {
                    "status": "running",
                    "started_at": now_utc().isoformat(),
                    "message": "running",
                },
            )
            with log_path.open("w", encoding="utf-8") as handle:
                process = subprocess.Popen(
                    command,
                    cwd=str(self._root_dir),
                    stdout=handle,
                    stderr=subprocess.STDOUT,
                    text=True,
                )
                self._set_run(run_id, {"pid": process.pid})
                return_code = process.wait()

            latest = self._get_run_snapshot(run_id) or {}
            latest["exit_code"] = return_code
            latest["finished_at"] = now_utc().isoformat()
            latest["last_output"] = self._tail_file(log_path, limit=120)
            latest["status"] = "success" if return_code == 0 else "failed"
            latest["message"] = (
                "check run passed"
                if return_code == 0
                else f"check run failed (exit_code={return_code})"
            )
            latest["report_path"] = self._write_run_report(latest)
            self._set_run(run_id, latest)
        except Exception as exc:  # noqa: BLE001
            failed = self._get_run_snapshot(run_id) or {}
            failed["status"] = "failed"
            failed["finished_at"] = now_utc().isoformat()
            failed["message"] = f"check run crashed: {exc}"
            failed["last_output"] = self._tail_file(log_path, limit=120)
            failed["report_path"] = self._write_run_report(failed)
            self._set_run(run_id, failed)

    def _load_runs_from_state(self) -> None:
        if self._state_store is None:
            return
        for payload in self._state_store.list(self.ENTITY_TYPE):
            run_id = str(payload.get("run_id", "")).strip()
            if not run_id:
                continue
            self._runs[run_id] = payload
