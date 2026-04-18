"""Copy a single MOVE row from source to destination, handling collisions."""

from __future__ import annotations

import shutil
from dataclasses import dataclass
from pathlib import Path
from typing import Optional


@dataclass
class CopyResult:
    row_id: int
    source_path: str
    dest_path: str          # actual path used (may differ if collision resolved)
    collision_resolved: bool
    error: Optional[str]    # None on success

    @property
    def ok(self) -> bool:
        return self.error is None


def resolve_collision(dest: Path) -> Path:
    """Append _2, _3, … to the stem until the path is free."""
    if not dest.exists():
        return dest
    stem = dest.stem
    suffix = dest.suffix
    parent = dest.parent
    counter = 2
    while True:
        candidate = parent / f"{stem}_{counter}{suffix}"
        if not candidate.exists():
            return candidate
        counter += 1


def copy_file(
    row_id: int,
    source_path: str,
    dest_path: str,
    dest_root: Path,
    dry_run: bool = False,
) -> CopyResult:
    """
    Copy source_path → dest_root / dest_path.

    Returns a CopyResult indicating success or the error message.
    """
    src = Path(source_path)
    dest = dest_root / dest_path

    if not src.exists():
        return CopyResult(
            row_id=row_id,
            source_path=source_path,
            dest_path=str(dest),
            collision_resolved=False,
            error=f"source not found: {src}",
        )

    resolved = resolve_collision(dest)
    collision = resolved != dest

    if dry_run:
        return CopyResult(
            row_id=row_id,
            source_path=source_path,
            dest_path=str(resolved),
            collision_resolved=collision,
            error=None,
        )

    try:
        resolved.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(src, resolved)
    except OSError as exc:
        return CopyResult(
            row_id=row_id,
            source_path=source_path,
            dest_path=str(resolved),
            collision_resolved=collision,
            error=str(exc),
        )

    return CopyResult(
        row_id=row_id,
        source_path=source_path,
        dest_path=str(resolved),
        collision_resolved=collision,
        error=None,
    )
