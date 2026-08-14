"""Command-line entry point for clearing local student storage."""

import argparse

from storage.database.clearOut import clear_out_student_storage


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Clear installed packs and recreate the local student SQLite and "
            "LanceDB stores."
        ),
    )
    parser.add_argument(
        "--yes",
        action="store_true",
        help="Perform the clear-out. Without this flag, only print the plan.",
    )
    return parser


def main() -> None:
    args = _build_parser().parse_args()
    dry_run = not args.yes
    if dry_run:
        print("Dry run only. Re-run with --yes to clear and recreate student storage.")

    clear_out_student_storage(dry_run=dry_run)


if __name__ == "__main__":
    main()
