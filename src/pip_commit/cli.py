"""Command-line entrypoint for pip-commit."""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

from pip_commit._version import __version__
from pip_commit.config import load_config
from pip_commit.freeze import (
    filter_freeze,
    git_add,
    git_repo_root,
    git_staged_files,
    in_virtualenv,
    looks_like_python_project,
    run_pip_freeze,
    write_if_changed,
)

# Exit codes
EXIT_OK = 0
EXIT_USER_DECLINED = 0  # declining is not an error
EXIT_ERROR = 1


def _build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="pip-commit",
        description="Refresh requirements.txt from the active environment.",
    )
    p.add_argument("--version", action="version", version=f"pip-commit {__version__}")
    p.add_argument(
        "-o",
        "--output",
        help="Path to write (default: requirements.txt or value from config).",
    )
    p.add_argument(
        "-e",
        "--exclude",
        action="append",
        default=None,
        metavar="NAME",
        help="Distribution name to drop from the output. May be repeated.",
    )
    p.add_argument(
        "--yes",
        "-y",
        action="store_true",
        help="Do not prompt; assume yes.",
    )
    p.add_argument(
        "--no-prompt",
        action="store_true",
        help="Alias for --yes (kept for clarity in hook configs).",
    )
    p.add_argument(
        "--allow-system",
        action="store_true",
        help="Allow running outside a virtual environment (not recommended).",
    )
    p.add_argument(
        "--no-stage",
        action="store_true",
        help="Do not run `git add` on the output file.",
    )
    p.add_argument(
        "--repo-root",
        type=Path,
        default=None,
        help="Override repo root detection (mostly for tests).",
    )
    p.add_argument(
        "filenames",
        nargs="*",
        help="Ignored. Accepted so pre-commit can pass staged file paths.",
    )
    return p


def _should_skip_env() -> str | None:
    """Return a reason string if env vars say we should skip, else None."""
    if os.environ.get("PIP_COMMIT_SKIP"):
        return "PIP_COMMIT_SKIP is set"
    return None


def _confirm(prompt_text: str) -> bool:
    """Prompt y/n on a TTY. Non-TTY assumes yes (frictionless in editor commits)."""
    if not sys.stdin.isatty():
        return True
    try:
        answer = input(prompt_text).strip().lower()
    except EOFError:
        return True
    if answer == "":
        return True  # default Y
    return answer in {"y", "yes"}


def main(argv: Sequence[str] | None = None) -> int:
    args = _build_parser().parse_args(argv)

    skip_reason = _should_skip_env()
    if skip_reason:
        print(f"pip-commit: skipping ({skip_reason}).", file=sys.stderr)
        return EXIT_OK

    repo_root = args.repo_root or git_repo_root(Path.cwd())
    if repo_root is None:
        print("pip-commit: not inside a git repository; nothing to do.", file=sys.stderr)
        return EXIT_OK

    staged = git_staged_files(repo_root)
    if not looks_like_python_project(repo_root, staged):
        # Don't surprise non-Python repos. Silent by design.
        return EXIT_OK

    overrides: dict = {}
    if args.output is not None:
        overrides["output"] = args.output
    if args.exclude is not None:
        overrides["exclude"] = args.exclude
    if args.allow_system:
        overrides["require_venv"] = False
    if args.yes or args.no_prompt:
        overrides["prompt"] = False

    cfg = load_config(repo_root, overrides=overrides)

    if cfg.require_venv and not in_virtualenv():
        print(
            "pip-commit: refusing to freeze a non-virtualenv interpreter "
            "(would capture system-wide packages).\n"
            "  Activate a venv, or set `require_venv = false` in [tool.pip-commit], "
            "or pass --allow-system.",
            file=sys.stderr,
        )
        return EXIT_ERROR

    if cfg.prompt and not _confirm("pip-commit: regenerate requirements.txt? [Y/n] "):
        print("pip-commit: skipped by user.", file=sys.stderr)
        return EXIT_USER_DECLINED

    try:
        frozen = run_pip_freeze()
    except subprocess.CalledProcessError as exc:
        print(
            f"pip-commit: `pip freeze` failed (exit {exc.returncode}).\n{exc.stderr}",
            file=sys.stderr,
        )
        return EXIT_ERROR
    except subprocess.TimeoutExpired:
        print("pip-commit: `pip freeze` timed out.", file=sys.stderr)
        return EXIT_ERROR
    except FileNotFoundError:
        print("pip-commit: could not invoke Python/pip.", file=sys.stderr)
        return EXIT_ERROR

    content = filter_freeze(frozen, cfg.exclude)
    output_path = (repo_root / cfg.output).resolve()

    # Safety: refuse to write outside the repo root.
    try:
        output_path.relative_to(repo_root.resolve())
    except ValueError:
        print(
            f"pip-commit: refusing to write outside repo root: {output_path}",
            file=sys.stderr,
        )
        return EXIT_ERROR

    wrote = write_if_changed(output_path, content)
    rel = output_path.relative_to(repo_root.resolve())

    if not wrote:
        print(f"pip-commit: {rel} is already up to date.")
        return EXIT_OK

    if not args.no_stage:
        try:
            git_add(output_path, repo_root)
        except subprocess.CalledProcessError as exc:
            print(
                f"pip-commit: failed to `git add {rel}` ({exc.returncode}).\n{exc.stderr}",
                file=sys.stderr,
            )
            return EXIT_ERROR

    print(f"pip-commit: updated and staged {rel}.")
    return EXIT_OK


if __name__ == "__main__":  # pragma: no cover
    sys.exit(main())
