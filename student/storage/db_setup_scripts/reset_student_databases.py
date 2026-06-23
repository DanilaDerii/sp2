"""Reset student development databases after schema changes."""

import argparse
import shutil
from pathlib import Path

from create_lancedb_db import LANCE_DIR, create_lancedb_db
from create_sqlite_db import SQLITE_DB_PATH, create_sqlite_db


SQLITE_SIDE_FILES = (
    Path(f"{SQLITE_DB_PATH}-shm"),
    Path(f"{SQLITE_DB_PATH}-wal"),
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Delete and recreate the local student SQLite and LanceDB stores. "
            "Use this only for development resets after schema changes."
        ),
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Actually delete and recreate databases. Without this, only prints the plan.",
    )
    parser.add_argument(
        "--sqlite-only",
        action="store_true",
        help="Reset only the SQLite database.",
    )
    parser.add_argument(
        "--lancedb-only",
        action="store_true",
        help="Reset only the LanceDB database.",
    )
    return parser


def _validate_args(args: argparse.Namespace) -> None:
    if args.sqlite_only and args.lancedb_only:
        raise ValueError("Choose at most one of --sqlite-only or --lancedb-only")


def _reset_sqlite(*, dry_run: bool) -> None:
    paths = (SQLITE_DB_PATH, *SQLITE_SIDE_FILES)
    for path in paths:
        if dry_run:
            print(f"Would delete SQLite file if present: {path}")
        elif path.exists():
            path.unlink()
            print(f"Deleted SQLite file: {path}")

    if dry_run:
        print(f"Would recreate SQLite database: {SQLITE_DB_PATH}")
    else:
        create_sqlite_db()


def _reset_lancedb(*, dry_run: bool) -> None:
    if dry_run:
        print(f"Would delete LanceDB directory if present: {LANCE_DIR}")
        print("Would recreate LanceDB schema with project default vector dimension")
        return

    if LANCE_DIR.exists():
        shutil.rmtree(LANCE_DIR)
        print(f"Deleted LanceDB directory: {LANCE_DIR}")

    create_lancedb_db()


def main() -> None:
    args = _build_parser().parse_args()
    _validate_args(args)

    reset_sqlite = not args.lancedb_only
    reset_lancedb = not args.sqlite_only
    dry_run = not args.yes

    if dry_run:
        print("Dry run only. Re-run with --yes to delete and recreate databases.")

    if reset_sqlite:
        _reset_sqlite(dry_run=dry_run)

    if reset_lancedb:
        _reset_lancedb(dry_run=dry_run)


if __name__ == "__main__":
    main()
