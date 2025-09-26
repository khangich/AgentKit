"""Application state and persistence utilities."""

from __future__ import annotations

import asyncio
import json
import os
import sqlite3
import time
import uuid
from contextlib import contextmanager
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional

DEFAULT_DB_PATH = Path(os.getenv("AGENTKIT_DATABASE", "./data/agentkit.db"))


class RunStore:
    """SQLite-backed run state with in-memory pub/sub for streaming."""

    def __init__(self, db_path: Path | str | None = None) -> None:
        self.db_path = Path(db_path) if db_path else DEFAULT_DB_PATH
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._queues: dict[str, List[asyncio.Queue]] = {}
        self._init_db()

    def _init_db(self) -> None:
        with self._connect() as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS runs (
                    id TEXT PRIMARY KEY,
                    status TEXT,
                    inputs TEXT,
                    started_at REAL,
                    finished_at REAL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS events (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    run_id TEXT,
                    type TEXT,
                    payload TEXT,
                    ts REAL
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS uploads (
                    id TEXT PRIMARY KEY,
                    path TEXT,
                    original_name TEXT,
                    mime TEXT,
                    size INTEGER
                )
                """
            )

    @contextmanager
    def _connect(self):
        conn = sqlite3.connect(self.db_path)
        try:
            yield conn
            conn.commit()
        finally:
            conn.close()

    # Run management -----------------------------------------------------

    def create_run(self, inputs: Dict[str, Any]) -> str:
        run_id = uuid.uuid4().hex
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO runs (id, status, inputs, started_at, finished_at) VALUES (?, ?, ?, ?, ?)",
                (run_id, "pending", json.dumps(inputs), time.time(), None),
            )
        return run_id

    def finish_run(self, run_id: str, status: str) -> None:
        with self._connect() as conn:
            conn.execute(
                "UPDATE runs SET status = ?, finished_at = ? WHERE id = ?",
                (status, time.time(), run_id),
            )

    # Events -------------------------------------------------------------

    def append_event(self, run_id: str, event_type: str, payload: Dict[str, Any]) -> None:
        record = {
            "type": event_type,
            "payload": payload,
            "ts": time.time(),
        }
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO events (run_id, type, payload, ts) VALUES (?, ?, ?, ?)",
                (run_id, event_type, json.dumps(payload), record["ts"]),
            )
        queues = self._queues.get(run_id)
        if queues:
            for queue in list(queues):
                try:
                    queue.put_nowait(record)
                except asyncio.QueueFull:  # pragma: no cover - defensive
                    pass

    def iter_events(self, run_id: str) -> Iterable[Dict[str, Any]]:
        with self._connect() as conn:
            for row in conn.execute(
                "SELECT type, payload, ts FROM events WHERE run_id = ? ORDER BY id ASC",
                (run_id,),
            ):
                yield {
                    "type": row[0],
                    "payload": json.loads(row[1]) if row[1] else {},
                    "ts": row[2],
                }

    # Uploads ------------------------------------------------------------

    def save_upload(
        self,
        upload_path: Path,
        original_name: str,
        mime: str,
        size: int,
    ) -> str:
        file_id = uuid.uuid4().hex
        with self._connect() as conn:
            conn.execute(
                "INSERT INTO uploads (id, path, original_name, mime, size) VALUES (?, ?, ?, ?, ?)",
                (file_id, str(upload_path), original_name, mime, size),
            )
        return file_id

    def list_uploads(self) -> List[Dict[str, Any]]:
        with self._connect() as conn:
            rows = conn.execute(
                "SELECT id, path, original_name, mime, size FROM uploads ORDER BY rowid DESC"
            ).fetchall()
        return [
            {
                "id": row[0],
                "path": row[1],
                "original_name": row[2],
                "mime": row[3],
                "size": row[4],
            }
            for row in rows
        ]

    # Streaming ----------------------------------------------------------

    def subscribe(self, run_id: str) -> asyncio.Queue:
        queue: asyncio.Queue = asyncio.Queue()
        self._queues.setdefault(run_id, []).append(queue)
        return queue

    def unsubscribe(self, run_id: str, queue: asyncio.Queue) -> None:
        queues = self._queues.get(run_id)
        if not queues:
            return
        try:
            queues.remove(queue)
        except ValueError:
            pass
        if not queues:
            self._queues.pop(run_id, None)

    # Queries ------------------------------------------------------------

    def get_run(self, run_id: str) -> Optional[Dict[str, Any]]:
        with self._connect() as conn:
            row = conn.execute(
                "SELECT id, status, inputs, started_at, finished_at FROM runs WHERE id = ?",
                (run_id,),
            ).fetchone()
        if not row:
            return None
        return {
            "id": row[0],
            "status": row[1],
            "inputs": json.loads(row[2]) if row[2] else {},
            "started_at": row[3],
            "finished_at": row[4],
        }


store = RunStore()


__all__ = ["RunStore", "store"]
