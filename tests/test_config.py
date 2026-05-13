from __future__ import annotations

from pathlib import Path

from pip_commit.config import Config, load_config


def test_defaults_when_no_config(tmp_path: Path):
    cfg = load_config(tmp_path)
    assert cfg == Config()


def test_reads_pyproject(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text(
        "[tool.pip-commit]\n"
        'output = "reqs/all.txt"\n'
        'exclude = ["ibapi", "foo"]\n'
        "require_venv = false\n"
        "prompt = false\n"
    )
    cfg = load_config(tmp_path)
    assert cfg.output == "reqs/all.txt"
    assert cfg.exclude == ("ibapi", "foo")
    assert cfg.require_venv is False
    assert cfg.prompt is False


def test_standalone_overrides_pyproject(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text('[tool.pip-commit]\noutput = "a.txt"\n')
    (tmp_path / ".pip-commit.toml").write_text('output = "b.txt"\n')
    cfg = load_config(tmp_path)
    assert cfg.output == "b.txt"


def test_cli_overrides_win(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text(
        '[tool.pip-commit]\noutput = "a.txt"\nexclude = ["x"]\n'
    )
    cfg = load_config(tmp_path, overrides={"output": "cli.txt", "exclude": ["y"]})
    assert cfg.output == "cli.txt"
    assert cfg.exclude == ("y",)


def test_malformed_pyproject_is_ignored(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text("not [valid toml")
    cfg = load_config(tmp_path)
    assert cfg == Config()


def test_none_overrides_are_ignored(tmp_path: Path):
    (tmp_path / "pyproject.toml").write_text('[tool.pip-commit]\noutput = "kept.txt"\n')
    cfg = load_config(tmp_path, overrides={"output": None, "exclude": None})
    assert cfg.output == "kept.txt"
