import json
from pathlib import Path

from control_center.main import app


def test_openapi_snapshot_stable() -> None:
    snapshot_path = Path(__file__).resolve().parents[1] / "snapshots" / "openapi.snapshot.json"
    assert snapshot_path.exists(), "missing OpenAPI snapshot: run scripts/update_openapi_snapshot.py"

    expected = json.loads(snapshot_path.read_text(encoding="utf-8"))
    current = app.openapi()

    assert current == expected, "OpenAPI changed: run scripts/update_openapi_snapshot.py and review diff"
