from __future__ import annotations

import json
import sqlite3
from pathlib import Path


class SQLiteStateStore:
    def __init__(self, db_path: str) -> None:
        self._db_path = Path(db_path)
        self._db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def _connect(self) -> sqlite3.Connection:
        return sqlite3.connect(self._db_path)

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS entities (
                  entity_type TEXT NOT NULL,
                  entity_id TEXT NOT NULL,
                  payload TEXT NOT NULL,
                  PRIMARY KEY (entity_type, entity_id)
                )
                """
            )
            conn.commit()

    def upsert(self, entity_type: str, entity_id: str, payload: dict[str, object]) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                INSERT INTO entities (entity_type, entity_id, payload)
                VALUES (?, ?, ?)
                ON CONFLICT(entity_type, entity_id)
                DO UPDATE SET payload=excluded.payload
                """,
                (entity_type, entity_id, json.dumps(payload, ensure_ascii=False)),
            )
            conn.commit()

    def list(self, entity_type: str) -> list[dict[str, object]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT payload FROM entities WHERE entity_type = ?",
                (entity_type,),
            ).fetchall()
        return [json.loads(row[0]) for row in rows]

    def clear(self) -> None:
        with self._connect() as conn:
            conn.execute("DELETE FROM entities")
            conn.commit()
