from __future__ import annotations

from pathlib import Path

from pip_commit.freeze import (
    filter_freeze,
    git_repo_root,
    git_staged_files,
    looks_like_python_project,
    write_if_changed,
)


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
