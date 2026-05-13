from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from pip_commit import cli


@pytest.fixture
def python_repo(git_repo: Path) -> Path:
    (git_repo / "pyproject.toml").write_text('[project]\nname = "x"\nversion = "0"\n')
    return git_repo


def _fake_freeze(content: str):
    def _run(*_a, **_kw):
        return content

    return _run


def test_skip_when_env_set(monkeypatch, capsys, python_repo: Path):
    monkeypatch.setenv("PIP_COMMIT_SKIP", "1")
    monkeypatch.chdir(python_repo)
    assert cli.main([]) == 0
    assert not (python_repo / "requirements.txt").exists()


def test_skip_when_not_in_git(monkeypatch, tmp_path: Path):
    monkeypatch.delenv("PIP_COMMIT_SKIP", raising=False)
    monkeypatch.chdir(tmp_path)
    # cwd is not a git repo
    assert cli.main(["--repo-root", str(tmp_path)]) == 0 or cli.main([]) == 0


def test_skip_non_python_repo(monkeypatch, git_repo: Path):
    monkeypatch.delenv("PIP_COMMIT_SKIP", raising=False)
    monkeypatch.chdir(git_repo)
    (git_repo / "README.md").write_text("# not python")
    assert cli.main([]) == 0
    assert not (git_repo / "requirements.txt").exists()


def test_refuses_outside_venv(monkeypatch, python_repo: Path):
    monkeypatch.delenv("PIP_COMMIT_SKIP", raising=False)
    monkeypatch.chdir(python_repo)
    monkeypatch.setattr(cli, "in_virtualenv", lambda: False)
    rc = cli.main(["--yes"])
    assert rc == 1


def test_happy_path_writes_and_stages(monkeypatch, python_repo: Path):
    monkeypatch.delenv("PIP_COMMIT_SKIP", raising=False)
    monkeypatch.chdir(python_repo)
    monkeypatch.setattr(cli, "in_virtualenv", lambda: True)
    monkeypatch.setattr(cli, "run_pip_freeze", _fake_freeze("requests==2.31.0\nibapi==9.81\n"))

    rc = cli.main(["--yes", "--exclude", "ibapi"])
    assert rc == 0

    out = (python_repo / "requirements.txt").read_text()
    assert "requests==2.31.0" in out
    assert "ibapi" not in out.lower()

    staged = subprocess.run(
        ["git", "-C", str(python_repo), "diff", "--cached", "--name-only"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert "requirements.txt" in staged


def test_idempotent_no_stage_when_unchanged(monkeypatch, python_repo: Path, capsys):
    monkeypatch.delenv("PIP_COMMIT_SKIP", raising=False)
    monkeypatch.chdir(python_repo)
    monkeypatch.setattr(cli, "in_virtualenv", lambda: True)
    monkeypatch.setattr(cli, "run_pip_freeze", _fake_freeze("a==1\n"))

    assert cli.main(["--yes"]) == 0
    assert cli.main(["--yes"]) == 0
    captured = capsys.readouterr().out
    assert "already up to date" in captured


def test_pip_freeze_failure_propagates(monkeypatch, python_repo: Path):
    monkeypatch.delenv("PIP_COMMIT_SKIP", raising=False)
    monkeypatch.chdir(python_repo)
    monkeypatch.setattr(cli, "in_virtualenv", lambda: True)

    def boom(*_a, **_kw):
        raise subprocess.CalledProcessError(2, ["pip", "freeze"], stderr="nope")

    monkeypatch.setattr(cli, "run_pip_freeze", boom)
    assert cli.main(["--yes"]) == 1


def test_no_stage_flag(monkeypatch, python_repo: Path):
    monkeypatch.delenv("PIP_COMMIT_SKIP", raising=False)
    monkeypatch.chdir(python_repo)
    monkeypatch.setattr(cli, "in_virtualenv", lambda: True)
    monkeypatch.setattr(cli, "run_pip_freeze", _fake_freeze("a==1\n"))

    assert cli.main(["--yes", "--no-stage"]) == 0
    staged = subprocess.run(
        ["git", "-C", str(python_repo), "diff", "--cached", "--name-only"],
        capture_output=True,
        text=True,
        check=True,
    ).stdout
    assert "requirements.txt" not in staged


def test_config_from_pyproject_used(monkeypatch, python_repo: Path):
    (python_repo / "pyproject.toml").write_text(
        '[project]\nname="x"\nversion="0"\n'
        '[tool.pip-commit]\noutput = "reqs.txt"\nexclude = ["ibapi"]\nprompt = false\n'
    )
    monkeypatch.delenv("PIP_COMMIT_SKIP", raising=False)
    monkeypatch.chdir(python_repo)
    monkeypatch.setattr(cli, "in_virtualenv", lambda: True)
    monkeypatch.setattr(cli, "run_pip_freeze", _fake_freeze("ibapi==1\nreq==2\n"))

    assert cli.main([]) == 0
    out = (python_repo / "reqs.txt").read_text()
    assert "req==2" in out
    assert "ibapi" not in out


def test_refuses_output_outside_repo(monkeypatch, python_repo: Path, tmp_path_factory):
    monkeypatch.delenv("PIP_COMMIT_SKIP", raising=False)
    monkeypatch.chdir(python_repo)
    monkeypatch.setattr(cli, "in_virtualenv", lambda: True)
    monkeypatch.setattr(cli, "run_pip_freeze", _fake_freeze("a==1\n"))

    elsewhere = tmp_path_factory.mktemp("outside")
    escape = elsewhere / "escape.txt"
    rc = cli.main(["--yes", "--output", str(escape)])
    assert rc == 1
    assert not escape.exists()


def test_prompt_decline(monkeypatch, python_repo: Path):
    monkeypatch.delenv("PIP_COMMIT_SKIP", raising=False)
    monkeypatch.chdir(python_repo)
    monkeypatch.setattr(cli, "in_virtualenv", lambda: True)
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _p="": "n")

    called = {"freeze": False}

    def fake(*_a, **_kw):
        called["freeze"] = True
        return ""

    monkeypatch.setattr(cli, "run_pip_freeze", fake)

    rc = cli.main([])
    assert rc == 0
    assert called["freeze"] is False
    assert not (python_repo / "requirements.txt").exists()


def test_prompt_accept_default(monkeypatch, python_repo: Path):
    monkeypatch.delenv("PIP_COMMIT_SKIP", raising=False)
    monkeypatch.chdir(python_repo)
    monkeypatch.setattr(cli, "in_virtualenv", lambda: True)
    monkeypatch.setattr(cli.sys.stdin, "isatty", lambda: True)
    monkeypatch.setattr("builtins.input", lambda _p="": "")  # bare Enter => Y
    monkeypatch.setattr(cli, "run_pip_freeze", _fake_freeze("a==1\n"))

    assert cli.main([]) == 0
    assert (python_repo / "requirements.txt").exists()


def test_version_flag(capsys):
    with pytest.raises(SystemExit) as exc:
        cli.main(["--version"])
    assert exc.value.code == 0
    out = capsys.readouterr().out
    assert "pip-commit" in out
