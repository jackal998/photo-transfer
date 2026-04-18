"""migrate.py — Execute pending MOVE actions from migration_manifest.sqlite.

Reads rows produced by photo-manager's scan.py and copies each MOVE file
to the destination root.  Updates executed=1 (done) or executed=2 (failed)
after each file so the run is resumable.

Usage examples:
  # Copy everything to NAS (SMB path)
  python migrate.py \\
    --manifest migration_manifest.sqlite \\
    --dest-root "\\\\LinXiaoYun\\home\\Photos"

  # Preview only — no files copied, no DB writes
  python migrate.py --manifest migration_manifest.sqlite \\
    --dest-root "\\\\LinXiaoYun\\home\\Photos" --dry-run

  # Test with first 50 files only
  python migrate.py --manifest migration_manifest.sqlite \\
    --dest-root "\\\\LinXiaoYun\\home\\Photos" --limit 50
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

try:
    from tqdm import tqdm
    _TQDM = True
except ImportError:
    _TQDM = False


def _print_summary(counts: dict[str, int], dest_root: Path, dry_run: bool) -> None:
    total_move = sum(v for k, v in counts.items() if k.startswith("MOVE"))
    done = counts.get("MOVE.1", 0)
    failed = counts.get("MOVE.2", 0)
    pending = counts.get("MOVE.0", 0)
    keep = counts.get("KEEP.0", 0)
    skip = counts.get("SKIP.0", 0)
    review = counts.get("REVIEW_DUPLICATE.0", 0)
    undated = counts.get("UNDATED.0", 0)

    prefix = "DRY-RUN " if dry_run else ""
    print(f"\n── {prefix}Migration Summary ────────────────────────────")
    print(f"  Manifest MOVE total  : {total_move:>7,}")
    print(f"  Copied this run      : {done:>7,}")
    print(f"  Failed this run      : {failed:>7,}")
    print(f"  Still pending        : {pending:>7,}")
    print(f"  ── Not copied (by design) ──────────────────────")
    print(f"  KEEP (iphone source) : {keep:>7,}")
    print(f"  SKIP (duplicates)    : {skip:>7,}")
    print(f"  REVIEW_DUPLICATE     : {review:>7,}  ← needs manual triage")
    print(f"  UNDATED              : {undated:>7,}  ← no EXIF date")
    print(f"  Destination root     : {dest_root}")
    print("────────────────────────────────────────────────────\n")


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Execute MOVE actions from migration_manifest.sqlite"
    )
    parser.add_argument(
        "--manifest",
        type=Path,
        default=Path("migration_manifest.sqlite"),
        help="Path to manifest (default: migration_manifest.sqlite)",
    )
    parser.add_argument(
        "--dest-root",
        type=Path,
        required=True,
        metavar="PATH",
        help=r"Destination root, e.g. \\LinXiaoYun\home\Photos",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print what would be copied without writing any files or updating the DB",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=None,
        metavar="N",
        help="Copy at most N files (useful for testing a batch)",
    )
    args = parser.parse_args()

    from transfer.db import open_db, pending_moves, mark_done, mark_failed, summary
    from transfer.executor import copy_file

    conn = open_db(args.manifest)
    rows = pending_moves(conn)

    if args.limit is not None:
        rows = rows[: args.limit]

    if not rows:
        print("No pending MOVE rows found — nothing to do.")
        _print_summary(summary(conn), args.dest_root, args.dry_run)
        return 0

    print(
        f"{'[DRY-RUN] ' if args.dry_run else ''}"
        f"Copying {len(rows):,} file(s) → {args.dest_root}"
    )

    done = failed = collisions = 0
    iterable = tqdm(rows, desc="Copying", unit="file") if _TQDM else rows

    for row in iterable:
        result = copy_file(
            row_id=row.id,
            source_path=row.source_path,
            dest_path=row.dest_path,
            dest_root=args.dest_root,
            dry_run=args.dry_run,
        )

        if result.ok:
            done += 1
            if result.collision_resolved:
                collisions += 1
            if not args.dry_run:
                mark_done(conn, row.id)
        else:
            failed += 1
            print(f"\n  ERROR {result.source_path}: {result.error}", file=sys.stderr)
            if not args.dry_run:
                mark_failed(conn, row.id)

    print(f"\n  Copied: {done:,}  |  Failed: {failed:,}  |  Collisions resolved: {collisions:,}")
    _print_summary(summary(conn), args.dest_root, args.dry_run)

    return 1 if failed else 0


if __name__ == "__main__":
    sys.exit(main())
