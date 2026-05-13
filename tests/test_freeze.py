from __future__ import annotations

import os
from importlib.metadata import Distribution
from pathlib import Path
from typing import Any, cast

import pytest

from pip_commit.freeze import (
    filter_freeze,
    freeze_installed,
    git_repo_root,
    git_staged_files,
    looks_like_python_project,
    write_if_changed,
)


class _FakeDist:
    """Minimal duck-typed stand-in for importlib.metadata.Distribution."""

    def __init__(self, name: str, version: str, direct_url: str | None = None) -> None:
        self.metadata: dict[str, str] = {"Name": name}
        self.version = version
        self._direct_url = direct_url

    def read_text(self, name: str) -> str | None:
        if name == "direct_url.json":
            return self._direct_url
        return None


def _dist(name: str, version: str = "1.0.0", direct_url: str | None = None) -> Distribution:
    return cast(Distribution, _FakeDist(name, version, direct_url))


def test_filter_freeze_drops_excluded_case_insensitive():
    frozen = "requests==2.31.0\nIBapi==9.81\nnumpy==1.26.0\n"
    out = filter_freeze(frozen, ["ibapi"])
    assert "ibapi" not in out.lower()
    assert "requests==2.31.0" in out
    assert "numpy==1.26.0" in out
    assert out.endswith("\n")


def test_filter_freeze_no_excludes_normalizes_trailing_newline():
    assert filter_freeze("a==1\nb==2", []) == "a==1\nb==2\n"


def test_filter_freeze_handles_url_and_marker_lines():
    frozen = (
        "pkg @ git+https://example.com/x.git\nother==1.0; python_version >= '3.9'\nibapi==9.81\n"
    )
    out = filter_freeze(frozen, ["IBAPI"])
    assert "ibapi" not in out.lower()
    assert "pkg @ git" in out
    assert "other==1.0" in out


def test_filter_freeze_empty_input():
    assert filter_freeze("", ["x"]) == ""


def test_write_if_changed_creates_file(tmp_path: Path):
    p = tmp_path / "requirements.txt"
    assert write_if_changed(p, "a==1\n") is True
    assert p.read_text() == "a==1\n"


def test_write_if_changed_skips_when_identical(tmp_path: Path):
    p = tmp_path / "requirements.txt"
    p.write_text("a==1\n")
    mtime_before = p.stat().st_mtime_ns
    assert write_if_changed(p, "a==1\n") is False
    assert p.stat().st_mtime_ns == mtime_before


def test_write_if_changed_creates_parents(tmp_path: Path):
    p = tmp_path / "nested" / "dir" / "requirements.txt"
    assert write_if_changed(p, "x==1\n") is True
    assert p.exists()


def test_git_repo_root(git_repo: Path):
    assert git_repo_root(git_repo) == git_repo
    sub = git_repo / "sub"
    sub.mkdir()
    assert git_repo_root(sub) == git_repo


def test_git_repo_root_outside_repo(tmp_path: Path):
    # tmp_path itself is not necessarily a repo
    assert git_repo_root(tmp_path) is None


def test_looks_like_python_project_pyproject(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text("[project]\nname='x'\n")
    assert looks_like_python_project(tmp_path)


def test_looks_like_python_project_requirements(tmp_path: Path):
    (tmp_path / "requirements.txt").write_text("")
    assert looks_like_python_project(tmp_path)


def test_looks_like_python_project_staged_py(tmp_path: Path):
    assert looks_like_python_project(tmp_path, ["main.py"])
    assert not looks_like_python_project(tmp_path, ["README.md"])


def test_looks_like_python_project_negative(tmp_path: Path):
    (tmp_path / "README.md").write_text("# hi")
    assert not looks_like_python_project(tmp_path)


def test_git_staged_files_empty(git_repo: Path):
    assert git_staged_files(git_repo) == []


def test_git_staged_files_after_add(git_repo: Path):
    import subprocess

    (git_repo / "a.py").write_text("x=1\n")
    subprocess.run(["git", "-C", str(git_repo), "add", "a.py"], check=True)
    assert "a.py" in git_staged_files(git_repo)


# --- freeze_installed --------------------------------------------------------


def test_freeze_installed_basic_sorting():
    dists = [_dist("Charlie", "1.0"), _dist("alpha", "2.0"), _dist("Bravo", "0.1")]
    out = freeze_installed(dists)
    assert out.splitlines() == ["alpha==2.0", "Bravo==0.1", "Charlie==1.0"]


def test_freeze_installed_skips_editable():
    editable = '{"url": "file:///x", "dir_info": {"editable": true}}'
    dists = [_dist("regular", "1.0"), _dist("editable_pkg", "1.0", direct_url=editable)]
    out = freeze_installed(dists)
    assert "editable_pkg" not in out
    assert "regular==1.0" in out


def test_freeze_installed_direct_url_install():
    du = '{"url": "https://example.com/x.whl", "archive_info": {}}'
    dists = [_dist("urlpkg", "1.0", direct_url=du)]
    out = freeze_installed(dists)
    assert "urlpkg @ https://example.com/x.whl" in out


def test_freeze_installed_vcs_install_includes_commit():
    du = '{"url": "https://example.com/x.git", "vcs_info": {"vcs": "git", "commit_id": "abc123"}}'
    dists = [_dist("vcspkg", "1.0", direct_url=du)]
    out = freeze_installed(dists)
    assert "vcspkg @ git+https://example.com/x.git@abc123" in out


def test_freeze_installed_handles_garbage_direct_url():
    dists = [_dist("ok", "1.0", direct_url="not json at all")]
    out = freeze_installed(dists)
    # Falls back to the regular `name==version` line.
    assert out.strip() == "ok==1.0"


def test_freeze_installed_skips_unnamed():
    dists = [_dist("", "1.0"), _dist("real", "2.0")]
    out = freeze_installed(dists)
    assert out.strip() == "real==2.0"


def test_freeze_installed_empty():
    assert freeze_installed([]) == ""


# --- atomic write ------------------------------------------------------------


def test_write_if_changed_atomic_failure_preserves_original(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    p = tmp_path / "requirements.txt"
    p.write_text("original\n")

    def broken_replace(src: Any, dst: Any) -> None:
        raise OSError("simulated rename failure")

    monkeypatch.setattr(os, "replace", broken_replace)

    with pytest.raises(OSError, match="simulated"):
        write_if_changed(p, "new content\n")

    assert p.read_text() == "original\n"
    leftovers = [
        x.name
        for x in tmp_path.iterdir()
        if x.name.startswith(".requirements.txt.") and x.name.endswith(".tmp")
    ]
    assert leftovers == [], f"temp file leaked: {leftovers}"


def test_write_if_changed_atomic_no_partial_visible(tmp_path: Path):
    """The target either contains old or new content, never a partial write."""
    p = tmp_path / "requirements.txt"
    p.write_text("old\n")
    write_if_changed(p, "completely new and longer content\n")
    # We can't easily race this in a unit test, but we can at least assert the
    # final state matches and no temp files remain.
    assert p.read_text() == "completely new and longer content\n"
    leftovers = [x for x in tmp_path.iterdir() if x.name.startswith(".requirements.txt.")]
    assert leftovers == []
