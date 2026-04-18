"""SQLite manifest access — read pending rows and record execution results."""

from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class ManifestRow:
    id: int
    source_path: str
    source_label: str
    dest_path: Optional[str]
    action: str
    source_hash: Optional[str]
    executed: int


def open_db(path: Path) -> sqlite3.Connection:
    if not path.exists():
        raise FileNotFoundError(f"Manifest not found: {path}")
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    return conn


def pending_moves(conn: sqlite3.Connection) -> list[ManifestRow]:
    """Return all MOVE rows not yet executed (executed=0)."""
    rows = conn.execute(
        "SELECT id, source_path, source_label, dest_path, action, source_hash, executed "
        "FROM migration_manifest WHERE action = 'MOVE' AND executed = 0"
    ).fetchall()
    return [ManifestRow(**dict(r)) for r in rows]


def mark_done(conn: sqlite3.Connection, row_id: int) -> None:
    conn.execute("UPDATE migration_manifest SET executed = 1 WHERE id = ?", (row_id,))
    conn.commit()


def mark_failed(conn: sqlite3.Connection, row_id: int) -> None:
    conn.execute("UPDATE migration_manifest SET executed = 2 WHERE id = ?", (row_id,))
    conn.commit()


def summary(conn: sqlite3.Connection) -> dict[str, int]:
    """Return counts by (action, executed) for a progress overview."""
    rows = conn.execute(
        "SELECT action, executed, COUNT(*) AS n FROM migration_manifest GROUP BY action, executed"
    ).fetchall()
    result: dict[str, int] = {}
    for r in rows:
        result[f"{r['action']}.{r['executed']}"] = r["n"]
    return result
