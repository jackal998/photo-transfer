"""Tests for transfer/executor.py — file copy + collision resolution."""

from __future__ import annotations

from pathlib import Path

import pytest

from transfer.executor import copy_file, resolve_collision


class TestResolveCollision:
    def test_no_collision_returns_same(self, tmp_path):
        dest = tmp_path / "photo.jpg"
        assert resolve_collision(dest) == dest

    def test_existing_file_gets_suffix(self, tmp_path):
        dest = tmp_path / "photo.jpg"
        dest.write_bytes(b"x")
        result = resolve_collision(dest)
        assert result.name == "photo_2.jpg"

    def test_multiple_collisions_increments(self, tmp_path):
        for name in ("photo.jpg", "photo_2.jpg", "photo_3.jpg"):
            (tmp_path / name).write_bytes(b"x")
        result = resolve_collision(tmp_path / "photo.jpg")
        assert result.name == "photo_4.jpg"


class TestCopyFile:
    def test_copies_file_to_dest(self, tmp_path):
        src = tmp_path / "src" / "IMG.jpg"
        src.parent.mkdir()
        src.write_bytes(b"data")
        dest_root = tmp_path / "dest"

        result = copy_file(
            row_id=1,
            source_path=str(src),
            dest_path="2024/20240601_jdrive/IMG.jpg",
            dest_root=dest_root,
        )

        assert result.ok
        assert (dest_root / "2024/20240601_jdrive/IMG.jpg").read_bytes() == b"data"
        assert not result.collision_resolved

    def test_creates_intermediate_directories(self, tmp_path):
        src = tmp_path / "a.jpg"
        src.write_bytes(b"x")
        dest_root = tmp_path / "dest"

        result = copy_file(1, str(src), "deep/nested/path/a.jpg", dest_root)

        assert result.ok
        assert (dest_root / "deep/nested/path/a.jpg").exists()

    def test_resolves_collision(self, tmp_path):
        src = tmp_path / "img.jpg"
        src.write_bytes(b"new")
        dest_root = tmp_path / "dest"
        existing = dest_root / "2024" / "img.jpg"
        existing.parent.mkdir(parents=True)
        existing.write_bytes(b"old")

        result = copy_file(1, str(src), "2024/img.jpg", dest_root)

        assert result.ok
        assert result.collision_resolved
        assert (dest_root / "2024" / "img_2.jpg").exists()
        assert existing.read_bytes() == b"old"  # original untouched

    def test_missing_source_returns_error(self, tmp_path):
        result = copy_file(1, str(tmp_path / "missing.jpg"), "2024/a.jpg", tmp_path / "dest")
        assert not result.ok
        assert "source not found" in result.error

    def test_dry_run_skips_copy(self, tmp_path):
        src = tmp_path / "img.jpg"
        src.write_bytes(b"x")
        dest_root = tmp_path / "dest"

        result = copy_file(1, str(src), "2024/img.jpg", dest_root, dry_run=True)

        assert result.ok
        assert not (dest_root / "2024" / "img.jpg").exists()

    def test_dry_run_reports_collision(self, tmp_path):
        src = tmp_path / "img.jpg"
        src.write_bytes(b"new")
        dest_root = tmp_path / "dest"
        existing = dest_root / "2024" / "img.jpg"
        existing.parent.mkdir(parents=True)
        existing.write_bytes(b"old")

        result = copy_file(1, str(src), "2024/img.jpg", dest_root, dry_run=True)

        assert result.ok
        assert result.collision_resolved
        assert not (dest_root / "2024" / "img_2.jpg").exists()  # nothing written
