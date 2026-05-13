"""Freezing and filtering logic. Pure functions, minimal I/O."""

from __future__ import annotations

import contextlib
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from collections.abc import Iterable, Sequence
from importlib.metadata import Distribution, distributions
from pathlib import Path
from typing import Any

# `name==version`, `name @ url`, `-e ...`, comments, etc.
_NAME_RE = re.compile(r"^\s*([A-Za-z0-9][A-Za-z0-9._-]*)")


def in_virtualenv() -> bool:
    """True when running under any kind of isolated Python environment."""
    if os.environ.get("VIRTUAL_ENV") or os.environ.get("CONDA_PREFIX"):
        return True
    base = getattr(sys, "base_prefix", sys.prefix)
    return sys.prefix != base


def _format_distribution(dist: Distribution) -> str | None:
    """Render one distribution in pip-freeze format, or None to skip.

    Mirrors `pip freeze --exclude-editable`:
      * editable installs (direct_url.json with dir_info.editable=True) are skipped
      * direct-URL installs render as `name @ url[@commit_id]`
      * regular installs render as `name==version`
    """
    name = dist.metadata["Name"]
    if not name:
        return None

    direct_url_text = dist.read_text("direct_url.json")
    if direct_url_text:
        try:
            du: dict[str, Any] = json.loads(direct_url_text)
        except json.JSONDecodeError:
            du = {}
        dir_info = du.get("dir_info")
        if isinstance(dir_info, dict) and dir_info.get("editable"):
            return None
        url = du.get("url", "")
        if isinstance(url, str) and url:
            vcs = du.get("vcs_info")
            if isinstance(vcs, dict):
                vcs_name = vcs.get("vcs", "")
                commit = vcs.get("commit_id", "")
                if isinstance(vcs_name, str) and vcs_name and not url.startswith(f"{vcs_name}+"):
                    url = f"{vcs_name}+{url}"
                if isinstance(commit, str) and commit:
                    url = f"{url}@{commit}"
            return f"{name} @ {url}"

    return f"{name}=={dist.version}"


def freeze_installed(dists: Iterable[Distribution] | None = None) -> str:
    """Return pip-freeze-equivalent output from installed distribution metadata.

    Equivalent to `pip freeze --exclude-editable` without spawning a subprocess.
    Pass `dists` to inject an iterable of distributions (used by tests).
    """
    src = distributions() if dists is None else dists
    keyed: list[tuple[str, str]] = []
    for dist in src:
        rendered = _format_distribution(dist)
        if rendered is None:
            continue
        match = _NAME_RE.match(rendered)
        sort_key = match.group(1).lower() if match else rendered.lower()
        keyed.append((sort_key, rendered))
    keyed.sort(key=lambda item: item[0])
    lines = [line for _, line in keyed]
    return "\n".join(lines) + ("\n" if lines else "")


def _line_name(line: str) -> str | None:
    m = _NAME_RE.match(line)
    return m.group(1).lower() if m else None


def filter_freeze(frozen: str, exclude: Iterable[str]) -> str:
    """Strip excluded distribution names (case-insensitive) from freeze output."""
    drop = {name.strip().lower() for name in exclude if name.strip()}
    if not drop:
        return _normalize(frozen)

    kept: list[str] = []
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
    """Atomically write `content` to `path` only if different.

    Atomicity: writes to a temp file in the same directory, then `os.replace`s
    it into position. A crash or `KeyboardInterrupt` mid-write cannot leave the
    target file half-written.

    Returns True if a write happened.
    """
    if path.exists():
        try:
            if path.read_text(encoding="utf-8") == content:
                return False
        except OSError:
            pass

    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp_str = tempfile.mkstemp(prefix=f".{path.name}.", suffix=".tmp", dir=path.parent)
    tmp_path = Path(tmp_str)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="") as fh:
            fh.write(content)
            fh.flush()
            # fsync unavailable on some filesystems (e.g. some tmpfs); not fatal.
            with contextlib.suppress(OSError):
                os.fsync(fh.fileno())
        os.replace(tmp_path, path)
    except BaseException:
        with contextlib.suppress(OSError):
            tmp_path.unlink()
        raise
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
    """Heuristic: is this a Python project we should manage requirements for?"""
    markers = ("pyproject.toml", "setup.py", "setup.cfg")
    for m in markers:
        if (repo_root / m).is_file():
            return True
    for req in repo_root.glob("requirements*.txt"):
        if req.is_file():
            return True
    if staged is None:
        return False
    return any(p.endswith(".py") for p in staged)


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
    "freeze_installed",
    "git_add",
    "git_repo_root",
    "git_staged_files",
    "in_virtualenv",
    "looks_like_python_project",
    "write_if_changed",
]
