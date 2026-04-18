"""Tests for transfer/db.py — manifest read + execution tracking."""

from __future__ import annotations

import sqlite3
from pathlib import Path

import pytest

from transfer.db import open_db, pending_moves, mark_done, mark_failed, summary


_DDL = """
CREATE TABLE migration_manifest (
    id               INTEGER PRIMARY KEY,
    source_path      TEXT NOT NULL,
    source_label     TEXT NOT NULL,
    dest_path        TEXT,
    action           TEXT NOT NULL,
    source_hash      TEXT,
    phash            TEXT,
    hamming_distance INTEGER,
    duplicate_of     TEXT,
    reason           TEXT,
    executed         INTEGER NOT NULL DEFAULT 0
);
"""


def _make_manifest(tmp_path: Path, rows: list[dict]) -> Path:
    db_path = tmp_path / "manifest.sqlite"
    with sqlite3.connect(db_path) as conn:
        conn.executescript(_DDL)
        for r in rows:
            conn.execute(
                "INSERT INTO migration_manifest "
                "(source_path, source_label, dest_path, action, source_hash, executed) "
                "VALUES (:source_path, :source_label, :dest_path, :action, :source_hash, :executed)",
                r,
            )
        conn.commit()
    return db_path


class TestOpenDb:
    def test_raises_on_missing_file(self, tmp_path):
        with pytest.raises(FileNotFoundError):
            open_db(tmp_path / "missing.sqlite")

    def test_returns_connection(self, tmp_path):
        db = _make_manifest(tmp_path, [])
        conn = open_db(db)
        assert conn is not None
        conn.close()


class TestPendingMoves:
    def test_returns_only_pending_move_rows(self, tmp_path):
        db = _make_manifest(tmp_path, [
            {"source_path": "/a.jpg", "source_label": "jdrive", "dest_path": "2024/a.jpg",
             "action": "MOVE", "source_hash": "h1", "executed": 0},
            {"source_path": "/b.jpg", "source_label": "jdrive", "dest_path": "2024/b.jpg",
             "action": "MOVE", "source_hash": "h2", "executed": 1},  # already done
            {"source_path": "/c.jpg", "source_label": "takeout", "dest_path": None,
             "action": "SKIP", "source_hash": "h3", "executed": 0},
        ])
        conn = open_db(db)
        rows = pending_moves(conn)
        assert len(rows) == 1
        assert rows[0].source_path == "/a.jpg"

    def test_empty_when_all_done(self, tmp_path):
        db = _make_manifest(tmp_path, [
            {"source_path": "/a.jpg", "source_label": "jdrive", "dest_path": "2024/a.jpg",
             "action": "MOVE", "source_hash": "h1", "executed": 1},
        ])
        conn = open_db(db)
        assert pending_moves(conn) == []


class TestMarkDone:
    def test_sets_executed_1(self, tmp_path):
        db = _make_manifest(tmp_path, [
            {"source_path": "/a.jpg", "source_label": "jdrive", "dest_path": "2024/a.jpg",
             "action": "MOVE", "source_hash": "h1", "executed": 0},
        ])
        conn = open_db(db)
        row_id = pending_moves(conn)[0].id
        mark_done(conn, row_id)
        assert pending_moves(conn) == []  # no longer pending


class TestMarkFailed:
    def test_sets_executed_2(self, tmp_path):
        db = _make_manifest(tmp_path, [
            {"source_path": "/a.jpg", "source_label": "jdrive", "dest_path": "2024/a.jpg",
             "action": "MOVE", "source_hash": "h1", "executed": 0},
        ])
        conn = open_db(db)
        row_id = pending_moves(conn)[0].id
        mark_failed(conn, row_id)
        # Not pending anymore, but not done either
        assert pending_moves(conn) == []
        executed = conn.execute(
            "SELECT executed FROM migration_manifest WHERE id = ?", (row_id,)
        ).fetchone()[0]
        assert executed == 2


class TestSummary:
    def test_counts_by_action_and_executed(self, tmp_path):
        db = _make_manifest(tmp_path, [
            {"source_path": "/a.jpg", "source_label": "jdrive", "dest_path": "2024/a.jpg",
             "action": "MOVE", "source_hash": "h1", "executed": 0},
            {"source_path": "/b.jpg", "source_label": "jdrive", "dest_path": "2024/b.jpg",
             "action": "MOVE", "source_hash": "h2", "executed": 1},
            {"source_path": "/c.jpg", "source_label": "jdrive", "dest_path": None,
             "action": "SKIP", "source_hash": "h3", "executed": 0},
        ])
        conn = open_db(db)
        s = summary(conn)
        assert s["MOVE.0"] == 1
        assert s["MOVE.1"] == 1
        assert s["SKIP.0"] == 1
