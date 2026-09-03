"""Run the complete cross-platform SP2 setup process."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from installation.lm_studio_setup import _find_lms, _setup_lm_studio  # noqa: E402
from installation.backend_setup import (  # noqa: E402
    _print_future_backend_command,
    _start_backend,
)
from installation.setup_helpers import (  # noqa: E402
    SetupError,
    _check_python_version,
    _check_system_memory,
    _create_venv,
    _initialize_storage,
    _install_requirements,
    _ok,
    _print_next_steps,
)


def _build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description=(
            "Install SP2, download its default LM Studio models, load the "
            "models, initialize local storage, and start the backend."
        )
    )
    parser.add_argument(
        "--skip-model-setup",
        action="store_true",
        help="Install SP2 without downloading or loading LM Studio models.",
    )
    return parser


def main() -> int:
    args = _build_parser().parse_args()
    print("SP2 setup")
    print(f"Repo root: {REPO_ROOT}")

    try:
        _check_python_version()
        _check_system_memory()
        lms_path = None if args.skip_model_setup else _find_lms()
        python_path = _create_venv()
        _install_requirements(python_path)
        _initialize_storage(python_path)

        if lms_path is not None:
            _setup_lm_studio(lms_path)

        _start_backend(python_path)
        _print_next_steps(
            python_path,
            model_setup_complete=lms_path is not None,
        )
        _print_future_backend_command(python_path)
    except SetupError as exc:
        print()
        print(f"[error] {exc}")
        return 1
    except KeyboardInterrupt:
        print()
        print("[error] Setup interrupted")
        return 130

    print()
    _ok("SP2 setup finished")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
