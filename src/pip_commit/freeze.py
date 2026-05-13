"""Freezing and filtering logic. Pure functions, no I/O on real disk."""

from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from collections.abc import Iterable, Sequence
from pathlib import Path

# `name==version`, `name @ url`, `-e ...`, comments, etc.
_NAME_RE = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")


def in_virtualenv() -> bool:
    """True when running under any kind of isolated Python environment."""
    if os.environ.get("VIRTUAL_ENV") or os.environ.get("CONDA_PREFIX"):
        return True
    base = getattr(sys, "base_prefix", sys.prefix)
    return sys.prefix != base


def run_pip_freeze(python: str | None = None, timeout: float = 60.0) -> str:
    """Invoke `pip freeze` and return stdout. Raises CalledProcessError on failure."""
    py = python or sys.executable
    result = subprocess.run(
        [py, "-m", "pip", "freeze", "--exclude-editable"],
        check=True,
        capture_output=True,
        text=True,
        timeout=timeout,
    )
    return result.stdout


def _line_name(line: str) -> str | None:
    m = _NAME_RE.match(line)
    return m.group(1).lower() if m else None


def filter_freeze(frozen: str, exclude: Iterable[str]) -> str:
    """Strip excluded distribution names (case-insensitive) from `pip freeze` output."""
    drop = {name.strip().lower() for name in exclude if name.strip()}
    if not drop:
        return _normalize(frozen)

    kept = []
    for line in frozen.splitlines():
        name = _line_name(line)
        if name is not None and name in drop:
            continue
        kept.append(line)
    return _normalize("\n".join(kept))


def _normalize(text: str) -> str:
    """Strip trailing whitespace per line and ensure trailing newline."""
    lines = [ln.rstrip() for ln in text.splitlines()]
    while lines and not lines[-1]:
        lines.pop()
    return "\n".join(lines) + "\n" if lines else ""


def write_if_changed(path: Path, content: str) -> bool:
    """Write `content` to `path` only if different. Returns True if a write happened."""
    if path.exists():
        try:
            if path.read_text(encoding="utf-8") == content:
                return False
        except OSError:
            pass
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(content, encoding="utf-8")
    return True


def git_add(path: Path, repo_root: Path) -> None:
    """Stage `path` via git. Raises CalledProcessError on failure."""
    git = shutil.which("git") or "git"
    subprocess.run(
        [git, "add", "--", str(path)],
        check=True,
        cwd=repo_root,
        capture_output=True,
        text=True,
    )


def git_repo_root(start: Path) -> Path | None:
    """Return the git repo root containing `start`, or None if not a repo."""
    git = shutil.which("git") or "git"
    try:
        result = subprocess.run(
            [git, "rev-parse", "--show-toplevel"],
            check=True,
            cwd=start,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return None
    out = result.stdout.strip()
    return Path(out) if out else None


def looks_like_python_project(repo_root: Path, staged: Sequence[str] | None = None) -> bool:
    """Heuristic: is this repo a Python project we should manage requirements for?

    True if any of:
      - pyproject.toml, setup.py, setup.cfg, or an existing requirements*.txt exist
      - any staged file ends in .py
    """
    markers = ("pyproject.toml", "setup.py", "setup.cfg")
    for m in markers:
        if (repo_root / m).is_file():
            return True
    for req in repo_root.glob("requirements*.txt"):
        if req.is_file():
            return True
    return bool(staged) and any(p.endswith(".py") for p in staged)


def git_staged_files(repo_root: Path) -> list[str]:
    git = shutil.which("git") or "git"
    try:
        result = subprocess.run(
            [git, "diff", "--cached", "--name-only"],
            check=True,
            cwd=repo_root,
            capture_output=True,
            text=True,
        )
    except (subprocess.CalledProcessError, FileNotFoundError):
        return []
    return [ln for ln in result.stdout.splitlines() if ln]


__all__ = [
    "filter_freeze",
    "git_add",
    "git_repo_root",
    "git_staged_files",
    "in_virtualenv",
    "looks_like_python_project",
    "run_pip_freeze",
    "write_if_changed",
]
