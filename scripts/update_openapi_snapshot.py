#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from control_center.main import app


def main() -> None:
    snapshot_path = ROOT / "tests" / "snapshots" / "openapi.snapshot.json"
    snapshot_path.parent.mkdir(parents=True, exist_ok=True)
    snapshot = app.openapi()
    snapshot_path.write_text(
        json.dumps(snapshot, indent=2, sort_keys=True, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    print(f"updated {snapshot_path}")


if __name__ == "__main__":
    main()
